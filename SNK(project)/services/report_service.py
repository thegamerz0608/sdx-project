"""
Report Service Layer
Orchestrates PDF report generation and CSV data exports, managing output directory structure and file naming conventions.
"""
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from reports.pdf_generator import pdf_generator, PDFReportGenerator
from reports.csv_exporter import csv_exporter, CSVExporter
from utils.logger import get_logger

logger = get_logger("services.report_service")


class ReportService:
    """Service facade for generating institutional PDF reports and CSV datasets."""

    def __init__(self):
        self.output_dir = Path("reports_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_builder = pdf_generator
        self.exporter = csv_exporter

    def generate_pdf_report(self, report_type: str, department_id: Optional[int] = None) -> str:
        """
        Generates requested PDF report type and saves to reports_output/.
        Supported types: 'ATTENDANCE_SUMMARY', 'LEAVE_LEDGER', 'ANOMALY_AUDIT'
        """
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if report_type == "ATTENDANCE_SUMMARY":
            filename = f"Attendance_Summary_Report_{stamp}.pdf"
            out_path = self.output_dir / filename
            return self.pdf_builder.generate_attendance_summary_pdf(str(out_path), department_id=department_id)

        elif report_type == "LEAVE_LEDGER":
            filename = f"Leave_Entitlement_Ledger_{stamp}.pdf"
            out_path = self.output_dir / filename
            return self.pdf_builder.generate_leave_ledger_pdf(str(out_path), department_id=department_id)

        elif report_type == "ANOMALY_AUDIT":
            filename = f"HR_Attendance_Anomaly_Audit_{stamp}.pdf"
            out_path = self.output_dir / filename
            return self.pdf_builder.generate_anomaly_audit_pdf(str(out_path), department_id=department_id)

        else:
            raise ValueError(f"Unsupported report type: '{report_type}'")

    def export_csv_dataset(self, export_type: str, department_id: Optional[int] = None) -> str:
        """
        Exports requested dataset type to CSV in reports_output/.
        Supported types: 'ATTENDANCE', 'LEAVE_LEDGER', 'ANOMALIES'
        """
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_type == "ATTENDANCE":
            filename = f"Attendance_Logs_{stamp}.csv"
            out_path = self.output_dir / filename
            return self.exporter.export_attendance_csv(str(out_path), department_id=department_id)

        elif export_type == "LEAVE_LEDGER":
            filename = f"Leave_Balances_{stamp}.csv"
            out_path = self.output_dir / filename
            return self.exporter.export_leave_ledger_csv(str(out_path), department_id=department_id)

        elif export_type == "ANOMALIES":
            filename = f"Attendance_Anomalies_{stamp}.csv"
            out_path = self.output_dir / filename
            return self.exporter.export_anomalies_csv(str(out_path), department_id=department_id)

        else:
            raise ValueError(f"Unsupported CSV export type: '{export_type}'")


report_service = ReportService()
