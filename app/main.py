"""Login Investigator: the Streamlit entry point.

Run from the repo root:  uv run streamlit run app/main.py
"""

import sys
from pathlib import Path

# Streamlit runs this file as a script, so make the repo root importable.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app import shared  # noqa: E402

st.set_page_config(page_title="Login Investigator", page_icon=":material/shield:",
                   layout="wide")

overview = st.Page("screens/overview.py", title="Overview", icon=":material/monitoring:",
                   default=True)
alerts = st.Page("screens/alerts.py", title="Alerts", icon=":material/notifications:")
explorer = st.Page("screens/log_explorer.py", title="Log explorer", icon=":material/table:")
DASHBOARD = (overview, alerts, explorer)

page = st.navigation(list(DASHBOARD))
if st.session_state.pop(shared.KEY_GOTO_EXPLORER, False):
    st.switch_page(explorer)  # set by "Open in Log explorer" on the Alerts screen
if page in DASHBOARD:
    # The shared filters live here, outside the screens, so they keep their values when the
    # analyst switches screens. The Investigator (Phase 5) will not show them.
    shared.sidebar_filters()
page.run()
