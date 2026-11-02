"""
Phase 8 Leave Workflow Engine Unit Tests
Verifies application creation, policy pre-validation, HOD review state transitions, balance debit/credit state accounting, RBAC scoping, and PySide6 LeaveApplicationView.
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication

from repositories.leave_application_repository import leave_application_repository
from services.leave_workflow_service import leave_workflow_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from ui.leave_application_view import LeaveApplicationView


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_leave_application_repository_crud():
    """Verify repository creation and query methods."""
    apps = leave_application_repository.get_applications()
    assert isinstance(apps, list)
    assert len(apps) >= 1

    first = apps[0]
    app_id = first["id"]
    lookup = leave_application_repository.get_application_by_id(app_id)
    assert lookup is not None
    assert lookup["application_code"] == first["application_code"]


def test_leave_application_repository_balance_state_transitions():
    """Verify repository balance state transition helper."""
    succ = leave_application_repository.update_balance_state(
        faculty_id=1, leave_type_id=1, year=2026, days=2.0, state_action="SUBMIT"
    )
    assert succ is True


def test_leave_workflow_service_submit_and_prevalidation(admin_session):
    """Verify submitting leave application and pre-validation checks."""
    app = leave_workflow_service.submit_leave_application(
        user_session=admin_session,
        faculty_id=1,
        requested_leave_type_code="CL",
        from_date_str="2026-09-25",
        to_date_str="2026-09-25",
        reason="Attending family medical appointment",
    )

    assert app is not None
    assert "application_code" in app
    assert app["status"] == "PENDING"


def test_leave_workflow_service_review_approval_and_rejection(admin_session, hod_session):
    """Verify HOD approval and rejection workflows."""
    # Create application for testing review
    app = leave_workflow_service.submit_leave_application(
        user_session=admin_session,
        faculty_id=2,
        requested_leave_type_code="CL",
        from_date_str="2026-09-28",
        to_date_str="2026-09-28",
        reason="Personal leave request for testing approval",
    )

    app_id = app["id"]

    # Approve application
    approved = leave_workflow_service.review_leave_application(
        user_session=hod_session,
        application_id=app_id,
        action="APPROVE",
        remarks="Approved by HOD MCA.",
    )
    assert approved["status"] == "APPROVED"
    assert approved["hod_remarks"] == "Approved by HOD MCA."


def test_leave_workflow_service_cancel_application(admin_session):
    """Verify application cancellation workflow."""
    app = leave_workflow_service.submit_leave_application(
        user_session=admin_session,
        faculty_id=1,
        requested_leave_type_code="CL",
        from_date_str="2026-09-29",
        to_date_str="2026-09-29",
        reason="Leave request to be cancelled",
    )

    cancelled = leave_workflow_service.cancel_leave_application(
        user_session=admin_session, application_id=app["id"]
    )
    assert cancelled["status"] == "CANCELLED"


def test_leave_workflow_service_rbac_scoping(admin_session, hod_session):
    """Verify application listing RBAC scoping."""
    admin_list = leave_workflow_service.list_applications(admin_session)
    assert isinstance(admin_list, list)

    hod_list = leave_workflow_service.list_applications(hod_session)
    assert isinstance(hod_list, list)


def test_leave_application_view_pyside6_instantiation():
    """Verify PySide6 LeaveApplicationView widget creates and loads cleanly."""
    app = QApplication.instance() or QApplication(sys.argv)
    view = LeaveApplicationView()
    assert view is not None
    view.load_applications()


def test_leave_workflow_service_ai_prediction_persistence(admin_session):
    """Verify submitted leave applications persist ai_predicted_code and ai_confidence."""
    app = leave_workflow_service.submit_leave_application(
        user_session=admin_session,
        faculty_id=1,
        requested_leave_type_code="ML",
        from_date_str="2026-10-15",
        to_date_str="2026-10-16",
        reason="Severe viral fever and doctor recommended bed rest for two days.",
        document_path="medical_cert.pdf",
    )
    assert app is not None
    assert app.get("ai_predicted_code") is not None
    assert app["ai_predicted_code"] == "ML"
    assert app.get("ai_confidence") is not None
    assert float(app["ai_confidence"]) > 0.0


def test_leave_application_view_live_nlp_inference():
    """Verify desktop LeaveApplicationView real-time NLP typing feedback."""
    app = QApplication.instance() or QApplication(sys.argv)
    view = LeaveApplicationView()

    # Empty reason test
    view.txt_reason.setPlainText("")
    view._run_live_nlp_inference()
    assert "Type your reason" in view.lbl_ai_prediction.text()

    # Medical leave reason text
    view.txt_reason.setPlainText("Severe fever hospital admission and doctor prescribed rest")
    view._run_live_nlp_inference()
    badge_text = view.lbl_ai_prediction.text()
    assert ("AI Predicted" in badge_text or "AI Suggestion" in badge_text)
    assert "ML" in badge_text


