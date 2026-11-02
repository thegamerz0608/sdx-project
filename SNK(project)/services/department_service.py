"""
Department Management Service
Business logic, input validation, and authorization for department operations.
"""
from typing import List, Dict, Any, Optional
from repositories.department_repository import DepartmentRepository
from repositories.audit_repository import AuditRepository
from services.auth_service import UserSession
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.department_service")


class DepartmentService:
    """Service handling department business logic and security policies."""

    def __init__(self):
        self.dept_repo = DepartmentRepository()
        self.audit_repo = AuditRepository()

    def list_departments(self) -> List[Dict[str, Any]]:
        """Returns all registered department records."""
        return self.dept_repo.get_all()

    def get_department(self, dept_id: int) -> Optional[Dict[str, Any]]:
        """Fetches department details by ID."""
        return self.dept_repo.get_by_id(dept_id)

    def create_department(self, user_session: UserSession, dept_data: Dict[str, Any]) -> int:
        """
        Creates a new department record.
        Enforces ADMIN role requirement and code uniqueness validation.
        """
        if not user_session or not user_session.is_admin():
            raise BusinessLogicError("Unauthorized: Only Administrators can create departments.")

        code = dept_data.get("code", "").strip().upper()
        name = dept_data.get("name", "").strip()

        if not code or len(code) < 2:
            raise ValidationError("Department Code must be at least 2 characters long.")

        if not name or len(name) < 3:
            raise ValidationError("Department Name must be at least 3 characters long.")

        # Check Code Uniqueness
        existing = self.dept_repo.get_by_code(code)
        if existing:
            raise ValidationError(f"Department code '{code}' already exists.")

        hod_id = dept_data.get("hod_faculty_id")
        status = dept_data.get("status", "ACTIVE")

        dept_id = self.dept_repo.create(code, name, hod_id, status)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="CREATE_DEPARTMENT",
            entity_type="DEPARTMENT",
            entity_id=str(dept_id),
            details=f"Created department '{code}' - '{name}'.",
        )
        return dept_id

    def update_department(self, user_session: UserSession, dept_id: int, dept_data: Dict[str, Any]):
        """Updates department record."""
        if not user_session or not user_session.is_admin():
            raise BusinessLogicError("Unauthorized: Only Administrators can modify departments.")

        code = dept_data.get("code", "").strip().upper()
        name = dept_data.get("name", "").strip()

        if not code or len(code) < 2:
            raise ValidationError("Department Code must be at least 2 characters long.")

        if not name or len(name) < 3:
            raise ValidationError("Department Name must be at least 3 characters long.")

        hod_id = dept_data.get("hod_faculty_id")
        status = dept_data.get("status", "ACTIVE")

        self.dept_repo.update(dept_id, code, name, hod_id, status)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="UPDATE_DEPARTMENT",
            entity_type="DEPARTMENT",
            entity_id=str(dept_id),
            details=f"Updated department '{code}'.",
        )


# Singleton service instance
department_service = DepartmentService()
