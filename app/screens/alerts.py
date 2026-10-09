"""Alerts: what the rules caught, why each alert fired, and a one-step check of the evidence."""

from collections import Counter

import pandas as pd
import streamlit as st

from app import shared
from login_investigator.rules import (
    GENERAL_ASSUMPTIONS,
    RULE_GUIDE,
    RULE_TITLES,
    findings_matching,
)

shared.header("Alerts")

TIME = "%Y-%m-%d %H:%M"
MAX_NAMES = 3

rows = shared.filtered_rows(shared.current_filters())
findings = findings_matching(shared.all_findings(), rows) if not rows.empty else []
findings = sorted(findings, key=lambda f: (f.last_seen, f.rule), reverse=True)  # newest first


def names(values: tuple[str, ...]) -> str:
    if len(values) <= MAX_NAMES:
        return ", ".join(values)
    return f"{', '.join(values[:MAX_NAMES])} and {len(values) - MAX_NAMES} more"


if not findings:
    shared.show_empty("alerts")
else:
    by_rule = Counter(RULE_TITLES[f.rule] for f in findings)
    st.markdown(f"**{len(findings)} alerts in the selected period** · "
                + " · ".join(f"{title}: {n}" for title, n in sorted(by_rule.items())))

    # Log values (summary, IPs, users) appear only inside this table, never as formatted text.
    table = pd.DataFrame({
        "Rule": [RULE_TITLES[f.rule] for f in findings],
        "Summary": [f.summary for f in findings],
        "IP addresses": [names(f.ips) for f in findings],
        "Users": [names(f.users) for f in findings],
        "Events": [f.event_count for f in findings],
        "First seen (UTC)": [f.first_seen.strftime(TIME) for f in findings],
        "Last seen (UTC)": [f.last_seen.strftime(TIME) for f in findings],
    })
    widths = {"Rule": "medium", "Summary": "large", "IP addresses": "small", "Users": "small",
              "Events": "small", "First seen (UTC)": "small", "Last seen (UTC)": "small"}
    # The key changes with the list, so a filter change never leaves a stale row selected.
    list_key = "alerts_" + str(abs(hash(tuple(f.row_ids[0] for f in findings))))
    picked = st.dataframe(
        table, hide_index=True, on_select="rerun", selection_mode="single-row", key=list_key,
        column_config={name: st.column_config.Column(width=w) for name, w in widths.items()},
    )

    if not picked.selection.rows:
        st.caption("Select an alert to see its evidence.")
    else:
        finding = findings[picked.selection.rows[0]]
        st.subheader(RULE_TITLES[finding.rule])
        st.caption(f"Showing {len(finding.evidence)} of {finding.event_count} events"
                   + (": the first and the last ones." if finding.event_count > len(
                       finding.evidence) else "."))
        evidence = pd.DataFrame(list(finding.evidence))
        st.dataframe(evidence, hide_index=True)
        st.button(
            "Open in Log explorer",
            icon=":material/table:",
            on_click=shared.open_in_explorer,
            args=(finding.ips[0], finding.first_seen.date(), finding.last_seen.date()),
            help="Shows every row from this IP address on the alert's dates.",
        )

with st.expander("How these rules work"):
    for guide in RULE_GUIDE:
        st.markdown(f"**{guide.title}.** Fires when: {guide.fires_when}  \n"
                    f"*Assumption:* {guide.assumption}")
    st.markdown("\n".join(f"- {line}" for line in GENERAL_ASSUMPTIONS))
