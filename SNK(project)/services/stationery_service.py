"""
Stationery Requisition Service
Manages business logic, approval routing to departmental HODs, and request tracking.
"""
from typing import List, Dict, Any, Optional
from repositories.stationery_repository import stationery_repository, StationeryRepository
from services.auth_service import UserSession
from utils.logger import get_logger
from utils.exceptions import ValidationError, BusinessLogicError

logger = get_logger("services.stationery_service")


class StationeryService:
    """Service facade managing stationery requests and HOD review workflows."""

    def __init__(self):
        self.repo = stationery_repository

    def get_predefined_items(self) -> List[str]:
        """Returns the standard catalog of consumable stationery items."""
        return self.repo.get_predefined_items()

    def submit_request(
        self,
        user_session: UserSession,
        item_name: str,
        quantity: int = 1,
        urgency: str = "NORMAL",
        purpose: str = "",
    ) -> Dict[str, Any]:
        """
        Submits a new stationery requisition on behalf of the active user.
        Routes request to their departmental HOD queue.
        """
        if not user_session:
            raise ValidationError("Authentication required to submit stationery requests.")

        if not item_name or not item_name.strip():
            raise ValidationError("Please select or specify a stationery item.")

        if quantity < 1 or quantity > 100:
            raise ValidationError("Quantity must be between 1 and 100 units.")

        payload = {
            "requester_user_id": user_session.user_id,
            "requester_name": user_session.full_name or user_session.username,
            "requester_role": user_session.role,
            "department_id": user_session.department_id or 1,
            "item_name": item_name.strip(),
            "quantity": int(quantity),
            "urgency": urgency.strip().upper(),
            "purpose": purpose.strip(),
        }

        req_id = self.repo.create_request(payload)
        logger.info(
            f"User '{user_session.username}' submitted stationery request #{req_id} for '{item_name}' (x{quantity})."
        )
        return {"request_id": req_id, "status": "PENDING", "message": "Stationery request submitted to HOD."}

    def get_my_requests(self, user_session: UserSession) -> List[Dict[str, Any]]:
        """Returns personal requisition history for the active user."""
        if not user_session:
            return []
        return self.repo.get_requests(user_id=user_session.user_id)

    def get_department_requests_for_hod(self, user_session: UserSession) -> List[Dict[str, Any]]:
        """
        Returns pending and past requests for the HOD's department.
        Admins can view all institutional department requests.
        """
        if not user_session:
            return []
        if user_session.is_admin():
            return self.repo.get_requests(department_id=None)

        dept_id = user_session.department_id
        return self.repo.get_requests(department_id=dept_id)

    def review_request(
        self,
        request_id: int,
        reviewer_session: UserSession,
        action: str,  # 'APPROVE' or 'REJECT'
        remarks: str = "",
    ) -> bool:
        """
        Processes HOD approval or rejection for a stationery request.
        """
        if not reviewer_session:
            raise ValidationError("Authentication required to review stationery requests.")

        if not (reviewer_session.is_hod() or reviewer_session.is_admin()):
            raise BusinessLogicError("Only Department Heads (HOD) or Administrators may approve stationery requests.")

        act_upper = action.strip().upper()
        if act_upper not in ("APPROVE", "REJECT"):
            raise ValidationError(f"Invalid review action '{action}'. Must be APPROVE or REJECT.")

        target_status = "APPROVED" if act_upper == "APPROVE" else "REJECTED"
        success = self.repo.update_status(
            request_id=request_id,
            status=target_status,
            hod_remarks=remarks.strip(),
            reviewed_by_user_id=reviewer_session.user_id,
        )

        if success:
            logger.info(
                f"HOD '{reviewer_session.username}' {target_status} stationery request #{request_id}."
            )
        return success


stationery_service = StationeryService()
