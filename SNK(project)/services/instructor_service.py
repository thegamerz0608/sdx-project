"""
Lab Instructor Management Service
Handles business logic, validation, audit logging, and RBAC policies for Lab Instructors.
"""
from typing import List, Dict, Any, Optional
import re
from repositories.instructor_repository import InstructorRepository
from repositories.audit_repository import AuditRepository
from services.auth_service import UserSession
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.instructor_service")


class InstructorService:
    """Service handling Lab Instructor CRUD operations and RBAC authorization."""

    def __init__(self):
        self.instructor_repo = InstructorRepository()
        self.audit_repo = AuditRepository()

    def list_instructors(
        self,
        user_session: Optional[UserSession],
        department_id_filter: Optional[int] = None,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves lab instructors with RBAC department scoping:
        - ADMIN: Full access across all departments.
        - HOD: Restricted to instructors in HOD's department.
        - FACULTY / LAB_INSTRUCTOR: Scoped to their department.
        """
        effective_dept = department_id_filter
        if user_session:
            if user_session.is_hod():
                effective_dept = user_session.department_id
            elif not user_session.is_admin() and effective_dept is None:
                effective_dept = user_session.department_id

        return self.instructor_repo.get_all(department_id=effective_dept, search_term=search_term)

    def get_instructor(self, user_session: Optional[UserSession], instructor_id: int) -> Optional[Dict[str, Any]]:
        """Fetches lab instructor details by ID with authorization checks."""
        inst = self.instructor_repo.get_by_id(instructor_id)
        if not inst:
            return None

        if user_session and user_session.is_hod() and inst["department_id"] != user_session.department_id:
            raise BusinessLogicError("Unauthorized: You can only view instructors in your department.")

        return inst

    def create_instructor(self, user_session: UserSession, instructor_data: Dict[str, Any]) -> int:
        """
        Creates a new Lab Instructor record and user credentials.
        Restricted to Administrators.
        """
        if not user_session or not user_session.is_admin():
            raise BusinessLogicError("Unauthorized: Only Administrators can create new Lab Instructors.")

        code = instructor_data.get("instructor_code", "").strip().upper()
        username = instructor_data.get("username", "").strip().lower()
        password = instructor_data.get("password", "").strip()
        first_name = instructor_data.get("first_name", "").strip()
        last_name = instructor_data.get("last_name", "").strip()
        email = instructor_data.get("email", "").strip().lower()

        if not code:
            raise ValidationError("Instructor Code is required (e.g., INS002).")
        if not username or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        if not first_name or not last_name:
            raise ValidationError("First and Last Name are required.")
        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            raise ValidationError("A valid institutional email address is required.")
        if not instructor_data.get("department_id"):
            raise ValidationError("Department selection is required.")

        existing = self.instructor_repo.get_by_code(code)
        if existing:
            raise ValidationError(f"Instructor Code '{code}' is already assigned to {existing['full_name']}.")

        inst_id = self.instructor_repo.create(instructor_data)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="CREATE_LAB_INSTRUCTOR",
            entity_type="LAB_INSTRUCTOR",
            entity_id=str(inst_id),
            details=f"Created lab instructor '{code}' ({first_name} {last_name}).",
        )
        return inst_id

    def update_instructor(self, user_session: UserSession, instructor_id: int, instructor_data: Dict[str, Any]):
        """Updates lab instructor profile."""
        if not user_session or not user_session.is_admin():
            raise BusinessLogicError("Unauthorized: Only Administrators can edit Lab Instructors.")

        existing = self.instructor_repo.get_by_id(instructor_id)
        if not existing:
            raise ValidationError("Lab instructor record not found.")

        first_name = instructor_data.get("first_name", "").strip()
        last_name = instructor_data.get("last_name", "").strip()
        email = instructor_data.get("email", "").strip().lower()

        if not first_name or not last_name:
            raise ValidationError("First and Last Name are required.")
        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            raise ValidationError("A valid institutional email address is required.")

        self.instructor_repo.update(instructor_id, instructor_data)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="UPDATE_LAB_INSTRUCTOR",
            entity_type="LAB_INSTRUCTOR",
            entity_id=str(instructor_id),
            details=f"Updated profile for lab instructor '{existing['instructor_code']}'.",
        )

    def delete_instructor(self, user_session: UserSession, instructor_id: int):
        """Deactivates/removes a lab instructor."""
        if not user_session or not user_session.is_admin():
            raise BusinessLogicError("Unauthorized: Only Administrators can remove Lab Instructors.")

        existing = self.instructor_repo.get_by_id(instructor_id)
        if not existing:
            raise ValidationError("Lab instructor record not found.")

        self.instructor_repo.delete(instructor_id)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="DELETE_LAB_INSTRUCTOR",
            entity_type="LAB_INSTRUCTOR",
            entity_id=str(instructor_id),
            details=f"Deactivated lab instructor '{existing['instructor_code']}'.",
        )


# Singleton service instance
instructor_service = InstructorService()
