"""Search and filter the log. The dashboard filters and the agent's search tool both call this."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from login_investigator.loader import (
    ALLOWED_OUTCOMES,
    TIMESTAMP_FORMAT,
    parse_window,
    to_records,
)

DEFAULT_SAMPLE_ROWS = 20
# The sample is capped so a broad search can never flood the agent's context; counts are exact.
MAX_SAMPLE_ROWS = 50


@dataclass(frozen=True)
class SearchResult:
    total: int
    successes: int
    failures: int
    distinct_users: int
    distinct_ips: int
    distinct_countries: int
    first_seen: pd.Timestamp | None
    last_seen: pd.Timestamp | None
    sample: tuple[dict, ...]  # the most recent matching rows, in time order
    truncated: bool  # True when more rows matched than the sample shows

    def to_dict(self) -> dict:
        def iso(moment):
            return None if moment is None else moment.strftime(TIMESTAMP_FORMAT)

        return {
            "total": self.total,
            "successes": self.successes,
            "failures": self.failures,
            "distinct_users": self.distinct_users,
            "distinct_ips": self.distinct_ips,
            "distinct_countries": self.distinct_countries,
            "first_seen": iso(self.first_seen),
            "last_seen": iso(self.last_seen),
            "sample": list(self.sample),
            "sample_shown": len(self.sample),
            "truncated": self.truncated,
        }


def filter_logins(df, user=None, ip=None, start=None, end=None, outcome=None, country=None):
    """Return the matching rows. Every filter is optional; together they all must match.

    Users and countries match without regard to case. The window is [start, end) in UTC.
    """
    if outcome is not None and outcome not in ALLOWED_OUTCOMES:
        raise ValueError(f"outcome {outcome!r} is not one of {', '.join(ALLOWED_OUTCOMES)}")
    start, end = parse_window(start, end)
    mask = pd.Series(True, index=df.index)
    if user is not None:
        mask &= df["username"].str.lower() == str(user).strip().lower()
    if ip is not None:
        mask &= df["source_ip"] == str(ip).strip()
    if country is not None:
        mask &= df["country"] == str(country).strip().upper()
    if outcome is not None:
        mask &= df["outcome"] == outcome
    if start is not None:
        mask &= df["timestamp_utc"] >= start
    if end is not None:
        mask &= df["timestamp_utc"] < end
    return df[mask].sort_values("timestamp_utc", kind="stable")


def search_logins(df, user=None, ip=None, start=None, end=None, outcome=None, country=None,
                  limit: int = DEFAULT_SAMPLE_ROWS) -> SearchResult:
    """Counts for every matching row, plus a capped sample of the most recent ones."""
    if not 1 <= limit <= MAX_SAMPLE_ROWS:
        raise ValueError(f"limit must be between 1 and {MAX_SAMPLE_ROWS}, got {limit}")
    rows = filter_logins(df, user, ip, start, end, outcome, country)
    empty = rows.empty
    return SearchResult(
        total=len(rows),
        successes=int((rows["outcome"] == "success").sum()),
        failures=int((rows["outcome"] == "failure").sum()),
        distinct_users=rows["username"].nunique(),
        distinct_ips=rows["source_ip"].nunique(),
        distinct_countries=rows["country"].nunique(),
        first_seen=None if empty else rows["timestamp_utc"].iloc[0],
        last_seen=None if empty else rows["timestamp_utc"].iloc[-1],
        sample=tuple(to_records(rows.tail(limit))),
        truncated=len(rows) > limit,
    )
