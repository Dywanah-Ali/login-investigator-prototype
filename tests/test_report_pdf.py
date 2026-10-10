"""The incident report PDF: every fixed field, the fixed frame, and plain text only."""

import io
from datetime import datetime, timezone

import pytest
from pypdf import PdfReader

from login_investigator import report_pdf
from login_investigator.agent import IncidentReport, TimelineEntry
from tests.test_agent import REPORT

CASE = "3f9c2a1be0d84c7f9a6b5e4d3c2b1a09"
WHEN = datetime(2026, 10, 10, 12, 5, tzinfo=timezone.utc)
LINK = "<a href='https://attacker.example/x'>click</a>"
IMAGE = "![x](https://attacker.example/leak.png) <img src='https://attacker.example/i.png'>"
BARE = "https://attacker.example/report"


def read(report: IncidentReport) -> PdfReader:
    return PdfReader(io.BytesIO(report_pdf.build(report, CASE, WHEN)))


def text(reader: PdfReader) -> str:
    return "\n".join(page.extract_text() for page in reader.pages)


def flat(value: str) -> str:
    """Text with all whitespace removed, so line wrapping cannot hide a match."""
    return "".join(value.split())


def long_report(**fields) -> IncidentReport:
    base = REPORT.model_dump() | {
        "timeline": [{"time_utc": f"2026-10-08T02:{m:02d}:00Z", "event": f"Event {m}"}
                     for m in range(60)],
    }
    return IncidentReport(**(base | fields))


def test_every_fixed_field_is_in_the_pdf():
    report = REPORT.model_copy(update={
        "affected_users": ["daniel.hughes", "priya.shah"],
        "recommended_next_steps": ["Block 185.218.86.24", "Reset the password of daniel.hughes"],
    })
    content = text(read(report))
    for heading in ("Summary", "Attacker IPs", "Affected users", "Timeline (UTC)", "Evidence",
                    "Recommended next steps"):
        assert heading in content
    expected = [report.title, "Critical severity", report.summary, *report.attacker_ips,
                *report.affected_users, *report.evidence,
                *(f"{n}. {step}" for n, step in enumerate(report.recommended_next_steps, 1))]
    expected += [part for entry in report.timeline for part in (entry.time_utc, entry.event)]
    for value in expected:
        assert flat(value) in flat(content), value


@pytest.mark.parametrize("severity", list(report_pdf.SEVERITY))
def test_every_severity_has_its_label(severity):
    report = REPORT.model_copy(update={"severity": severity})
    assert report_pdf.SEVERITY[severity][0] in text(read(report))


def test_empty_lists_say_none():
    report = IncidentReport(title="Nothing found", severity="none", summary="No attack.",
                            attacker_ips=[], affected_users=[], timeline=[], evidence=[],
                            recommended_next_steps=[])
    content = text(read(report))
    assert "No incident" in content
    assert content.count("None") == 5  # the five list fields


def test_every_page_has_the_header_and_footer():
    reader = read(long_report())
    pages = len(reader.pages)
    assert pages >= 2
    for number, page in enumerate(reader.pages, 1):
        content = page.extract_text()
        assert report_pdf.CLASSIFICATION in content
        assert f"Case {CASE}" in content
        assert "Generated 10 Oct 2026, 12:05 UTC" in content
        assert report_pdf.WARNING in content
        assert f"Page {number} of {pages}" in content


def test_injected_links_and_images_stay_plain_text():
    report = REPORT.model_copy(update={
        "title": f"Takeover {LINK}",
        "summary": f"{IMAGE} {BARE}",
        "evidence": [LINK, IMAGE],
        "timeline": [TimelineEntry(time_utc="2026-10-08T02:32:20Z", event=IMAGE)],
    })
    data = report_pdf.build(report, CASE, WHEN)
    reader = PdfReader(io.BytesIO(data))
    for page in reader.pages:
        assert "/Annots" not in page
        assert "/XObject" not in page["/Resources"]
    assert b"/URI" not in data and b"/Link" not in data
    content = flat(text(reader))
    for injected in (LINK, IMAGE, BARE):
        assert flat(injected) in content


def test_the_model_cannot_change_the_page_count():
    # fpdf2 replaces "{nb}" with the page count by default; the PDF must print it as written.
    report = REPORT.model_copy(update={"summary": "Pages: {nb}"})
    assert "Pages: {nb}" in text(read(report))


def test_unicode_from_the_model_is_kept():
    words = "Attacker → signed in — “twice” at 02:32 ‘UTC’ … café"
    assert words in text(read(REPORT.model_copy(update={"summary": words})))


def test_a_character_the_font_lacks_is_shown_as_missing():
    assert report_pdf.plain("user 漢") == f"user {report_pdf.MISSING}"


def test_control_characters_become_spaces():
    assert report_pdf.plain("a\x00b\tc‮d\r\ne") == "a b c d\ne"


def test_file_name_never_uses_the_model_text():
    name = report_pdf.file_name(CASE, 2)
    assert name == "incident-report-3f9c2a1b-2.pdf"
