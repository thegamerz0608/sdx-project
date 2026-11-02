"""
Unit Tests for Phase 16: Audit Trail, Security Log Service, and RBAC Engine
"""
import pytest
from PySide6.QtWidgets import QApplication
from repositories.audit_repository import audit_repository, AuditRepository
from services.audit_service import audit_service, AuditService
from services.auth_service import auth_service
from ui.audit_view import AuditView


@pytest.fixture(scope="module")
def qapp():
    """Provides single QApplication instance for PySide6 GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_audit_repository_log_and_query():
    """Tests logging security events and filtering audit records from repository."""
    repo = AuditRepository()

    # Log events
    repo.log_event(
        user_id=1,
        action="TEST_ACTION_LOGIN",
        entity_type="USER",
        entity_id="101",
        details="User logged in from test suite.",
    )
    repo.log_event(
        user_id=2,
        action="TEST_ACTION_LEAVE",
        entity_type="LEAVE_APPLICATION",
        entity_id="LV-999",
        details="Submitted test leave application.",
    )

    # Fetch all
    logs = repo.get_audit_logs(limit=50)
    assert len(logs) >= 2

    # Filter by action
    login_logs = repo.get_audit_logs(action="TEST_ACTION_LOGIN")
    assert any(l["action"] == "TEST_ACTION_LOGIN" for l in login_logs)

    # Filter by search term
    search_logs = repo.get_audit_logs(search_term="LV-999")
    assert any(l["entity_id"] == "LV-999" for l in search_logs)


def test_audit_service_log_activity_and_rbac():
    """Tests AuditService logging, RBAC scoping, matrix definitions, and log reader."""
    service = AuditService()

    # Admin Login
    auth_service.login("admin", "Password@123")
    assert auth_service.current_user is not None
    assert auth_service.current_user.is_admin()

    # Log activity under admin
    service.log_activity(
        action="ADMIN_CONFIG_CHANGE",
        entity_type="SYSTEM",
        entity_id="CFG_01",
        details="Changed system grace period threshold.",
    )

    # Admin view - should return logs
    admin_logs = service.get_audit_logs(limit=50)
    assert isinstance(admin_logs, list)
    assert len(admin_logs) > 0

    # Non-admin Login (HOD)
    auth_service.login("hod_mca", "Password@123")
    assert auth_service.current_user is not None
    assert auth_service.current_user.is_hod()

    # HOD view - scoped to HOD's user_id
    hod_logs = service.get_audit_logs(limit=50)
    assert isinstance(hod_logs, list)
    assert all(l.get("user_id") == auth_service.current_user.user_id for l in hod_logs if l.get("user_id"))

    # RBAC Permission Matrix Test
    matrix = service.get_rbac_permission_matrix()
    assert isinstance(matrix, list)
    assert len(matrix) >= 15
    first_item = matrix[0]
    assert "module" in first_item
    assert "ADMIN" in first_item
    assert "HOD" in first_item
    assert "FACULTY" in first_item

    # System Logs Reader Test
    sys_logs = service.get_system_logs(max_lines=20)
    assert isinstance(sys_logs, list)
    assert len(sys_logs) > 0


def test_audit_view_pyside6_instantiation(qapp):
    """Tests PySide6 AuditView widget creation, sub-tabs setup, and table population."""
    auth_service.login("admin", "Password@123")

    view = AuditView()
    assert view is not None
    assert view.tabs.count() == 3
    assert view.audit_table.columnCount() == 8
    assert view.rbac_table.columnCount() == 5

    # Check that audit table loaded rows
    assert view.audit_table.rowCount() > 0

    # Check RBAC table loaded rows
    assert view.rbac_table.rowCount() >= 15

    # Check filter execution
    view.combo_action.setCurrentText("LOGIN_SUCCESS")
    view.load_audit_logs()
    assert view.audit_table.rowCount() >= 0
