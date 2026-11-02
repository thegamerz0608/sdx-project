"""
Grace & Policy Engine Service
Orchestrates grace minute deductions, ledger reports, RBAC scoping, and policy enforcement warnings.
"""
from typing import List, Dict, Any, Optional
from repositories.grace_repository import grace_repository, GraceRepository
from repositories.audit_repository import audit_repository, AuditRepository
from services.auth_service import UserSession
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.grace_service")


class GraceService:
    """Service facade managing grace minute rules, department ledgers, and policy warnings."""

    def __init__(self):
        self.grace_repo = grace_repository
        self.audit_repo = audit_repository

    def get_department_grace_summary(
        self,
        user_session: UserSession,
        month_year: str = "2026-09",
        department_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves grace ledger and aggregate KPI metrics for department/institution.
        Enforces HOD department scoping.
        """
        if not user_session:
            raise BusinessLogicError("Authentication required.")

        # HOD restriction check
        target_dept_id = department_id
        if user_session.is_hod():
            target_dept_id = user_session.department_id

        ledger = self.grace_repo.get_ledger(department_id=target_dept_id, month_year=month_year)

        total_faculty = len(ledger)
        total_allowed = sum([r["allowed_minutes"] for r in ledger])
        total_used = sum([r["used_minutes"] for r in ledger])
        total_remaining = sum([r["remaining_minutes"] for r in ledger])
        warning_count = sum([1 for r in ledger if r["status"] == "WARNING"])
        exhausted_count = sum([1 for r in ledger if r["status"] == "EXHAUSTED"])

        summary = {
            "month_year": month_year,
            "total_faculty": total_faculty,
            "total_allowed": total_allowed,
            "total_used": total_used,
            "total_remaining": total_remaining,
            "warning_count": warning_count,
            "exhausted_count": exhausted_count,
        }

        return {
            "summary": summary,
            "ledger": ledger,
        }

    def get_faculty_grace_status(
        self, faculty_id: int, month_year: str = "2026-09"
    ) -> Dict[str, Any]:
        """Retrieves grace status for a specific faculty member and month."""
        record = self.grace_repo.get_faculty_grace(faculty_id, month_year)
        if record:
            return record
        return {
            "faculty_id": faculty_id,
            "month_year": month_year,
            "allowed_minutes": 45,
            "used_minutes": 0,
            "remaining_minutes": 45,
            "status": "NORMAL",
        }

    def process_late_arrival(
        self,
        user_session: UserSession,
        faculty_id: int,
        date_str: str,
        late_minutes: int,
    ) -> Dict[str, Any]:
        """
        Deducts late arrival minutes from current month's grace pool.
        Evaluates policy penalty if grace limit is breached.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can process late arrival deductions.")

        if late_minutes <= 0:
            raise ValidationError("Late minutes must be greater than zero.")

        month_year = date_str[:7]
        updated_grace = self.grace_repo.deduct_grace_minutes(
            faculty_id=faculty_id, month_year=month_year, minutes=late_minutes
        )

        remaining = updated_grace.get("remaining_minutes", 0)
        policy_violation = remaining < 0

        recommendation = None
        if policy_violation:
            recommendation = (
                f"Exhausted monthly grace pool by {abs(remaining)} minutes. "
                "Recommended Action: Deduct 0.5 Casual Leave (CL) or mark as Loss of Pay (LOP)."
            )

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="DEDUCT_GRACE",
            entity_type="FACULTY_GRACE",
            entity_id=str(faculty_id),
            details=f"Deducted {late_minutes} late mins for {date_str}. Remaining: {remaining} mins.",
        )

        return {
            "faculty_id": faculty_id,
            "month_year": month_year,
            "late_minutes_deducted": late_minutes,
            "remaining_minutes": remaining,
            "status": updated_grace.get("status", "NORMAL"),
            "policy_violation": policy_violation,
            "recommended_action": recommendation,
        }

    def adjust_faculty_allowance(
        self,
        user_session: UserSession,
        faculty_id: int,
        month_year: str,
        new_allowed: int,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Updates monthly grace minute allowance for a faculty member.
        Enforces Admin/HOD permission.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can adjust grace allowances.")

        if new_allowed < 0 or new_allowed > 300:
            raise ValidationError("Allowed grace minutes must be between 0 and 300 minutes.")

        if not reason or len(reason.strip()) < 5:
            raise ValidationError("A valid administrative reason (min 5 chars) is required.")

        success = self.grace_repo.update_allowed_minutes(
            faculty_id=faculty_id, month_year=month_year, new_allowed=new_allowed
        )

        if not success:
            raise BusinessLogicError("Failed to update grace allowance.")

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="ADJUST_GRACE_ALLOWANCE",
            entity_type="FACULTY_GRACE",
            entity_id=str(faculty_id),
            details=f"Updated grace allowance for {month_year} to {new_allowed} mins. Reason: {reason.strip()}",
        )

        updated_record = self.grace_repo.get_faculty_grace(faculty_id, month_year)
        return {
            "success": True,
            "message": f"Updated grace allowance to {new_allowed} minutes.",
            "record": updated_record,
        }

    def ensure_monthly_allocations(self, user_session: UserSession, month_year: str) -> int:
        """Executes bulk monthly grace minute allocation for all active faculty."""
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can trigger grace allocation.")

        count = self.grace_repo.allocate_monthly_grace(month_year)
        logger.info(f"Allocated monthly grace for {month_year} covering {count} faculty members.")
        return count


grace_service = GraceService()
