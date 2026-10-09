"""Pieces every dashboard screen shares: cached data, the header, the filters, empty results.

Display rule: log fields (usernames, user agents and so on) are shown only inside tables
(st.dataframe), never as formatted text. The S5 rows carry planted instructions, and a table shows
them as harmless plain text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from login_investigator.generator import CAPTURED_AT
from login_investigator.loader import TIMESTAMP_FORMAT, load_log
from login_investigator.rules import detect_all
from login_investigator.search import filter_logins

ALL = "All"
OUTCOMES = (ALL, "success", "failure")

# Filter widget keys, kept in session state so the filters survive switching screens.
KEY_DATES = "filter_dates"
KEY_OUTCOME = "filter_outcome"
KEY_COUNTRY = "filter_country"
KEY_USER = "filter_user"
KEY_IP = "filter_ip"  # Log explorer only
KEY_GOTO_EXPLORER = "goto_explorer"

# Chart colours: categorical slots 1 and 2 of the reference palette, validated as a pair in
# light and dark mode (CVD and normal-vision separation, contrast). Failed is always orange.
COLOURS = {
    "light": {"success": "#2a78d6", "failure": "#eb6834"},
    "dark": {"success": "#3987e5", "failure": "#d95926"},
}


@st.cache_data(show_spinner="Loading the log…")
def log() -> pd.DataFrame:
    return load_log()


@st.cache_data(show_spinner="Running the detection rules…")
def all_findings():
    """Every finding on the whole log. The rules need each user's full history, so they run
    once on everything; the filters then only select from the results."""
    return detect_all(log())


def log_dates() -> tuple[date, date]:
    times = log()["timestamp_utc"]
    return times.min().date(), times.max().date()


def colours() -> dict[str, str]:
    theme = getattr(st.context.theme, "type", None)
    return COLOURS["dark" if theme == "dark" else "light"]


def header(title: str) -> None:
    st.title(title)
    st.badge("Synthetic data", icon=":material/science:", color="violet")
    st.caption(
        f"Log captured {CAPTURED_AT.day} {CAPTURED_AT:%b %Y, %H:%M} UTC. "
        "The app treats this as today. "
        "All times are UTC."
    )


def _reset_filters() -> None:
    st.session_state[KEY_DATES] = log_dates()
    st.session_state[KEY_OUTCOME] = ALL
    st.session_state[KEY_COUNTRY] = ALL
    st.session_state[KEY_USER] = ALL
    st.session_state[KEY_IP] = ""


def sidebar_filters() -> None:
    """The shared filters. Rendered once by the entry point, before the screen runs."""
    first, last = log_dates()
    df = log()
    st.session_state.setdefault(KEY_DATES, (first, last))
    with st.sidebar:
        st.header("Filters")
        st.date_input("Date range (UTC)", key=KEY_DATES, min_value=first, max_value=last)
        st.selectbox("Outcome", OUTCOMES, key=KEY_OUTCOME,
                     format_func=lambda v: v if v == ALL else v.capitalize())
        st.selectbox("Country", (ALL, *sorted(df["country"].unique())), key=KEY_COUNTRY)
        st.selectbox("User", (ALL, *sorted(df["username"].unique())), key=KEY_USER)
        st.button("Reset filters", on_click=_reset_filters, width="stretch")


@dataclass(frozen=True)
class Filters:
    start: pd.Timestamp | None
    end: pd.Timestamp | None
    outcome: str | None
    country: str | None
    user: str | None
    ip: str | None = None


def current_filters(ip: str | None = None) -> Filters:
    def chosen(key):
        value = st.session_state.get(key, ALL)
        return None if value == ALL else value

    dates = st.session_state.get(KEY_DATES) or log_dates()
    if len(dates) == 1:  # the picker returns one date while a range is half chosen
        dates = (dates[0], dates[0])
    start = pd.Timestamp(dates[0], tz="UTC")
    end = pd.Timestamp(dates[1], tz="UTC") + timedelta(days=1)
    return Filters(start, end, chosen(KEY_OUTCOME), chosen(KEY_COUNTRY), chosen(KEY_USER), ip)


def filtered_rows(filters: Filters) -> pd.DataFrame:
    return filter_logins(log(), user=filters.user, ip=filters.ip, start=filters.start,
                         end=filters.end, outcome=filters.outcome, country=filters.country)


def show_empty(what: str = "sign-ins") -> None:
    st.info(f"No {what} match these filters. Widen the date range or press Reset filters.",
            icon=":material/filter_alt_off:")


def open_in_explorer(ip: str, first: date, last: date) -> None:
    """Button callback on the Alerts screen: point the Log explorer at one alert."""
    st.session_state[KEY_DATES] = (first, last)
    st.session_state[KEY_OUTCOME] = ALL
    st.session_state[KEY_COUNTRY] = ALL
    st.session_state[KEY_USER] = ALL
    st.session_state[KEY_IP] = ip
    st.session_state[KEY_GOTO_EXPLORER] = True


def for_display(rows: pd.DataFrame) -> pd.DataFrame:
    """Rows ready for a table: readable UTC times, newest first, raw values otherwise."""
    shown = rows.sort_values("timestamp_utc", ascending=False, kind="stable").copy()
    shown["timestamp_utc"] = shown["timestamp_utc"].dt.strftime(TIMESTAMP_FORMAT)
    return shown.reset_index(drop=True)


def count(n: int, unit: str) -> str:
    """A number with its unit, singular or plural: "1 event", "1,856 events", "1 IP"."""
    return f"{n:,} {unit if n == 1 else unit + 's'}"
