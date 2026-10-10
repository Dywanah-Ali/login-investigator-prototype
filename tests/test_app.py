"""The dashboard screens, run headless with Streamlit's own test tool.

One test per PRD dashboard acceptance criterion, plus the display-safety rules. Expected values
come from evals/ground_truth.json.
"""

import re

import pytest
from streamlit.testing.v1 import AppTest

from app import shared
from login_investigator.search import filter_logins

SCREENS = ("screens/overview.py", "screens/alerts.py", "screens/log_explorer.py")
# What a tile counts is said in its label; the value is the bare number (UI polish, 10 Oct).
COUNTED = ("attempts", "events", "usernames", "ips", "alerts")
BARE_NUMBER = re.compile(r"\d{1,3}(,\d{3})*")


def start(screen=SCREENS[0]):
    at = AppTest.from_file("../app/main.py", default_timeout=60)
    at.run()
    if screen != SCREENS[0]:
        at.switch_page(screen).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def metrics(at):
    return {m.label: m.value for m in at.metric}


def alert_table(at):
    return at.dataframe[0].value


def info_texts(at):
    return [i.value for i in at.info]


@pytest.mark.parametrize("screen", SCREENS)
def test_every_screen_loads_with_the_synthetic_label_and_capture_date(screen):
    at = start(screen)
    assert any("Synthetic data" in m.value for m in at.markdown)
    assert any("Log captured 8 Oct 2026, 09:00 UTC" in c.value for c in at.caption)


@pytest.mark.parametrize("screen", ("screens/overview.py", "screens/log_explorer.py"))
def test_every_metric_says_what_it_counts_in_its_label(screen):
    at = start(screen)
    assert at.metric
    for label, value in metrics(at).items():
        assert any(word in label.lower() for word in COUNTED), f"{label!r} names no counted thing"
        assert BARE_NUMBER.fullmatch(value), f"{label}: {value!r} is not a bare number"


def test_overview_counts_match_the_core(log, truth):
    at = start()
    m = metrics(at)
    assert m["Sign-in attempts"] == f"{truth['row_count']:,}"
    assert m["Alerts"] == "5"


def test_s1_to_s4_appear_on_the_alerts_screen(s):
    table = alert_table(start("screens/alerts.py"))
    rows = set(zip(table["Rule"], table["IP addresses"]))
    assert ("Brute force", s["S1"]["attacker_ip"]) in rows
    assert ("Password spraying", s["S2"]["attacker_ip"]) in rows
    assert ("Success after repeated failures", s["S3"]["attacker_ip"]) in rows
    assert ("Sign-in from a new country", s["S4"]["ip"]) in rows


def test_alerts_are_listed_newest_first():
    table = alert_table(start("screens/alerts.py"))
    assert list(table["Last seen (UTC)"]) == sorted(table["Last seen (UTC)"], reverse=True)


def test_a_filter_change_updates_every_screen_consistently(log, s):
    """Set one filter, then visit each screen: all three agree with the core."""
    user = s["S4"]["user"]
    expected = len(filter_logins(log, user=user))
    at = start()
    at.selectbox(key=shared.KEY_USER).set_value(user).run()
    assert metrics(at)["Sign-in attempts"] == f"{expected:,}"

    at.switch_page("screens/alerts.py").run()
    table = alert_table(at)
    assert list(table["Rule"]) == ["Sign-in from a new country"]

    at.switch_page("screens/log_explorer.py").run()
    assert metrics(at)["Matching events"] == f"{expected:,}"
    assert at.selectbox(key=shared.KEY_USER).value == user  # the filter survived the switch


@pytest.mark.parametrize("screen", SCREENS)
def test_an_empty_filter_shows_a_clear_message(screen, s):
    at = start(screen)
    # An unknown username tried by the spraying attacker never succeeded.
    at.selectbox(key=shared.KEY_USER).set_value(s["S2"]["unknown_usernames"][0])
    at.selectbox(key=shared.KEY_OUTCOME).set_value("success").run()
    assert not at.exception
    assert any("match these filters" in text for text in info_texts(at))
    assert not at.get("plotly_chart")


def test_reset_restores_the_whole_log(truth, s):
    at = start()
    at.selectbox(key=shared.KEY_USER).set_value(s["S4"]["user"]).run()
    at.button[0].click().run()
    assert metrics(at)["Sign-in attempts"] == f"{truth['row_count']:,}"


def test_open_in_log_explorer_points_at_the_alert(log, s):
    at = start("screens/alerts.py")
    day = s["S1"]["first_seen"][:10]
    shared_state = {
        shared.KEY_DATES: (__import__("datetime").date.fromisoformat(day),) * 2,
        shared.KEY_IP: s["S1"]["attacker_ip"],
        shared.KEY_GOTO_EXPLORER: True,
    }
    for key, value in shared_state.items():
        at.session_state[key] = value
    at.run()
    assert at.title[0].value == "Log explorer"
    expected = len(filter_logins(log, ip=s["S1"]["attacker_ip"], start=day,
                                 end=f"{day}T23:59:59Z"))
    assert metrics(at)["Matching events"] == f"{expected:,}"


def test_an_invalid_ip_is_refused_without_echoing_it():
    at = start("screens/log_explorer.py")
    at.text_input(key=shared.KEY_IP).set_value("<b>not-an-ip</b>").run()
    assert at.error
    assert all("not-an-ip" not in e.value for e in at.error)
    assert not at.dataframe


def test_log_text_never_appears_as_formatted_text(s, log):
    """Usernames and the S5 text may appear only inside tables, never in markdown or captions."""
    usernames = set(log["username"])
    for screen in SCREENS:
        at = start(screen)
        texts = [m.value for m in at.markdown] + [c.value for c in at.caption]
        for text in texts:
            assert s["S5"]["text"] not in text
            assert not any(name in text for name in usernames), text


def test_counts_use_the_right_singular_or_plural():
    assert shared.count(1, "event") == "1 event"
    assert shared.count(1856, "event") == "1,856 events"
    assert shared.count(1, "IP") == "1 IP"
    assert shared.count(0, "finding") == "0 findings"


def test_one_matching_event_shows_ones(log, s):
    at = start("screens/log_explorer.py")
    at.text_input(key=shared.KEY_IP).set_value(s["S4"]["ip"]).run()
    m = metrics(at)
    assert m["Matching events"] == "1"
    assert m["Distinct IPs"] == "1"
    assert set(m) == {"Matching events", "Successful events", "Failed events", "Usernames seen",
                      "Distinct IPs"}
