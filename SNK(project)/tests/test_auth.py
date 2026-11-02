"""
Phase 3 Authentication & Security Unit Tests
Verifies password hashing, authentication service, session context, RBAC policies, and Login GUI.
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication

from utils.security import hash_password, verify_password, validate_username, validate_password_strength
from utils.exceptions import AuthenticationError
from services.auth_service import auth_service, UserSession
from ui.login_dialog import LoginDialog


def test_password_hashing_and_verification():
    """Verify PBKDF2 password hashing and verification."""
    password = "Password@123"
    hashed = hash_password(password)

    assert "$" in hashed
    assert verify_password("Password@123", hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False


def test_input_validation():
    """Verify username and password strength validation."""
    val_u, _ = validate_username("admin")
    assert val_u is True

    val_u2, _ = validate_username("a")
    assert val_u2 is False

    val_p, _ = validate_password_strength("Password@123")
    assert val_p is True

    val_p2, _ = validate_password_strength("123")
    assert val_p2 is False


def test_auth_service_admin_login():
    """Verify successful Admin authentication and session creation."""
    session = auth_service.login("admin", "Password@123")

    assert session is not None
    assert isinstance(session, UserSession)
    assert session.username == "admin"
    assert session.role == "ADMIN"
    assert session.is_admin() is True
    assert auth_service.is_authenticated() is True

    auth_service.logout()
    assert auth_service.is_authenticated() is False


def test_auth_service_hod_login():
    """Verify HOD authentication and department access scoping."""
    session = auth_service.login("hod_mca", "Password@123")

    assert session.role == "HOD"
    assert session.is_hod() is True
    assert session.department_code == "MCA"
    assert auth_service.can_access_department(session.department_id) is True
    assert auth_service.can_access_department(999) is False

    auth_service.logout()


def test_auth_service_invalid_credentials():
    """Verify AuthenticationError on invalid login attempts."""
    with pytest.raises(AuthenticationError):
        auth_service.login("admin", "WrongPassword")

    with pytest.raises(AuthenticationError):
        auth_service.login("non_existent_user", "Password@123")


def test_login_dialog_instantiation():
    """Verify PySide6 Login Dialog widget initializes correctly."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dlg = LoginDialog()
    assert dlg is not None
    assert dlg.txt_username is not None
    assert dlg.txt_password is not None
    assert dlg.btn_login is not None
