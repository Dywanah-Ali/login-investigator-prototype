"""Investigator: ask the agent about the log, see where each answer came from, get the report.

Display rule: everything the agent or the report writer produces is shown with st.text, never as
markdown, so it cannot contain a link or an image. Tool inputs and results are shown with st.code.
A known prompt-injection escape route makes the model write an image link to an attacker's server,
which the browser would fetch on its own; plain text closes that route (PRD, Security).
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from app import shared
from login_investigator import agent as investigator
from login_investigator import investigations, report_pdf
from login_investigator.tool_views import describe

STARTERS = (
    "Anything suspicious last night?",
    "Was any account compromised this week?",
    "Which IP addresses attacked us, and how bad are they?",
)
# What the agent is doing, in plain words, while it answers. The tool's own name read like code.
PROGRESS = {
    "find_suspicious_activity": "Checking the detection rules…",
    "search_logins": "Searching the sign-in log…",
    "lookup_ip_reputation": "Looking up IP reputation…",
}
SCOPE = ("I search the sign-in log, run the detection rules and look up IP reputation, and I can "
         "write an incident report. I only read: I cannot block, change or delete anything.")
AI_NOTE = ("Answers are AI-generated and can be wrong. Check them against the tool calls under "
           "each answer.")
SEVERITY = {  # label and badge colour; the report's severity is checked against this list
    "none": ("No incident", "green"),
    "low": ("Low severity", "blue"),
    "medium": ("Medium severity", "orange"),
    "high": ("High severity", "red"),
    "critical": ("Critical severity", "red"),
}

KEY_AGENT = "investigator_agent"
KEY_MODEL = "investigator_model"
KEY_CASE = "investigator_case"  # thread id of the open case; None for a new, empty case
KEY_ASK = "investigator_ask"  # a question waiting to be asked, from a starter button
KEY_REPORT = "investigator_report"  # the report request, set when the report button is pressed
KEY_ERROR = "investigator_error"  # a failure to show after the page is redrawn
KEY_SHOWN = "investigator_cases_shown"  # how many past cases the sidebar box shows
CASES_STEP = 3  # the box shows the newest three, then three more per click
# The past-cases box: a soft shadow, an arrow-only button, and new cards that slide open instead of
# appearing at once. Styled through the `st-key-<key>` class Streamlit gives each keyed element.
# A constant written here, never log data or model output.
CASES_STYLE = """<style>
.st-key-past_cases {
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28), 0 1px 3px rgba(0, 0, 0, 0.18);
}
.st-key-past_cases [class*="st-key-case_"] {
    overflow: hidden;
    animation: case-open 320ms ease-out both;
}
@keyframes case-open {
    from { opacity: 0; max-height: 0; transform: translateY(-6px); }
    to { opacity: 1; max-height: 160px; transform: none; }
}
.st-key-cases_more button, .st-key-cases_fewer button { justify-content: center; }
.st-key-cases_more [data-testid="stIconMaterial"],
.st-key-cases_fewer [data-testid="stIconMaterial"] { font-size: 1.9rem; }
@media (prefers-reduced-motion: reduce) {
    .st-key-past_cases [class*="st-key-case_"] { animation: none; }
}
</style>"""


@st.cache_resource(show_spinner=False)
def memory(path: str):
    """One connection to the memory file per app process, shared by every browser session."""
    return investigations.open_memory(Path(path))


def agent_and_model():
    """The agent is built once per browser session, so Streamlit's reruns never reset it."""
    if KEY_AGENT not in st.session_state:
        model = investigator.make_model()
        st.session_state[KEY_MODEL] = model
        st.session_state[KEY_AGENT] = investigator.build_agent(
            model, memory(str(investigations.MEMORY_PATH)))
    return st.session_state[KEY_AGENT], st.session_state[KEY_MODEL]


def literal(text: str) -> str:
    """Escape markdown, for the few widgets whose labels are always markdown (buttons)."""
    return re.sub(r"([\\`*_{}\[\]()<>#+\-.!|~$:])", r"\\\1", text)


def new_case() -> None:
    st.session_state[KEY_CASE] = None


def open_case(thread_id: str) -> None:
    st.session_state[KEY_CASE] = thread_id


def show_more_cases() -> None:
    st.session_state[KEY_SHOWN] = st.session_state.get(KEY_SHOWN, CASES_STEP) + CASES_STEP


def show_fewer_cases() -> None:
    st.session_state[KEY_SHOWN] = CASES_STEP


def cases_to_show(cases: list, current: str | None) -> int:
    """The newest three, plus three per click, and always enough to include the open case."""
    shown = st.session_state.get(KEY_SHOWN, CASES_STEP)
    ids = [case.thread_id for case in cases]
    if current in ids and ids.index(current) >= shown:
        shown = (ids.index(current) // CASES_STEP + 1) * CASES_STEP
        st.session_state[KEY_SHOWN] = shown
    return shown


def ask_starter(question: str) -> None:
    st.session_state[KEY_ASK] = question


def ask_for_report(request: str) -> None:
    st.session_state[KEY_REPORT] = request


# --- Display -------------------------------------------------------------------------------------

def show_tools(turn: investigator.Turn) -> None:
    """What each tool was asked and what it returned, in plain lines written by code, with log
    rows in a table and the raw JSON one switch away (the author's choice, 9 Oct)."""
    if not turn.tools:
        return
    with st.expander(shared.count(len(turn.tools), "tool call"), icon=":material/build:"):
        for number, use in enumerate(turn.tools):
            view = describe(use.name, use.args, use.result)
            if number:
                st.divider()
            st.markdown(f"**{view.title}**")  # a fixed title from TITLES, never tool data
            st.text(f"Asked:  {view.asked}\nFound:  {view.found}")
            if view.rows is not None:
                st.dataframe(view.rows, hide_index=True,
                             height=min(36 * (len(view.rows) + 1) + 2, 300))
            if st.toggle("Show raw data", key=f"raw_{use.call_id or number}"):
                st.code(view.raw, language="json", height=250, wrap_lines=True)


def show_report(report: investigator.IncidentReport, case_id: str, number: int) -> None:
    label, colour = SEVERITY[report.severity]
    with st.container(border=True):
        st.caption("Incident report")
        st.text(report.title)
        st.badge(label, color=colour)
        sections = (
            ("Summary", report.summary),
            ("Attacker IPs", "\n".join(report.attacker_ips) or "None"),
            ("Affected users", "\n".join(report.affected_users) or "None"),
            ("Timeline (UTC)", "\n".join(f"{e.time_utc}  {e.event}" for e in report.timeline)
             or "None"),
            ("Evidence", "\n".join(f"- {item}" for item in report.evidence) or "None"),
            ("Recommended next steps",
             "\n".join(f"{n}. {step}" for n, step in enumerate(report.recommended_next_steps, 1))
             or "None"),
        )
        for heading, body in sections:
            st.caption(heading)
            st.text(body)
        # Built only when clicked. The PDF is plain text with no links or images (PRD, Security).
        st.download_button(
            "Download PDF",
            data=lambda: report_pdf.build(report, case_id, datetime.now(timezone.utc)),
            file_name=report_pdf.file_name(case_id, number), mime="application/pdf",
            key=f"pdf_{case_id}_{number}", on_click="ignore", icon=":material/download:",
        )


def show_turn(turn: investigator.Turn, case_id: str, reports: int) -> None:
    """reports: how many reports the case holds up to and including this turn."""
    with st.chat_message("user"):
        st.text(turn.question)
    with st.chat_message("assistant"):
        if turn.report is not None:
            show_report(turn.report, case_id, reports)
        else:
            st.text(investigator.as_plain_text(turn.answer) or "No answer was given.")
            show_tools(turn)


def fail(what: str) -> None:
    """Keep the failure for the redraw that follows, so the input is never left locked."""
    st.session_state[KEY_ERROR] = what


def show_error(what: str) -> None:
    # The exception's text is not shown: it can be long, and it comes from outside the app.
    st.error(f"{what} The model could not be reached or returned an error. Try again.",
             icon=":material/error:")


# --- Running a question or the report ------------------------------------------------------------

def ask(agent, question: str) -> None:
    """Ask a question and stream the answer. A failure is kept for the redraw."""
    if st.session_state.get(KEY_CASE) is None:
        st.session_state[KEY_CASE] = investigations.start(
            question, investigations.MEMORY_PATH).thread_id
    with st.chat_message("user"):
        st.text(question)
    with st.chat_message("assistant"):
        status, body, text = st.empty(), st.empty(), ""
        status.caption("Thinking…")
        try:
            for piece in investigator.ask(agent, st.session_state[KEY_CASE], question):
                if piece.kind == "tool":
                    status.caption(PROGRESS.get(piece.value, "Using a tool…"))
                else:
                    text += piece.value
                    body.text(investigator.as_plain_text(text))
        except Exception:
            status.empty()
            fail("The agent stopped before it finished.")


def write_report(agent, model, request: str) -> None:
    with st.chat_message("user"):
        st.text(request)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Writing the incident report…"):
                investigator.write_report(agent, model, st.session_state[KEY_CASE], request)
        except Exception:
            fail("The report could not be written.")


# --- The page ------------------------------------------------------------------------------------

shared.header("Investigator")

try:
    agent, model = agent_and_model()
except RuntimeError as error:  # no key: make_model's message names the setting, never a value
    st.error(str(error), icon=":material/key_off:")
    st.stop()

cases = investigations.list_all(investigations.MEMORY_PATH)
current = st.session_state.setdefault(KEY_CASE, None)

with st.sidebar:
    st.button("New investigation", icon=":material/add:", on_click=new_case, width="stretch",
              type="primary" if current is None else "secondary")
    st.subheader("Past investigations")
    if not cases:
        st.caption("None yet. Ask a question to start one.")
    else:
        # One box: the newest cases, and an arrow on its bottom edge that shows three more.
        shown = cases_to_show(cases, current)
        st.html(CASES_STYLE)
        with st.container(border=True, key="past_cases"):
            for case in cases[:shown]:
                st.button(
                    f"{literal(case.first_question)}  \n{case.started_at:%d %b %Y, %H:%M} UTC",
                    key=f"case_{case.thread_id}", on_click=open_case, args=(case.thread_id,),
                    width="stretch", type="primary" if case.thread_id == current else "secondary",
                )
            hidden = len(cases) - shown
            if hidden > 0:
                st.button("", key="cases_more", icon=":material/expand_more:", type="tertiary",
                          help=f"Show {min(hidden, CASES_STEP)} more", width="stretch",
                          on_click=show_more_cases)
            elif len(cases) > CASES_STEP:
                st.button("", key="cases_fewer", icon=":material/expand_less:", type="tertiary",
                          help="Show fewer", width="stretch", on_click=show_fewer_cases)

past = investigator.history(agent, current) if current else []
reports = 0
for turn in past:
    reports += turn.report is not None
    show_turn(turn, current, reports)

# Locked while an answer is written: a message sent mid-answer would cut the answer off (B-025).
# submit_mode covers typed questions; `disabled` covers the starter and report buttons.
busy = KEY_ASK in st.session_state or KEY_REPORT in st.session_state
question = st.chat_input("Ask about the sign-in log", submit_mode="disable", disabled=busy)
question = question or st.session_state.pop(KEY_ASK, None)
wants_report = st.session_state.pop(KEY_REPORT, None)
# Offered only when it would add something: not twice in a row, and as an update after new answers.
report_offer = investigator.report_request(past)

# The answer being written, then the starters or the report button. A container, so the AI note
# below stays last, just above the input.
live = st.container()
st.caption(AI_NOTE)

# The starters or the report button. Cleared before an answer streams, or the previous run's
# buttons would stay on screen, greyed out, until the answer finished.
with live:
    if failure := st.session_state.pop(KEY_ERROR, None):
        show_error(failure)
    footer = st.empty()
    if question:
        footer.empty()
        ask(agent, question)
        st.rerun()  # redraw from memory, with the tool calls under the answer, and unlock the input
    elif wants_report and current and wants_report == report_offer:
        footer.empty()
        write_report(agent, model, wants_report)
        st.rerun()
    elif not past:
        with footer.container():
            st.markdown(SCOPE)
            st.caption("Ask a question below, or start with one of these:")
            for starter in STARTERS:
                st.button(starter, on_click=ask_starter, args=(starter,),
                          icon=":material/search:")
    elif report_offer:
        with footer.container():
            st.button(report_offer, icon=":material/description:", on_click=ask_for_report,
                      args=(report_offer,),
                      help=f"Sends \"{report_offer}\" and shows the report as a card.")
