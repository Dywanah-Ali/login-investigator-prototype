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

# --- Thresholds. The reason for each one is in RULE_GUIDE and GENERAL_ASSUMPTIONS below, written
# to be quoted; the Alerts screen shows the same text. ---

ATTACK_WINDOW = timedelta(minutes=60)
BRUTE_FORCE_MIN_FAILURES = 20
SPRAYING_MIN_ACCOUNTS = 10
SUCCESS_AFTER_MIN_FAILURES = 10
NEW_COUNTRY_MIN_HISTORY = 5
INCIDENT_GAP = timedelta(minutes=30)

# A finding carries at most this many evidence rows; the counts always cover every event.
MAX_EVIDENCE_ROWS = 20

BRUTE_FORCE = "brute_force"
PASSWORD_SPRAYING = "password_spraying"
SUCCESS_AFTER_FAILURES = "success_after_failures"
NEW_COUNTRY = "new_country"


@dataclass(frozen=True)
class RuleGuide:
    """What a rule looks for and the assumption behind its threshold, in plain words."""

    rule: str
    title: str
    fires_when: str
    assumption: str


_HOUR = f"{int(ATTACK_WINDOW.total_seconds() // 60)} minutes"

RULE_GUIDE = (
    RuleGuide(
        BRUTE_FORCE,
        "Brute force",
        f"{BRUTE_FORCE_MIN_FAILURES} or more failed sign-ins on one account from one IP address "
        f"within {_HOUR}.",
        "In this dataset, staff mistype a password at most 4 times in a day, so we assume "
        f"{BRUTE_FORCE_MIN_FAILURES} failures on one account within an hour is automated guessing.",
    ),
    RuleGuide(
        PASSWORD_SPRAYING,
        "Password spraying",
        f"One IP address fails on {SPRAYING_MIN_ACCOUNTS} or more different accounts within "
        f"{_HOUR}.",
        "In this dataset, the busiest office address sees at most 3 people mistype within an hour, "
        f"so we assume {SPRAYING_MIN_ACCOUNTS} accounts failing from one address within an hour "
        "is a list being worked through.",
    ),
    RuleGuide(
        SUCCESS_AFTER_FAILURES,
        "Success after repeated failures",
        f"A successful sign-in follows {SUCCESS_AFTER_MIN_FAILURES} or more failures from the same "
        f"IP address on the same account within the {_HOUR} before.",
        "In this dataset, staff who mistype succeed after 1 or 2 tries, so we assume a success "
        f"after {SUCCESS_AFTER_MIN_FAILURES} or more failures means the password was guessed.",
    ),
    RuleGuide(
        NEW_COUNTRY,
        "Sign-in from a new country",
        "A successful sign-in from a country the user has never signed in from before, once the "
        f"user has at least {NEW_COUNTRY_MIN_HISTORY} earlier successful sign-ins.",
        f"We assume {NEW_COUNTRY_MIN_HISTORY} earlier sign-ins are enough to establish a user's "
        "usual country; with fewer, the rule does not judge.",
    ),
)

GENERAL_ASSUMPTIONS = (
    "These thresholds are assumptions tuned to this synthetic dataset, not general facts about "
    "attackers. A real deployment would set them from its own baseline of normal activity.",
    "We assume an hour is long enough to catch an automated tool and short enough that, in this "
    "dataset, a busy office's ordinary typos never add up.",
    f"We assume flagged activity separated by a pause longer than "
    f"{int(INCIDENT_GAP.total_seconds() // 60)} minutes is two separate incidents.",
    "Usernames are compared without regard to case, so changing case cannot split a count.",
)

RULE_TITLES = {guide.rule: guide.title for guide in RULE_GUIDE}


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
    # Index labels of every log row the finding covers, for matching against filters. Not part of
    # to_dict: the agent sees the counts and the evidence, not row numbers.
    row_ids: tuple = ()

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
        row_ids=tuple(rows.index),
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


def findings_matching(findings: list[Finding], rows: pd.DataFrame) -> list[Finding]:
    """Keep the findings with at least one event among `rows`, such as the rows that pass the
    dashboard filters. `rows` must keep the index of the loaded log."""
    wanted = set(rows.index)
    return [f for f in findings if wanted.intersection(f.row_ids)]
