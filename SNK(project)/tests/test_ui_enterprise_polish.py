"""
Unit Tests for Enterprise UI/UX Polish & Modern Styling System
Verifies Enterprise QSS rules, EmptyStateWidget behaviors, responsive layout policies,
and data grid styling.
"""
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication, QTableWidget, QPushButton, QLineEdit

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.styles import ENTERPRISE_QSS, apply_enterprise_theme
from ui.empty_state import EmptyStateWidget
from ui.main_window import MainWindow
from ui.faculty_view import FacultyView
from ui.instructor_view import InstructorManagementWidget
from ui.attendance_view import AttendanceView


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_enterprise_qss_content():
    """Verify that the centralized QSS defines typography, tables, scrollbars, and interactive states."""
    assert "Segoe UI" in ENTERPRISE_QSS
    assert "QTableWidget" in ENTERPRISE_QSS
    assert "QScrollBar:vertical" in ENTERPRISE_QSS
    assert "QPushButton:hover" in ENTERPRISE_QSS
    assert "QLineEdit:focus" in ENTERPRISE_QSS
    assert "gridline-color: transparent" in ENTERPRISE_QSS
    assert "#kpiCard" in ENTERPRISE_QSS


def test_apply_enterprise_theme(qapp):
    """Verify applying enterprise theme to QApplication executes cleanly."""
    apply_enterprise_theme(qapp)
    sheet = qapp.styleSheet()
    assert "QTableWidget" in sheet
    assert "Segoe UI" in sheet


def test_empty_state_widget(qapp):
    """Verify EmptyStateWidget displays icon, title, description, and triggers action callback."""
    action_clicked = []

    def on_click():
        action_clicked.append(True)

    empty_widget = EmptyStateWidget(
        icon="📋",
        title="No Records",
        message="Please check back later.",
        action_text="Refresh",
        action_callback=on_click,
    )

    assert empty_widget.lbl_icon.text() == "📋"
    assert empty_widget.lbl_title.text() == "No Records"
    assert empty_widget.lbl_message.text() == "Please check back later."
    assert empty_widget.has_action_button is True

    # Simulate button click
    empty_widget.btn_action.click()
    assert len(action_clicked) == 1

    # Test dynamic update via set_state
    empty_widget.set_state(
        icon="🔍",
        title="Search Empty",
        message="No matches found.",
        action_text=None,
    )
    assert empty_widget.lbl_icon.text() == "🔍"
    assert empty_widget.lbl_title.text() == "Search Empty"
    assert empty_widget.has_action_button is False


def test_views_empty_state_integration(qapp):
    """Verify that FacultyView, InstructorView, and AttendanceView integrate EmptyStateWidget."""
    fac_view = FacultyView()
    assert hasattr(fac_view, "empty_state")
    assert isinstance(fac_view.empty_state, EmptyStateWidget)

    inst_view = InstructorManagementWidget()
    assert hasattr(inst_view, "empty_state")
    assert isinstance(inst_view.empty_state, EmptyStateWidget)

    att_view = AttendanceView()
    assert hasattr(att_view, "empty_state_roster")
    assert isinstance(att_view.empty_state_roster, EmptyStateWidget)


def test_main_window_with_enterprise_qss(qapp):
    """Verify MainWindow initializes cleanly with the modern enterprise stylesheet."""
    window = MainWindow()
    assert window is not None
    assert window.styleSheet() != ""
    assert "Segoe UI" in window.styleSheet()
    assert window.dashboard_widget is not None
    assert window.stacked_widget.count() >= 17
