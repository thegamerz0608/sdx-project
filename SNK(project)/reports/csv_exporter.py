"""
CSV Data Exporter Utility
Exports tabular ERP datasets (attendance logs, leave ledgers, anomaly logs) into standard CSV format.
"""
import sys
import os
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

from repositories.attendance_repository import attendance_repository
from repositories.leave_repository import leave_repository
from services.analytics_service import analytics_service
from utils.logger import get_logger

logger = get_logger("reports.csv_exporter")


class CSVExporter:
    """Exports structured data tables to CSV format."""

    def export_attendance_csv(self, output_path: str, department_id: Optional[int] = None) -> str:
        """Exports faculty attendance logs to CSV."""
        logger.info(f"Exporting Attendance CSV -> {output_path}")
        logs = attendance_repository.get_all(department_id=department_id)

        fieldnames = [
            "id",
            "faculty_id",
            "employee_code",
            "faculty_name",
            "department_id",
            "department_code",
            "attendance_date",
            "login_time",
            "logout_time",
            "status",
            "late_minutes",
            "working_hours",
            "early_departure_minutes",
            "is_flagged",
        ]

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in logs:
                writer.writerow(row)

        logger.info(f"Successfully exported {len(logs)} attendance rows to {output_path}")
        return str(out_path.resolve())

    def export_leave_ledger_csv(self, output_path: str, department_id: Optional[int] = None) -> str:
        """Exports leave entitlement balances to CSV."""
        logger.info(f"Exporting Leave Ledger CSV -> {output_path}")
        balances = leave_repository.get_department_balances(department_id=department_id, year=2026)

        fieldnames = [
            "id",
            "faculty_id",
            "employee_code",
            "faculty_name",
            "department_id",
            "department_code",
            "leave_type_code",
            "leave_type_name",
            "allocated_days",
            "used_days",
            "pending_days",
            "remaining_days",
        ]

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in balances:
                writer.writerow(row)

        logger.info(f"Successfully exported {len(balances)} leave balance rows to {output_path}")
        return str(out_path.resolve())

    def export_anomalies_csv(self, output_path: str, department_id: Optional[int] = None) -> str:
        """Exports detected attendance anomalies to CSV."""
        logger.info(f"Exporting Anomalies CSV -> {output_path}")
        anomalies = analytics_service.detect_attendance_anomalies(department_id=department_id)

        fieldnames = [
            "anomaly_id",
            "faculty_id",
            "employee_code",
            "faculty_name",
            "department_code",
            "anomaly_type",
            "anomaly_name",
            "severity",
            "metric_value",
            "z_score",
            "recommendation",
        ]

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in anomalies:
                writer.writerow(row)

        logger.info(f"Successfully exported {len(anomalies)} anomaly rows to {output_path}")
        return str(out_path.resolve())


csv_exporter = CSVExporter()
