"""
Student Management Service
Provides business validation, RBAC checks, and search facilities for student entities.
"""
from typing import List, Dict, Any, Optional
import re
from repositories.student_repository import student_repository, StudentRepository
from repositories.audit_repository import audit_repository
from services.auth_service import UserSession
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.student_service")


class StudentService:
    """Service facade for student search, profile inspection, and administration."""

    def __init__(self, repo: Optional[StudentRepository] = None):
        self.repo = repo or student_repository
        self.audit_repo = audit_repository

    def search_students(
        self,
        user_session: Optional[UserSession],
        search_term: Optional[str] = None,
        department_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Multi-field search across USN, Name, Phone, and Year with HOD department scoping.
        """
        # HODs are scoped to their own department
        dept_filter = department_id
        if user_session and user_session.is_hod():
            dept_filter = user_session.department_id

        return self.repo.search_students(
            search_term=search_term,
            department_id=dept_filter,
            year=year,
        )

    def get_student_by_id(self, user_session: Optional[UserSession], student_id: int) -> Dict[str, Any]:
        """Retrieves a single student profile by ID."""
        student = self.repo.get_by_id(student_id)
        if not student:
            raise ValidationError(f"Student record with ID {student_id} not found.")

        if user_session and user_session.is_hod() and user_session.department_id != student.get("department_id"):
            raise BusinessLogicError("Unauthorized: HODs can only view students enrolled in their department.")

        return student

    def register_student(
        self,
        user_session: UserSession,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Registers a new student. Accessible to ADMIN and HOD.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can register new students.")

        data = dict(payload) if payload else {}
        data.update(kwargs)

        usn = data.get("usn", "").strip().upper()
        if not usn or len(usn) < 5:
            raise ValidationError("A valid Student USN (minimum 5 characters) is required.")

        name = data.get("name", "").strip()
        if not name or len(name) < 2:
            raise ValidationError("Student Full Name must be at least 2 characters.")

        year = data.get("year", 1)
        try:
            year_int = int(year)
            if not 1 <= year_int <= 5:
                raise ValueError()
        except Exception:
            raise ValidationError("Academic Year must be an integer between 1 and 5.")

        dept_id = data.get("department_id")
        if not dept_id:
            dept_id = user_session.department_id or 1

        if user_session.is_hod() and int(dept_id) != user_session.department_id:
            raise BusinessLogicError("HODs can only enroll students into their designated department.")

        # Check unique USN
        existing = self.repo.get_by_usn(usn)
        if existing:
            raise ValidationError(f"A student with USN '{usn}' already exists.")

        created = self.repo.create({
            "usn": usn,
            "name": name,
            "year": year_int,
            "phone_number": data.get("phone_number", "").strip(),
            "department_id": int(dept_id),
            "profile_image_path": data.get("profile_image_path", ""),
        })

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="CREATE_STUDENT",
            entity_type="STUDENT",
            entity_id=usn,
            details=f"Registered student {name} ({usn}) in department ID {dept_id}.",
        )

        logger.info(f"Student successfully registered: {usn} - {name}")
        return created


student_service = StudentService()
