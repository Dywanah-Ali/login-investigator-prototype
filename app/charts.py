"""The Overview charts, as plain functions that build Plotly figures.

Only validated values reach a chart: times, counts, outcomes and IP addresses (checked by the
loader). Free-text log fields never become labels, so the planted S5 text cannot reach a chart.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

OUTCOME_LABELS = {"success": "Successful", "failure": "Failed"}


def hourly_bars(counts: pd.DataFrame, colours: dict[str, str]) -> go.Figure:
    """Stacked bars of sign-in attempts per UTC hour: successful below, failed on top."""
    fig = go.Figure()
    for outcome in ("success", "failure"):
        part = counts[counts["outcome"] == outcome]
        fig.add_bar(
            x=part["hour"],
            y=part["events"],
            name=OUTCOME_LABELS[outcome],
            marker_color=colours[outcome],
            hovertemplate="%{x|%d %b, %H:00} UTC<br>" + OUTCOME_LABELS[outcome]
            + ": %{y} events<extra></extra>",
        )
    fig.update_layout(
        barmode="stack",
        bargap=0.1,
        barcornerradius=2,
        height=360,
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        hovermode="closest",
    )
    fig.update_xaxes(title="Hour (UTC)", showgrid=False)
    fig.update_yaxes(title="Sign-in attempts (events)", rangemode="tozero")
    return fig


def top_ips_bars(table: pd.DataFrame, colour: str) -> go.Figure:
    """Horizontal bars of failed sign-ins per source IP, the most failures at the top."""
    fig = go.Figure(go.Bar(
        x=table["failures"],
        y=table["source_ip"],
        orientation="h",
        marker_color=colour,
        customdata=table["accounts"],
        hovertemplate="%{y}<br>Failed sign-ins: %{x} events<br>Accounts tried: %{customdata}"
        "<extra></extra>",
    ))
    fig.update_layout(
        bargap=0.25,
        barcornerradius=2,
        height=max(160, 34 * len(table) + 60),
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
    )
    fig.update_yaxes(title=None, autorange="reversed", type="category")
    fig.update_xaxes(title="Failed sign-ins (events)", rangemode="tozero")
    return fig
