"""
Profile Change Service
Manages business logic, strict server-side validation, cryptographic audit trails,
and RBAC permissions enforcement for profile change approval workflows.
"""
import os
import re
import shutil
import time
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from repositories.profile_change_repository import profile_change_repository, ProfileChangeRepository
from repositories.audit_repository import AuditRepository
from repositories.faculty_repository import faculty_repository
from services.auth_service import UserSession
from config.profile_permissions import (
    is_direct_edit_field,
    is_approval_required_field,
    is_locked_field,
    can_review_profile_changes,
    can_review_specific_request,
    get_field_label,
)
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.profile_change_service")

# Server-side validation regex patterns
REGEX_PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
REGEX_AADHAAR = re.compile(r"^\d{12}$")
REGEX_UAN = re.compile(r"^\d{12}$")
REGEX_ACCOUNT = re.compile(r"^\d{9,18}$")
REGEX_PHONE = re.compile(r"^\d{10}$")
REGEX_EMAIL = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


def mask_sensitive_value(value: Optional[str]) -> str:
    """Masks sensitive values (e.g. PAN, Aadhaar, Account No) as XXXXXX1234."""
    val = str(value or "").strip()
    if not val:
        return "N/A"
    if len(val) <= 4:
        return "XXXX"
    return "XXXXXX" + val[-4:]


class ProfileChangeService:
    """Service coordinating profile change requests, reviews, and audits."""

    def __init__(self):
        self.change_repo = profile_change_repository
        self.audit_repo = AuditRepository()
        self.faculty_repo = faculty_repository

    def validate_field_value(self, field_name: str, value: str):
        """
        Server-side validation of field formats.
        Raises ValidationError if value format violates institutional standards.
        """
        val = str(value or "").strip()
        label = get_field_label(field_name)

        if not val:
            raise ValidationError(f"{label} cannot be empty.")

        if field_name == "pan_number":
            if not REGEX_PAN.match(val):
                raise ValidationError("Invalid PAN Card format. Expected format: ABCDE1234F (5 letters, 4 digits, 1 letter).")

        elif field_name == "aadhaar_number":
            if not REGEX_AADHAAR.match(val):
                raise ValidationError("Invalid Aadhaar format. Aadhaar number must be exactly 12 numeric digits.")

        elif field_name == "uan_number":
            if not REGEX_UAN.match(val):
                raise ValidationError("Invalid UAN format. UAN number must be exactly 12 numeric digits.")

        elif field_name == "salary_account_no":
            if not REGEX_ACCOUNT.match(val):
                raise ValidationError("Invalid Bank Account number. Must be numeric and between 9 to 18 digits.")

        elif field_name == "phone":
            if not REGEX_PHONE.match(val):
                raise ValidationError("Mobile number must be exactly 10 numeric digits.")

        elif field_name == "personal_email":
            if not REGEX_EMAIL.match(val.lower()):
                raise ValidationError("Invalid email address format.")

        elif field_name == "dob":
            try:
                dt = datetime.strptime(val[:10], "%Y-%m-%d").date()
                if dt >= date.today():
                    raise ValidationError("Date of Birth cannot be today or in the future.")
            except ValueError:
                raise ValidationError("Invalid Date of Birth format. Please use YYYY-MM-DD.")

        elif field_name in ("name", "first_name", "last_name"):
            if len(val) < 2:
                raise ValidationError(f"{label} must be at least 2 characters long.")

    def handle_proof_upload(self, source_file_path: str, employee_id: int, field_name: str) -> str:
        """
        Validates and securely stores proof documents in uploads/proofs/.
        Allows only JPG, PNG, PDF with maximum file size of 2 MB.
        Returns relative path to stored proof.
        """
        src = Path(source_file_path)
        if not src.exists():
            raise ValidationError("Specified proof file does not exist.")

        # Check file extension
        ext = src.suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".pdf"]:
            raise ValidationError("Invalid proof file format. Only JPG, PNG, and PDF files are allowed.")

        # Check file size (<= 2 MB)
        size_bytes = src.stat().st_size
        if size_bytes > 2 * 1024 * 1024:
            size_mb = size_bytes / (1024 * 1024)
            raise ValidationError(f"Proof file is too large ({size_mb:.2f} MB). Maximum allowed size is 2.0 MB.")

        # Destination path with sanitized timestamped filename
        base_dir = Path(__file__).resolve().parent.parent
        target_dir = base_dir / "uploads" / "proofs"
        target_dir.mkdir(parents=True, exist_ok=True)

        target_name = f"proof_emp{employee_id}_{field_name}_{int(time.time())}{ext}"
        target_file = target_dir / target_name

        try:
            shutil.copy2(str(src), str(target_file))
            rel_path = f"uploads/proofs/{target_name}"
            logger.info(f"Proof stored securely at {rel_path}")
            return rel_path
        except Exception as exc:
            logger.error(f"Failed to copy proof file: {exc}")
            raise BusinessLogicError(f"Failed to save proof document: {exc}")

    def submit_change_request(
        self,
        user_session: UserSession,
        field_name: str,
        new_value: str,
        reason: str,
        proof_file_path: Optional[str] = None,
    ) -> int:
        """
        Submits a change request for an approval-required profile field.
        Enforces duplicate prevention, field format checks, and mandatory reason.
        """
        if not user_session or not user_session.faculty_id:
            raise BusinessLogicError("Unauthorized: An active employee session is required to request profile changes.")

        employee_id = user_session.faculty_id
        fac = self.faculty_repo.get_by_id(employee_id)
        if not fac:
            raise ValidationError("Employee profile record not found.")

        # 1. Classification check
        if is_locked_field(field_name):
            raise BusinessLogicError(f"Field '{get_field_label(field_name)}' is strictly locked and cannot be requested by employee.")

        if is_direct_edit_field(field_name):
            raise BusinessLogicError(f"Field '{get_field_label(field_name)}' does not require approval and should be updated directly.")

        # 2. Check for existing pending request (prevent duplicates)
        existing_pending = self.change_repo.get_pending_by_employee_and_field(employee_id, field_name)
        if existing_pending:
            field_label = get_field_label(field_name)
            raise ValidationError(
                f"A change request for '{field_label}' is already pending HR approval.\n\n"
                f"Requested on: {existing_pending.get('requested_at')}\n"
                "Please wait for review or cancel the pending request before submitting a new one."
            )

        # 3. Mandatory reason check
        clean_reason = str(reason or "").strip()
        if len(clean_reason) < 5:
            raise ValidationError("Please provide a specific reason for requesting this profile change (at least 5 characters).")

        # 4. Server-side format validation
        clean_val = str(new_value or "").strip()
        self.validate_field_value(field_name, clean_val)

        # 5. Check if value is actually different from current value
        old_val = str(fac.get(field_name, "") or "").strip()
        if old_val == clean_val:
            raise ValidationError(f"The new {get_field_label(field_name)} is identical to your current value.")

        # 6. Process optional proof file
        proof_rel_path = None
        if proof_file_path:
            proof_rel_path = self.handle_proof_upload(proof_file_path, employee_id, field_name)

        # 7. Create request record
        req_id = self.change_repo.create_request(
            employee_id=employee_id,
            field_name=field_name,
            old_value=old_val,
            new_value=clean_val,
            reason=clean_reason,
            proof_path=proof_rel_path,
        )

        # 8. Audit trail and System Activity Security Log entry
        masked_new = mask_sensitive_value(clean_val)
        emp_code = user_session.employee_code or f"EMP{employee_id}"
        field_lbl = get_field_label(field_name)
        log_line = f"[PROFILE_CHANGE] Requested by {emp_code} for {field_lbl} (new: {masked_new})"

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="REQUEST_PROFILE_CHANGE",
            entity_type="FACULTY_PROFILE",
            entity_id=str(req_id),
            details=log_line,
        )
        self.change_repo.log_audit(req_id, "SUBMITTED", user_session.user_id, log_line)
        logger.info(log_line)

        return req_id

    def cancel_request(self, user_session: UserSession, request_id: int) -> bool:
        """Allows faculty to cancel their own pending change request."""
        req = self.change_repo.get_by_id(request_id)
        if not req:
            raise ValidationError("Change request not found.")

        if req.get("status") != "PENDING":
            raise BusinessLogicError(f"Cannot cancel request with status '{req.get('status')}'.")

        # Requester verification (only the requester or Admin can cancel)
        is_owner = (
            user_session.faculty_id == req.get("employee_id")
            or user_session.user_id == req.get("requester_user_id")
        )
        if not is_owner and not user_session.is_admin():
            raise BusinessLogicError("Unauthorized: You can only cancel your own pending requests.")

        success = self.change_repo.cancel_request(request_id, user_session.user_id)
        if success:
            emp_code = user_session.employee_code or f"USER_{user_session.user_id}"
            field_lbl = get_field_label(req.get("field_name", ""))
            log_line = f"[PROFILE_CHANGE] CANCELLED by {emp_code} for {field_lbl}"
            self.audit_repo.log_event(
                user_id=user_session.user_id,
                action="CANCEL_PROFILE_CHANGE",
                entity_type="FACULTY_PROFILE",
                entity_id=str(request_id),
                details=log_line,
            )
            logger.info(log_line)
        return success

    def approve_request(
        self,
        reviewer_session: UserSession,
        request_id: int,
        reviewer_remark: Optional[str] = None,
    ) -> bool:
        """
        Validates reviewer authority and atomically approves the change request.
        Updates faculty profile in a single transaction.
        """
        req = self.change_repo.get_by_id(request_id)
        if not req:
            raise ValidationError("Change request not found.")

        if req.get("status") != "PENDING":
            raise BusinessLogicError(f"Request is already resolved with status '{req.get('status')}'.")

        # Strict RBAC and self-approval validation
        allowed, reason = can_review_specific_request(
            reviewer_role=reviewer_session.role,
            reviewer_user_id=reviewer_session.user_id,
            requester_user_id=req.get("requester_user_id") or 0,
            requester_role=req.get("requester_role", "FACULTY"),
        )
        if not allowed:
            raise BusinessLogicError(reason)

        success = self.change_repo.approve_request(
            request_id=request_id,
            reviewer_id=reviewer_session.user_id,
            reviewer_remark=reviewer_remark or "Approved by reviewer.",
        )

        if success:
            rev_code = reviewer_session.employee_code or reviewer_session.username
            emp_code = req.get("employee_code", f"EMP{req.get('employee_id')}")
            field_lbl = get_field_label(req.get("field_name", ""))
            log_line = f"[PROFILE_CHANGE] APPROVED by {rev_code} for {emp_code} - {field_lbl}"

            self.audit_repo.log_event(
                user_id=reviewer_session.user_id,
                action="APPROVE_PROFILE_CHANGE",
                entity_type="FACULTY_PROFILE",
                entity_id=str(request_id),
                details=log_line,
            )
            logger.info(log_line)
        return success

    def reject_request(
        self,
        reviewer_session: UserSession,
        request_id: int,
        reviewer_remark: str,
    ) -> bool:
        """
        Validates reviewer authority and marks request as REJECTED.
        Reviewer remark is strictly mandatory on rejection.
        """
        clean_remark = str(reviewer_remark or "").strip()
        if not clean_remark or len(clean_remark) < 4:
            raise ValidationError("A reviewer remark is mandatory when rejecting a profile change request (min 4 characters).")

        req = self.change_repo.get_by_id(request_id)
        if not req:
            raise ValidationError("Change request not found.")

        if req.get("status") != "PENDING":
            raise BusinessLogicError(f"Request is already resolved with status '{req.get('status')}'.")

        # Strict RBAC and self-approval validation
        allowed, reason = can_review_specific_request(
            reviewer_role=reviewer_session.role,
            reviewer_user_id=reviewer_session.user_id,
            requester_user_id=req.get("requester_user_id") or 0,
            requester_role=req.get("requester_role", "FACULTY"),
        )
        if not allowed:
            raise BusinessLogicError(reason)

        success = self.change_repo.reject_request(
            request_id=request_id,
            reviewer_id=reviewer_session.user_id,
            reviewer_remark=clean_remark,
        )

        if success:
            rev_code = reviewer_session.employee_code or reviewer_session.username
            emp_code = req.get("employee_code", f"EMP{req.get('employee_id')}")
            field_lbl = get_field_label(req.get("field_name", ""))
            log_line = f"[PROFILE_CHANGE] REJECTED by {rev_code} for {emp_code} - {field_lbl} (Remark: {clean_remark})"

            self.audit_repo.log_event(
                user_id=reviewer_session.user_id,
                action="REJECT_PROFILE_CHANGE",
                entity_type="FACULTY_PROFILE",
                entity_id=str(request_id),
                details=log_line,
            )
            logger.info(log_line)
        return success

    def bulk_approve(
        self,
        reviewer_session: UserSession,
        request_ids: List[int],
        reviewer_remark: Optional[str] = "Bulk approved",
    ) -> Dict[str, Any]:
        """Approves multiple selected requests, skipping self-requests and logging each action."""
        approved_count = 0
        skipped = []

        for req_id in request_ids:
            try:
                if self.approve_request(reviewer_session, req_id, reviewer_remark):
                    approved_count += 1
                else:
                    skipped.append((req_id, "Request could not be approved."))
            except Exception as exc:
                skipped.append((req_id, str(exc)))

        return {
            "approved_count": approved_count,
            "total_requested": len(request_ids),
            "skipped": skipped,
        }

    def bulk_reject(
        self,
        reviewer_session: UserSession,
        request_ids: List[int],
        reviewer_remark: str,
    ) -> Dict[str, Any]:
        """Rejects multiple selected requests with mandatory remark."""
        rejected_count = 0
        skipped = []

        for req_id in request_ids:
            try:
                if self.reject_request(reviewer_session, req_id, reviewer_remark):
                    rejected_count += 1
                else:
                    skipped.append((req_id, "Request could not be rejected."))
            except Exception as exc:
                skipped.append((req_id, str(exc)))

        return {
            "rejected_count": rejected_count,
            "total_requested": len(request_ids),
            "skipped": skipped,
        }

    def get_my_requests(self, user_session: UserSession) -> List[Dict[str, Any]]:
        """Returns all change requests for the currently logged in faculty member."""
        if not user_session or not user_session.faculty_id:
            return []
        return self.change_repo.get_requests_by_employee(user_session.faculty_id)

    def get_pending_fields_for_employee(self, employee_id: int) -> Set[str]:
        """Returns set of field names that have a PENDING request for this employee."""
        reqs = self.change_repo.get_requests_by_employee(employee_id)
        return {r["field_name"] for r in reqs if r.get("status") == "PENDING"}

    def get_recent_decision_notices(self, user_session: UserSession, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns recent APPROVED or REJECTED change decisions for the active employee to show in notifications."""
        if not user_session or not user_session.faculty_id:
            return []
        reqs = self.change_repo.get_requests_by_employee(user_session.faculty_id)
        decided = [r for r in reqs if r.get("status") in ("APPROVED", "REJECTED")]
        return decided[:limit]


profile_change_service = ProfileChangeService()
