"""
Attendance Service
Business logic, authorization policies, CSV/Excel import orchestration, and roster reporting.
"""
from typing import List, Dict, Any, Optional
import uuid
from imports.attendance_importer import CSVAttendanceProvider, generate_sample_csv
from repositories.attendance_repository import AttendanceRepository
from repositories.audit_repository import AuditRepository
from services.auth_service import UserSession
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.attendance_service")


class AttendanceService:
    """Service facade managing attendance imports, validation, and roster reporting."""

    def __init__(self):
        self.provider = CSVAttendanceProvider()
        self.attendance_repo = AttendanceRepository()
        self.audit_repo = AuditRepository()

    def parse_import_file(self, user_session: Optional[UserSession], file_path: str) -> Dict[str, Any]:
        """
        Parses and validates attendance file.
        Enforces Admin/HOD permission check.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can import attendance files.")

        report = self.provider.parse_and_validate(file_path)

        # HOD restriction check: Filter valid records to HOD's department only
        if user_session.is_hod():
            hod_dept = user_session.department_id
            filtered_valid = [r for r in report["valid_records"] if r["department_id"] == hod_dept]
            report["valid_records"] = filtered_valid
            report["summary"] += f" (Filtered to {len(filtered_valid)} records for Department ID={hod_dept})"

        return report

    def commit_import(
        self,
        user_session: UserSession,
        valid_records: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
    ) -> int:
        """
        Commits validated attendance records to database and logs security audit trail.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can commit attendance imports.")

        if not valid_records:
            raise ValidationError("No valid attendance records to commit.")

        if not batch_id:
            batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"

        saved_count = self.attendance_repo.save_imported_records(valid_records, batch_id)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="IMPORT_ATTENDANCE",
            entity_type="ATTENDANCE_BATCH",
            entity_id=batch_id,
            details=f"Imported {saved_count} valid attendance records.",
        )
        return saved_count

    def list_attendance(
        self,
        user_session: Optional[UserSession],
        department_id: Optional[int] = None,
        faculty_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves attendance records with RBAC scoping:
        - ADMIN: Full access across all departments and faculty.
        - HOD: Restricted to faculty in their department.
        - FACULTY: Restricted strictly to their own attendance records.
        """
        eff_dept = department_id
        eff_fac = faculty_id

        if user_session:
            if user_session.is_hod():
                eff_dept = user_session.department_id
            elif user_session.is_faculty():
                eff_fac = user_session.faculty_id

        return self.attendance_repo.get_all(
            department_id=eff_dept,
            faculty_id=eff_fac,
            start_date=start_date,
            end_date=end_date,
        )

    def generate_demo_sample(self, target_path: str = "sample_attendance.csv") -> str:
        """Generates sample test CSV file."""
        return generate_sample_csv(target_path)


# Singleton service instance
attendance_service = AttendanceService()
