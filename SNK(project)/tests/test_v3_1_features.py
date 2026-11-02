"""
Unit and Integration Tests for v3.1 Feature Expansion:
1. Multi-Department Seeding & CSD Faculty/HODs
2. Lab Instructors across departments & Substitute Recommendation inclusion
3. Student Marks Entry & Real-Time VTU Grade Calculations
4. Official Mark Sheet PDF Generation (ReportLab)
5. Stationery Request Workflow & HOD Review Actions
6. Strict Role-Based Access Control for Security Logs (Tab 14)
"""
import sys
import os
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.auth_service import auth_service, UserSession
from services.student_marks_service import student_marks_service
from services.stationery_service import stationery_service
from services.substitute_service import substitute_service
from repositories.department_repository import department_repository
from repositories.faculty_repository import faculty_repository
from repositories.instructor_repository import instructor_repository
from repositories.user_repository import user_repository
from utils.security import verify_password
from ui.main_window import MainWindow
from ui.student_marks_view import StudentMarksView
from ui.stationery_view import StationeryView


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
def faculty_session():
    return auth_service.login("fac_rahul", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_item1_department_and_faculty_seeding():
    """Verify CSD department is registered and all departments have HODs and faculty with valid credentials."""
    depts = department_repository.get_all()
    dept_codes = [d["code"] for d in depts]
    assert "CSD" in dept_codes
    assert "MECH" in dept_codes
    assert "CIVIL" in dept_codes
    assert "MCA" in dept_codes
    assert "CSE" in dept_codes

    # Verify CSD HOD & Faculty exist in user repository
    csd_hod = user_repository.get_by_username("fac_csd_hod")
    assert csd_hod is not None
    assert csd_hod["role"] == "HOD"
    assert verify_password("Password@123", csd_hod["password_hash"]) is True

    csd_fac = user_repository.get_by_username("fac_csd1")
    assert csd_fac is not None
    assert csd_fac["role"] == "FACULTY"
    assert verify_password("Password@123", csd_fac["password_hash"]) is True


def test_item2_instructor_seeding_and_substitute_recommendations(faculty_session):
    """Verify instructors exist across departments and are included in substitute recommendations."""
    instructors = instructor_repository.get_all()
    assert len(instructors) >= 6
    inst_codes = [i.get("instructor_code") for i in instructors]
    assert "INS001" in inst_codes  # MCA
    assert "INS002" in inst_codes  # CSE
    assert "INS003" in inst_codes  # CSD

    # Verify recommendations include both faculty and instructors globally
    candidates = substitute_service.recommend_substitutes(
        user_session=faculty_session,
        original_faculty_id=2,  # Rahul Sharma (MCA)
        assignment_date="2026-10-15",
        department_id=1,
    )
    assert len(candidates) > 0
    # At least one instructor should be in the candidate list
    has_instructor = any(c.get("is_instructor") is True for c in candidates)
    assert has_instructor is True


def test_item3_student_marks_calculation_and_saving(faculty_session):
    """Verify grade computation against VTU 10-point scale and bulk marks persistence."""
    # Test calculations
    tot1, grd1, st1 = student_marks_service.calculate_grade_and_status(23.5, 22.0, 9.5, 36.0)
    assert tot1 == 91.0
    assert grd1 == "O"
    assert st1 == "PASS"

    tot2, grd2, st2 = student_marks_service.calculate_grade_and_status(10.0, 10.0, 5.0, 10.0)
    assert tot2 == 35.0
    assert grd2 == "F"
    assert st2 == "FAIL"

    # Test retrieval and persistence
    records = student_marks_service.get_marks_for_subject("MCA101", semester=1)
    assert len(records) > 0

    save_payload = [
        {
            "student_id": records[0]["student_id"],
            "subject_code": "MCA101",
            "semester": 1,
            "internal_1": 24.0,
            "internal_2": 23.0,
            "assignment": 9.0,
            "semester_exam": 38.0,
        }
    ]
    saved = student_marks_service.save_marks(save_payload, recorded_by_user_id=faculty_session.user_id)
    assert saved == 1


def test_item4_marksheet_pdf_generation():
    """Verify ReportLab PDF Mark Sheet compilation."""
    pdf_path = student_marks_service.generate_marksheet_pdf("MCA101", semester=1)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    assert pdf_path.endswith(".pdf")


def test_item5_stationery_workflow(faculty_session, hod_session):
    """Verify stationery indent submission, HOD queue retrieval, and approval/rejection."""
    items = stationery_service.get_predefined_items()
    assert "Whiteboard Markers (Pack of 4 - Black/Blue/Red/Green)" in items
    assert "A4 Paper Ream (75 GSM, 500 Sheets)" in items

    # Submit request
    res = stationery_service.submit_request(
        user_session=faculty_session,
        item_name="A4 Paper Ream (75 GSM, 500 Sheets)",
        quantity=3,
        urgency="HIGH",
        purpose="Mid-term exam evaluation sheets",
    )
    req_id = res["request_id"]
    assert req_id > 0
    assert res["status"] == "PENDING"

    # HOD review queue
    hod_requests = stationery_service.get_department_requests_for_hod(hod_session)
    matching = [r for r in hod_requests if r["id"] == req_id]
    assert len(matching) == 1

    # HOD Approves
    success = stationery_service.review_request(
        request_id=req_id,
        reviewer_session=hod_session,
        action="APPROVE",
        remarks="Approved for mid-terms",
    )
    assert success is True

    # Verify updated status
    my_requests = stationery_service.get_my_requests(faculty_session)
    updated = next((r for r in my_requests if r["id"] == req_id), None)
    assert updated is not None
    assert updated["status"] == "APPROVED"
    assert updated["hod_remarks"] == "Approved for mid-terms"


def test_item6_and_item7_ui_decongestion_and_strict_security_logs_rbac(qapp, faculty_session, admin_session):
    """
    Verifies that StudentMarksView and StationeryView have scroll areas for de-congestion,
    and that Tab 14 (Security Logs) is strictly restricted to ADMIN and blocked for Faculty.
    """
    marks_view = StudentMarksView()
    assert marks_view.findChild(object, "marksScrollArea") is not None

    stat_view = StationeryView()
    assert stat_view.findChild(object, "stationeryScrollArea") is not None

    window = MainWindow()

    # 1. Non-admin login (faculty)
    auth_service._current_session = faculty_session
    window.update_session_ui()
    assert window.audit_view.isEnabled() is False

    # Attempt to switch to Tab 14 as Faculty -> Should be denied and redirected to 0
    window.switch_to_tab(14)
    assert window.stacked_widget.currentIndex() == 0

    # 2. Admin login
    auth_service._current_session = admin_session
    window.update_session_ui()
    assert window.audit_view.isEnabled() is True

    # Attempt to switch to Tab 14 as Admin -> Should succeed
    window.switch_to_tab(14)
    assert window.stacked_widget.currentIndex() == 14
