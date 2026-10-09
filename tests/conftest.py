"""Shared fixtures. Expected answers always come from evals/ground_truth.json, never the tests."""

import json

import pandas as pd
import pytest

from login_investigator import generator
from login_investigator.loader import load_log


@pytest.fixture(scope="session")
def log():
    return load_log()


@pytest.fixture(scope="session")
def truth():
    with open(generator.GROUND_TRUTH_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def s(truth):
    """Shortcut to the planted scenarios."""
    return truth["scenarios"]


@pytest.fixture
def make_log():
    """Build a small log in the same shape load_log returns, for threshold edge cases.

    Each event is (minutes after start, username, ip, outcome) or with a fifth item: country.
    """

    def build(events, start="2026-10-01T00:00:00Z"):
        origin = pd.Timestamp(start)
        rows = []
        for event in events:
            minutes, user, ip, outcome, *rest = event
            rows.append({
                "timestamp_utc": origin + pd.Timedelta(minutes=minutes),
                "username": user,
                "source_ip": ip,
                "country": rest[0] if rest else "GB",
                "outcome": outcome,
                "failure_reason": "bad_password" if outcome == "failure" else "",
                "user_agent": "test-agent",
            })
        return pd.DataFrame(rows)

    return build
