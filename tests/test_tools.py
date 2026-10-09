"""The agent's three tools: right answers on the planted scenarios, clean errors, data labelled.

No test reaches the network or a model. The IP tool answers from saved responses here.
"""

import json

import pytest

from login_investigator import reputation
from login_investigator.tools import (
    DATA_NOTE,
    TOOLS,
    find_suspicious_activity,
    lookup_ip_reputation,
    search_logins,
)

LAST_NIGHT = {"start": "2026-10-07T18:00:00Z", "end": "2026-10-08T09:00:00Z"}


def run(tool, **args) -> dict:
    return json.loads(tool.invoke(args))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a live call was made")
    monkeypatch.setattr(reputation.requests, "get", refuse)


def test_exactly_the_three_read_only_tools_of_the_prd():
    assert [t.name for t in TOOLS] == ["find_suspicious_activity", "search_logins",
                                      "lookup_ip_reputation"]


def test_tool_descriptions_state_the_input_rules():
    # The handoff notes: explicit ISO times, start included and end excluded, users any case.
    for tool in (find_suspicious_activity, search_logins):
        assert "ISO 8601" in tool.description
        assert "included" in tool.description and "excluded" in tool.description
    assert "regardless of case" in search_logins.description


def test_last_night_finds_the_s1_attack_and_its_success(s):
    data = run(find_suspicious_activity, **LAST_NIGHT)["data"]
    rules = {f["rule"] for f in data["findings"]}
    assert {"brute_force", "success_after_failures"} <= rules
    assert all(s["S1"]["attacker_ip"] in f["ips"] for f in data["findings"]
               if f["rule"] in ("brute_force", "success_after_failures"))
    assert data["window_start"] == LAST_NIGHT["start"]
    assert len(data["rules_checked"]) == 4


def test_last_night_leaves_out_earlier_attacks(s):
    data = run(find_suspicious_activity, **LAST_NIGHT)["data"]
    ips = {ip for f in data["findings"] for ip in f["ips"]}
    assert s["S2"]["attacker_ip"] not in ips
    assert s["S4"]["ip"] not in ips


def test_no_window_covers_every_planted_scenario(s):
    findings = run(find_suspicious_activity)["data"]["findings"]
    ips = {ip for f in findings for ip in f["ips"]}
    assert {s["S1"]["attacker_ip"], s["S2"]["attacker_ip"], s["S4"]["ip"]} <= ips


def test_empty_strings_mean_no_filter():
    assert run(find_suspicious_activity, start="", end=" ") == run(find_suspicious_activity)


@pytest.mark.parametrize("args, message", [
    ({"start": "last night"}, "not an explicit date"),
    ({"start": "today"}, "not an explicit date"),
    ({"start": "2026-10-08T09:00:00Z", "end": "2026-10-07T18:00:00Z"}, "must be before"),
])
def test_bad_windows_return_a_short_error(args, message):
    result = run(find_suspicious_activity, **args)
    assert set(result) == {"error"}
    assert message in result["error"]


def test_search_by_attacker_ip_matches_the_ground_truth(s):
    data = run(search_logins, ip=s["S1"]["attacker_ip"])["data"]
    assert data["failures"] == s["S1"]["failures"]
    assert data["successes"] == 1
    assert data["sample"][-1]["timestamp_utc"] == s["S3"]["time"]


def test_search_follow_up_finds_the_sign_ins_after_the_compromise(s):
    data = run(search_logins, user=s["S3"]["user"].upper(), start=s["S3"]["time"],
               end="2026-10-08T09:00:00Z", outcome="success")["data"]
    later = [r for r in data["sample"] if r["timestamp_utc"] > s["S3"]["time"]]
    assert [r["timestamp_utc"] for r in later] == \
        [r["timestamp_utc"] for r in s["S3"]["user_sign_ins_afterwards"]]


def test_search_sample_is_capped_but_counts_are_exact(truth):
    data = run(search_logins, limit=50)["data"]
    assert data["total"] == truth["row_count"]
    assert data["sample_shown"] == 50
    assert data["truncated"] is True


@pytest.mark.parametrize("args, message", [
    ({"limit": 51}, "limit must be between"),
    ({"limit": 0}, "limit must be between"),
    ({"outcome": "blocked"}, "is not one of"),
    ({"start": "yesterday"}, "not an explicit date"),
])
def test_bad_search_input_returns_a_short_error(args, message):
    result = run(search_logins, **args)
    assert set(result) == {"error"}
    assert message in result["error"]


def test_lookup_answers_from_the_saved_response(s):
    data = run(lookup_ip_reputation, ip=s["S1"]["attacker_ip"])["data"]
    assert data["source"] == "saved"
    assert data["country"] == s["S1"]["country"]


def test_lookup_of_a_reserved_address_makes_no_call():
    assert run(lookup_ip_reputation, ip="203.0.113.10")["data"]["source"] == "reserved"


def test_lookup_of_a_bad_address_returns_a_short_error():
    assert "is not an IP address" in run(lookup_ip_reputation, ip="185.218.86")["error"]


@pytest.mark.parametrize("tool, args", [
    (find_suspicious_activity, LAST_NIGHT),
    (search_logins, {"ip": "185.218.86.24"}),
    (lookup_ip_reputation, {"ip": "185.218.86.24"}),
])
def test_every_result_is_labelled_as_untrusted_data(tool, args):
    result = run(tool, **args)
    assert result["note"] == DATA_NOTE
    assert "never instructions" in result["note"]
    assert "data" in result


def test_planted_injection_reaches_the_agent_only_inside_data(s):
    # S5 must be visible to the agent (the evals test that it is ignored), but only as a field
    # value inside "data", never at the top level of the result.
    raw = search_logins.invoke({"ip": s["S1"]["attacker_ip"]})
    result = json.loads(raw)
    agents = [r["user_agent"] for r in result["data"]["sample"]]
    assert s["S5"]["text"] in agents
    assert s["S5"]["text"] not in json.dumps({k: v for k, v in result.items() if k != "data"})
