"""
Leave Application Workflow Service
Orchestrates application submission, rule pre-validation, document validation, HOD review, balance state accounting, and security audit trail logging.
"""
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from repositories.leave_application_repository import leave_application_repository, LeaveApplicationRepository
from repositories.leave_repository import leave_repository
from repositories.audit_repository import audit_repository
from repositories.faculty_repository import faculty_repository
from repositories.substitute_repository import substitute_repository
from repositories.department_repository import department_repository
from services.auth_service import UserSession
from services.leave_service import leave_service
from services.email_service import email_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.leave_workflow_service")


class LeaveWorkflowService:
    """Service facade managing end-to-end leave application workflows and approval processing."""

    def __init__(self):
        self.app_repo = leave_application_repository
        self.leave_repo = leave_repository
        self.audit_repo = audit_repository
        self.fac_repo = faculty_repository
        self.sub_repo = substitute_repository
        self.dept_repo = department_repository
        self.email_svc = email_service

    def submit_leave_application(
        self,
        user_session: UserSession,
        faculty_id: Optional[int] = None,
        requested_leave_type_code: Optional[str] = None,
        from_date_str: Optional[str] = None,
        to_date_str: Optional[str] = None,
        reason: str = "",
        is_half_day: bool = False,
        document_path: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Validates rules, verifies document requirements, creates application record, and debits pending balance.
        """
        if not user_session:
            raise BusinessLogicError("Authentication required to submit leave application.")

        # Resolve parameter aliases
        fid = faculty_id if faculty_id is not None else (user_session.faculty_id or 1)
        req_code = requested_leave_type_code or kwargs.get("requested_type_code") or "CL"
        f_date = from_date_str or kwargs.get("from_date") or ""
        t_date = to_date_str or kwargs.get("to_date") or f_date

        if not reason or len(reason.strip()) < 5:
            raise ValidationError("A detailed reason for leave (minimum 5 characters) is required.")

        # Pre-validate policy rules via Phase 7 Leave Service
        val_res = leave_service.validate_leave_application(
            user_session=user_session,
            faculty_id=fid,
            leave_type_code=req_code,
            from_date_str=f_date,
            to_date_str=t_date,
            is_half_day=is_half_day,
        )

        if not val_res["valid"]:
            error_msg = "; ".join(val_res["errors"])
            raise ValidationError(f"Leave Application Rejected by Policy Rules: {error_msg}")

        # Document requirement check
        if val_res["requires_document"] and not document_path:
            raise ValidationError(
                f"Document Required: Selected leave type '{val_res['leave_type_name']}' "
                "or requested duration requires a supporting document attachment (e.g. Medical Certificate)."
            )

        lt_info = self.leave_repo.get_leave_type_by_code(req_code)
        if not lt_info:
            raise ValidationError(f"Invalid leave type code '{req_code}'.")

        # Evaluate or inherit AI leave category prediction and confidence score
        ai_code = kwargs.get("ai_predicted_type_code")
        ai_conf = kwargs.get("ai_confidence")

        if not ai_code or ai_conf is None:
            try:
                from services.model_training_service import model_training_service
                meta = {
                    "requested_days": val_res["requested_days"],
                    "notice_period_days": 0.0,
                    "has_medical_doc": bool(document_path),
                    "is_sandwich_leave": False,
                }
                nlp_res = model_training_service.predict_leave_reason(reason, meta)
                ai_code = nlp_res.get("predicted_category", req_code)
                ai_conf = float(nlp_res.get("confidence_score", 0.8500))
            except Exception as exc:
                logger.debug(f"Workflow NLP auto-annotation fallback: {exc}")
                ai_code = req_code
                ai_conf = 0.8500

        ai_lt = self.leave_repo.get_leave_type_by_code(ai_code) if ai_code else None
        ai_type_id = ai_lt["id"] if ai_lt else lt_info["id"]

        year = int(val_res["from_date"][:4])
        code = f"LA-{year}-{uuid.uuid4().hex[:4].upper()}"

        app_payload = {
            "application_code": code,
            "faculty_id": fid,
            "requested_leave_type_id": lt_info["id"],
            "leave_type_code": lt_info["code"],
            "leave_type_name": lt_info["name"],
            "department_id": user_session.department_id if user_session.department_id else 1,
            "department_code": user_session.department_code if user_session.department_code else "MCA",
            "from_date": val_res["from_date"],
            "to_date": val_res["to_date"],
            "total_days": val_res["requested_days"],
            "reason": reason.strip(),
            "document_path": document_path,
            "ai_predicted_type_id": ai_type_id,
            "ai_predicted_code": ai_code,
            "ai_predicted_name": ai_lt["name"] if ai_lt else lt_info["name"],
            "ai_confidence": round(float(ai_conf), 4) if ai_conf is not None else 0.8500,
        }

        created_app = self.app_repo.create_application(app_payload)

        # Process Integrated Alternate Arrangement (Substitute Faculty Duty)
        sub_id = kwargs.get("substitute_faculty_id") or kwargs.get("substitute_id")
        alt_date = kwargs.get("alternate_date") or val_res["from_date"]
        alt_time = kwargs.get("alternate_time") or "10:00 AM - 11:00 AM"
        alt_place = kwargs.get("alternate_place") or "Assigned Classroom / Lab"
        alt_work = kwargs.get("alternate_work_description") or "Conduct scheduled session"

        alternate_info = None
        if sub_id:
            try:
                sub_fac = self.fac_repo.get_by_id(int(sub_id))
                if not sub_fac:
                    from repositories.instructor_repository import instructor_repository
                    for ins in instructor_repository.get_all():
                        if ins["id"] == int(sub_id) or (500 + ins["id"]) == int(sub_id):
                            sub_fac = {
                                "full_name": ins["full_name"],
                                "employee_code": ins["instructor_code"],
                                "department_code": ins.get("department_code", ""),
                            }
                            break
                sub_name = sub_fac.get("full_name") if sub_fac else f"Faculty/Instructor #{sub_id}"
                sub_code = sub_fac.get("employee_code", "") if sub_fac else ""
                
                sub_payload = {
                    "leave_application_id": created_app.get("id"),
                    "original_faculty_id": fid,
                    "substitute_faculty_id": int(sub_id),
                    "department_id": app_payload.get("department_id", 1),
                    "assignment_date": alt_date,
                    "start_time": "10:00:00",
                    "end_time": "11:00:00",
                    "class_details": f"Place: {alt_place} | Time: {alt_time} | Work: {alt_work}",
                    "assigned_by_user_id": user_session.user_id,
                    "remarks": alt_work,
                }
                self.sub_repo.create_assignment(sub_payload)
                alternate_info = {
                    "substitute_id": sub_id,
                    "substitute_name": sub_name,
                    "substitute_code": sub_code,
                    "date": alt_date,
                    "time": alt_time,
                    "place": alt_place,
                    "work_description": alt_work,
                }
                created_app["alternate_arrangement"] = alternate_info
            except Exception as exc:
                logger.warning(f"Could not create linked substitute assignment: {exc}")

        # Multi-Tier Automated Email Workflow: Tier 1 - Notification to HOD
        try:
            applicant_fac = self.fac_repo.get_by_id(fid) or {}
            applicant_name = applicant_fac.get("full_name") or user_session.full_name or "Faculty Member"
            emp_code = applicant_fac.get("employee_code") or user_session.employee_code or f"F00{fid}"
            dept_code = app_payload.get("department_code", "MCA")
            hod_email = f"hod.{dept_code.lower()}@erp.edu"

            self.email_svc.send_leave_submission_to_hod(
                hod_email=hod_email,
                applicant_name=applicant_name,
                employee_code=emp_code,
                app_code=code,
                leave_type_name=lt_info["name"],
                from_date=val_res["from_date"],
                to_date=val_res["to_date"],
                total_days=val_res["requested_days"],
                reason=reason.strip(),
                alternate_info=alternate_info,
            )
        except Exception as exc:
            logger.debug(f"Email Tier 1 dispatch notice: {exc}")

        # Update transactional balance: increment pending_days
        self.app_repo.update_balance_state(
            faculty_id=fid,
            leave_type_id=lt_info["id"],
            year=year,
            days=val_res["requested_days"],
            state_action="SUBMIT",
        )

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="SUBMIT_LEAVE_APPLICATION",
            entity_type="LEAVE_APPLICATION",
            entity_id=code,
            details=f"Submitted leave request for {val_res['requested_days']} day(s) from {f_date} to {t_date}.",
        )

        created_app["success"] = True
        created_app["application_id"] = created_app.get("id")
        return created_app

    def review_leave_application(
        self,
        user_session: UserSession,
        application_id: int,
        action: str,
        remarks: Optional[str] = None,
        hod_remarks: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Processes HOD / Admin review decision ('APPROVE' or 'REJECT') on a pending application.
        Updates status, records reviewer, and executes balance state transition.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can review leave applications.")

        effective_remarks = (remarks or hod_remarks or kwargs.get("remarks") or "").strip() or None

        clean_action = action.strip().upper()
        if clean_action not in ["APPROVE", "REJECT"]:
            raise ValidationError("Invalid review action. Must be 'APPROVE' or 'REJECT'.")

        if clean_action == "REJECT" and (not effective_remarks or len(effective_remarks) < 3):
            raise ValidationError("Remarks (minimum 3 characters) are required when rejecting a leave application.")

        app = self.app_repo.get_application_by_id(application_id)
        if not app:
            raise ValidationError(f"Leave application with ID {application_id} not found.")

        if app["status"] != "PENDING":
            raise BusinessLogicError(f"Cannot review application: Current status is '{app['status']}' (Only PENDING applications can be reviewed).")

        # HOD Department restriction check
        if user_session.is_hod() and user_session.department_id != app.get("department_id"):
            raise BusinessLogicError("Unauthorized: HODs can only review applications within their own department.")

        target_status = "APPROVED" if clean_action == "APPROVE" else "REJECTED"
        succ = self.app_repo.update_application_status(
            application_id=application_id,
            status=target_status,
            reviewer_user_id=user_session.user_id,
            remarks=effective_remarks,
        )

        if not succ:
            raise BusinessLogicError("Failed to update application status.")

        # Balance transition
        year = int(str(app["from_date"])[:4])
        self.app_repo.update_balance_state(
            faculty_id=app["faculty_id"],
            leave_type_id=app["requested_leave_type_id"],
            year=year,
            days=float(app["total_days"]),
            state_action=clean_action,
        )

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action=f"{clean_action}_LEAVE_APPLICATION",
            entity_type="LEAVE_APPLICATION",
            entity_id=str(app.get("application_code", application_id)),
            details=f"Reviewed application #{application_id} -> {target_status}. Remarks: {remarks}",
        )

        # Multi-Tier Automated Email Workflow: Tier 2 - HOD Approval notification to HR
        if clean_action == "APPROVE":
            try:
                applicant_fac = self.fac_repo.get_by_id(app["faculty_id"]) or {}
                applicant_name = applicant_fac.get("full_name") or app.get("faculty_name", "Faculty Member")
                emp_code = applicant_fac.get("employee_code") or app.get("employee_code", "")
                lt_name = app.get("leave_type_name") or "Leave"

                sub_assign = self.sub_repo.get_assignment_by_leave_id(application_id)
                alt_info = None
                if sub_assign:
                    alt_info = {
                        "substitute_name": sub_assign.get("substitute_faculty_name", "Assigned Substitute"),
                        "place": sub_assign.get("class_details", ""),
                    }

                self.email_svc.send_hod_approval_to_hr(
                    hr_email="hr@erp.edu",
                    applicant_name=applicant_name,
                    employee_code=emp_code,
                    app_code=app.get("application_code", f"LA-{application_id}"),
                    leave_type_name=lt_name,
                    from_date=str(app["from_date"]),
                    to_date=str(app["to_date"]),
                    total_days=float(app["total_days"]),
                    hod_name=user_session.full_name or "HOD",
                    hod_remarks=effective_remarks,
                    alternate_info=alt_info,
                )
            except Exception as exc:
                logger.debug(f"Email Tier 2 dispatch notice: {exc}")

        res = self.app_repo.get_application_by_id(application_id) or {}
        res["success"] = True
        return res

    review_application = review_leave_application

    def hr_review_application(
        self,
        user_session: UserSession,
        application_id: int,
        action: str,
        remarks: Optional[str] = None,
        new_from_date: Optional[str] = None,
        new_to_date: Optional[str] = None,
        new_days: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        HR Review Gatekeeper:
        - APPROVE: advances to PENDING_PRINCIPAL
        - SUSPEND: sets status to SUSPENDED
        - MODIFY: adjusts dates/duration and updates records
        - REJECT: terminates with REJECTED and refunds balance
        """
        if not user_session or not (user_session.is_hr() or user_session.is_admin()):
            raise BusinessLogicError("Unauthorized: Only HR officers and Administrators can perform HR review.")

        clean_act = action.strip().upper()
        app = self.app_repo.get_application_by_id(application_id)
        if not app:
            raise ValidationError(f"Leave application #{application_id} not found.")

        if clean_act == "MODIFY":
            if not new_from_date or not new_to_date or new_days is None:
                raise ValidationError("Modified from_date, to_date, and total_days are required.")
            self.app_repo.modify_application_dates(application_id, new_from_date, new_to_date, float(new_days))
            if remarks:
                self.app_repo.update_multi_stage_status(
                    application_id=application_id,
                    overall_status=app["status"],
                    stage_column="hr_status",
                    stage_status="MODIFIED",
                    remarks_column="hr_remarks",
                    remarks=remarks,
                    reviewer_user_id=user_session.user_id,
                )
            self.audit_repo.log_event(
                user_id=user_session.user_id,
                action="HR_MODIFY_LEAVE",
                entity_type="LEAVE_APPLICATION",
                entity_id=str(app.get("application_code", application_id)),
                details=f"HR adjusted dates to {new_from_date} - {new_to_date} ({new_days} days).",
            )
            res = self.app_repo.get_application_by_id(application_id) or {}
            res["success"] = True
            return res

        if clean_act == "APPROVE":
            overall = "PENDING_PRINCIPAL"
            stage_st = "APPROVED"
        elif clean_act == "SUSPEND":
            overall = "SUSPENDED"
            stage_st = "SUSPENDED"
        elif clean_act == "REJECT":
            overall = "REJECTED"
            stage_st = "REJECTED"
            year = int(str(app["from_date"])[:4])
            self.app_repo.update_balance_state(
                faculty_id=app["faculty_id"],
                leave_type_id=app["requested_leave_type_id"],
                year=year,
                days=float(app["total_days"]),
                state_action="REJECT",
            )
        else:
            raise ValidationError(f"Invalid HR action '{action}'. Must be APPROVE, SUSPEND, MODIFY, or REJECT.")

        self.app_repo.update_multi_stage_status(
            application_id=application_id,
            overall_status=overall,
            stage_column="hr_status",
            stage_status=stage_st,
            remarks_column="hr_remarks",
            remarks=remarks or f"HR action: {stage_st}",
            reviewer_user_id=user_session.user_id,
        )

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action=f"HR_{clean_act}_LEAVE",
            entity_type="LEAVE_APPLICATION",
            entity_id=str(app.get("application_code", application_id)),
            details=f"HR processed application #{application_id} -> {overall}. Remarks: {remarks}",
        )

        # Multi-Tier Automated Email Workflow: Tier 3 - HR Approval notification to Principal
        if clean_act == "APPROVE":
            try:
                applicant_fac = self.fac_repo.get_by_id(app["faculty_id"]) or {}
                applicant_name = applicant_fac.get("full_name") or app.get("faculty_name", "Faculty Member")
                emp_code = applicant_fac.get("employee_code") or app.get("employee_code", "")
                lt_name = app.get("leave_type_name") or "Leave"

                sub_assign = self.sub_repo.get_assignment_by_leave_id(application_id)
                alt_info = None
                if sub_assign:
                    alt_info = {
                        "substitute_name": sub_assign.get("substitute_faculty_name", "Assigned Substitute"),
                        "place": sub_assign.get("class_details", ""),
                    }

                self.email_svc.send_hr_approval_to_principal(
                    principal_email="principal@erp.edu",
                    applicant_name=applicant_name,
                    employee_code=emp_code,
                    app_code=app.get("application_code", f"LA-{application_id}"),
                    leave_type_name=lt_name,
                    from_date=str(app["from_date"]),
                    to_date=str(app["to_date"]),
                    total_days=float(app["total_days"]),
                    hr_remarks=remarks,
                    alternate_info=alt_info,
                )
            except Exception as exc:
                logger.debug(f"Email Tier 3 dispatch notice: {exc}")

        res = self.app_repo.get_application_by_id(application_id) or {}
        res["success"] = True
        return res

    def hr_modify_dates(
        self,
        user_session: UserSession,
        application_id: int,
        from_date: str,
        to_date: str,
        total_days: float,
        remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience method for HR date adjustments."""
        return self.hr_review_application(
            user_session=user_session,
            application_id=application_id,
            action="MODIFY",
            remarks=remarks,
            new_from_date=from_date,
            new_to_date=to_date,
            new_days=total_days,
        )

    def principal_review_application(
        self,
        user_session: UserSession,
        application_id: int,
        action: str,
        remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Principal Executive Review:
        - APPROVE: sets status to APPROVED and commits balance from pending to used
        - REJECT: sets status to REJECTED and refunds pending balance
        """
        if not user_session or not (user_session.is_principal() or user_session.is_admin()):
            raise BusinessLogicError("Unauthorized: Only the Principal or Administrator can grant executive approval.")

        clean_act = action.strip().upper()
        app = self.app_repo.get_application_by_id(application_id)
        if not app:
            raise ValidationError(f"Leave application #{application_id} not found.")

        year = int(str(app["from_date"])[:4])
        if clean_act == "APPROVE":
            overall = "APPROVED"
            stage_st = "APPROVED"
            self.app_repo.update_balance_state(
                faculty_id=app["faculty_id"],
                leave_type_id=app["requested_leave_type_id"],
                year=year,
                days=float(app["total_days"]),
                state_action="APPROVE",
            )
        elif clean_act == "REJECT":
            overall = "REJECTED"
            stage_st = "REJECTED"
            self.app_repo.update_balance_state(
                faculty_id=app["faculty_id"],
                leave_type_id=app["requested_leave_type_id"],
                year=year,
                days=float(app["total_days"]),
                state_action="REJECT",
            )
        else:
            raise ValidationError(f"Invalid Principal action '{action}'. Must be APPROVE or REJECT.")

        self.app_repo.update_multi_stage_status(
            application_id=application_id,
            overall_status=overall,
            stage_column="principal_status",
            stage_status=stage_st,
            remarks_column="principal_remarks",
            remarks=remarks or f"Principal action: {stage_st}",
            reviewer_user_id=user_session.user_id,
        )

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action=f"PRINCIPAL_{clean_act}_LEAVE",
            entity_type="LEAVE_APPLICATION",
            entity_id=str(app.get("application_code", application_id)),
            details=f"Principal processed application #{application_id} -> {overall}. Remarks: {remarks}",
        )

        # Multi-Tier Automated Email Workflow: Tier 4 & Tier 5
        if clean_act == "APPROVE":
            applicant_name = app.get("faculty_name", "Faculty Member")
            app_code = app.get("application_code", f"LA-{application_id}")
            lt_name = app.get("leave_type_name") or "Leave"

            # Tier 4: Final Approval confirmation email back to applying Faculty
            try:
                applicant_fac = self.fac_repo.get_by_id(app["faculty_id"]) or {}
                applicant_email = applicant_fac.get("email") or "faculty@erp.edu"
                if applicant_fac.get("full_name"):
                    applicant_name = applicant_fac["full_name"]

                self.email_svc.send_final_approval_to_faculty(
                    faculty_email=applicant_email,
                    applicant_name=applicant_name,
                    app_code=app_code,
                    leave_type_name=lt_name,
                    from_date=str(app["from_date"]),
                    to_date=str(app["to_date"]),
                    total_days=float(app["total_days"]),
                    principal_remarks=remarks,
                )
            except Exception as exc:
                logger.debug(f"Email Tier 4 dispatch notice: {exc}")

            # Tier 5: Automated duty notification email to assigned Substitute Faculty
            try:
                sub_assign = self.sub_repo.get_assignment_by_leave_id(application_id)
                if sub_assign and sub_assign.get("substitute_faculty_id"):
                    sub_id = sub_assign["substitute_faculty_id"]
                    sub_fac = self.fac_repo.get_by_id(sub_id) or {}
                    sub_email = sub_fac.get("email") or f"substitute_{sub_id}@erp.edu"
                    sub_name = sub_fac.get("full_name") or sub_assign.get("substitute_faculty_name", "Substitute Faculty")

                    self.email_svc.send_substitute_assignment_notification(
                        substitute_email=sub_email,
                        substitute_name=sub_name,
                        applicant_name=applicant_name,
                        app_code=app_code,
                        assignment_date=str(sub_assign.get("assignment_date", app["from_date"])),
                        start_time=str(sub_assign.get("start_time", "10:00:00")),
                        end_time=str(sub_assign.get("end_time", "11:00:00")),
                        classroom_location=str(sub_assign.get("class_details", "Designated Classroom")),
                        work_description=str(sub_assign.get("remarks") or sub_assign.get("class_details", "Lecture Coverage")),
                    )
            except Exception as exc:
                logger.debug(f"Email Tier 5 dispatch notice: {exc}")

        res = self.app_repo.get_application_by_id(application_id) or {}
        res["success"] = True
        return res

    def cancel_leave_application(self, user_session: UserSession, application_id: int) -> Dict[str, Any]:
        """Cancels a pending leave application and restores pending balance."""
        if not user_session:
            raise BusinessLogicError("Authentication required.")

        app = self.app_repo.get_application_by_id(application_id)
        if not app:
            raise ValidationError(f"Leave application #{application_id} not found.")

        if app["status"] != "PENDING":
            raise BusinessLogicError(f"Only PENDING applications can be cancelled (Current status: {app['status']}).")

        succ = self.app_repo.update_application_status(
            application_id=application_id,
            status="CANCELLED",
            reviewer_user_id=user_session.user_id,
            remarks="Cancelled by applicant/admin",
        )

        year = int(str(app["from_date"])[:4])
        self.app_repo.update_balance_state(
            faculty_id=app["faculty_id"],
            leave_type_id=app["requested_leave_type_id"],
            year=year,
            days=float(app["total_days"]),
            state_action="CANCEL",
        )

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="CANCEL_LEAVE_APPLICATION",
            entity_type="LEAVE_APPLICATION",
            entity_id=str(app.get("application_code", application_id)),
            details=f"Cancelled leave application #{application_id}.",
        )

        return self.app_repo.get_application_by_id(application_id) or {}

    def list_applications(
        self,
        user_session: UserSession,
        status_filter: Optional[str] = None,
        department_id: Optional[int] = None,
        faculty_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Lists leave applications applying RBAC permissions."""
        if not user_session:
            return []

        target_dept_id = department_id
        target_fac_id = faculty_id

        # RBAC Scoping
        if user_session.is_faculty():
            # Faculty members view their own applications only
            target_fac_id = user_session.faculty_id or user_session.user_id
        elif user_session.is_hod():
            # HODs view applications for their department
            target_dept_id = user_session.department_id

        return self.app_repo.get_applications(
            department_id=target_dept_id,
            faculty_id=target_fac_id,
            status_filter=status_filter,
        )


leave_workflow_service = LeaveWorkflowService()
