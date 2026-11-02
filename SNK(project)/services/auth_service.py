"""
Authentication & Role-Based Authorization Service
Manages user authentication, password verification, active session state, and RBAC policies.
"""
from dataclasses import dataclass
from typing import Optional
from repositories.user_repository import UserRepository
from repositories.audit_repository import AuditRepository
from utils.security import (
    verify_password,
    hash_password,
    needs_rehash,
    validate_username,
    validate_password_strength,
)
from utils.exceptions import AuthenticationError
from utils.logger import get_logger

logger = get_logger("services.auth_service")


@dataclass
class UserSession:
    """Active User Session Data Context."""

    user_id: int
    username: str
    role: str  # 'ADMIN', 'HOD', 'FACULTY'
    status: str
    faculty_id: Optional[int] = None
    employee_code: Optional[str] = None
    department_id: Optional[int] = None
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    designation: str = ""
    profile_image_path: Optional[str] = None

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    def is_authenticated(self) -> bool:
        return True

    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    def is_hod(self) -> bool:
        return self.role == "HOD"

    def is_faculty(self) -> bool:
        return self.role == "FACULTY"

    def is_lab_instructor(self) -> bool:
        return self.role == "LAB_INSTRUCTOR"

    def is_hr(self) -> bool:
        return self.role == "HR"

    def is_principal(self) -> bool:
        return self.role == "PRINCIPAL"

    def __repr__(self) -> str:
        return f"<UserSession user='{self.username}' role='{self.role}' dept='{self.department_code}'>"


class AuthService:
    """Singleton Authentication and Session Management Service."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.audit_repo = AuditRepository()
        self._current_session: Optional[UserSession] = None

    @property
    def current_user(self) -> Optional[UserSession]:
        """Returns the currently active UserSession object."""
        return self._current_session

    def is_authenticated(self) -> bool:
        """Returns True if a valid user session is active."""
        return self._current_session is not None

    def login(self, username: str, password: str) -> UserSession:
        """
        Authenticates user credentials using Employee ID or username.
        Raises AuthenticationError if authentication fails.
        """
        identifier = username.strip() if username else ""
        # 1. Input Validation
        valid_user, msg_user = validate_username(identifier)
        if not valid_user:
            raise AuthenticationError("Please enter a valid Employee ID or username (alphanumeric, min 3 characters).")

        valid_pass, msg_pass = validate_password_strength(password)
        if not valid_pass:
            raise AuthenticationError(msg_pass)

        # 2. Fetch User Profile by Employee ID or Username
        user_record = self.user_repo.get_by_username(identifier)
        if not user_record:
            self.audit_repo.log_event(
                user_id=None,
                action="LOGIN_FAILED",
                entity_type="USER",
                entity_id=identifier,
                details="Invalid Employee ID or username provided.",
            )
            raise AuthenticationError("Invalid Employee ID/username or password.")

        # 3. Check Account Status
        if user_record.get("status") != "ACTIVE":
            self.audit_repo.log_event(
                user_id=user_record.get("user_id"),
                action="LOGIN_BLOCKED",
                entity_type="USER",
                entity_id=username,
                details=f"Account status is {user_record.get('status')}.",
            )
            raise AuthenticationError(f"Account is {user_record.get('status')}. Contact Administrator.")

        # 4. Verify Password Hash
        stored_hash = user_record.get("password_hash", "")
        if not verify_password(password, stored_hash):
            self.audit_repo.log_event(
                user_id=user_record.get("user_id"),
                action="LOGIN_FAILED",
                entity_type="USER",
                entity_id=username,
                details="Password verification failed.",
            )
            raise AuthenticationError("Invalid username or password.")

        # Transparently upgrade legacy PBKDF2/SHA256 password hash to Scrypt
        if needs_rehash(stored_hash):
            try:
                new_scrypt_hash = hash_password(password)
                self.user_repo.update_password(user_record["user_id"], new_scrypt_hash)
                logger.info(f"User '{username}' (ID={user_record['user_id']}) password hash transparently upgraded to Scrypt.")
            except Exception as rehash_err:
                logger.warning(f"Transparent rehash deferred for {username}: {rehash_err}")

        # 5. Create Session Context
        session = UserSession(
            user_id=user_record["user_id"],
            username=user_record["username"],
            role=user_record["role"],
            status=user_record["status"],
            faculty_id=user_record.get("faculty_id"),
            employee_code=user_record.get("employee_code"),
            department_id=user_record.get("department_id"),
            department_code=user_record.get("department_code"),
            department_name=user_record.get("department_name"),
            first_name=user_record.get("first_name", ""),
            last_name=user_record.get("last_name", ""),
            email=user_record.get("email", ""),
            designation=user_record.get("designation", ""),
            profile_image_path=user_record.get("profile_image_path"),
        )

        self._current_session = session
        self.user_repo.update_last_login(session.user_id)

        # 6. Audit Log Entry
        self.audit_repo.log_event(
            user_id=session.user_id,
            action="LOGIN_SUCCESS",
            entity_type="USER",
            entity_id=str(session.user_id),
            details=f"User '{session.username}' logged in successfully with role '{session.role}'.",
        )

        logger.info(f"User authentication successful: {session}")
        return session

    def logout(self):
        """Terminates active session and records logout audit log."""
        if self._current_session:
            user_id = self._current_session.user_id
            username = self._current_session.username
            self._current_session = None

            self.audit_repo.log_event(
                user_id=user_id,
                action="LOGOUT",
                entity_type="USER",
                entity_id=str(user_id),
                details=f"User '{username}' logged out.",
            )
            logger.info(f"User '{username}' logged out.")

    def has_role(self, *allowed_roles: str) -> bool:
        """
        Checks if the currently authenticated user possesses one of the allowed roles.
        """
        if not self.is_authenticated() or not self._current_session:
            return False
        return self._current_session.role in allowed_roles

    def can_access_department(self, department_id: int) -> bool:
        """
        Authorization check for HOD department scoping.
        Admins can access all departments.
        HODs can only access their designated department.
        """
        if not self.is_authenticated() or not self._current_session:
            return False
        if self._current_session.is_admin():
            return True
        if self._current_session.is_hod() or self._current_session.is_lab_instructor():
            return self._current_session.department_id == department_id
        return False


# Singleton service instance
auth_service = AuthService()
