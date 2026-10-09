"""Counts behind the Overview charts. Plain pandas: no Streamlit, no Plotly."""

from __future__ import annotations

import pandas as pd

from login_investigator.loader import account_key

DEFAULT_TOP_IPS = 10


def hourly_counts(rows: pd.DataFrame) -> pd.DataFrame:
    """Sign-in attempts per UTC hour and outcome: columns hour, outcome, events.

    Hours with no attempts are left out; the chart's time axis keeps the gaps honest.
    """
    if rows.empty:
        return pd.DataFrame({"hour": pd.Series(dtype="datetime64[us, UTC]"),
                             "outcome": pd.Series(dtype="string"),
                             "events": pd.Series(dtype="int64")})
    counts = (
        rows.assign(hour=rows["timestamp_utc"].dt.floor("h"))
        .groupby(["hour", "outcome"], sort=True)
        .size()
        .rename("events")
        .reset_index()
    )
    return counts


def top_failed_ips(rows: pd.DataFrame, n: int = DEFAULT_TOP_IPS) -> pd.DataFrame:
    """The IP addresses with the most failed sign-ins: columns source_ip, failures, accounts.

    Ties are broken by address, so the order never changes between runs.
    """
    failures = rows[rows["outcome"] == "failure"]
    if failures.empty:
        return pd.DataFrame({"source_ip": pd.Series(dtype="string"),
                             "failures": pd.Series(dtype="int64"),
                             "accounts": pd.Series(dtype="int64")})
    table = (
        failures.assign(account=account_key(failures["username"]))
        .groupby("source_ip")
        .agg(failures=("outcome", "size"), accounts=("account", "nunique"))
        .reset_index()
        .sort_values(["failures", "source_ip"], ascending=[False, True], kind="stable")
        .head(n)
        .reset_index(drop=True)
    )
    return table
