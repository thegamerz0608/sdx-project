"""
Publication-Grade PDF Report Generator
Parses docs/PROJECT_REPORT.md and renders docs/PROJECT_REPORT.pdf using ReportLab.
Features header styling, clean table borders, code block formatting, and page numbering.
"""

import sys
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
)
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_MD = PROJECT_ROOT / "docs" / "PROJECT_REPORT.md"
OUTPUT_PDF = PROJECT_ROOT / "docs" / "PROJECT_REPORT.pdf"


class NumberedCanvas(canvas.Canvas):
    """Adds running headers and footers with dynamic page numbers (Page X of Y)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(
                54,
                11 * 72 - 36,
                "MCA Major Project: AI-Enabled Faculty Attendance & Leave ERP (v3.2.0)",
            )
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 36, footer_text)
        self.drawString(54, 36, "A.J. Institute of Engineering & Technology - Dept of MCA")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * 72 - 54, 46)

        self.restoreState()


def build_pdf_report():
    if not REPORT_MD.exists():
        print(f"[ERROR] Source report {REPORT_MD} does not exist.")
        return False

    with open(REPORT_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "ReportH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "ReportH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        "ReportH3",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    quote_style = ParagraphStyle(
        "ReportQuote",
        parent=body_style,
        fontName="Helvetica-Oblique",
        leftIndent=18,
        rightIndent=18,
        textColor=colors.HexColor("#475569"),
        spaceBefore=4,
        spaceAfter=6,
    )

    code_style = ParagraphStyle(
        "ReportCode",
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []
    lines = md_text.splitlines()

    in_code_block = False
    code_block_lines = []
    in_table = False
    table_lines = []

    def flush_table():
        nonlocal in_table, table_lines
        if not table_lines:
            in_table = False
            return

        rows = []
        for line in table_lines:
            if re.match(r"^\|?[\s\-:|]+\|?$", line.strip()):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells:
                rows.append([Paragraph(re.sub(r"[*_`]", "", c), body_style) for c in cells])

        if rows:
            t = Table(rows, repeatRows=1)
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ])
            )
            story.append(t)
            story.append(Spacer(1, 6))

        table_lines = []
        in_table = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                code_text = "\n".join(code_block_lines)
                story.append(Preformatted(code_text, code_style))
                story.append(Spacer(1, 4))
                code_block_lines = []
                in_code_block = False
            else:
                if in_table:
                    flush_table()
                in_code_block = True
                code_block_lines = []
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            flush_table()

        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], title_style))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], h1_style))
        elif stripped.startswith("### "):
            story.append(Paragraph(stripped[4:], h2_style))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            clean = re.sub(r"[*_`]", "", stripped[2:])
            clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f"&bull; {clean}", bullet_style))
        elif stripped.startswith("> "):
            clean = re.sub(r"[*_`]", "", stripped[2:])
            clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(clean, quote_style))
        elif stripped == "---":
            story.append(Spacer(1, 4))
        elif stripped:
            clean = re.sub(r"[*_`]", "", stripped)
            clean = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(clean, body_style))

    if in_table:
        flush_table()

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"\n[OK] Master Project Report generated successfully in PDF format:")
    print(f"     -> {OUTPUT_PDF}\n")
    return True


if __name__ == "__main__":
    build_pdf_report()
