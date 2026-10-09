"""Detection rules. Each rule reads the whole log and returns findings in one shared shape.

The rules always run on the whole log; callers filter findings by time afterwards. The new-country
rule needs each user's history, so cutting the log first would make every user look new.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd

from login_investigator.loader import TIMESTAMP_FORMAT, account_key, parse_window, to_records

# --- Thresholds. Each comment is the reason, written to be quoted. ---
# These are assumptions tuned to this synthetic dataset, not general facts about attackers. A real
# deployment would set them from its own baseline of normal activity.

# We assume an hour is long enough to catch an automated tool and short enough that, in this
# dataset, a busy office's ordinary typos never add up.
ATTACK_WINDOW = timedelta(minutes=60)

# In this dataset, staff mistype a password at most 4 times in a day, so we assume 20 failures on
# one account within an hour is automated guessing.
BRUTE_FORCE_MIN_FAILURES = 20

# In this dataset, the busiest office address sees at most 3 people mistype within an hour, so we
# assume 10 accounts failing from one address within an hour is a list being worked through.
SPRAYING_MIN_ACCOUNTS = 10

# In this dataset, staff who mistype succeed after 1 or 2 tries, so we assume a success after 10 or
# more failures from the same address in the hour before means the password was guessed.
SUCCESS_AFTER_MIN_FAILURES = 10

# We assume 5 earlier sign-ins are enough to establish a user's usual country; with fewer, the rule
# does not judge.
NEW_COUNTRY_MIN_HISTORY = 5

# We assume flagged activity separated by a pause longer than 30 minutes is two separate incidents.
INCIDENT_GAP = timedelta(minutes=30)

# A finding carries at most this many evidence rows; the counts always cover every event.
MAX_EVIDENCE_ROWS = 20

BRUTE_FORCE = "brute_force"
PASSWORD_SPRAYING = "password_spraying"
SUCCESS_AFTER_FAILURES = "success_after_failures"
NEW_COUNTRY = "new_country"


@dataclass(frozen=True)
class Finding:
    """One suspicious pattern. The same shape for every rule."""

    rule: str
    summary: str
    ips: tuple[str, ...]
    users: tuple[str, ...]
    event_count: int
    failure_count: int
    success_count: int
    first_seen: pd.Timestamp
    last_seen: pd.Timestamp
    evidence: tuple[dict, ...]  # raw log rows: the first and last events when there are many

    def to_dict(self) -> dict:
        """Plain data, ready for JSON (the agent tool) or a table (the Alerts screen)."""
        return {
            "rule": self.rule,
            "summary": self.summary,
            "ips": list(self.ips),
            "users": list(self.users),
            "event_count": self.event_count,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "first_seen": self.first_seen.strftime(TIMESTAMP_FORMAT),
            "last_seen": self.last_seen.strftime(TIMESTAMP_FORMAT),
            "evidence": list(self.evidence),
            "evidence_shown": len(self.evidence),
        }


def _finding(rule: str, summary: str, rows: pd.DataFrame) -> Finding:
    rows = rows.sort_values("timestamp_utc", kind="stable")
    if len(rows) > MAX_EVIDENCE_ROWS:
        half = MAX_EVIDENCE_ROWS // 2
        evidence_rows = pd.concat([rows.head(half), rows.tail(MAX_EVIDENCE_ROWS - half)])
    else:
        evidence_rows = rows
    return Finding(
        rule=rule,
        summary=summary,
        ips=tuple(sorted(rows["source_ip"].unique())),
        users=tuple(sorted(rows["username"].unique())),
        event_count=len(rows),
        failure_count=int((rows["outcome"] == "failure").sum()),
        success_count=int((rows["outcome"] == "success").sum()),
        first_seen=rows["timestamp_utc"].iloc[0],
        last_seen=rows["timestamp_utc"].iloc[-1],
        evidence=tuple(to_records(evidence_rows)),
    )


def _failures(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["outcome"] == "failure"].sort_values("timestamp_utc", kind="stable")


def _flagged_runs(rows: pd.DataFrame, qualifies) -> list[pd.DataFrame]:
    """Mark every row inside a one-hour window that qualifies, then split the marked rows into
    runs wherever the pause exceeds INCIDENT_GAP. `rows` must be sorted by time."""
    times = rows["timestamp_utc"].dt.tz_localize(None).to_numpy()  # plain UTC datetime64
    window_ends = np.searchsorted(times, times + np.timedelta64(ATTACK_WINDOW), side="right")
    marked = np.zeros(len(rows), dtype=bool)
    for start, end in enumerate(window_ends):
        if qualifies(rows.iloc[start:end]):
            marked[start:end] = True
    flagged = rows[marked]
    if flagged.empty:
        return []
    new_run = flagged["timestamp_utc"].diff() > INCIDENT_GAP
    return [run for _, run in flagged.groupby(new_run.cumsum())]


def brute_force(df: pd.DataFrame) -> list[Finding]:
    """Many failed passwords on one account from one IP within an hour."""
    findings = []
    failures = _failures(df)
    keys = [failures["source_ip"], account_key(failures["username"])]
    for (ip, user), rows in failures.groupby(keys, sort=True):
        runs = _flagged_runs(rows, lambda w: len(w) >= BRUTE_FORCE_MIN_FAILURES)
        for run in runs:
            findings.append(_finding(
                BRUTE_FORCE,
                f"{len(run)} failed sign-ins on {user} from {ip}",
                run,
            ))
    return findings


def password_spraying(df: pd.DataFrame) -> list[Finding]:
    """One IP failing against many different accounts within an hour."""
    findings = []
    for ip, rows in _failures(df).groupby("source_ip", sort=True):
        runs = _flagged_runs(
            rows, lambda w: account_key(w["username"]).nunique() >= SPRAYING_MIN_ACCOUNTS
        )
        for run in runs:
            findings.append(_finding(
                PASSWORD_SPRAYING,
                f"{ip} failed on {account_key(run['username']).nunique()} accounts "
                f"in {len(run)} attempts",
                run,
            ))
    return findings


def success_after_failures(df: pd.DataFrame) -> list[Finding]:
    """A successful sign-in from the same IP and account soon after many failures."""
    findings = []
    ordered = df.sort_values("timestamp_utc", kind="stable")
    keys = [ordered["source_ip"], account_key(ordered["username"])]
    for (ip, user), rows in ordered.groupby(keys, sort=True):
        failures = rows[rows["outcome"] == "failure"]
        for index in rows.index[rows["outcome"] == "success"]:
            moment = rows.at[index, "timestamp_utc"]
            before = failures[(failures["timestamp_utc"] < moment)
                              & (failures["timestamp_utc"] >= moment - ATTACK_WINDOW)]
            if len(before) >= SUCCESS_AFTER_MIN_FAILURES:
                findings.append(_finding(
                    SUCCESS_AFTER_FAILURES,
                    f"{user} signed in from {ip} after {len(before)} failures "
                    f"in the hour before",
                    pd.concat([before, rows.loc[[index]]]),
                ))
    return findings


def new_country(df: pd.DataFrame) -> list[Finding]:
    """A successful sign-in from a country the user has never signed in from before."""
    findings = []
    successes = df[df["outcome"] == "success"].sort_values("timestamp_utc", kind="stable")
    for user, rows in successes.groupby(account_key(successes["username"]), sort=True):
        seen: dict[str, int] = {}
        history = 0
        for position in range(len(rows)):
            country = rows["country"].iloc[position]
            if country not in seen and history >= NEW_COUNTRY_MIN_HISTORY:
                usual = ", ".join(sorted(seen))
                findings.append(_finding(
                    NEW_COUNTRY,
                    f"{user} signed in from {country} for the first time; "
                    f"{history} earlier sign-ins were from {usual}",
                    rows.iloc[[position]],
                ))
            seen[country] = seen.get(country, 0) + 1
            history += 1
    return findings


RULES = (brute_force, password_spraying, success_after_failures, new_country)


def detect_all(df: pd.DataFrame, start=None, end=None) -> list[Finding]:
    """Run every rule on the whole log, then keep findings that overlap [start, end)."""
    start, end = parse_window(start, end)
    findings = [f for rule in RULES for f in rule(df)]
    if start is not None:
        findings = [f for f in findings if f.last_seen >= start]
    if end is not None:
        findings = [f for f in findings if f.first_seen < end]
    return sorted(findings, key=lambda f: (f.first_seen, f.rule))
