"""
Project Report Word (.docx) Document Generator
Reads docs/PROJECT_REPORT.md and generates a beautifully formatted Microsoft Word document
using python-docx with custom styles, headers, tables, and callouts.
"""

import sys
import re
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_MD = PROJECT_ROOT / "docs" / "PROJECT_REPORT.md"
OUTPUT_DOCX = PROJECT_ROOT / "docs" / "PROJECT_REPORT.docx"


def set_cell_background(cell, fill_hex: str):
    """Sets background shading of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def build_docx_report():
    if not REPORT_MD.exists():
        print(f"[ERROR] Source report {REPORT_MD} does not exist.")
        return False

    with open(REPORT_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = Document()

    # Set standard margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base styling
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)

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
                continue  # Divider line
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells:
                rows.append(cells)

        if rows:
            num_cols = max(len(r) for r in rows)
            table = doc.add_table(rows=len(rows), cols=num_cols)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            for r_idx, row_data in enumerate(rows):
                for c_idx, cell_value in enumerate(row_data):
                    if c_idx < num_cols:
                        cell = table.cell(r_idx, c_idx)
                        clean_val = re.sub(r"[*_`]", "", cell_value)
                        cell.text = clean_val
                        # Format header row
                        if r_idx == 0:
                            set_cell_background(cell, "1E3A8A")
                            for paragraph in cell.paragraphs:
                                for run in paragraph.runs:
                                    run.font.bold = True
                                    run.font.color.rgb = RGBColor(255, 255, 255)
                        elif r_idx % 2 == 1:
                            set_cell_background(cell, "F8FAFC")
            doc.add_paragraph()  # Spacing

        table_lines = []
        in_table = False

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                # Flush code block
                code_text = "\n".join(code_block_lines)
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.4)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(code_text)
                run.font.name = "Consolas"
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(15, 23, 42)
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

        # Handle markdown tables
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            flush_table()

        # Handle Headers
        if stripped.startswith("# "):
            h = doc.add_heading(stripped[2:], level=1)
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(6)
            for r in h.runs:
                r.font.name = "Calibri"
                r.font.color.rgb = RGBColor(30, 58, 138)
        elif stripped.startswith("## "):
            h = doc.add_heading(stripped[3:], level=2)
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(4)
            for r in h.runs:
                r.font.name = "Calibri"
                r.font.color.rgb = RGBColor(37, 99, 235)
        elif stripped.startswith("### "):
            h = doc.add_heading(stripped[4:], level=3)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
            for r in h.runs:
                r.font.name = "Calibri"
                r.font.color.rgb = RGBColor(15, 23, 42)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            clean_text = re.sub(r"[*_`]", "", stripped[2:])
            p.add_run(clean_text)
        elif stripped.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.4)
            run = p.add_run(stripped[2:].replace('"', ''))
            run.font.italic = True
            run.font.color.rgb = RGBColor(71, 85, 105)
        elif stripped == "---":
            continue
        elif stripped:
            p = doc.add_paragraph()
            # Clean basic markdown formatting
            clean_line = re.sub(r"[*_`]", "", stripped)
            p.add_run(clean_line)

    if in_table:
        flush_table()

    doc.save(OUTPUT_DOCX)
    print(f"\n[OK] Master Project Report generated successfully in Word format:")
    print(f"     -> {OUTPUT_DOCX}\n")
    return True


if __name__ == "__main__":
    build_docx_report()
