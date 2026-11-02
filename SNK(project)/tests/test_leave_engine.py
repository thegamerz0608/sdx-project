"""
Phase 7 Leave Rules & Policy Engine Unit Tests
Verifies leave repository catalog & balances, policy validations (sandwich rules, consecutive day limits, medical certs, notice periods), service entitlement management, and PySide6 LeaveRulesView.
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication

from repositories.leave_repository import leave_repository
from services.leave_service import leave_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from ui.leave_rules_view import LeaveRulesView


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_leave_repository_types_and_balances():
    """Verify leave type catalog retrieval and faculty balance lookups."""
    types = leave_repository.get_leave_types()
    assert isinstance(types, list)
    assert len(types) >= 1
    codes = [t["code"] for t in types]
    assert "CL" in codes
    assert "ML" in codes

    cl_type = leave_repository.get_leave_type_by_code("CL")
    assert cl_type is not None
    assert cl_type["code"] == "CL"

    fac_balances = leave_repository.get_faculty_balances(faculty_id=1, year=2026)
    assert isinstance(fac_balances, list)
    assert len(fac_balances) >= 1


def test_leave_repository_allocation_update():
    """Verify updating annual leave balance allocation quota."""
    success = leave_repository.update_balance_allocation(faculty_id=1, leave_type_id=1, year=2026, new_allocated=15.0)
    assert success is True

    balances = leave_repository.get_faculty_balances(faculty_id=1, year=2026)
    cl_bal = [b for b in balances if b["leave_type_code"] == "CL"][0]
    assert cl_bal["allocated_days"] == 15.0


def test_leave_service_summary_and_rbac(admin_session, hod_session):
    """Verify service department balance summary and RBAC scoping."""
    admin_summary = leave_service.get_department_balances_summary(admin_session, year=2026)
    assert "summary" in admin_summary
    assert "balances" in admin_summary
    assert admin_summary["summary"]["total_faculty"] >= 1

    hod_summary = leave_service.get_department_balances_summary(hod_session, year=2026)
    assert "summary" in hod_summary
    assert "balances" in hod_summary


def test_leave_service_sandwich_rule_and_consecutive_limit_validation(admin_session):
    """Verify sandwich rule warning detection and consecutive day limit enforcement."""
    # Valid single-day Casual Leave
    valid_res = leave_service.validate_leave_application(
        user_session=admin_session,
        faculty_id=1,
        leave_type_code="CL",
        from_date_str="2026-09-15",
        to_date_str="2026-09-15",
    )
    assert valid_res["valid"] is True
    assert valid_res["requested_days"] == 1.0

    # Sandwich Rule Test: Friday (2026-09-18) to Monday (2026-09-21) spans Saturday & Sunday
    sand_res = leave_service.validate_leave_application(
        user_session=admin_session,
        faculty_id=1,
        leave_type_code="CL",
        from_date_str="2026-09-18",
        to_date_str="2026-09-21",
    )
    assert sand_res["sandwich_days"] == 2
    assert any("Sandwich Rule Alert" in w for w in sand_res["warnings"])

    # Consecutive CL limit breach (> 3 days)
    limit_res = leave_service.validate_leave_application(
        user_session=admin_session,
        faculty_id=1,
        leave_type_code="CL",
        from_date_str="2026-09-15",
        to_date_str="2026-09-19",  # 5 calendar days
    )
    assert limit_res["valid"] is False
    assert any("Casual Leave Policy Limit Breached" in e for e in limit_res["errors"])


def test_leave_service_medical_doc_and_notice_period_checks(admin_session):
    """Verify medical document requirement triggering and EL prior notice checks."""
    # Medical leave > 2 days requires document
    ml_res = leave_service.validate_leave_application(
        user_session=admin_session,
        faculty_id=1,
        leave_type_code="ML",
        from_date_str="2026-09-15",
        to_date_str="2026-09-17",  # 3 days
    )
    assert ml_res["requires_document"] is True
    assert any("Medical Certificate Required" in w for w in ml_res["warnings"])

    # Earned Leave with short notice (< 7 days)
    el_res = leave_service.validate_leave_application(
        user_session=admin_session,
        faculty_id=1,
        leave_type_code="EL",
        from_date_str="2026-09-16",
        to_date_str="2026-09-17",
    )
    assert any("Notice Period Warning" in w for w in el_res["warnings"])


def test_leave_service_insufficient_balance_rejection(admin_session):
    """Verify leave application rejection when requested days exceed available balance."""
    # Faculty ID 4 has 0 CL balance remaining in seed/demo
    res = leave_service.validate_leave_application(
        user_session=admin_session,
        faculty_id=4,
        leave_type_code="CL",
        from_date_str="2026-09-15",
        to_date_str="2026-09-16",
    )
    assert res["valid"] is False
    assert any("Insufficient Leave Balance" in e for e in res["errors"])


def test_leave_rules_view_pyside6_instantiation():
    """Verify PySide6 LeaveRulesView widget creates and loads cleanly."""
    app = QApplication.instance() or QApplication(sys.argv)
    view = LeaveRulesView()
    assert view is not None
    view.load_balances()
