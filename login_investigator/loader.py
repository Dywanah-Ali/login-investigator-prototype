"""Load the authentication log and check every row before anything else uses it.

Every field is read as plain text, so nothing is converted or "fixed" behind our back. Only the
timestamp becomes a real UTC time. Any problem stops the load with a clear message; no row is ever
dropped or repaired.
"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path

import pandas as pd

from login_investigator.generator import COLUMNS, LOG_PATH

ALLOWED_OUTCOMES = ("failure", "success")
ALLOWED_FAILURE_REASONS = ("bad_password", "unknown_user")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
MAX_REPORTED_PROBLEMS = 10


class LogValidationError(ValueError):
    """The log file is missing, malformed, or contains a row that breaks the schema."""


def load_log(path: Path | str = LOG_PATH) -> pd.DataFrame:
    """Read and validate the log. Returns one row per sign-in attempt, in file order."""
    path = Path(path)
    if not path.is_file():
        raise LogValidationError(f"Log file not found: {path}")
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    except pd.errors.EmptyDataError:
        raise LogValidationError(f"{path.name} is empty: no header and no rows") from None

    columns = list(df.columns)
    if columns != COLUMNS:
        missing = [c for c in COLUMNS if c not in columns]
        unexpected = [c for c in columns if c not in COLUMNS]
        raise LogValidationError(
            f"{path.name} has the wrong columns. Expected {COLUMNS}. "
            f"Missing: {missing or 'none'}. Unexpected: {unexpected or 'none'}."
            + ("" if missing or unexpected else " The order is different.")
        )
    if df.empty:
        raise LogValidationError(f"{path.name} has a header but no rows")

    timestamps = pd.to_datetime(
        df["timestamp_utc"], format=TIMESTAMP_FORMAT, utc=True, errors="coerce"
    )
    problems = _find_problems(df, timestamps)
    if problems:
        shown = "\n".join(f"- {p}" for p in problems[:MAX_REPORTED_PROBLEMS])
        more = len(problems) - MAX_REPORTED_PROBLEMS
        raise LogValidationError(
            f"{path.name} failed validation with {len(problems)} problem(s):\n{shown}"
            + (f"\n- ... and {more} more" if more > 0 else "")
        )

    df["timestamp_utc"] = timestamps
    return df


def _find_problems(df: pd.DataFrame, timestamps: pd.Series) -> list[str]:
    problems = []
    for index, row in df.iterrows():
        line = index + 2  # line 1 is the header

        def bad(column: str, why: str) -> None:
            problems.append(f"line {line}, column '{column}': {why}")

        raw_time = row["timestamp_utc"]
        if not TIMESTAMP_PATTERN.match(raw_time):
            bad("timestamp_utc", f"{raw_time!r} is not a UTC time like 2026-10-08T01:12:07Z")
        elif pd.isna(timestamps[index]):
            bad("timestamp_utc", f"{raw_time!r} is not a real date and time")

        if not row["username"].strip():
            bad("username", "is empty")

        try:
            ipaddress.ip_address(row["source_ip"])
        except ValueError:
            bad("source_ip", f"{row['source_ip']!r} is not a valid IP address")

        if not COUNTRY_PATTERN.match(row["country"]):
            bad("country", f"{row['country']!r} is not a two-letter country code like GB")

        outcome, reason = row["outcome"], row["failure_reason"]
        if outcome not in ALLOWED_OUTCOMES:
            bad("outcome", f"{outcome!r} is not one of {', '.join(ALLOWED_OUTCOMES)}")
        elif outcome == "success" and reason:
            bad("failure_reason", f"a success must have no failure reason, found {reason!r}")
        elif outcome == "failure" and reason not in ALLOWED_FAILURE_REASONS:
            bad("failure_reason",
                f"{reason!r} is not one of {', '.join(ALLOWED_FAILURE_REASONS)}")
    return problems


def parse_utc(value, name: str) -> pd.Timestamp:
    """Read a date or date-time. A time without a zone is taken as UTC, like the whole log."""
    try:
        moment = pd.Timestamp(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} {value!r} is not a date and time") from None
    if pd.isna(moment):
        raise ValueError(f"{name} {value!r} is not a date and time")
    return moment.tz_localize("UTC") if moment.tzinfo is None else moment.tz_convert("UTC")


def parse_window(start, end) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Parse an optional [start, end) window. The start must come before the end."""
    start = None if start is None else parse_utc(start, "start")
    end = None if end is None else parse_utc(end, "end")
    if start is not None and end is not None and start >= end:
        raise ValueError(f"start {start} must be before end {end}")
    return start, end


def to_records(rows: pd.DataFrame) -> list[dict]:
    """Turn log rows into plain dicts with ISO timestamps, ready for JSON. Values stay raw."""
    records = []
    for row in rows.to_dict("records"):
        row["timestamp_utc"] = row["timestamp_utc"].strftime(TIMESTAMP_FORMAT)
        records.append(row)
    return records
