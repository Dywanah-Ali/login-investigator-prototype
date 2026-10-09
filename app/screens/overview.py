"""Overview: make the overnight spike impossible to miss."""

import streamlit as st

from app import charts, shared
from login_investigator.rules import findings_matching
from login_investigator.search import summarize
from login_investigator.stats import hourly_counts, top_failed_ips

shared.header("Overview")

filters = shared.current_filters()
rows = shared.filtered_rows(filters)
if rows.empty:
    shared.show_empty()
    st.stop()

summary = summarize(rows)
alerts = findings_matching(shared.all_findings(), rows)
failed_share = summary.failures / summary.total

tiles = st.columns(4)
tiles[0].metric("Sign-in attempts", shared.count(summary.total, "event"))
tiles[1].metric("Failed attempts", shared.count(summary.failures, "event"))
tiles[1].caption(f"{failed_share:.1%} of attempts")
tiles[2].metric("Usernames seen", shared.count(summary.distinct_users, "username"),
                help="Includes usernames that do not exist, such as ones an attacker guessed.")
tiles[3].metric("Alerts", shared.count(len(alerts), "finding"),
                help="Findings from the detection rules with at least one event in this view. "
                     "Details on the Alerts screen.")

colours = shared.colours()

st.subheader("Sign-in attempts per hour")
st.plotly_chart(charts.hourly_bars(hourly_counts(rows), colours), key="hourly")

st.subheader("Top source IPs by failed sign-ins")
top = top_failed_ips(rows)
if top.empty:
    shared.show_empty("failed sign-ins")
else:
    st.plotly_chart(charts.top_ips_bars(top, colours["failure"]), key="top_ips")
