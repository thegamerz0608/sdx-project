"""
Leave Rules & Policy Engine Service
Orchestrates leave entitlement tracking, policy validations (sandwich rules, consecutive limits, notice requirements), and administrative quota adjustments.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from repositories.leave_repository import leave_repository, LeaveRepository
from repositories.audit_repository import audit_repository, AuditRepository
from services.auth_service import UserSession
from services.time_service import TimeService
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.leave_service")


class LeaveService:
    """Service facade managing institutional leave policy evaluation and entitlements."""

    def __init__(self):
        self.leave_repo = leave_repository
        self.audit_repo = audit_repository

    def get_department_balances_summary(
        self,
        user_session: UserSession,
        year: int = 2026,
        department_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves leave balance ledger and aggregate KPI metrics for department/institution.
        Enforces HOD department scoping.
        """
        if not user_session:
            raise BusinessLogicError("Authentication required.")

        target_dept_id = department_id
        if user_session.is_hod():
            target_dept_id = user_session.department_id

        balances = self.leave_repo.get_department_balances(department_id=target_dept_id, year=year)

        unique_faculty = set([b["faculty_id"] for b in balances])
        total_faculty = len(unique_faculty)

        cl_remaining = sum([b["remaining_days"] for b in balances if b["leave_type_code"] == "CL"])
        ml_remaining = sum([b["remaining_days"] for b in balances if b["leave_type_code"] == "ML"])
        el_remaining = sum([b["remaining_days"] for b in balances if b["leave_type_code"] == "EL"])
        total_pending = sum([b["pending_days"] for b in balances])

        summary = {
            "year": year,
            "total_faculty": total_faculty,
            "total_cl_remaining": cl_remaining,
            "total_ml_remaining": ml_remaining,
            "total_el_remaining": el_remaining,
            "total_pending_days": total_pending,
        }

        return {
            "summary": summary,
            "balances": balances,
        }

    def get_faculty_balances(self, faculty_id: int, year: int = 2026) -> List[Dict[str, Any]]:
        """Retrieves active leave balances for a specific faculty member."""
        return self.leave_repo.get_faculty_balances(faculty_id=faculty_id, year=year)

    get_leave_balances_summary = get_faculty_balances

    def validate_leave_application(
        self,
        user_session: UserSession,
        faculty_id: int,
        leave_type_code: str,
        from_date_str: str,
        to_date_str: str,
        is_half_day: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates a proposed leave application against institutional leave rules:
        - Date range and half-day duration
        - Sandwich leave detection across weekend/holiday boundaries
        - Maximum consecutive day limits
        - Medical document requirements
        - Prior notice requirement checks
        - Sufficient entitlement balance check
        """
        if not user_session:
            raise BusinessLogicError("Authentication required.")

        clean_code = leave_type_code.strip().upper()
        leave_type_info = self.leave_repo.get_leave_type_by_code(clean_code)
        if not leave_type_info:
            raise ValidationError(f"Invalid or inactive leave type code '{leave_type_code}'.")

        try:
            from_dt = datetime.strptime(from_date_str.strip(), "%Y-%m-%d").date()
            to_dt = datetime.strptime(to_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Dates must be provided in valid 'YYYY-MM-DD' format.")

        if to_dt < from_dt:
            raise ValidationError("End date ('to_date') cannot be earlier than start date ('from_date').")

        calendar_days = (to_dt - from_dt).days + 1
        if is_half_day:
            if calendar_days != 1:
                raise ValidationError("Half-day leave option can only be selected for a single-day request.")
            requested_days = 0.5
        else:
            requested_days = float(calendar_days)

        warnings = []
        errors = []

        # 1. Sandwich Rule Evaluation (Weekend Intersect Check)
        sandwich_days = 0
        current_day = from_dt
        while current_day <= to_dt:
            if current_day.weekday() in [5, 6]:  # Saturday (5) or Sunday (6)
                sandwich_days += 1
            current_day += timedelta(days=1)

        if sandwich_days > 0 and clean_code in ["CL", "RL"] and calendar_days > 1:
            warnings.append(
                f"Sandwich Rule Alert: Leave range includes {sandwich_days} weekend day(s). "
                "Intervening non-working days may be debited from balance per institutional policy."
            )

        # 2. Maximum Consecutive Days Limit Rule
        if clean_code == "CL" and calendar_days > 3:
            errors.append(
                f"Casual Leave Policy Limit Breached: Requested {calendar_days} consecutive days (Maximum allowed CL is 3 days)."
            )

        # 3. Medical Document Requirement Rule
        requires_document = bool(leave_type_info.get("requires_document", 0))
        if clean_code == "ML" and requested_days > 2.0:
            requires_document = True
            warnings.append("Medical Certificate Required: Medical leave exceeding 2 days requires a valid medical certificate.")

        # 4. Prior Notice Requirement Rule (EL / AVL require at least 7 days notice)
        today = TimeService.get_current_date()
        notice_days = (from_dt - today).days
        if clean_code in ["EL", "AVL"] and notice_days < 7:
            warnings.append(
                f"Notice Period Warning: {leave_type_info['name']} requires at least 7 days prior notice. "
                f"Notice provided: {max(0, notice_days)} day(s)."
            )

        # 5. Balance Entitlement Check
        year = from_dt.year
        faculty_balances = self.leave_repo.get_faculty_balances(faculty_id=faculty_id, year=year)
        target_balance = None
        for b in faculty_balances:
            if b["leave_type_code"] == clean_code:
                target_balance = b
                break

        remaining = 0.0
        if target_balance:
            remaining = float(target_balance.get("remaining_days", 0.0))
        else:
            errors.append(f"No active leave balance record found for {clean_code} in year {year}.")

        if requested_days > remaining:
            errors.append(
                f"Insufficient Leave Balance: Requested {requested_days} day(s), but remaining {clean_code} balance is only {remaining} day(s)."
            )

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "faculty_id": faculty_id,
            "leave_type_code": clean_code,
            "leave_type_name": leave_type_info["name"],
            "from_date": str(from_dt),
            "to_date": str(to_dt),
            "calendar_days": calendar_days,
            "requested_days": requested_days,
            "sandwich_days": sandwich_days,
            "requires_document": requires_document,
            "remaining_balance": remaining,
            "warnings": warnings,
            "errors": errors,
        }

    def adjust_entitlement_allocation(
        self,
        user_session: UserSession,
        faculty_id: int,
        leave_type_code: str,
        year: int,
        new_allocated: float,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Updates allocated leave quota for a faculty member and leave type.
        Enforces Admin/HOD authorization.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can adjust leave entitlements.")

        if new_allocated < 0.0 or new_allocated > 365.0:
            raise ValidationError("Allocated leave days must be between 0.0 and 365.0 days.")

        if not reason or len(reason.strip()) < 5:
            raise ValidationError("A valid administrative reason (min 5 chars) is required.")

        lt_info = self.leave_repo.get_leave_type_by_code(leave_type_code)
        if not lt_info:
            raise ValidationError(f"Invalid leave type code '{leave_type_code}'.")

        success = self.leave_repo.update_balance_allocation(
            faculty_id=faculty_id,
            leave_type_id=lt_info["id"],
            year=year,
            new_allocated=new_allocated,
        )

        if not success:
            raise BusinessLogicError("Failed to update leave balance allocation.")

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="ADJUST_LEAVE_ENTITLEMENT",
            entity_type="FACULTY_LEAVE_BALANCE",
            entity_id=str(faculty_id),
            details=f"Adjusted {leave_type_code} allocation for year {year} to {new_allocated} days. Reason: {reason.strip()}",
        )

        return {
            "success": True,
            "message": f"Updated {leave_type_code} annual quota to {new_allocated} days for year {year}.",
        }

    def initialize_year_balances(self, user_session: UserSession, year: int = 2026) -> int:
        """Initializes default annual leave balances for faculty members."""
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can initialize leave balances.")

        count = self.leave_repo.init_faculty_annual_balances(faculty_id=1, year=year)
        logger.info(f"Initialized annual leave balances for year {year}.")
        return count


leave_service = LeaveService()
