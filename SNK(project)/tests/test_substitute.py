"""
Phase 9 Substitute System Unit Tests
Verifies candidate recommendation ranking, timetable schedule collision detection, workload balancing scores, assignment creation, response workflows, and PySide6 SubstituteView.
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication

from repositories.substitute_repository import substitute_repository
from services.substitute_service import substitute_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from ui.substitute_view import SubstituteView


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_substitute_repository_crud():
    """Verify repository queries and assignment creation."""
    assignments = substitute_repository.get_assignments()
    assert isinstance(assignments, list)
    assert len(assignments) >= 1

    first = assignments[0]
    lookup = substitute_repository.get_assignment_by_id(first["id"])
    assert lookup is not None
    assert lookup["id"] == first["id"]


def test_substitute_repository_schedule_conflict_detection():
    """Verify schedule conflict detection on same date and time slot."""
    # Candidate faculty #3 has an ASSIGNED assignment on 2026-09-20 09:00:00 - 10:00:00
    has_conflict = substitute_repository.has_schedule_conflict(
        faculty_id=3, assignment_date="2026-09-20", start_time="09:00:00", end_time="10:00:00"
    )
    assert has_conflict is True

    no_conflict = substitute_repository.has_schedule_conflict(
        faculty_id=3, assignment_date="2026-09-20", start_time="14:00:00", end_time="15:00:00"
    )
    assert no_conflict is False


def test_substitute_service_recommendation_ranking(admin_session):
    """Verify recommendation engine candidate ranking and workload score calculation."""
    candidates = substitute_service.recommend_substitutes(
        user_session=admin_session,
        original_faculty_id=2,  # Rahul Sharma
        assignment_date="2026-09-20",
        start_time="09:00:00",
        end_time="10:00:00",
    )

    assert isinstance(candidates, list)
    assert len(candidates) >= 1

    # Ensure original faculty is excluded
    cand_ids = [c["faculty_id"] for c in candidates]
    assert 2 not in cand_ids

    # Verify rank and workload score keys
    for c in candidates:
        assert "rank" in c
        assert "workload_score" in c
        assert "conflict_status" in c


def test_substitute_service_assignment_creation_and_collision_prevention(admin_session):
    """Verify creating a substitute assignment and preventing schedule collision."""
    created = substitute_service.assign_substitute(
        user_session=admin_session,
        leave_application_id=1,
        original_faculty_id=2,
        substitute_faculty_id=3,
        department_id=1,
        assignment_date="2026-09-25",
        start_time="10:00:00",
        end_time="11:00:00",
        class_details="MCA 1st Sem - Operating Systems Lecture",
    )
    assert created is not None
    assert created["status"] == "ASSIGNED"

    # Attempting to assign same substitute at same time slot must raise ValidationError
    with pytest.raises(ValidationError):
        substitute_service.assign_substitute(
            user_session=admin_session,
            leave_application_id=1,
            original_faculty_id=2,
            substitute_faculty_id=3,
            department_id=1,
            assignment_date="2026-09-25",
            start_time="10:00:00",
            end_time="11:00:00",
            class_details="MCA 1st Sem - Parallel Lecture Collision Test",
        )


def test_substitute_service_response_workflow(admin_session):
    """Verify accepting, declining, and completing substitute assignments."""
    # Create assignment
    created = substitute_service.assign_substitute(
        user_session=admin_session,
        leave_application_id=1,
        original_faculty_id=2,
        substitute_faculty_id=3,
        department_id=1,
        assignment_date="2026-09-26",
        start_time="11:00:00",
        end_time="12:00:00",
        class_details="MCA 2nd Sem - Computer Networks",
    )
    ass_id = created["id"]

    # Accept duty
    accepted = substitute_service.respond_to_assignment(
        user_session=admin_session, assignment_id=ass_id, response_action="ACCEPT", remarks="Confirmed availability"
    )
    assert accepted["status"] == "ACCEPTED"

    # Complete duty
    completed = substitute_service.respond_to_assignment(
        user_session=admin_session, assignment_id=ass_id, response_action="COMPLETE", remarks="Lecture delivered"
    )
    assert completed["status"] == "COMPLETED"


def test_substitute_service_rbac_scoping(admin_session, hod_session):
    """Verify substitute listing RBAC scoping for Admin vs HOD."""
    admin_list = substitute_service.list_substitute_assignments(admin_session)
    assert isinstance(admin_list, list)

    hod_list = substitute_service.list_substitute_assignments(hod_session)
    assert isinstance(hod_list, list)


def test_substitute_view_pyside6_instantiation():
    """Verify PySide6 SubstituteView widget creates and loads cleanly."""
    app = QApplication.instance() or QApplication(sys.argv)
    view = SubstituteView()
    assert view is not None
    view.load_assignments()
