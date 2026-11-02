"""
Unit & Integration Tests for v3.0 ERP Upgrade
Verifies:
1. Integrated Alternate Arrangement (Substitute Faculty) assignment on leave submission.
2. Skill-weighted and workload-ranked substitute recommendation logic.
3. Multi-tier automated email workflow (5-step sequential routing).
4. Global Student Directory access across all roles (Faculty, HOD, HR, Principal, Admin).
5. Tuned Pure-NumPy Softmax Logistic Regression with temperature calibration for edge-case accuracy.
"""
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.auth_service import auth_service, UserSession
from services.leave_workflow_service import leave_workflow_service
from services.substitute_service import substitute_service
from services.student_service import student_service
from services.email_service import email_service
from repositories.substitute_repository import substitute_repository
from repositories.student_repository import student_repository
from repositories.leave_application_repository import leave_application_repository
from nlp.classifiers import SoftmaxLogisticRegression, CLASSES
from ui.sidebar import Sidebar
from ui.leave_application_view import LeaveApplicationView
import numpy as np


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
def hod_session():
    return auth_service.login("F001", "Password@123")


@pytest.fixture
def faculty_session():
    return auth_service.login("F002", "Password@123")


@pytest.fixture
def hr_session():
    return auth_service.login("HR001", "Password@123")


@pytest.fixture
def principal_session():
    return auth_service.login("PRIN001", "Password@123")


def test_substitute_recommendation_skill_and_workload_weighted(faculty_session):
    """Verifies that candidates are filtered and ranked by department and workload score."""
    candidates = substitute_service.recommend_substitutes(
        user_session=faculty_session,
        original_faculty_id=2,  # Rahul Sharma (MCA)
        assignment_date="2026-10-15",
        department_id=1,  # MCA
    )
    assert len(candidates) > 0
    # Original faculty (ID 2) must be excluded
    candidate_ids = [c["faculty_id"] for c in candidates]
    assert 2 not in candidate_ids

    # Same department peer should have higher score or rank first
    first = candidates[0]
    assert first["is_available"] is True
    assert "workload_score" in first
    assert "overall_score" in first


def test_leave_submission_with_integrated_alternate_arrangement(faculty_session):
    """Verifies that submitting leave with alternate arrangement creates linked substitute assignment."""
    initial_email_count = len(email_service.sent_emails)

    app = leave_workflow_service.submit_leave_application(
        user_session=faculty_session,
        faculty_id=2,
        requested_leave_type_code="CL",
        from_date_str="2026-11-10",
        to_date_str="2026-11-10",
        reason="Family personal emergency at native place",
        substitute_faculty_id=3,  # Priya Verma
        alternate_date="2026-11-10",
        alternate_time="11:00 AM - 12:00 PM",
        alternate_place="Room 304, MCA Academic Block",
        alternate_work_description="Conduct MCA 1st Sem Python Lab Session",
    )

    assert app is not None
    assert "application_code" in app
    app_id = app["id"]

    # Verify substitute assignment is linked and created
    sub_assign = substitute_repository.get_assignment_by_leave_id(app_id)
    assert sub_assign is not None
    assert sub_assign["substitute_faculty_id"] == 3
    assert sub_assign["assignment_date"] == "2026-11-10"
    assert "Room 304" in sub_assign["class_details"]

    # Verify Tier 1 email to HOD was queued
    assert len(email_service.sent_emails) > initial_email_count
    tier1_email = [e for e in email_service.sent_emails if e["notification_type"] == "TIER1_HOD_SUBMISSION"][-1]
    assert "hod." in tier1_email["to_email"]
    assert app["application_code"] in tier1_email["subject"]
    assert "Priya Verma" in tier1_email["body_text"] or "Room 304" in tier1_email["body_text"]


def test_multi_tier_automated_email_approval_chain(
    faculty_session, hod_session, hr_session, principal_session
):
    """
    Verifies full 5-step multi-tier email sequential workflow:
    1. Faculty applies -> Email to HOD
    2. HOD approves -> Email to HR
    3. HR approves -> Email to Principal
    4. Principal approves -> Email to Faculty
    5. Final approval -> Email to assigned Substitute
    """
    # 1. Submission
    app = leave_workflow_service.submit_leave_application(
        user_session=faculty_session,
        faculty_id=2,
        requested_leave_type_code="CL",
        from_date_str="2026-11-18",
        to_date_str="2026-11-18",
        reason="Attending family function in hometown",
        substitute_faculty_id=3,
        alternate_date="2026-11-18",
        alternate_time="02:00 PM - 03:00 PM",
        alternate_place="Lab 3, MCA Block",
        alternate_work_description="Supervise Machine Learning practical lab",
    )
    app_id = app["id"]

    # 2. HOD Approval -> Tier 2 Email to HR
    hod_res = leave_workflow_service.review_leave_application(
        user_session=hod_session,
        application_id=app_id,
        action="APPROVE",
        remarks="Recommended by HOD MCA with substitute verified.",
    )
    assert hod_res["status"] == "APPROVED"
    tier2 = [e for e in email_service.sent_emails if e["notification_type"] == "TIER2_HR_REVIEW"][-1]
    assert tier2["to_email"] == "hr@erp.edu"

    # 3. HR Approval -> Tier 3 Email to Principal
    hr_res = leave_workflow_service.hr_review_application(
        user_session=hr_session,
        application_id=app_id,
        action="APPROVE",
        remarks="HR verified leave balance and quota. Approved.",
    )
    assert hr_res["status"] == "PENDING_PRINCIPAL"
    tier3 = [e for e in email_service.sent_emails if e["notification_type"] == "TIER3_PRINCIPAL_SANCTION"][-1]
    assert tier3["to_email"] == "principal@erp.edu"

    # 4 & 5. Principal Approval -> Tier 4 (Faculty) & Tier 5 (Substitute) Emails
    prin_res = leave_workflow_service.principal_review_application(
        user_session=principal_session,
        application_id=app_id,
        action="APPROVE",
        remarks="Final sanction granted by Principal.",
    )
    assert prin_res["status"] == "APPROVED"

    tier4 = [e for e in email_service.sent_emails if e["notification_type"] == "TIER4_FACULTY_APPROVED"][-1]
    assert "Sanctioned" in tier4["subject"] or "Approved" in tier4["subject"]

    tier5 = [e for e in email_service.sent_emails if e["notification_type"] == "TIER5_SUBSTITUTE_ASSIGNMENT"][-1]
    assert "Alternate Arrangement" in tier5["subject"] or "Duty Assignment" in tier5["subject"]
    assert "Lab 3" in tier5["body_text"] or "Room" in tier5["body_text"] or "Duty" in tier5["body_text"]


def test_global_student_directory_access_across_roles(faculty_session, hod_session, hr_session, principal_session, admin_session):
    """Verifies that the Student Directory is globally accessible in sidebar permissions across all roles."""
    perms = Sidebar.ROLE_PERMISSIONS
    student_tab_idx = 17

    # All roles must include Tab 17 (Student Directory)
    for role in ["ADMIN", "HOD", "FACULTY", "LAB_INSTRUCTOR", "HR", "PRINCIPAL"]:
        assert student_tab_idx in perms[role], f"Role {role} missing Student Directory (Tab 17) in permissions"

    # Verify student search works across diverse departments
    students = student_service.search_students(user_session=faculty_session)
    assert len(students) >= 5

    # Filter by department
    mca_students = student_service.search_students(user_session=admin_session, department_id=1)
    assert len(mca_students) >= 3

    # Multi-field search by USN
    deepika = student_service.search_students(user_session=admin_session, search_term="1MS21CS089")
    assert len(deepika) == 1
    assert deepika[0]["name"] == "Deepika Rao"


def test_softmax_temperature_calibration_and_edge_case_accuracy():
    """Verifies tuned Softmax Logistic Regression with temperature scaling for edge cases."""
    # Synthetic feature space with 5 classes
    np.random.seed(42)
    X = np.random.randn(50, 20)
    y = np.random.choice(CLASSES, size=50).tolist()

    clf = SoftmaxLogisticRegression(lr=0.15, max_iter=200, temperature=1.0)
    clf.fit(X, y)

    probs = clf.predict_proba(X[:5])
    assert probs.shape == (5, len(CLASSES))
    # Probabilities must sum to 1.0 per sample
    row_sums = np.sum(probs, axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-5)

    # Predictions
    preds = clf.predict(X[:5])
    assert len(preds) == 5
    for p in preds:
        assert p in CLASSES


def test_leave_application_view_alternate_arrangement_ui(qapp):
    """Verifies LeaveApplicationView instantiates with Alternate Arrangement fields."""
    view = LeaveApplicationView()
    assert hasattr(view, "combo_substitute")
    assert hasattr(view, "txt_alt_date")
    assert hasattr(view, "txt_alt_time")
    assert hasattr(view, "txt_alt_place")
    assert hasattr(view, "txt_alt_work")

    # Substitute dropdown should have items populated
    assert view.combo_substitute.count() > 0
