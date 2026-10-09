"""Investigator: ask the agent about the log, see where each answer came from, get the report.

Display rule: everything the agent or the report writer produces is shown with st.text, never as
markdown, so it cannot contain a link or an image. Tool inputs and results are shown with st.code.
A known prompt-injection escape route makes the model write an image link to an attacker's server,
which the browser would fetch on its own; plain text closes that route (PRD, Security).
"""

import re
from pathlib import Path

import streamlit as st

from app import shared
from login_investigator import agent as investigator
from login_investigator import investigations
from login_investigator.tool_views import describe
from login_investigator.tools import TOOLS

STARTERS = (
    "Anything suspicious last night?",
    "Was any account compromised this week?",
    "Which IP addresses attacked us, and how bad are they?",
)
TOOL_NAMES = {tool.name for tool in TOOLS}
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


def show_report(report: investigator.IncidentReport) -> None:
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


def show_turn(turn: investigator.Turn) -> None:
    with st.chat_message("user"):
        st.text(turn.question)
    with st.chat_message("assistant"):
        if turn.report is not None:
            show_report(turn.report)
        else:
            st.text(investigator.as_plain_text(turn.answer) or "No answer was given.")
            show_tools(turn)


def show_error(what: str) -> None:
    # The exception's text is not shown: it can be long, and it comes from outside the app.
    st.error(f"{what} The model could not be reached or returned an error. Try again.",
             icon=":material/error:")


# --- Running a question or the report ------------------------------------------------------------

def ask(agent, question: str) -> bool:
    """Ask a question and stream the answer. Returns False if it failed."""
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
                    name = piece.value if piece.value in TOOL_NAMES else "a tool"
                    status.caption(f"Running {name}…")
                else:
                    text += piece.value
                    body.text(investigator.as_plain_text(text))
        except Exception:
            status.empty()
            show_error("The agent stopped before it finished.")
            return False
    return True


def write_report(agent, model, request: str) -> bool:
    with st.chat_message("user"):
        st.text(request)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Writing the incident report…"):
                investigator.write_report(agent, model, st.session_state[KEY_CASE], request)
        except Exception:
            show_error("The report could not be written.")
            return False
    return True


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
    for case in cases:
        st.button(
            f"{literal(case.first_question)}  \n{case.started_at:%d %b %Y, %H:%M} UTC",
            key=f"case_{case.thread_id}", on_click=open_case, args=(case.thread_id,),
            width="stretch", type="primary" if case.thread_id == current else "secondary",
        )

past = investigator.history(agent, current) if current else []
for turn in past:
    show_turn(turn)

question = st.chat_input("Ask about the sign-in log")
question = question or st.session_state.pop(KEY_ASK, None)
wants_report = st.session_state.pop(KEY_REPORT, None)
# Offered only when it would add something: not twice in a row, and as an update after new answers.
report_offer = investigator.report_request(past)

# The starters or the report button. Cleared before an answer streams, or the previous run's
# buttons would stay on screen, greyed out, until the answer finished.
footer = st.empty()
if question:
    footer.empty()
    if ask(agent, question):
        st.rerun()  # redraw from memory, with the tool calls under the answer
elif wants_report and current and wants_report == report_offer:
    footer.empty()
    if write_report(agent, model, wants_report):
        st.rerun()
elif not past:
    with footer.container():
        st.caption("Ask a question below, or start with one of these:")
        for starter in STARTERS:
            st.button(starter, on_click=ask_starter, args=(starter,), icon=":material/search:")
elif report_offer:
    with footer.container():
        st.button(report_offer, icon=":material/description:", on_click=ask_for_report,
                  args=(report_offer,),
                  help=f"Sends \"{report_offer}\" and shows the report as a card.")
