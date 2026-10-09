"""Tool calls in plain words, for the "tool calls" panel under each answer.

Each call becomes a title, one line for what was asked, one line for what came back, and, where
there are log rows, a table. Code writes these lines from the tool's JSON, never the model, so
the panel shows exactly what the agent read. The raw JSON stays available for checking.

Values from the log and from AbuseIPDB appear here as they are. The screen shows these lines as
plain text and the rows only inside tables (PRD, Security).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from login_investigator.loader import parse_utc
from login_investigator.rules import RULE_TITLES

TITLES = {
    "find_suspicious_activity": "Detection rules",
    "search_logins": "Sign-in search",
    "lookup_ip_reputation": "IP reputation",
}


@dataclass(frozen=True)
class ToolView:
    title: str
    asked: str
    found: str
    rows: pd.DataFrame | None  # a table for the screen, or None
    raw: str  # the tool's result, pretty-printed when it is JSON


def describe(name: str, args: dict, result: str) -> ToolView:
    try:
        parsed = json.loads(result)
        raw = json.dumps(parsed, indent=1)
    except ValueError:
        parsed, raw = None, result
    title = TITLES.get(name, "Unknown tool")
    asked = _asked(name, args)
    if not isinstance(parsed, dict):
        return ToolView(title, asked, "The result could not be read.", None, raw)
    if "error" in parsed:
        return ToolView(title, asked, f"Error: {parsed['error']}", None, raw)
    data = parsed.get("data")
    if not isinstance(data, dict):
        return ToolView(title, asked, "The result could not be read.", None, raw)
    found, rows = _FOUND.get(name, _unknown)(data)
    return ToolView(title, asked, found, rows, raw)


# --- What was asked ------------------------------------------------------------------------------

def _time(value) -> str:
    """"2026-10-07T18:00:00Z" as "7 Oct 18:00". Anything else, such as "today", is shown as it
    came: the strict parser never reads the computer's clock."""
    try:
        moment = parse_utc(value, "time")
    except ValueError:
        return repr(value)
    return f"{moment.day} {moment:%b %H:%M}"


def _window(args: dict) -> str | None:
    start, end = args.get("start") or None, args.get("end") or None
    if start is None and end is None:
        return None
    if end is None:
        return f"from {_time(start)} UTC"
    if start is None:
        return f"until {_time(end)} UTC"
    return f"{_time(start)} → {_time(end)} UTC"


def _asked(name: str, args: dict) -> str:
    if name == "find_suspicious_activity":
        return _window(args) or "the whole log"
    if name == "search_logins":
        parts = [f"{label} {args[key]}" for key, label in
                 (("user", "user"), ("ip", "IP"), ("outcome", "outcome"), ("country", "country"))
                 if args.get(key)]
        parts.append(_window(args) or "all times")
        return ", ".join(parts)
    if name == "lookup_ip_reputation":
        return str(args.get("ip", ""))
    return json.dumps(args)


# --- What came back ------------------------------------------------------------------------------

def _count(n: int, unit: str) -> str:
    return f"{n:,} {unit if n == 1 else unit + 's'}"


def _findings(data: dict) -> tuple[str, pd.DataFrame | None]:
    findings = data.get("findings") or []
    if not findings:
        return "No findings in this window.", None
    titles = ", ".join(dict.fromkeys(RULE_TITLES.get(f.get("rule"), f.get("rule"))
                                     for f in findings))
    rows = pd.DataFrame({
        "Rule": [RULE_TITLES.get(f.get("rule"), f.get("rule")) for f in findings],
        "Summary": [f.get("summary") for f in findings],
        "IP addresses": [", ".join(f.get("ips") or []) for f in findings],
        "Users": [", ".join(f.get("users") or []) for f in findings],
        "Events": [f.get("event_count") for f in findings],
        "First seen (UTC)": [_time(f.get("first_seen")) for f in findings],
        "Last seen (UTC)": [_time(f.get("last_seen")) for f in findings],
    })
    return f"{_count(len(findings), 'finding')}: {titles}", rows


def _search(data: dict) -> tuple[str, pd.DataFrame | None]:
    total = data.get("total", 0)
    if not total:
        return "No sign-ins match.", None
    found = (f"{_count(total, 'event')}: {data.get('failures', 0):,} failed, "
             f"{data.get('successes', 0):,} succeeded; "
             f"{_count(data.get('distinct_users', 0), 'user')}, "
             f"{_count(data.get('distinct_ips', 0), 'IP')}; "
             f"{_time(data.get('first_seen'))} to {_time(data.get('last_seen'))} UTC")
    sample = data.get("sample") or []
    if len(sample) < total:
        found += f". The table shows the {len(sample)} most recent."
    return found, pd.DataFrame(sample) if sample else None


def _reputation(data: dict) -> tuple[str, pd.DataFrame | None]:
    if data.get("source") == "reserved":
        return str(data.get("note", "Reserved address: no reputation data.")), None
    whitelisted = "whitelisted" if data.get("is_whitelisted") else "not whitelisted"
    reports = data.get("total_reports")
    parts = [
        f"score {data.get('abuse_confidence_score')}/100",
        str(data.get("country")),
        str(data.get("isp")),
        str(data.get("usage_type")),
        whitelisted,
        _count(reports, "report") if isinstance(reports, int) else "reports unknown",
    ]
    source = ("live lookup" if data.get("source") == "live"
              else f"saved response from {_time(data.get('fetched_at'))} UTC")
    return f"{', '.join(parts)} ({source})", None


def _unknown(data: dict) -> tuple[str, pd.DataFrame | None]:
    return "See the raw data.", None


_FOUND = {
    "find_suspicious_activity": _findings,
    "search_logins": _search,
    "lookup_ip_reputation": _reputation,
}
