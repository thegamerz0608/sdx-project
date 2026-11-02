"""
Unit & Integration Tests for Lab Instructors, User Profiles, and Dedicated Authentication Window.
Verifies RBAC access for LAB_INSTRUCTOR, circular avatar generation, LoginWindow transitions, and CRUD services.
"""
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.auth_service import auth_service, UserSession
from services.instructor_service import instructor_service
from repositories.instructor_repository import InstructorRepository
from utils.exceptions import ValidationError, BusinessLogicError
from ui.avatar_utils import create_circular_avatar, get_role_color
from ui.login_window import LoginWindow
from ui.instructor_view import InstructorManagementWidget
from ui.main_window import ModernMainWindow, MainWindow


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def instructor_session():
    return auth_service.login("inst_kavita", "Password@123")


def test_user_session_lab_instructor(instructor_session):
    """Verifies that LAB_INSTRUCTOR is recognized as an active role in UserSession."""
    assert instructor_session is not None
    assert instructor_session.role == "LAB_INSTRUCTOR"
    assert instructor_session.is_lab_instructor() is True
    assert instructor_session.is_admin() is False
    assert instructor_session.is_hod() is False
    assert instructor_session.is_faculty() is False
    assert instructor_session.profile_image_path == "uploads/avatars/inst_kavita.png"


def test_instructor_service_list_and_rbac(admin_session, instructor_session):
    """Verifies listing lab instructors with Admin full scope and Instructor department scope."""
    # Admin lists all instructors
    all_inst = instructor_service.list_instructors(admin_session)
    assert isinstance(all_inst, list)
    assert len(all_inst) >= 1
    assert any(i["instructor_code"] == "INS001" for i in all_inst)

    # Non-admin cannot create new instructor
    with pytest.raises(BusinessLogicError):
        instructor_service.create_instructor(
            instructor_session,
            {
                "instructor_code": "INS999",
                "username": "inst_fail",
                "password": "Password@123",
                "first_name": "Test",
                "last_name": "Instructor",
                "email": "test.fail@erp.edu",
                "department_id": 1,
            },
        )


def test_instructor_creation_and_update(admin_session):
    """Verifies Admin can create, read, update, and remove a lab instructor."""
    payload = {
        "instructor_code": "INS088",
        "username": "inst_rohit",
        "password": "Password@123",
        "first_name": "Rohit",
        "last_name": "Verma",
        "email": "rohit.verma@erp.edu",
        "phone": "9876543299",
        "department_id": 1,
        "lab_specialization": "IoT & Embedded Systems Lab",
        "profile_image_path": "uploads/avatars/inst_kavita.png",
    }
    inst_id = instructor_service.create_instructor(admin_session, payload)
    assert inst_id is not None

    inst_data = instructor_service.get_instructor(admin_session, inst_id)
    assert inst_data is not None
    assert inst_data["instructor_code"] == "INS088"
    assert inst_data["lab_specialization"] == "IoT & Embedded Systems Lab"

    # Update specialization
    payload["lab_specialization"] = "Advanced Robotics Lab"
    instructor_service.update_instructor(admin_session, inst_id, payload)
    updated = instructor_service.get_instructor(admin_session, inst_id)
    assert updated["lab_specialization"] == "Advanced Robotics Lab"

    # Deactivate / Delete
    instructor_service.delete_instructor(admin_session, inst_id)
    after_del = instructor_service.get_instructor(admin_session, inst_id)
    assert after_del["status"] == "INACTIVE"


def test_circular_avatar_generation(qapp):
    """Verifies circular avatar QPixmap generation with and without images."""
    # 1. Existing avatar image
    pix_img = create_circular_avatar("uploads/avatars/admin.png", size=48, name="System Admin", role="ADMIN")
    assert pix_img is not None
    assert not pix_img.isNull()
    assert pix_img.width() == 48
    assert pix_img.height() == 48

    # 2. Non-existent path falls back to initials smoothly
    pix_initials = create_circular_avatar(None, size=48, name="Kavita Nair", role="LAB_INSTRUCTOR")
    assert pix_initials is not None
    assert not pix_initials.isNull()
    assert pix_initials.width() == 48
    assert pix_initials.height() == 48

    # 3. Role color palette
    assert get_role_color("LAB_INSTRUCTOR") == "#B45309"
    assert get_role_color("ADMIN") == "#1E40AF"


def test_login_window_instantiation(qapp):
    """Verifies that LoginWindow instantiates with correct credentials fields and persona buttons."""
    win = LoginWindow()
    assert win is not None
    assert win.txt_username is not None
    assert win.txt_password is not None
    assert win.btn_login is not None
    # Strict manual authentication: fields must be blank on launch
    assert win.txt_username.text() == ""
    assert win.txt_password.text() == ""


def test_instructor_management_widget(qapp, admin_session):
    """Verifies that InstructorManagementWidget initializes and renders the instructors roster."""
    widget = InstructorManagementWidget()
    assert widget is not None
    assert widget.tbl_instructors.columnCount() == 8
    assert widget.tbl_instructors.rowCount() >= 1


def test_modern_main_window_integration(qapp, admin_session):
    """Verifies ModernMainWindow supports logout workflow and includes InstructorManagementWidget."""
    win = ModernMainWindow()
    assert win is not None
    assert win.stacked_widget.count() >= 17
    assert hasattr(win, "instructor_view")
    assert win.lbl_top_avatar is not None
    assert win.tab_widget.count() == 16  # Verifies backwards compatibility proxy
