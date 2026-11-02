"""
Phase 15 Automated Reporting & PDF Export Engine Unit Tests
Verifies ReportLab PDF report generation, CSV file exports, ReportService facade operations, and PySide6 ReportView interface.
"""
import sys
import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import pytest
from PySide6.QtWidgets import QApplication

from reports.pdf_generator import pdf_generator
from reports.csv_exporter import csv_exporter
from services.report_service import report_service, ReportService
from ui.report_view import ReportView


@pytest.fixture
def qapp():
    """Ensure a PySide6 QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_pdf_report_generator_builds():
    """Verify PDF Report Generator builds all 3 PDF report types with non-zero byte sizes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_att = os.path.join(tmpdir, "test_attendance.pdf")
        pdf_leave = os.path.join(tmpdir, "test_leave.pdf")
        pdf_ano = os.path.join(tmpdir, "test_anomaly.pdf")

        # 1. Attendance Summary PDF
        path1 = pdf_generator.generate_attendance_summary_pdf(pdf_att)
        assert os.path.exists(path1)
        assert os.path.getsize(path1) > 1000

        # 2. Leave Ledger PDF
        path2 = pdf_generator.generate_leave_ledger_pdf(pdf_leave)
        assert os.path.exists(path2)
        assert os.path.getsize(path2) > 1000

        # 3. Anomaly Audit PDF
        path3 = pdf_generator.generate_anomaly_audit_pdf(pdf_ano)
        assert os.path.exists(path3)
        assert os.path.getsize(path3) > 1000


def test_csv_exporter_builds():
    """Verify CSV Exporter generates attendance, leave, and anomaly CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_att = os.path.join(tmpdir, "test_attendance.csv")
        csv_leave = os.path.join(tmpdir, "test_leave.csv")
        csv_ano = os.path.join(tmpdir, "test_anomaly.csv")

        p1 = csv_exporter.export_attendance_csv(csv_att)
        assert os.path.exists(p1)
        assert os.path.getsize(p1) > 100

        p2 = csv_exporter.export_leave_ledger_csv(csv_leave)
        assert os.path.exists(p2)
        assert os.path.getsize(p2) > 100

        p3 = csv_exporter.export_anomalies_csv(csv_ano)
        assert os.path.exists(p3)
        assert os.path.getsize(p3) > 100


def test_report_service_facade():
    """Test ReportService facade PDF and CSV generation into reports_output/."""
    p_pdf = report_service.generate_pdf_report("ATTENDANCE_SUMMARY")
    assert os.path.exists(p_pdf)
    assert os.path.getsize(p_pdf) > 1000

    p_csv = report_service.export_csv_dataset("ATTENDANCE")
    assert os.path.exists(p_csv)
    assert os.path.getsize(p_csv) > 100


def test_report_view_gui(qapp, monkeypatch):
    """Verify PySide6 ReportView widget instantiates and executes report actions."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)

    view = ReportView()
    assert view is not None
    assert view.sub_tabs.count() == 2

    # Check combos populated
    assert view.combo_pdf_type.count() == 3
    assert view.combo_dept_scope.count() >= 1

    # Test PDF generation click action
    view.generate_pdf_clicked()
    assert view.tbl_recent_pdfs.rowCount() > 0
    assert "SUCCESS:" in view.lbl_pdf_status.text()
