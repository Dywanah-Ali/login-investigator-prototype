"""The tool panel's plain lines: written by code from the tool's JSON, never by the model."""

import json

import pytest

from login_investigator.tool_views import describe
from login_investigator.tools import find_suspicious_activity, lookup_ip_reputation, search_logins

LAST_NIGHT = {"start": "2026-10-07T18:00:00Z", "end": "2026-10-08T09:00:00Z"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    from login_investigator import reputation

    def refuse(*args, **kwargs):
        raise AssertionError("a live call was made")
    monkeypatch.setattr(reputation.requests, "get", refuse)


def view(tool, **args):
    return describe(tool.name, args, tool.invoke(args))


def test_detection_rules_view_names_the_window_and_the_findings():
    v = view(find_suspicious_activity, **LAST_NIGHT)
    assert v.title == "Detection rules"
    assert v.asked == "7 Oct 18:00 → 8 Oct 09:00 UTC"
    assert v.found.startswith("3 findings: Brute force")
    assert list(v.rows["IP addresses"]).count("185.218.86.24") >= 2


def test_rules_without_a_window_say_so():
    assert view(find_suspicious_activity).asked == "the whole log"


def test_search_view_gives_exact_counts_and_the_sample_table(s):
    v = view(search_logins, ip=s["S1"]["attacker_ip"])
    assert v.asked == f"IP {s['S1']['attacker_ip']}, all times"
    assert v.found.startswith(f"151 events: {s['S1']['failures']} failed, 1 succeeded")
    assert "The table shows the 20 most recent." in v.found
    assert len(v.rows) == 20


def test_search_view_lists_every_filter():
    v = view(search_logins, user="daniel.hughes", outcome="success", **LAST_NIGHT)
    assert v.asked == "user daniel.hughes, outcome success, 7 Oct 18:00 → 8 Oct 09:00 UTC"


def test_reputation_view_gives_score_country_owner_and_source(s):
    v = view(lookup_ip_reputation, ip=s["S1"]["attacker_ip"])
    assert v.title == "IP reputation"
    assert v.found.startswith("score 100/100, NL, ")
    assert "not whitelisted" in v.found
    assert "saved response from" in v.found
    assert v.rows is None


def test_reserved_address_view_says_there_is_no_data():
    assert "no reputation data" in view(lookup_ip_reputation, ip="203.0.113.10").found


def test_a_tool_error_is_shown_as_an_error():
    v = view(search_logins, start="today")
    assert v.found.startswith("Error: start 'today' is not an explicit date")
    # "today" is shown as typed, never turned into the computer's date.
    assert v.asked == "from 'today' UTC"


def test_empty_results_say_so():
    assert view(search_logins, ip="192.0.2.99").found == "No sign-ins match."
    v = view(find_suspicious_activity, start="2026-10-02T00:00:00Z", end="2026-10-02T01:00:00Z")
    assert v.found == "No findings in this window."


@pytest.mark.parametrize("result", ["not json", "[]", '{"data": "x"}'])
def test_unreadable_results_do_not_break_the_panel(result):
    v = describe("search_logins", {}, result)
    assert v.found == "The result could not be read."
    assert v.raw


def test_raw_data_is_the_full_tool_result():
    result = search_logins.invoke({"ip": "185.218.86.24"})
    assert json.loads(describe("search_logins", {}, result).raw) == json.loads(result)
