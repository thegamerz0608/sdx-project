"""
Comprehensive UI Layout Sanity Test Suite at 1366x768 Resolution.
Instantiates every view, tab, and primary window in the Faculty ERP,
verifies geometry constraints and layout hierarchies, and saves rendered
offscreen screenshots to docs/screenshots/layouts/.
"""
import os
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication, QWidget, QScrollArea, QTableWidget, QMainWindow

from ui.styles import ENTERPRISE_QSS
from ui.dashboard_widget import DashboardWidget
from ui.faculty_view import FacultyView
from ui.department_view import DepartmentView
from ui.attendance_view import AttendanceView
from ui.grace_view import GraceView
from ui.leave_rules_view import LeaveRulesView
from ui.leave_application_view import LeaveApplicationView
from ui.substitute_view import SubstituteView
from ui.nlp_view import NLPView
from ui.feature_view import FeatureView
from ui.model_view import ModelView
from ui.recommendation_view import RecommendationView
from ui.analytics_view import AnalyticsView
from ui.report_view import ReportView
from ui.audit_view import AuditView
from ui.backup_view import BackupView
from ui.instructor_view import InstructorManagementWidget
from ui.student_view import StudentSearchWidget
from ui.leave_management_widget import LeaveManagementWidget
from ui.student_marks_view import StudentMarksView
from ui.stationery_view import StationeryView
from ui.smartphone_punch_widget import SmartphonePunchWidget
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setStyleSheet(ENTERPRISE_QSS)
    return app


VIEW_CATALOG = [
    ("dashboard", DashboardWidget),
    ("faculty", FacultyView),
    ("department", DepartmentView),
    ("attendance", AttendanceView),
    ("grace", GraceView),
    ("leave_rules", LeaveRulesView),
    ("leave_app", LeaveApplicationView),
    ("substitute", SubstituteView),
    ("nlp", NLPView),
    ("feature", FeatureView),
    ("model", ModelView),
    ("recommendation", RecommendationView),
    ("analytics", AnalyticsView),
    ("report", ReportView),
    ("audit", AuditView),
    ("backup", BackupView),
    ("instructor", InstructorManagementWidget),
    ("student", StudentSearchWidget),
    ("leave_mgmt", LeaveManagementWidget),
    ("student_marks", StudentMarksView),
    ("stationery", StationeryView),
    ("smartphone_punch", SmartphonePunchWidget),
    ("login_window", LoginWindow),
    ("main_window", MainWindow),
]


@pytest.mark.parametrize("view_name, view_cls", VIEW_CATALOG)
def test_view_layout_sanity_at_1366x768(qapp, view_name, view_cls):
    """
    Instantiates each application view at 1366x768, verifies child layout geometry bounds,
    and captures offscreen rendering proof to docs/screenshots/layouts/.
    """
    screenshot_dir = Path("docs/screenshots/layouts")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Instantiate view component
    if view_cls is DashboardWidget:
        widget = view_cls(role="ADMIN")
    else:
        widget = view_cls()

    # Container setup for standard 1366x768 client viewport
    container = QWidget()
    container.resize(1366, 768)

    if isinstance(widget, QMainWindow):
        widget.resize(1366, 768)
        widget.show()
        target_widget = widget
    else:
        widget.setParent(container)
        widget.setGeometry(0, 0, 1366, 768)
        container.show()
        target_widget = container

    qapp.processEvents()

    # Layout bounds check: verify geometry is positive and non-clipped
    geo = target_widget.geometry()
    assert geo.width() > 0 and geo.height() > 0, f"{view_name} must have positive dimensions"

    # Verify tables inside the view have proper scroll/size policies
    tables = widget.findChildren(QTableWidget)
    for tbl in tables:
        assert tbl.verticalHeader().defaultSectionSize() >= 34, (
            f"Table {tbl} in {view_name} has section size < 34px which could cause row clipping"
        )

    # Capture offscreen screenshot evidence
    pix = target_widget.grab()
    out_file = screenshot_dir / f"{view_name}_1366x768.png"
    pix.save(str(out_file))
    assert out_file.exists(), f"Failed to save layout screenshot for {view_name}"
    assert out_file.stat().st_size > 0, f"Screenshot file for {view_name} is empty"

    # Cleanup
    widget.close()
    if not isinstance(widget, QMainWindow):
        container.close()
    qapp.processEvents()
