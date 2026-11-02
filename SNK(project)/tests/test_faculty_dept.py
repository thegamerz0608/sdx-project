"""
Phase 4 Faculty & Department Unit Tests
Verifies department/faculty repositories, services, RBAC department scoping, and PySide6 view components.
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication

from services.auth_service import auth_service, UserSession
from services.department_service import department_service
from services.faculty_service import faculty_service
from utils.exceptions import ValidationError, BusinessLogicError
from ui.department_view import DepartmentView
from ui.faculty_view import FacultyView


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_department_service_list_and_get(admin_session):
    """Verify listing departments."""
    depts = department_service.list_departments()
    assert isinstance(depts, list)
    assert len(depts) >= 1

    first_dept = depts[0]
    assert "code" in first_dept
    assert "name" in first_dept

    dept_by_id = department_service.get_department(first_dept["id"])
    assert dept_by_id is not None
    assert dept_by_id["code"] == first_dept["code"]


def test_department_creation_validation(admin_session):
    """Verify department creation and code uniqueness validation."""
    payload = {
        "code": "TEST_DEPT",
        "name": "Test Department of Research",
        "hod_faculty_id": None,
        "status": "ACTIVE",
    }
    dept_id = department_service.create_department(admin_session, payload)
    assert dept_id is not None

    # Duplicate code attempt
    with pytest.raises(ValidationError):
        department_service.create_department(admin_session, payload)


def test_faculty_service_list_and_rbac_scoping(admin_session, hod_session):
    """Verify faculty listing and HOD department scoping."""
    # Admin can list all faculty
    all_fac = faculty_service.list_faculty(admin_session)
    assert len(all_fac) >= 2

    # HOD MCA can only list MCA faculty
    hod_fac = faculty_service.list_faculty(hod_session)
    assert len(hod_fac) >= 1
    for f in hod_fac:
        assert f["department_id"] == hod_session.department_id


def test_faculty_creation_and_validation(admin_session):
    """Verify registering a new faculty member."""
    faculty_payload = {
        "employee_code": "F999",
        "username": "fac_test999",
        "password": "Password@123",
        "first_name": "Test",
        "last_name": "Faculty",
        "email": "test.faculty@erp.edu",
        "phone": "9998887770",
        "department_id": 1,
        "designation": "Assistant Professor",
        "role": "FACULTY",
    }
    fac_id = faculty_service.create_faculty(admin_session, faculty_payload)
    assert fac_id is not None

    fac_data = faculty_service.get_faculty(admin_session, fac_id)
    assert fac_data is not None
    assert fac_data["employee_code"] == "F999"
    assert fac_data["email"] == "test.faculty@erp.edu"

    # Duplicate employee code check
    with pytest.raises(ValidationError):
        faculty_service.create_faculty(admin_session, faculty_payload)


def test_views_instantiation():
    """Verify DepartmentView and FacultyView UI widgets instantiate correctly."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dept_v = DepartmentView()
    assert dept_v is not None
    assert dept_v.tbl_departments is not None

    fac_v = FacultyView()
    assert fac_v is not None
    assert fac_v.tbl_faculty is not None
