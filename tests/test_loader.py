"""The loader accepts the real log unchanged and refuses any broken file loudly."""

import csv
from datetime import date, datetime

import pandas as pd
import pytest

from login_investigator import generator
from login_investigator.loader import (
    MAX_REPORTED_PROBLEMS,
    LogValidationError,
    load_log,
    parse_utc,
)


def test_real_log_loads_every_row(log, truth):
    assert len(log) == truth["row_count"]
    assert str(log["timestamp_utc"].dt.tz) == "UTC"
    assert list(log.columns) == generator.COLUMNS


def test_injection_text_is_kept_exactly_as_written(log, s):
    injected = log[log["user_agent"] == s["S5"]["text"]]
    assert len(injected) == s["S5"]["rows"]


@pytest.fixture
def real_rows():
    with open(generator.LOG_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_log(path, rows, columns=None):
    columns = columns or generator.COLUMNS
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def broken(tmp_path, real_rows, row_index, column, value):
    rows = [dict(r) for r in real_rows]
    rows[row_index][column] = value
    return write_log(tmp_path / "log.csv", rows)


def failure_row(real_rows):
    return next(i for i, r in enumerate(real_rows) if r["outcome"] == "failure")


def success_row(real_rows):
    return next(i for i, r in enumerate(real_rows) if r["outcome"] == "success")


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(LogValidationError, match="not found"):
        load_log(tmp_path / "nope.csv")


def test_empty_file_is_refused(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text("")
    with pytest.raises(LogValidationError, match="empty"):
        load_log(path)


def test_header_without_rows_is_refused(tmp_path):
    path = write_log(tmp_path / "log.csv", [])
    with pytest.raises(LogValidationError, match="no rows"):
        load_log(path)


def test_missing_column_is_named(tmp_path, real_rows):
    columns = [c for c in generator.COLUMNS if c != "country"]
    path = write_log(tmp_path / "log.csv", real_rows, columns)
    with pytest.raises(LogValidationError, match=r"Missing: \['country'\]"):
        load_log(path)


def test_unexpected_column_is_named(tmp_path, real_rows):
    columns = generator.COLUMNS + ["note"]
    path = write_log(tmp_path / "log.csv", real_rows, columns)
    with pytest.raises(LogValidationError, match=r"Unexpected: \['note'\]"):
        load_log(path)


def test_reordered_columns_are_refused(tmp_path, real_rows):
    columns = list(reversed(generator.COLUMNS))
    path = write_log(tmp_path / "log.csv", real_rows, columns)
    with pytest.raises(LogValidationError, match="order is different"):
        load_log(path)


@pytest.mark.parametrize("value, why", [
    ("2026-10-08T01:12:07+03:00", "is not a UTC time"),
    ("2026-10-08 01:12:07", "is not a UTC time"),
    ("2026-13-08T01:12:07Z", "is not a real date"),
    ("", "is not a UTC time"),
])
def test_bad_timestamps_are_refused(tmp_path, real_rows, value, why):
    path = broken(tmp_path, real_rows, 5, "timestamp_utc", value)
    with pytest.raises(LogValidationError, match=f"line 7, column 'timestamp_utc'.*{why}"):
        load_log(path)


@pytest.mark.parametrize("column, value, why", [
    ("outcome", "sucess", "is not one of failure, success"),
    ("outcome", "", "is not one of failure, success"),
    ("source_ip", "999.1.1.1", "is not a valid IP address"),
    ("country", "Russia", "is not a two-letter country code"),
    ("country", "gb", "is not a two-letter country code"),
    ("username", "  ", "is empty"),
])
def test_bad_values_are_refused(tmp_path, real_rows, column, value, why):
    path = broken(tmp_path, real_rows, 5, column, value)
    with pytest.raises(LogValidationError, match=f"line 7, column '{column}'.*{why}"):
        load_log(path)


def test_success_with_a_failure_reason_is_refused(tmp_path, real_rows):
    i = success_row(real_rows)
    path = broken(tmp_path, real_rows, i, "failure_reason", "bad_password")
    with pytest.raises(LogValidationError, match="a success must have no failure reason"):
        load_log(path)


@pytest.mark.parametrize("reason", ["", "mfa_timeout"])
def test_failure_needs_a_known_reason(tmp_path, real_rows, reason):
    i = failure_row(real_rows)
    path = broken(tmp_path, real_rows, i, "failure_reason", reason)
    with pytest.raises(LogValidationError, match="is not one of bad_password, unknown_user"):
        load_log(path)


def test_one_bad_row_fails_the_whole_load(tmp_path, real_rows):
    """Never drop a row silently: the load fails instead of returning the other rows."""
    path = broken(tmp_path, real_rows, len(real_rows) - 1, "outcome", "maybe")
    with pytest.raises(LogValidationError):
        load_log(path)


def test_many_problems_are_summarised(tmp_path, real_rows):
    rows = [dict(r, outcome="maybe") for r in real_rows[:25]] + real_rows[25:]
    path = write_log(tmp_path / "log.csv", rows)
    with pytest.raises(LogValidationError) as error:
        load_log(path)
    message = str(error.value)
    assert "25 problem(s)" in message
    assert message.count("\n- line") == MAX_REPORTED_PROBLEMS
    assert f"and {25 - MAX_REPORTED_PROBLEMS} more" in message


# --- Query times: "today" is the log's capture date, never the computer's clock (B-004) ---


@pytest.mark.parametrize("word", ["now", "today", "yesterday", "tomorrow", "NOW", " today "])
def test_relative_words_are_refused(word):
    with pytest.raises(ValueError, match="not an explicit date or time"):
        parse_utc(word, "start")


@pytest.mark.parametrize("value", ["Oct 8 2026", "8/10/2026", "1759900000", "", "last night"])
def test_loose_formats_are_refused(value):
    with pytest.raises(ValueError, match="not an explicit date or time"):
        parse_utc(value, "start")


@pytest.mark.parametrize("value", [1759900000, None, 3.5])
def test_non_dates_are_refused(value):
    with pytest.raises(ValueError, match="is not a date and time"):
        parse_utc(value, "start")


@pytest.mark.parametrize("value, expected", [
    ("2026-10-08", "2026-10-08T00:00:00Z"),
    ("2026-10-08T01:12:07Z", "2026-10-08T01:12:07Z"),
    ("2026-10-08T01:12", "2026-10-08T01:12:00Z"),
    ("2026-10-08 04:12:07+03:00", "2026-10-08T01:12:07Z"),
    (date(2026, 10, 8), "2026-10-08T00:00:00Z"),
    (datetime(2026, 10, 8, 1, 12, 7), "2026-10-08T01:12:07Z"),
    (pd.Timestamp("2026-10-08T01:12:07Z"), "2026-10-08T01:12:07Z"),
])
def test_explicit_dates_are_accepted_as_utc(value, expected):
    assert parse_utc(value, "start") == pd.Timestamp(expected)
