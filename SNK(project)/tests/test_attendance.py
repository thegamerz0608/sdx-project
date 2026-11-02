"""
Phase 5 Attendance Importer and Processing Engine Unit Tests
Verifies CSV parsing, late minutes calculation, working hours, duplicate handling, repository methods, service layer, and PySide6 AttendanceView.
"""
import sys
import os
import tempfile
import pytest
from PySide6.QtWidgets import QApplication

from imports.attendance_importer import CSVAttendanceProvider, generate_sample_csv
from repositories.attendance_repository import attendance_repository
from services.attendance_service import attendance_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError
from ui.attendance_view import AttendanceView


@pytest.fixture
def admin_session():
    return auth_service.login("admin", "Password@123")


@pytest.fixture
def hod_session():
    return auth_service.login("hod_mca", "Password@123")


def test_generate_sample_csv():
    """Verify generating sample CSV file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "sample.csv")
        res_path = generate_sample_csv(csv_path)
        assert os.path.exists(res_path)
        assert os.path.getsize(res_path) > 0


def test_csv_importer_parse_and_validate():
    """Verify CSVAttendanceProvider parses sample data correctly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "test_attendance.csv")
        generate_sample_csv(csv_path)

        provider = CSVAttendanceProvider()
        result = provider.parse_and_validate(csv_path)

        assert result["records_found"] > 0
        assert "valid_records" in result
        assert "invalid_records" in result
        assert "duplicate_records" in result

        # Check calculated fields on valid records
        for rec in result["valid_records"]:
            assert "employee_code" in rec
            assert "attendance_date" in rec
            assert "status" in rec
            assert "late_minutes" in rec
            assert "working_hours" in rec
            assert rec["working_hours"] >= 0


def test_csv_importer_invalid_file_handling():
    """Verify handling of missing file or non-existent path."""
    provider = CSVAttendanceProvider()
    with pytest.raises((FileNotFoundError, ValidationError)):
        provider.parse_and_validate("non_existent_file_path.csv")


def test_attendance_repository_operations():
    """Verify saving imported records and listing roster."""
    records = [
        {
            "faculty_id": 1,
            "employee_code": "FAC001",
            "faculty_name": "Dr. Alan Turing",
            "department_id": 1,
            "department_code": "MCA",
            "attendance_date": "2026-03-01",
            "login_time": "08:55:00",
            "logout_time": "17:05:00",
            "status": "PRESENT",
            "late_minutes": 0,
            "working_hours": 8.17,
            "is_flagged": 0,
            "flag_reason": None,
        }
    ]

    res = attendance_repository.save_imported_records(records, batch_id="TEST_BATCH_001")
    assert res >= 1

    roster = attendance_repository.get_all(department_id=None, faculty_id=1, start_date="2026-03-01", end_date="2026-03-01")
    assert isinstance(roster, list)
    assert len(roster) >= 1
    assert roster[0]["employee_code"] == "FAC001"


def test_attendance_service_process_and_commit(admin_session):
    """Verify service parse_import_file and commit_import workflow."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "service_test.csv")
        generate_sample_csv(csv_path)

        report = attendance_service.parse_import_file(admin_session, csv_path)
        assert len(report["valid_records"]) > 0

        commit_res = attendance_service.commit_import(
            user_session=admin_session,
            valid_records=report["valid_records"],
            batch_id="TEST_BATCH_SERVICE"
        )
        assert commit_res == len(report["valid_records"])


def test_attendance_service_list_roster(admin_session, hod_session):
    """Verify service listing for admin vs HOD."""
    admin_roster = attendance_service.list_attendance(admin_session)
    assert isinstance(admin_roster, list)

    hod_roster = attendance_service.list_attendance(hod_session)
    assert isinstance(hod_roster, list)


def test_attendance_view_pyside6_instantiation():
    """Verify PySide6 AttendanceView widget creates without error."""
    app = QApplication.instance() or QApplication(sys.argv)
    view = AttendanceView()
    assert view is not None
    view.load_attendance_roster()
