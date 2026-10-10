"""The Investigator screen, run headless with a fake model and a temporary memory file.

These tests check the screen's plumbing and display rules. The real agent's answers are checked
live (Gate 2) and by the evals.
"""

import pytest
from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest

from login_investigator import agent as investigator
from login_investigator import investigations
from tests.test_agent import REPORT, FakeModel, tool_call

PAGE = "screens/investigator.py"
INJECTED = "![x](https://attacker.example/leak.png) [click](https://attacker.example)"


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """Point the screen at a temporary memory file and a fake model; count model builds."""
    monkeypatch.setattr(investigations, "MEMORY_PATH", tmp_path / "memory.sqlite")
    built = []

    def make_model():
        built.append(1)
        return FakeModel(responses=[
            tool_call("search_logins", {"ip": "185.218.86.24"}),
            AIMessage(f"**150** failures from 185.218.86.24. {INJECTED}"),
            AIMessage("No other sign-ins."),
        ])

    monkeypatch.setattr(investigator, "make_model", make_model)
    return built


def open_page():
    at = AppTest.from_file("../app/main.py", default_timeout=60)
    at.run()
    at.switch_page(PAGE).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def click(at, label):
    [button] = [b for b in at.button if b.label == label]
    button.click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def texts(at):
    return [t.value for t in at.text]


def test_empty_case_shows_the_header_and_starters_but_no_filters(fake):
    at = open_page()
    assert any("Synthetic data" in m.value for m in at.markdown)
    assert any("Log captured 8 Oct 2026, 09:00 UTC" in c.value for c in at.caption)
    labels = [b.label for b in at.button]
    assert "Anything suspicious last night?" in labels
    assert "New investigation" in labels
    assert not at.sidebar.date_input  # the dashboard filters are not on this page
    assert "Write the incident report" not in labels


def test_a_starter_asks_and_shows_the_answer_as_plain_text(fake):
    at = click(open_page(), "Anything suspicious last night?")
    assert "Anything suspicious last night?" in texts(at)
    answer = f"150 failures from 185.218.86.24. {INJECTED}"
    assert answer in texts(at)  # markdown markers removed, nothing rendered
    # The agent's text never reaches a widget that renders markdown, links or images.
    for widget in (*at.markdown, *at.caption):
        assert "attacker.example" not in widget.value


def test_tool_calls_are_listed_under_the_answer_in_plain_words(fake):
    at = click(open_page(), "Anything suspicious last night?")
    [expander] = at.expander
    assert expander.label == "1 tool call"
    assert any("Sign-in search" in m.value for m in at.markdown)
    lines = "\n".join(texts(at))
    assert "Asked:  IP 185.218.86.24, all times" in lines
    assert "Found:  151 events: 150 failed, 1 succeeded" in lines
    # The log rows are in a table, and the raw JSON is hidden until asked for.
    assert any("username" in d.value.columns for d in at.dataframe)
    assert not at.code
    at.toggle[0].set_value(True).run()
    assert any('"failures": 150' in c.value for c in at.code)


def test_the_case_is_listed_in_the_sidebar(fake):
    at = click(open_page(), "Anything suspicious last night?")
    assert any(b.label.startswith("Anything suspicious last night") for b in at.sidebar.button)


def test_the_agent_is_built_once_per_session(fake):
    at = click(open_page(), "Anything suspicious last night?")
    at.chat_input[0].set_value("Anything else?").run()
    assert "No other sign-ins." in texts(at)
    assert len(fake) == 1


def test_the_report_button_shows_every_fixed_field(fake):
    at = click(click(open_page(), "Anything suspicious last night?"),
               "Write the incident report")
    assert investigator.REPORT_REQUEST in texts(at)
    shown = "\n".join(texts(at))
    assert REPORT.title in shown
    assert REPORT.summary in shown
    assert "185.218.86.24" in shown
    assert "daniel.hughes" in shown
    assert "2026-10-08T02:32:20Z  Attacker signed in" in shown
    assert "- 150 failures (find_suspicious_activity)" in shown
    assert "1. Block 185.218.86.24" in shown
    captions = [c.value for c in at.caption]
    for heading in ("Summary", "Attacker IPs", "Affected users", "Timeline (UTC)", "Evidence",
                    "Recommended next steps"):
        assert heading in captions
    assert any("Critical severity" in m.value for m in at.markdown)  # the badge


def test_a_past_case_reopens_and_new_starts_empty(fake):
    at = click(open_page(), "Anything suspicious last night?")
    click(at, "New investigation")
    assert "Anything suspicious last night?" not in texts(at)
    [past] = at.sidebar.button[1:]
    past.click().run()
    assert "Anything suspicious last night?" in texts(at)


def test_a_missing_key_gives_a_clear_message(monkeypatch, tmp_path):
    monkeypatch.setattr(investigations, "MEMORY_PATH", tmp_path / "memory.sqlite")
    monkeypatch.setattr(investigator, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv(investigator.KEY_NAME, raising=False)
    at = open_page()
    assert any("OPENROUTER_API_KEY is not set" in e.value for e in at.error)


def labels(at):
    return [b.label for b in at.button]


def test_the_report_button_waits_for_something_new(fake):
    at = click(click(open_page(), "Anything suspicious last night?"),
               "Write the incident report")
    # Right after a report there is nothing new to report.
    assert "Write the incident report" not in labels(at)
    assert "Update the incident report" not in labels(at)

    at.chat_input[0].set_value("Anything else?").run()
    assert "Update the incident report" in labels(at)

    click(at, "Update the incident report")
    assert "Update the incident report" in texts(at)  # the request, shown in the chat
    assert texts(at).count(REPORT.title) == 2  # the first report stays, the update is added
    assert "Update the incident report" not in labels(at)


def downloads(at):
    return at.get("download_button")


def test_each_report_card_offers_its_own_pdf(fake):
    at = click(open_page(), "Anything suspicious last night?")
    assert not downloads(at)  # no report yet, no PDF

    click(at, "Write the incident report")
    [first] = downloads(at)
    assert first.proto.label == "Download PDF"
    assert first.proto.deferred_file_id  # built only when clicked

    at.chat_input[0].set_value("Anything else?").run()
    click(at, "Update the incident report")
    ids = [d.proto.id for d in downloads(at)]
    assert len(ids) == 2 and len(set(ids)) == 2
    assert ids[0].endswith("_1") and ids[1].endswith("_2")  # the number in the file name
