"""
Unit & Integration Tests for Students Directory, Multi-Stage Leave Workflow & HR/Principal Roles.
Verifies Employee ID login, multi-field student search & registration, HR/Principal multi-stage
approval state machine, HR date modifications, and UI widget instantiation.
"""
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.auth_service import auth_service, UserSession
from services.student_service import student_service
from services.leave_workflow_service import leave_workflow_service
from repositories.student_repository import student_repository, DEMO_STUDENTS
from repositories.leave_application_repository import leave_application_repository
from utils.exceptions import ValidationError, BusinessLogicError, AuthenticationError
from ui.student_view import StudentSearchWidget, StudentProfileDialog
from ui.leave_management_widget import LeaveManagementWidget, ModifyDatesDialog
from ui.main_window import ModernMainWindow
from ui.dashboard_widget import DashboardWidget


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def admin_session():
    return auth_service.login("EMP001", "Password@123")


@pytest.fixture
def hr_session():
    return auth_service.login("HR001", "Password@123")


@pytest.fixture
def principal_session():
    return auth_service.login("PRIN001", "Password@123")


@pytest.fixture
def faculty_session():
    return auth_service.login("F002", "Password@123")


# ==============================================================================
# Module 1 Tests: Employee ID Authentication & Role Helpers
# ==============================================================================

def test_login_via_employee_id():
    """Verifies that users can log in using their Employee ID / Staff Code."""
    # 1. Admin login via Employee ID
    session = auth_service.login("EMP001", "Password@123")
    assert session is not None
    assert session.username == "admin"
    assert session.role == "ADMIN"
    assert session.is_admin() is True

    # 2. HR login via Employee ID
    hr_sess = auth_service.login("HR001", "Password@123")
    assert hr_sess is not None
    assert hr_sess.role == "HR"
    assert hr_sess.is_hr() is True
    assert hr_sess.is_admin() is False

    # 3. Principal login via Employee ID
    prin_sess = auth_service.login("PRIN001", "Password@123")
    assert prin_sess is not None
    assert prin_sess.role == "PRINCIPAL"
    assert prin_sess.is_principal() is True

    # 4. Faculty login via Faculty Code
    fac_sess = auth_service.login("F002", "Password@123")
    assert fac_sess is not None
    assert fac_sess.role == "FACULTY"
    assert fac_sess.is_faculty() is True


def test_invalid_employee_id_login():
    """Verifies authentication failure for non-existent employee ID or bad password."""
    with pytest.raises(AuthenticationError):
        auth_service.login("INVALID_ID", "Password@123")

    with pytest.raises(AuthenticationError):
        auth_service.login("EMP001", "WrongPassword")


# ==============================================================================
# Module 2 & 3 Tests: Student Search & Registration (StudentService)
# ==============================================================================

def test_student_multi_field_search(admin_session):
    """Verifies multi-field student search by USN, Name, Phone, and Year."""
    # 1. Search by USN
    results = student_service.search_students(admin_session, search_term="1MS23MCA001")
    assert len(results) >= 1
    assert results[0]["usn"] == "1MS23MCA001"

    # 2. Search by Name (case-insensitive substring)
    results = student_service.search_students(admin_session, search_term="Aarav")
    assert len(results) >= 1
    assert "Aarav" in results[0]["name"]

    # 3. Search by Phone number substring
    results = student_service.search_students(admin_session, search_term="9876543211")
    assert len(results) >= 1
    assert results[0]["usn"] == "1MS23MCA002"

    # 4. Filter by Year
    results = student_service.search_students(admin_session, year=1)
    assert len(results) >= 1
    for s in results:
        assert s["year"] == 1


def test_student_registration_validation(admin_session):
    """Verifies that student registration enforces USN uniqueness and field validation."""
    # Register a new unique student
    new_usn = f"1MS24TEST{len(DEMO_STUDENTS) + 1}"
    registered = student_service.register_student(
        user_session=admin_session,
        usn=new_usn,
        name="Test Candidate",
        email=f"candidate_{new_usn.lower()}@erp.edu",
        phone_number="9876500000",
        department_id=1,
        year=1,
        semester=1,
    )
    assert registered is not None
    assert registered["usn"] == new_usn

    # Duplicate USN should raise ValidationError
    with pytest.raises(ValidationError):
        student_service.register_student(
            user_session=admin_session,
            usn=new_usn,
            name="Duplicate Candidate",
            email="another@erp.edu",
            phone_number="9876500001",
            department_id=1,
        )


def test_student_registration_rbac_restriction(faculty_session):
    """Verifies that regular faculty cannot register students (Admin/HOD only)."""
    with pytest.raises(BusinessLogicError):
        student_service.register_student(
            user_session=faculty_session,
            usn="1MS24UNAUTH",
            name="Unauthorized Student",
            email="unauth@erp.edu",
            phone_number="9876599999",
            department_id=1,
        )


# ==============================================================================
# Module 4 Tests: Multi-Stage Leave Workflow & HR Adjustments
# ==============================================================================

def test_multi_stage_leave_workflow_transitions(hr_session, principal_session):
    """Verifies the state machine progression: PENDING_HR -> PENDING_PRINCIPAL -> APPROVED."""
    # Target Application 1 (initially PENDING_HR)
    app_id = 1

    # 1. HR reviews and approves -> moves to PENDING_PRINCIPAL
    hr_result = leave_workflow_service.hr_review_application(
        user_session=hr_session,
        application_id=app_id,
        action="APPROVE",
        remarks="HR verified leave balance and quota. Advanced to Principal.",
    )
    assert hr_result is not None
    assert hr_result["status"] == "PENDING_PRINCIPAL"
    assert hr_result["hr_status"] == "APPROVED"
    assert "HR verified" in hr_result["hr_remarks"]

    # 2. Principal reviews and grants final executive sign-off -> APPROVED
    prin_result = leave_workflow_service.principal_review_application(
        user_session=principal_session,
        application_id=app_id,
        action="APPROVE",
        remarks="Final executive sign-off granted by Principal.",
    )
    assert prin_result is not None
    assert prin_result["status"] == "APPROVED"
    assert prin_result["principal_status"] == "APPROVED"


def test_hr_leave_suspension_and_rejection(hr_session):
    """Verifies that HR can suspend or reject a leave application."""
    # Application 2
    app_id = 2

    # Suspend application
    suspended = leave_workflow_service.hr_review_application(
        user_session=hr_session,
        application_id=app_id,
        action="SUSPEND",
        remarks="Suspended due to overlapping departmental examinations.",
    )
    assert suspended["status"] == "SUSPENDED"
    assert suspended["hr_status"] == "SUSPENDED"

    # Reject application
    rejected = leave_workflow_service.hr_review_application(
        user_session=hr_session,
        application_id=app_id,
        action="REJECT",
        remarks="Quota exceeded for the active academic quarter.",
    )
    assert rejected["status"] == "REJECTED"
    assert rejected["hr_status"] == "REJECTED"


def test_hr_modify_leave_dates(hr_session):
    """Verifies that HR has the special authority to modify requested dates and total days."""
    app_id = 1
    updated = leave_workflow_service.hr_modify_dates(
        user_session=hr_session,
        application_id=app_id,
        from_date="2026-11-01",
        to_date="2026-11-03",
        total_days=3.0,
        remarks="Adjusted to align with mid-term schedule.",
    )
    assert updated is not None
    assert str(updated["from_date"]) == "2026-11-01"
    assert str(updated["to_date"]) == "2026-11-03"
    assert float(updated["total_days"]) == 3.0


# ==============================================================================
# UI Integration & RBAC Tests
# ==============================================================================

def test_system_diagnostics_admin_only_visibility(qapp):
    """Verifies that System Diagnostics & Maintenance is strictly visible to ADMIN only."""
    # 1. Admin dashboard shows diagnostics
    dash_admin = DashboardWidget(role="ADMIN")
    assert dash_admin.diag_group.isVisibleTo(dash_admin) or not dash_admin.diag_group.isHidden()

    # 2. HOD dashboard hides diagnostics
    dash_hod = DashboardWidget(role="HOD")
    assert dash_hod.diag_group.isHidden()

    # 3. Faculty dashboard hides diagnostics
    dash_fac = DashboardWidget(role="FACULTY")
    assert dash_fac.diag_group.isHidden()

    # 4. HR dashboard hides diagnostics
    dash_hr = DashboardWidget(role="HR")
    assert dash_hr.diag_group.isHidden()

    # 5. Principal dashboard hides diagnostics
    dash_prin = DashboardWidget(role="PRINCIPAL")
    assert dash_prin.diag_group.isHidden()


def test_student_search_widget_instantiation(qapp, admin_session):
    """Verifies that StudentSearchWidget initializes properly with data table and controls."""
    widget = StudentSearchWidget()
    assert widget is not None
    assert widget.tbl_students.columnCount() == 7
    widget.load_students()
    assert widget.tbl_students.rowCount() >= 1


def test_leave_management_widget_instantiation(qapp, hr_session):
    """Verifies that LeaveManagementWidget initializes properly with table and action buttons."""
    widget = LeaveManagementWidget()
    assert widget is not None
    assert widget.tbl_apps.columnCount() == 11
    widget.load_applications()
    assert widget.tbl_apps.rowCount() >= 1
    assert widget.btn_hr_approve is not None
    assert widget.btn_hr_modify is not None
    assert widget.btn_prin_approve is not None


def test_modern_main_window_expanded_views(qapp, admin_session):
    """Verifies that ModernMainWindow wires StudentSearchWidget and LeaveManagementWidget."""
    win = ModernMainWindow()
    assert win is not None
    assert hasattr(win, "student_view")
    assert hasattr(win, "leave_mgmt_view")
    assert win.stacked_widget.count() >= 19


def test_login_window_captcha_and_split_layout(qapp):
    """Verifies LoginWindow split layout, CAPTCHA rendering, and local validation."""
    from ui.login_window import LoginWindow
    win = LoginWindow()
    assert win is not None
    assert win.txt_username is not None
    assert win.txt_password is not None
    assert win.txt_captcha is not None
    assert win.lbl_captcha_img is not None
    assert win.lbl_captcha_img.pixmap() is not None
    assert not win.lbl_captcha_img.pixmap().isNull()
    assert win.current_captcha_code != ""
    assert len(win.current_captcha_code) == 4

    # 1. Invalid CAPTCHA triggers local validation failure
    win.txt_username.setText("EMP001")
    win.txt_password.setText("Password@123")
    win.txt_captcha.setText("0000_INVALID")
    win.handle_login()
    assert not win.lbl_error.isHidden()
    assert "CAPTCHA" in win.lbl_error.text()

    # 2. Refresh CAPTCHA: verifies new code is generated and input field remains blank
    old_code = win.current_captcha_code
    win.regenerate_captcha()
    assert win.current_captcha_code != old_code
    assert win.txt_captcha.text() == ""


def test_settings_repository_and_biometric_settings():
    """Verifies SettingsRepository reads, writes, and caches global system settings."""
    from repositories.settings_repository import settings_repository
    # Set a custom setting
    test_url = "https://test-biometric.ngrok-free.app/punch-interface"
    settings_repository.set_setting("BIOMETRIC_SERVER_URL", test_url, "Test URL")

    # Read back
    val = settings_repository.get_setting("BIOMETRIC_SERVER_URL")
    assert val == test_url

