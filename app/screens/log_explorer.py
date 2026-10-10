"""Log explorer: check any claim, from an alert or from the agent, against the raw rows."""

import ipaddress

import streamlit as st

from app import shared
from login_investigator.search import export_csv, summarize

shared.header("Log explorer")

ip = st.text_input("IP address", key=shared.KEY_IP, placeholder="Any, for example 203.0.113.10",
                   help="This screen only. The other filters are in the sidebar.").strip()
if ip:
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        # The typed value is not echoed back: it is shown only in the box itself.
        st.error("That is not a valid IP address. Clear the box or enter one like 203.0.113.10.")
        st.stop()

rows = shared.filtered_rows(shared.current_filters(ip=ip or None))
if rows.empty:
    shared.show_empty()
    st.stop()

summary = summarize(rows)
tiles = st.columns(5)
tiles[0].metric("Matching events", f"{summary.total:,}")
tiles[1].metric("Successful events", f"{summary.successes:,}")
tiles[2].metric("Failed events", f"{summary.failures:,}")
tiles[3].metric("Usernames seen", f"{summary.distinct_users:,}")
tiles[4].metric("Distinct IPs", f"{summary.distinct_ips:,}")

# Every matching row, not a sample: the 20-row cap protects the agent's context, but a person
# can scroll. Log fields appear only inside the table.
# The table grows with the rows, up to a fixed height, then scrolls.
st.dataframe(shared.for_display(rows), hide_index=True, height=min(520, 35 * (len(rows) + 1) + 3))

st.download_button(
    "Download these rows (CSV)",
    data=export_csv(rows),
    file_name="login-investigator-rows.csv",
    mime="text/csv",
    icon=":material/download:",
    help="Values a spreadsheet would run as a formula get a leading apostrophe.",
)
