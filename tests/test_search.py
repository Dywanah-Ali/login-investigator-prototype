"""The search function counts every match exactly and returns a capped, recent sample."""

import json

import pytest

from login_investigator.search import (
    DEFAULT_SAMPLE_ROWS,
    MAX_SAMPLE_ROWS,
    filter_logins,
    search_logins,
)


def test_no_filters_counts_the_whole_log(log, truth):
    result = search_logins(log)
    assert result.total == truth["row_count"]
    assert result.successes + result.failures == result.total
    assert len(result.sample) == DEFAULT_SAMPLE_ROWS
    assert result.truncated


def test_s1_ip_search_shows_the_failures_and_the_success(log, s):
    result = search_logins(log, ip=s["S1"]["attacker_ip"])
    assert result.failures == s["S1"]["failures"]
    assert result.successes == 1
    assert result.distinct_users == 1
    # The sample holds the most recent rows, so the final success is visible.
    assert result.sample[-1]["timestamp_utc"] == s["S3"]["time"]
    assert result.sample[-1]["outcome"] == "success"
    times = [r["timestamp_utc"] for r in result.sample]
    assert times == sorted(times)


def test_did_the_victim_sign_in_elsewhere_afterwards(log, s):
    """The core scenario's follow-up question, answered from the log."""
    result = search_logins(log, user=s["S3"]["user"], start=s["S3"]["time"])
    expected = s["S3"]["user_sign_ins_afterwards"]
    # The window start is inclusive, so the compromise itself is the first row.
    assert result.total == len(expected) + 1
    later = [{k: r[k] for k in ("timestamp_utc", "source_ip", "country", "outcome")}
             for r in result.sample[1:]]
    assert later == expected


def test_filters_combine(log, s):
    result = search_logins(log, ip=s["S2"]["attacker_ip"], outcome="failure",
                           user=s["S2"]["unknown_usernames"][0])
    direct = log[(log["source_ip"] == s["S2"]["attacker_ip"])
                 & (log["username"] == s["S2"]["unknown_usernames"][0])]
    assert result.total == len(direct) > 0
    assert result.failures == result.total


def test_user_and_country_ignore_case(log, s):
    assert search_logins(log, user=s["S4"]["user"].upper()).total == \
        search_logins(log, user=s["S4"]["user"]).total
    result = search_logins(log, country=s["S4"]["new_country"].lower())
    assert result.total == 1
    assert result.sample[0]["source_ip"] == s["S4"]["ip"]


def test_window_end_is_exclusive(log, s):
    moment = s["S4"]["time"]
    assert search_logins(log, start=moment, end="2026-10-06T13:47:13Z").total >= 1
    assert search_logins(log, ip=s["S4"]["ip"], end=moment).total == 0


def test_no_match_gives_zero_counts_not_an_error(log):
    result = search_logins(log, user="nobody.here")
    assert result.total == 0
    assert result.sample == ()
    assert result.first_seen is None
    assert not result.truncated


def test_sample_cap(log):
    assert len(search_logins(log, limit=MAX_SAMPLE_ROWS).sample) == MAX_SAMPLE_ROWS
    for bad in (0, MAX_SAMPLE_ROWS + 1):
        with pytest.raises(ValueError, match="limit must be between"):
            search_logins(log, limit=bad)


@pytest.mark.parametrize("kwargs, message", [
    ({"outcome": "sucess"}, "is not one of"),
    ({"start": "2026-10-08", "end": "2026-10-07"}, "must be before"),
    ({"start": "yesterday"}, "not an explicit date"),
    ({"end": "now"}, "not an explicit date"),
])
def test_bad_input_raises_a_clear_error(log, kwargs, message):
    with pytest.raises(ValueError, match=message):
        search_logins(log, **kwargs)


def test_filter_logins_returns_every_matching_row(log, s):
    rows = filter_logins(log, ip=s["S2"]["attacker_ip"])
    assert len(rows) == s["S2"]["attempts"]


def test_result_is_json_ready(log, s):
    json.dumps(search_logins(log, ip=s["S1"]["attacker_ip"]).to_dict())
    json.dumps(search_logins(log, user="nobody.here").to_dict())
