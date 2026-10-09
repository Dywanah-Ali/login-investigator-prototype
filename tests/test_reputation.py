"""The IP lookup answers from the cheapest source and fails with short, safe messages.

No test reaches the network: live calls are replaced with fakes.
"""

import json

import pytest
import requests

from login_investigator import reputation
from login_investigator.reputation import ReputationError, lookup

SECRET = "test-key-must-never-appear"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


@pytest.fixture
def no_network(monkeypatch):
    """Fail the test if anything tries a live call."""
    def refuse(*args, **kwargs):
        raise AssertionError("a live call was made")
    monkeypatch.setattr(reputation.requests, "get", refuse)


@pytest.fixture
def live(monkeypatch):
    """Answer live calls with a chosen response, and record what was sent."""
    sent = {}

    def answer_with(response):
        def fake_get(url, headers, params, timeout):
            sent.update(url=url, headers=headers, params=params, timeout=timeout)
            if isinstance(response, Exception):
                raise response
            return response
        monkeypatch.setattr(reputation.requests, "get", fake_get)
        return sent

    return answer_with


@pytest.mark.parametrize("ip", ["203.0.113.10", "192.0.2.10", "198.51.100.20", "10.0.0.1",
                                "::1", "2001:db8::1"])
def test_reserved_addresses_are_answered_without_a_call(ip, no_network):
    result = lookup(ip, api_key=SECRET)
    assert result["source"] == "reserved"
    assert "no reputation data" in result["note"]


def test_every_planted_scenario_ip_has_a_saved_response(s, no_network):
    for scenario in ("S1", "S2"):
        ip = s[scenario]["attacker_ip"]
        result = lookup(ip)
        assert result["source"] == "saved"
        assert result["ip"] == ip
        assert result["country"] == s[scenario]["country"]
        assert result["abuse_confidence_score"] is not None
    assert lookup(s["S4"]["ip"])["country"] == s["S4"]["new_country"]


def test_decoys_have_saved_responses(truth, no_network):
    for decoy in truth["decoys"]:
        assert lookup(decoy["ip"])["source"] == "saved"


def test_saved_response_carries_every_field_the_tool_promises(s, no_network):
    result = lookup(s["S1"]["attacker_ip"])
    for field in ("abuse_confidence_score", "total_reports", "country", "isp", "usage_type",
                  "fetched_at"):
        assert result[field] is not None, field


def test_whitelisted_decoy_keeps_its_flag(no_network):
    # 8.8.8.8 has many reports but a score of 0: the agent must see both.
    result = lookup("8.8.8.8")
    assert result["is_whitelisted"] is True
    assert result["abuse_confidence_score"] == 0
    assert result["total_reports"] > 0


@pytest.mark.parametrize("bad", ["not-an-ip", "", "999.1.1.1", "../../.env", "8.8.8.8; rm"])
def test_bad_input_is_refused_before_any_file_or_call(bad, no_network):
    with pytest.raises(ReputationError, match="is not an IP address"):
        lookup(bad, api_key=SECRET)


def test_unsaved_ip_without_a_key_fails_cleanly(tmp_path, monkeypatch, no_network):
    monkeypatch.delenv(reputation.KEY_NAME, raising=False)
    with pytest.raises(ReputationError, match="no AbuseIPDB key"):
        lookup("1.1.1.1", saved_dir=tmp_path)


def test_live_call_uses_https_and_the_key_header(tmp_path, live):
    sent = live(FakeResponse(200, {"data": {"ipAddress": "1.1.1.1", "abuseConfidenceScore": 3,
                                            "countryCode": "AU"}}))
    result = lookup("1.1.1.1", saved_dir=tmp_path, api_key=SECRET)
    assert sent["url"].startswith("https://")
    assert sent["headers"]["Key"] == SECRET
    assert SECRET not in json.dumps(sent["params"])
    assert sent["timeout"] == reputation.TIMEOUT_SECONDS
    assert result["source"] == "live"
    assert result["abuse_confidence_score"] == 3
    assert result["fetched_at"]


def test_live_answer_is_not_written_to_disk(tmp_path, live):
    live(FakeResponse(200, {"data": {"ipAddress": "1.1.1.1"}}))
    lookup("1.1.1.1", saved_dir=tmp_path, api_key=SECRET)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("response, message", [
    (requests.ConnectionError(f"failed with key {SECRET}"), "could not be reached"),
    (requests.Timeout(), "could not be reached"),
    (FakeResponse(429, {}), "daily lookup limit"),
    (FakeResponse(401, {"errors": [SECRET]}), "HTTP 401"),
    (FakeResponse(200, ValueError("not json")), "could not be read"),
    (FakeResponse(200, {"no_data": True}), "could not be read"),
])
def test_live_failures_give_a_short_message_without_the_key(tmp_path, live, response, message):
    live(response)
    with pytest.raises(ReputationError, match=message) as caught:
        lookup("1.1.1.1", saved_dir=tmp_path, api_key=SECRET)
    assert SECRET not in str(caught.value)
    # Any original error, which may hold the key, is hidden from the traceback.
    assert caught.value.__context__ is None or caught.value.__suppress_context__
