"""
Phase 6 Time & Grace Engine Unit Tests
Verifies grace repository ledger queries, deductions, exhaustion warnings, service layer RBAC, policy rules, and PySide6 GraceView layout.
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication

from repositories.grace_repository import grace_repository
from services.grace_service import grace_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from ui.grace_view import GraceView


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_grace_repository_ledger_and_faculty_lookup():
    """Verify ledger retrieval and faculty grace record lookup."""
    ledger = grace_repository.get_ledger(department_id=None, month_year="2026-09")
    assert isinstance(ledger, list)
    assert len(ledger) >= 1

    first = ledger[0]
    assert "faculty_id" in first
    assert "allowed_minutes" in first
    assert "used_minutes" in first
    assert "remaining_minutes" in first
    assert "status" in first

    fac_grace = grace_repository.get_faculty_grace(faculty_id=first["faculty_id"], month_year="2026-09")
    assert fac_grace is not None
    assert fac_grace["faculty_id"] == first["faculty_id"]


def test_grace_repository_deduction_and_status():
    """Verify deducting grace minutes and automatic status computation."""
    res = grace_repository.deduct_grace_minutes(faculty_id=1, month_year="2026-09", minutes=10)
    assert res is not None
    assert res["used_minutes"] >= 10
    assert "status" in res


def test_grace_repository_allowance_update():
    """Verify updating allowed grace minutes quota."""
    success = grace_repository.update_allowed_minutes(faculty_id=1, month_year="2026-09", new_allowed=60)
    assert success is True

    fac_grace = grace_repository.get_faculty_grace(faculty_id=1, month_year="2026-09")
    assert fac_grace["allowed_minutes"] == 60


def test_grace_service_summary_and_rbac(admin_session, hod_session):
    """Verify service department summary and RBAC scoping."""
    admin_summary = grace_service.get_department_grace_summary(admin_session, month_year="2026-09")
    assert "summary" in admin_summary
    assert "ledger" in admin_summary
    assert admin_summary["summary"]["total_faculty"] >= 1

    hod_summary = grace_service.get_department_grace_summary(hod_session, month_year="2026-09")
    assert "summary" in hod_summary
    assert "ledger" in hod_summary


def test_grace_service_late_arrival_processing_and_policy_violation(admin_session):
    """Verify late arrival deduction and policy penalty advice on grace exhaustion."""
    # Deduct standard late arrival
    res = grace_service.process_late_arrival(
        user_session=admin_session, faculty_id=1, date_str="2026-09-05", late_minutes=15
    )
    assert res["faculty_id"] == 1
    assert res["late_minutes_deducted"] == 15

    # Deduct large amount to force exhaustion
    exh_res = grace_service.process_late_arrival(
        user_session=admin_session, faculty_id=1, date_str="2026-09-06", late_minutes=200
    )
    assert exh_res["policy_violation"] is True
    assert exh_res["recommended_action"] is not None


def test_grace_service_allowance_adjustment_validation(admin_session):
    """Verify input validation during allowance adjustment."""
    # Invalid minutes
    with pytest.raises(ValidationError):
        grace_service.adjust_faculty_allowance(
            user_session=admin_session,
            faculty_id=1,
            month_year="2026-09",
            new_allowed=500,
            reason="Exceeds maximum limit",
        )

    # Empty reason
    with pytest.raises(ValidationError):
        grace_service.adjust_faculty_allowance(
            user_session=admin_session,
            faculty_id=1,
            month_year="2026-09",
            new_allowed=50,
            reason="  ",
        )


def test_grace_view_pyside6_instantiation():
    """Verify PySide6 GraceView widget creates and loads cleanly."""
    app = QApplication.instance() or QApplication(sys.argv)
    view = GraceView()
    assert view is not None
    view.load_ledger()
