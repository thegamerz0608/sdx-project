"""
ReportLab PDF Document Generator
Builds publication-ready PDF reports with institutional header banners, KPI summaries, styled data tables, and audit footers.
"""
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from services.analytics_service import analytics_service
from repositories.leave_repository import leave_repository
from repositories.faculty_repository import faculty_repository
from repositories.department_repository import department_repository
from utils.logger import get_logger

logger = get_logger("reports.pdf_generator")


class PDFReportGenerator:
    """Generates styled institutional PDF reports using ReportLab."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        self.title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1b365d"),
            alignment=0,
        )
        self.subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#555555"),
        )
        self.section_heading = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1b365d"),
            spaceBefore=10,
            spaceAfter=6,
        )
        self.cell_style = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#222222"),
        )
        self.cell_header_style = ParagraphStyle(
            "TableHeaderCell",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
        )

    def _build_header_flowables(self, report_title: str, report_subtitle: str) -> List[Any]:
        flowables = []
        flowables.append(Paragraph(report_title, self.title_style))
        flowables.append(Spacer(1, 4))
        flowables.append(Paragraph(report_subtitle, self.subtitle_style))
        flowables.append(Spacer(1, 4))

        meta_str = f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Institution: MCA ERP System"
        flowables.append(Paragraph(meta_str, self.subtitle_style))
        flowables.append(Spacer(1, 8))
        flowables.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1b365d"), spaceAfter=12))
        return flowables

    def generate_attendance_summary_pdf(self, output_path: str, department_id: Optional[int] = None) -> str:
        """Generates Faculty Attendance & Punctuality Summary PDF Report."""
        logger.info(f"Generating Attendance Summary PDF -> {output_path}")
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        elements = []

        # Header
        elements.extend(self._build_header_flowables("Faculty Attendance & Punctuality Summary Report", "Executive Institutional Attendance Metrics and Department Compliance"))

        # KPI Summary Box
        kpis = analytics_service.get_institutional_kpis(department_id=department_id)
        kpi_table_data = [
            [
                Paragraph("<b>Overall Attendance Rate:</b>", self.cell_style),
                Paragraph(f"<b>{kpis['overall_attendance_rate']:.1f}%</b>", self.cell_style),
                Paragraph("<b>Avg Late Mins:</b>", self.cell_style),
                Paragraph(f"<b>{kpis['avg_late_minutes']:.1f} mins</b>", self.cell_style),
            ],
            [
                Paragraph("<b>Active Faculty Count:</b>", self.cell_style),
                Paragraph(str(kpis["total_faculty"]), self.cell_style),
                Paragraph("<b>Unexcused Absences:</b>", self.cell_style),
                Paragraph(str(kpis["unexcused_absences"]), self.cell_style),
            ],
        ]
        t_kpi = Table(kpi_table_data, colWidths=[130, 100, 130, 100])
        t_kpi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#dcdfe6")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_kpi)
        elements.append(Spacer(1, 15))

        # Department Breakdown Table
        elements.append(Paragraph("Department Attendance Performance", self.section_heading))
        dept_data = analytics_service.get_department_breakdown()

        table_data = [[
            Paragraph("Dept Code", self.cell_header_style),
            Paragraph("Department Name", self.cell_header_style),
            Paragraph("Faculty Count", self.cell_header_style),
            Paragraph("Attendance Rate", self.cell_header_style),
            Paragraph("Avg Late Mins", self.cell_header_style),
        ]]

        for d in dept_data:
            table_data.append([
                Paragraph(d["department_code"], self.cell_style),
                Paragraph(d["department_name"], self.cell_style),
                Paragraph(str(d["faculty_count"]), self.cell_style),
                Paragraph(f"{d['attendance_rate']:.1f}%", self.cell_style),
                Paragraph(f"{d['avg_late_minutes']:.1f} mins", self.cell_style),
            ])

        t_dept = Table(table_data, colWidths=[70, 200, 80, 90, 80])
        t_dept.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b365d")),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        elements.append(t_dept)

        # Footer Signature Block
        elements.append(Spacer(1, 30))
        sig_data = [
            [Paragraph("____________________", self.cell_style), Paragraph("____________________", self.cell_style)],
            [Paragraph("Prepared by ERP System Administrator", self.cell_style), Paragraph("Approved by Head of Department / HR", self.cell_style)],
        ]
        t_sig = Table(sig_data, colWidths=[260, 260])
        elements.append(t_sig)

        doc.build(elements)
        logger.info(f"Successfully built Attendance Summary PDF -> {output_path}")
        return output_path

    def generate_leave_ledger_pdf(self, output_path: str, department_id: Optional[int] = None) -> str:
        """Generates Leave Entitlement & Usage Ledger PDF Report."""
        logger.info(f"Generating Leave Ledger PDF -> {output_path}")
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        elements = []

        elements.extend(self._build_header_flowables("Faculty Leave Entitlement & Usage Ledger Report", "Yearly Leave Allocation, Consumed Days, and Remaining Balances"))

        # Fetch balances
        if department_id:
            balances = leave_repository.get_department_balances(department_id=department_id, year=2026)
        else:
            balances = leave_repository.get_department_balances(department_id=None, year=2026)

        table_data = [[
            Paragraph("Emp Code", self.cell_header_style),
            Paragraph("Faculty Name", self.cell_header_style),
            Paragraph("Dept", self.cell_header_style),
            Paragraph("Leave Type", self.cell_header_style),
            Paragraph("Allocated", self.cell_header_style),
            Paragraph("Used", self.cell_header_style),
            Paragraph("Pending", self.cell_header_style),
            Paragraph("Remaining", self.cell_header_style),
        ]]

        for b in balances:
            table_data.append([
                Paragraph(b.get("employee_code", ""), self.cell_style),
                Paragraph(b.get("faculty_name", ""), self.cell_style),
                Paragraph(b.get("department_code", ""), self.cell_style),
                Paragraph(f"{b.get('leave_type_code', '')} - {b.get('leave_type_name', '')}", self.cell_style),
                Paragraph(f"{b.get('allocated_days', 0):.1f}", self.cell_style),
                Paragraph(f"{b.get('used_days', 0):.1f}", self.cell_style),
                Paragraph(f"{b.get('pending_days', 0):.1f}", self.cell_style),
                Paragraph(f"<b>{b.get('remaining_days', 0):.1f}</b>", self.cell_style),
            ])

        t_ledger = Table(table_data, colWidths=[55, 110, 45, 130, 45, 45, 45, 45])
        t_ledger.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b365d")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        elements.append(t_ledger)

        doc.build(elements)
        logger.info(f"Successfully built Leave Ledger PDF -> {output_path}")
        return output_path

    def generate_anomaly_audit_pdf(self, output_path: str, department_id: Optional[int] = None) -> str:
        """Generates Attendance Anomaly & HR Compliance Audit PDF Report."""
        logger.info(f"Generating Anomaly Audit PDF -> {output_path}")
        doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        elements = []

        elements.extend(self._build_header_flowables("Attendance Anomaly & HR Compliance Audit Report", "Statistical Z-Score Outliers, Pattern Absenteeism, and Audit Flags"))

        anomalies = analytics_service.detect_attendance_anomalies(department_id=department_id)

        table_data = [[
            Paragraph("Anomaly ID", self.cell_header_style),
            Paragraph("Emp Code", self.cell_header_style),
            Paragraph("Faculty Name", self.cell_header_style),
            Paragraph("Anomaly Type", self.cell_header_style),
            Paragraph("Severity", self.cell_header_style),
            Paragraph("Outlier Metric", self.cell_header_style),
            Paragraph("Action Recommendation", self.cell_header_style),
        ]]

        for a in anomalies:
            table_data.append([
                Paragraph(a.get("anomaly_id", ""), self.cell_style),
                Paragraph(a.get("employee_code", ""), self.cell_style),
                Paragraph(a.get("faculty_name", ""), self.cell_style),
                Paragraph(a.get("anomaly_name", ""), self.cell_style),
                Paragraph(f"<b>{a.get('severity', '')}</b>", self.cell_style),
                Paragraph(a.get("metric_value", ""), self.cell_style),
                Paragraph(a.get("recommendation", ""), self.cell_style),
            ])

        t_ano = Table(table_data, colWidths=[65, 55, 95, 95, 50, 75, 85])
        t_ano.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c62828")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff5f5")]),
        ]))
        elements.append(t_ano)

        doc.build(elements)
        logger.info(f"Successfully built Anomaly Audit PDF -> {output_path}")
        return output_path


pdf_generator = PDFReportGenerator()
