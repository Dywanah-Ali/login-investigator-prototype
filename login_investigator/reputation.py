"""IP reputation from AbuseIPDB. The agent's `lookup_ip_reputation` tool calls this.

The cheapest answer wins. A reserved or private address has no reputation, so it is answered
without a call. A saved response in data/ip_reputation/ is used next, so the planted scenarios work
with the network off. Otherwise one live HTTPS call is made. Live answers are not written to disk:
the lookup only reads.
"""

from __future__ import annotations

import ipaddress
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from login_investigator.generator import REPO_ROOT

SAVED_DIR = REPO_ROOT / "data" / "ip_reputation"
API_URL = "https://api.abuseipdb.com/api/v2/check"
KEY_NAME = "ABUSEIPDB_API_KEY"
MAX_AGE_DAYS = 90  # reports older than this are not counted
TIMEOUT_SECONDS = 10

RESERVED_NOTE = ("Reserved or private address: it is not routable on the internet, so no "
                 "reputation data exists for it.")


class ReputationError(Exception):
    """A lookup that could not be answered. The message is short and safe to show the analyst."""


def parse_ip(value) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        return ipaddress.ip_address(str(value).strip())
    except ValueError:
        raise ReputationError(f"{value!r} is not an IP address") from None


def lookup(ip, *, saved_dir: Path = SAVED_DIR, api_key: str | None = None) -> dict:
    """The reputation of one IP, from the cheapest source that has it."""
    address = parse_ip(ip)
    if not address.is_global:
        return {"ip": str(address), "source": "reserved", "note": RESERVED_NOTE}

    # The file name comes from the parsed address, never from the raw input.
    saved = saved_dir / f"{address}.json"
    if saved.exists():
        payload = json.loads(saved.read_text())
        return summarize(payload["data"], source="saved", fetched_at=payload.get("fetchedAt"))

    key = api_key or os.environ.get(KEY_NAME)
    if not key:
        raise ReputationError(f"no saved response for {address}, and no AbuseIPDB key is set")
    return summarize(_fetch(str(address), key), source="live",
                     fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))


def _fetch(ip: str, key: str) -> dict:
    # Error messages never include the request, so the key cannot leak into the chat.
    try:
        response = requests.get(
            API_URL,
            headers={"Key": key, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": MAX_AGE_DAYS},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        raise ReputationError("AbuseIPDB could not be reached (network error or timeout)") from None
    if response.status_code == 429:
        raise ReputationError("AbuseIPDB's daily lookup limit is used up; try again tomorrow")
    if response.status_code != 200:
        raise ReputationError(f"AbuseIPDB answered with HTTP {response.status_code}")
    try:
        return response.json()["data"]
    except (ValueError, KeyError, TypeError):
        raise ReputationError("AbuseIPDB sent an answer that could not be read") from None


def summarize(data: dict, source: str, fetched_at: str | None) -> dict:
    """The fields the analyst needs. Text values (ISP, domain) come from AbuseIPDB as they are."""
    return {
        "ip": data.get("ipAddress"),
        "source": source,
        "fetched_at": fetched_at,
        "abuse_confidence_score": data.get("abuseConfidenceScore"),
        "total_reports": data.get("totalReports"),
        "distinct_reporters": data.get("numDistinctUsers"),
        "last_reported_at": data.get("lastReportedAt"),
        "is_whitelisted": data.get("isWhitelisted"),
        "is_tor": data.get("isTor"),
        "country": data.get("countryCode"),
        "isp": data.get("isp"),
        "domain": data.get("domain"),
        "usage_type": data.get("usageType"),
    }
