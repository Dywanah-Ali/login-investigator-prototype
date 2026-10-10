"""The incident report as a PDF, for handing to someone who never saw the case.

Plain Python with no Streamlit. The report is model output built from untrusted log data, so the
PDF is plain text only (PRD, Security): every field is written as raw text and never parsed as
markdown or HTML, and the file holds no links and no images. The header and footer are written by
this code, never by the model, so nothing in a report can change its classification or warning.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from functools import cache
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from login_investigator.agent import IncidentReport

APP = "Login Investigator"
CLASSIFICATION = "TLP:CLEAR · Educational use · Synthetic data"  # PRD decisions log, 10 Oct
WARNING = "AI-generated from synthetic data. Verify before acting."

FONT = "DejaVu"  # a Unicode font: the core PDF fonts cover Latin-1 only (PRD decisions log)
FONT_DIR = Path(__file__).parent / "fonts"
FONT_FILES = {"": FONT_DIR / "DejaVuSans.ttf", "B": FONT_DIR / "DejaVuSans-Bold.ttf"}
MISSING = "\N{REPLACEMENT CHARACTER}"  # shown for a character the font cannot draw

SEVERITY = {  # label and badge colour (RGB)
    "none": ("No incident", (46, 125, 50)),
    "low": ("Low severity", (21, 101, 192)),
    "medium": ("Medium severity", (230, 81, 0)),
    "high": ("High severity", (211, 47, 47)),
    "critical": ("Critical severity", (127, 0, 0)),
}
GREY = (110, 110, 110)
LIGHT = (238, 238, 238)
MARGIN = 18  # mm


@cache
def _drawable() -> frozenset[int]:
    """Code points both fonts can draw, read from the fonts as fpdf2 loads them."""
    pdf = FPDF()
    for style, path in FONT_FILES.items():
        pdf.add_font(FONT, style, path)
    regular, bold = (pdf.fonts[f"{FONT.lower()}{style}"].cmap for style in FONT_FILES)
    return frozenset(regular) & frozenset(bold)


def plain(text: str) -> str:
    """Text as the PDF will hold it. Control characters become spaces (line breaks are kept),
    and a character the font cannot draw becomes a visible replacement mark, never a silent gap."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n"))
    text = re.sub(r"[^\S\n]", " ", text)  # tabs and other spacing become plain spaces
    return "".join(_char(ch, _drawable()) for ch in text)


def _char(ch: str, drawable: frozenset[int]) -> str:
    if ch == "\n":
        return ch
    if unicodedata.category(ch).startswith("C"):  # control, format or unassigned
        return " "
    return ch if ord(ch) in drawable else MISSING


class _ReportPDF(FPDF):
    def __init__(self, case_id: str, generated_at: datetime, total_pages: int | None):
        super().__init__(format="A4")
        self.case_id = case_id
        self.generated_at = generated_at
        self.total_pages = total_pages
        # fpdf2 replaces "{nb}" anywhere on a page, model text included. Off: pages are counted
        # by rendering twice instead.
        self.alias_nb_pages(None)
        for style, path in FONT_FILES.items():
            self.add_font(FONT, style, path)
        self.set_margins(MARGIN, 28, MARGIN)
        self.set_auto_page_break(True, margin=22)
        self.set_title("Incident report")
        self.set_creator(APP)
        self.set_lang("en")
        self.set_creation_date(generated_at)

    def header(self):
        self.set_xy(MARGIN, 10)
        self.set_font(FONT, "B", 9)
        self.set_text_color(0)
        self.cell(self.epw / 2, 5, f"{APP} · Incident report")
        self.cell(self.epw / 2, 5, CLASSIFICATION, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font(FONT, "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 5, f"Case {self.case_id} · Generated "
                        f"{self.generated_at:%d %b %Y, %H:%M} UTC", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*GREY)
        self.line(MARGIN, 21, self.w - MARGIN, 21)
        self.set_y(28)

    def footer(self):
        self.set_draw_color(*GREY)
        self.line(MARGIN, self.h - 16, self.w - MARGIN, self.h - 16)
        self.set_xy(MARGIN, self.h - 14)
        self.set_font(FONT, "", 8)
        self.set_text_color(*GREY)
        page = f"Page {self.page_no()}"
        if self.total_pages:
            page += f" of {self.total_pages}"
        self.cell(self.epw * 0.75, 5, WARNING)
        self.cell(self.epw * 0.25, 5, page, align="R")

    # --- Body ------------------------------------------------------------------------------------

    def text_block(self, text: str, size: float = 10, style: str = "") -> None:
        self.set_font(FONT, style, size)
        self.set_text_color(0)
        self.multi_cell(0, size * 0.5, plain(text), align="L", new_x="LMARGIN", new_y="NEXT")

    def heading(self, text: str) -> None:
        self.ln(4)
        self.text_block(text, 11, "B")
        self.ln(1)

    def items(self, values: list[str], marker) -> None:
        """A list with a hanging indent; "None" when it is empty."""
        if not values:
            self.text_block("None")
            return
        self.set_font(FONT, "", 10)
        for number, value in enumerate(values, 1):
            self.set_x(MARGIN)
            self.cell(7, 5, marker(number))
            self.multi_cell(0, 5, plain(value), align="L", new_x="LMARGIN", new_y="NEXT")
            self.ln(0.8)

    def severity(self, severity: str) -> None:
        label, colour = SEVERITY[severity]
        self.ln(2)
        self.set_font(FONT, "B", 9)
        self.set_fill_color(*colour)
        self.set_text_color(255)
        self.cell(self.get_string_width(label) + 6, 6, label, fill=True, align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0)

    def timeline(self, report: IncidentReport) -> None:
        if not report.timeline:
            self.text_block("None")
            return
        self.set_font(FONT, "", 9)
        self.set_draw_color(*GREY)
        self.set_fill_color(255)  # the severity badge leaves its colour set
        heading = FontFace(family=FONT, emphasis="BOLD", fill_color=LIGHT)
        with self.table(col_widths=(42, self.epw - 42), text_align="LEFT", line_height=5,
                        padding=1.5, headings_style=heading) as table:
            table.row(("Time (UTC)", "Event"))
            for entry in report.timeline:
                table.row((plain(entry.time_utc), plain(entry.event)))


def _render(report: IncidentReport, case_id: str, generated_at: datetime,
            total_pages: int | None) -> _ReportPDF:
    pdf = _ReportPDF(case_id, generated_at, total_pages)
    pdf.add_page()
    pdf.text_block(report.title, 16, "B")
    pdf.severity(report.severity)
    pdf.heading("Summary")
    pdf.text_block(report.summary)
    pdf.heading("Attacker IPs")
    pdf.items(report.attacker_ips, lambda _: "•")
    pdf.heading("Affected users")
    pdf.items(report.affected_users, lambda _: "•")
    pdf.heading("Timeline (UTC)")
    pdf.timeline(report)
    pdf.heading("Evidence")
    pdf.items(report.evidence, lambda _: "•")
    pdf.heading("Recommended next steps")
    pdf.items(report.recommended_next_steps, lambda n: f"{n}.")
    return pdf


def build(report: IncidentReport, case_id: str, generated_at: datetime) -> bytes:
    """The report as PDF bytes. Rendered twice: the first pass counts the pages for the footer."""
    pages = _render(report, case_id, generated_at, None).pages_count
    return bytes(_render(report, case_id, generated_at, pages).output())


def file_name(case_id: str, number: int) -> str:
    """Built from the case id and the report's number in the case, never from the model's text."""
    return f"incident-report-{case_id[:8]}-{number}.pdf"
