"""The Overview's counts are exact, and the attacks stand out where the design says they will."""

import pandas as pd

from login_investigator.search import filter_logins
from login_investigator.stats import hourly_counts, top_failed_ips


def test_hourly_counts_cover_every_row(log):
    counts = hourly_counts(log)
    assert counts["events"].sum() == len(log)
    assert set(counts["outcome"]) == {"success", "failure"}


def test_s1_is_the_busiest_failure_hour(log, s):
    counts = hourly_counts(log)
    failures = counts[counts["outcome"] == "failure"]
    busiest = failures.loc[failures["events"].idxmax(), "hour"]
    first = pd.Timestamp(s["S1"]["first_seen"])
    last = pd.Timestamp(s["S1"]["last_seen"])
    assert first.floor("h") <= busiest <= last.floor("h")


def test_s1_hours_hold_all_its_failures(log, s):
    rows = filter_logins(log, ip=s["S1"]["attacker_ip"], outcome="failure")
    counts = hourly_counts(rows)
    assert counts["events"].sum() == s["S1"]["failures"]


def test_top_failed_ips_puts_the_attackers_first(log, s):
    table = top_failed_ips(log)
    assert list(table["source_ip"][:2]) == [s["S1"]["attacker_ip"], s["S2"]["attacker_ip"]]
    assert table.loc[0, "failures"] == s["S1"]["failures"]
    assert table.loc[1, "accounts"] == s["S2"]["accounts_tried"]


def test_top_failed_ips_respects_n_and_is_stable(log):
    assert len(top_failed_ips(log, n=3)) == 3
    assert top_failed_ips(log).equals(top_failed_ips(log))


def test_empty_rows_give_empty_tables(log):
    empty = log.iloc[0:0]
    assert hourly_counts(empty).empty
    assert top_failed_ips(empty).empty
