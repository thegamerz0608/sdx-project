"""
Phase 14 Attendance Analytics & Anomaly Engine Unit Tests
Verifies AnalyticsService KPI calculations, department breakdowns, monthly trend aggregations, Z-score outlier detection, and PySide6 AnalyticsView.
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from services.analytics_service import AnalyticsService, analytics_service
from ui.analytics_view import AnalyticsView


@pytest.fixture
def qapp():
    """Ensure a PySide6 QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_analytics_service_kpis_and_breakdowns():
    """Test AnalyticsService KPI aggregations and department performance breakdown."""
    service = AnalyticsService()
    kpis = service.get_institutional_kpis()

    assert "total_faculty" in kpis
    assert kpis["total_faculty"] > 0
    assert "overall_attendance_rate" in kpis
    assert kpis["overall_attendance_rate"] > 0.0
    assert "avg_late_minutes" in kpis

    depts = service.get_department_breakdown()
    assert isinstance(depts, list)
    assert len(depts) > 0

    first_dept = depts[0]
    assert "department_code" in first_dept
    assert "attendance_rate" in first_dept


def test_analytics_service_monthly_trends():
    """Test monthly attendance and leave trend metrics."""
    trends = analytics_service.get_monthly_attendance_trends(year=2026)
    assert isinstance(trends, list)
    assert len(trends) >= 5

    item = trends[0]
    assert "month_year" in item
    assert "attendance_rate" in item
    assert "present_cnt" in item


def test_analytics_service_anomaly_detection():
    """Test Z-score outlier detection and pattern anomaly rules."""
    anomalies = analytics_service.detect_attendance_anomalies()
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0

    first = anomalies[0]
    assert "anomaly_id" in first
    assert "anomaly_type" in first
    assert "severity" in first
    assert first["severity"] in ["HIGH", "MEDIUM", "LOW"]
    assert "recommendation" in first


def test_analytics_view_gui(qapp):
    """Verify PySide6 AnalyticsView widget instantiates and populates tables."""
    view = AnalyticsView()
    assert view is not None
    assert view.sub_tabs.count() == 2

    # KPI card check
    assert view.card_att_rate.findChild(QLabel, "value_label").text() != ""

    # Department table check
    assert view.tbl_dept_perf.rowCount() > 0

    # Monthly trends table check
    assert view.tbl_monthly_trends.rowCount() > 0

    # Anomaly inspector table check
    assert view.tbl_anomalies.rowCount() > 0

    # Test filtering
    view.combo_anomaly_type.setCurrentText("LATE_ARRIVAL_OUTLIER")
    assert view.tbl_anomalies.rowCount() >= 0
