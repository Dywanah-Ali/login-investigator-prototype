"""Gate 1: the rules catch S1 to S4, and flag nothing else.

Expected values come from evals/ground_truth.json. Threshold edge cases use small made-up logs.
"""

import ipaddress
import json

import pandas as pd
import pytest

from login_investigator import rules
from login_investigator.rules import (
    BRUTE_FORCE,
    BRUTE_FORCE_MIN_FAILURES,
    MAX_EVIDENCE_ROWS,
    NEW_COUNTRY,
    NEW_COUNTRY_MIN_HISTORY,
    PASSWORD_SPRAYING,
    SPRAYING_MIN_ACCOUNTS,
    SUCCESS_AFTER_FAILURES,
    SUCCESS_AFTER_MIN_FAILURES,
)


def ts(text):
    return pd.Timestamp(text)


@pytest.fixture(scope="module")
def findings(log):
    return rules.detect_all(log)


def by_rule(findings, rule):
    return [f for f in findings if f.rule == rule]


# --- Catches the planted attacks ---


def test_s1_brute_force_is_caught(findings, s):
    [f] = by_rule(findings, BRUTE_FORCE)
    assert f.ips == (s["S1"]["attacker_ip"],)
    assert f.users == (s["S1"]["target_user"],)
    assert f.failure_count == s["S1"]["failures"]
    assert f.first_seen == ts(s["S1"]["first_seen"])
    assert f.last_seen == ts(s["S1"]["last_seen"])


def test_s5_injection_rows_count_toward_s1(log, findings, s):
    """The instruction-like rows are data: they sit inside the S1 burst and are counted."""
    [f] = by_rule(findings, BRUTE_FORCE)
    for moment in s["S5"]["times"]:
        assert f.first_seen <= ts(moment) <= f.last_seen
    s1_failures = log[(log["source_ip"] == s["S1"]["attacker_ip"])
                      & (log["outcome"] == "failure")]
    assert (s1_failures["user_agent"] == s["S5"]["text"]).sum() == s["S5"]["rows"]
    assert f.failure_count == len(s1_failures)


def test_s2_password_spraying_is_caught(findings, s):
    [f] = by_rule(findings, PASSWORD_SPRAYING)
    assert f.ips == (s["S2"]["attacker_ip"],)
    assert len(f.users) == s["S2"]["accounts_tried"]
    assert set(s["S2"]["unknown_usernames"]) <= set(f.users)
    assert f.failure_count == s["S2"]["attempts"]
    assert f.success_count == s["S2"]["successes"]
    assert f.first_seen == ts(s["S2"]["first_seen"])
    assert f.last_seen == ts(s["S2"]["last_seen"])


def test_s3_success_after_failures_is_caught(findings, s):
    [f] = by_rule(findings, SUCCESS_AFTER_FAILURES)
    assert f.ips == (s["S3"]["attacker_ip"],)
    assert f.users == (s["S3"]["user"],)
    assert f.success_count == 1
    assert f.failure_count >= SUCCESS_AFTER_MIN_FAILURES
    assert f.last_seen == ts(s["S3"]["time"])


def test_s4_new_country_is_caught(findings, s):
    [f] = [f for f in by_rule(findings, NEW_COUNTRY) if f.users == (s["S4"]["user"],)]
    assert f.ips == (s["S4"]["ip"],)
    assert f.first_seen == ts(s["S4"]["time"])
    assert f.evidence[0]["country"] == s["S4"]["new_country"]


def test_s3_compromise_also_counts_as_a_new_country(findings, s):
    """The attacker's success came from a country the victim never uses. That is correct."""
    [f] = [f for f in by_rule(findings, NEW_COUNTRY) if f.users == (s["S3"]["user"],)]
    assert f.ips == (s["S3"]["attacker_ip"],)
    assert f.first_seen == ts(s["S3"]["time"])
    assert f.evidence[0]["country"] == s["S1"]["country"]


# --- Flags nothing else ---


def test_exactly_the_planted_findings_and_no_others(findings):
    counts = {rule: len(by_rule(findings, rule)) for rule in
              (BRUTE_FORCE, PASSWORD_SPRAYING, SUCCESS_AFTER_FAILURES, NEW_COUNTRY)}
    assert counts == {BRUTE_FORCE: 1, PASSWORD_SPRAYING: 1, SUCCESS_AFTER_FAILURES: 1,
                      NEW_COUNTRY: 2}


def test_only_attacker_ips_are_flagged(findings, s):
    attackers = {s["S1"]["attacker_ip"], s["S2"]["attacker_ip"], s["S4"]["ip"]}
    flagged = {ip for f in findings for ip in f.ips}
    assert flagged <= attackers


def test_decoy_ips_are_never_flagged(findings, truth):
    flagged = {ip for f in findings for ip in f.ips}
    for decoy in truth["decoys"]:
        assert decoy["ip"] not in flagged


def test_reserved_addresses_of_normal_staff_are_never_flagged(findings):
    for f in findings:
        for ip in f.ips:
            assert ipaddress.ip_address(ip).is_global, f"normal staff address {ip} flagged"


def test_normal_users_are_never_flagged(findings, s):
    """Outside the spraying list, only the two planted victims may appear."""
    victims = {s["S1"]["target_user"], s["S4"]["user"]}
    for f in findings:
        if f.rule != PASSWORD_SPRAYING:
            assert set(f.users) <= victims, f.summary


# --- Threshold edges, on small made-up logs ---


def failures(n, user="u1", ip="1.2.3.4", every_minutes=1):
    return [(i * every_minutes, user, ip, "failure") for i in range(n)]


def test_brute_force_threshold_edge(make_log):
    assert rules.brute_force(make_log(failures(BRUTE_FORCE_MIN_FAILURES - 1))) == []
    assert len(rules.brute_force(make_log(failures(BRUTE_FORCE_MIN_FAILURES)))) == 1


def test_brute_force_needs_the_failures_within_an_hour(make_log):
    spread = failures(BRUTE_FORCE_MIN_FAILURES, every_minutes=10)  # over three hours
    assert rules.brute_force(make_log(spread)) == []


def test_brute_force_counts_one_account_only(make_log):
    many_users = [(i, f"u{i}", "1.2.3.4", "failure") for i in range(BRUTE_FORCE_MIN_FAILURES)]
    assert rules.brute_force(make_log(many_users)) == []


def test_spraying_threshold_edge(make_log):
    def spray(accounts):
        return make_log([(i, f"u{i}", "1.2.3.4", "failure") for i in range(accounts)])

    assert rules.password_spraying(spray(SPRAYING_MIN_ACCOUNTS - 1)) == []
    assert len(rules.password_spraying(spray(SPRAYING_MIN_ACCOUNTS))) == 1


def test_success_after_failures_threshold_edge(make_log):
    def attempt(n, success_at):
        return make_log(failures(n) + [(success_at, "u1", "1.2.3.4", "success")])

    n = SUCCESS_AFTER_MIN_FAILURES
    assert rules.success_after_failures(attempt(n - 1, n)) == []
    assert len(rules.success_after_failures(attempt(n, n))) == 1
    assert rules.success_after_failures(attempt(n, n + 120)) == []  # two hours later


def test_success_after_failures_needs_the_same_ip(make_log):
    events = failures(SUCCESS_AFTER_MIN_FAILURES) + [(30, "u1", "5.6.7.8", "success")]
    assert rules.success_after_failures(make_log(events)) == []


def test_new_country_threshold_edge(make_log):
    def history(n):
        home = [(i * 60, "u1", "1.2.3.4", "success", "GB") for i in range(n)]
        return make_log(home + [(n * 60, "u1", "5.6.7.8", "success", "RU")])

    assert rules.new_country(history(NEW_COUNTRY_MIN_HISTORY - 1)) == []
    assert len(rules.new_country(history(NEW_COUNTRY_MIN_HISTORY))) == 1


def test_new_country_flags_only_the_first_visit(make_log):
    home = [(i * 60, "u1", "1.2.3.4", "success", "GB") for i in range(NEW_COUNTRY_MIN_HISTORY)]
    abroad = [(600 + i, "u1", "5.6.7.8", "success", "RU") for i in range(3)]
    assert len(rules.new_country(make_log(home + abroad))) == 1


def test_new_country_ignores_failed_attempts(make_log):
    home = [(i * 60, "u1", "1.2.3.4", "success", "GB") for i in range(NEW_COUNTRY_MIN_HISTORY)]
    abroad = [(600, "u1", "5.6.7.8", "failure", "RU")]
    assert rules.new_country(make_log(home + abroad)) == []


# --- The shared shape and the time window ---


def test_every_finding_has_the_shared_shape_and_is_json_ready(findings):
    for f in findings:
        data = f.to_dict()
        json.dumps(data)
        assert set(data) >= {"rule", "ips", "users", "event_count", "first_seen",
                             "last_seen", "evidence"}
        assert 1 <= len(f.evidence) <= MAX_EVIDENCE_ROWS
        assert f.event_count == f.failure_count + f.success_count


def test_evidence_shows_the_start_and_the_end(findings, s):
    [f] = by_rule(findings, SUCCESS_AFTER_FAILURES)
    assert f.evidence[-1]["timestamp_utc"] == s["S3"]["time"]
    assert f.evidence[-1]["outcome"] == "success"


def test_window_keeps_last_night_only(log, s, truth):
    """From 18:00 the evening before until the log was captured."""
    last_night = rules.detect_all(log, start="2026-10-07T18:00:00Z", end=truth["captured_at"])
    found = {(f.rule, f.users) for f in last_night}
    assert found == {
        (BRUTE_FORCE, (s["S1"]["target_user"],)),
        (SUCCESS_AFTER_FAILURES, (s["S3"]["user"],)),
        (NEW_COUNTRY, (s["S3"]["user"],)),
    }


def test_window_on_s4_day_still_sees_the_user_history(log, s):
    day = s["S4"]["time"][:10]
    found = rules.detect_all(log, start=f"{day}T12:00:00Z", end=f"{day}T15:00:00Z")
    assert [(f.rule, f.users) for f in found] == [(NEW_COUNTRY, (s["S4"]["user"],))]


def test_bad_window_is_refused(log):
    with pytest.raises(ValueError, match="must be before"):
        rules.detect_all(log, start="2026-10-08", end="2026-10-07")
    with pytest.raises(ValueError, match="not an explicit date"):
        rules.detect_all(log, start="last night")


# --- Usernames are one account regardless of case, in the rules and in search (B-005) ---


def alternating_case(n, ip="1.2.3.4", outcome="failure"):
    return [(i, "Daniel.Hughes" if i % 2 else "daniel.hughes", ip, outcome) for i in range(n)]


def test_brute_force_cannot_be_split_by_changing_case(make_log):
    found = rules.brute_force(make_log(alternating_case(30)))
    assert len(found) == 1
    assert found[0].failure_count == 30
    assert set(found[0].users) == {"Daniel.Hughes", "daniel.hughes"}  # raw values kept


def test_spraying_counts_case_variants_as_one_account(make_log):
    accounts = SPRAYING_MIN_ACCOUNTS - 1
    events = [(i, f"user{i}", "1.2.3.4", "failure") for i in range(accounts)]
    events += [(30 + i, f"USER{i}", "1.2.3.4", "failure") for i in range(accounts)]
    assert rules.password_spraying(make_log(events)) == []


def test_success_after_failures_across_case_variants(make_log):
    events = alternating_case(SUCCESS_AFTER_MIN_FAILURES)
    events.append((SUCCESS_AFTER_MIN_FAILURES, "DANIEL.HUGHES", "1.2.3.4", "success"))
    assert len(rules.success_after_failures(make_log(events))) == 1


def test_new_country_history_spans_case_variants(make_log):
    home = [(i * 60, "u1" if i % 2 else "U1", "1.2.3.4", "success", "GB")
            for i in range(NEW_COUNTRY_MIN_HISTORY)]
    abroad = [(600, "u1", "5.6.7.8", "success", "RU")]
    assert len(rules.new_country(make_log(home + abroad))) == 1


def test_rules_and_search_agree_on_the_account(make_log):
    from login_investigator.search import search_logins

    log = make_log(alternating_case(30))
    [finding] = rules.brute_force(log)
    assert search_logins(log, user="DANIEL.HUGHES").total == finding.event_count
