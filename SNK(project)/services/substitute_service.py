"""
Substitute Recommendation & Workload Balancing Service
Orchestrates intelligent substitute ranking, schedule collision checks, workload balancing, assignment creation, and response workflows.
"""
from typing import List, Dict, Any, Optional
from repositories.substitute_repository import substitute_repository, SubstituteRepository
from repositories.faculty_repository import faculty_repository
from repositories.audit_repository import audit_repository
from services.auth_service import UserSession
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("services.substitute_service")


class SubstituteService:
    """Service facade managing substitute recommendation ranking, schedule collision checks, and workload balancing."""

    def __init__(self):
        self.sub_repo = substitute_repository
        self.fac_repo = faculty_repository
        self.audit_repo = audit_repository

    def recommend_substitutes(
        self,
        user_session: Optional[UserSession] = None,
        original_faculty_id: int = 1,
        assignment_date: str = "2026-10-15",
        start_time: str = "10:00:00",
        end_time: str = "11:00:00",
        department_id: Optional[int] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Ranks eligible candidate faculty members for substitute assignment:
        - Excludes original faculty on leave.
        - Performs timetable schedule collision check for the requested date and time slot.
        - Computes workload balancing score based on monthly substitute duty count.
        - Ranks available candidates in order of suitability.
        """
        from services.auth_service import auth_service
        session = user_session or auth_service.current_user
        target_dept_id = department_id or (session.department_id if session else None)
        all_faculty = self.fac_repo.get_all(department_id=None)  # Fetch all faculty to allow cross-department fallback
        
        # Also include all lab instructors for global substitute & alternate arrangement selection
        from repositories.instructor_repository import instructor_repository
        all_instructors = instructor_repository.get_all(department_id=None)

        candidates = []
        month_yr = assignment_date[:7]

        # Normalise original_faculty_id to handle both integer and string representations safely
        orig_fac_norm = None
        if original_faculty_id is not None:
            try:
                orig_fac_norm = int(original_faculty_id)
            except (ValueError, TypeError):
                orig_fac_norm = str(original_faculty_id)

        for f in all_faculty:
            fac_id = f["id"]
            try:
                fac_id_norm = int(fac_id)
            except (ValueError, TypeError):
                fac_id_norm = str(fac_id)

            # Strict exclusion of faculty requesting substitute
            if orig_fac_norm is not None and fac_id_norm == orig_fac_norm:
                continue

            # Exclude administrative non-teaching accounts and inactive faculty
            if f.get("role") == "ADMIN" or f.get("designation") == "System Administrator":
                continue
            if f.get("status") == "INACTIVE":
                continue

            has_conflict = self.sub_repo.has_schedule_conflict(
                faculty_id=fac_id,
                assignment_date=assignment_date,
                start_time=start_time,
                end_time=end_time,
            )

            sub_count = self.sub_repo.get_faculty_monthly_substitute_count(fac_id, month_year=month_yr)
            workload_score = max(0, 100 - (sub_count * 15))

            same_dept = bool(target_dept_id and f.get("department_id") == target_dept_id)
            dept_bonus = 20 if same_dept else 0
            overall_rank_score = (0 if has_conflict else 1000) + dept_bonus + workload_score

            candidates.append(
                {
                    "faculty_id": fac_id,
                    "employee_code": f.get("employee_code", ""),
                    "faculty_name": f.get("full_name", f"{f.get('first_name', '')} {f.get('last_name', '')}"),
                    "department_id": f.get("department_id"),
                    "department_code": f.get("department_code", ""),
                    "is_available": not has_conflict,
                    "conflict_status": "COLLISION" if has_conflict else "AVAILABLE",
                    "monthly_substitute_count": sub_count,
                    "workload_score": workload_score,
                    "overall_score": overall_rank_score,
                    "same_department": same_dept,
                    "is_instructor": False,
                }
            )

        for ins in all_instructors:
            ins_id = 500 + ins["id"]
            if orig_fac_norm is not None:
                if ins_id == orig_fac_norm or ins.get("user_id") == orig_fac_norm:
                    continue
                try:
                    if int(ins["id"]) == orig_fac_norm or int(ins.get("user_id", -1)) == orig_fac_norm:
                        continue
                except (ValueError, TypeError):
                    pass

            sub_count = 0
            workload_score = 100
            same_dept = bool(target_dept_id and ins.get("department_id") == target_dept_id)
            dept_bonus = 20 if same_dept else 0
            overall_rank_score = 1000 + dept_bonus + workload_score

            candidates.append(
                {
                    "faculty_id": ins_id,
                    "employee_code": ins.get("instructor_code", ""),
                    "faculty_name": f"{ins.get('full_name', '')} (Lab Instructor)",
                    "department_id": ins.get("department_id"),
                    "department_code": ins.get("department_code", ""),
                    "is_available": True,
                    "conflict_status": "AVAILABLE",
                    "monthly_substitute_count": sub_count,
                    "workload_score": workload_score,
                    "overall_score": overall_rank_score,
                    "same_department": same_dept,
                    "is_instructor": True,
                }
            )

        # Sort candidates: Available first, then highest overall score
        candidates.sort(key=lambda c: c["overall_score"], reverse=True)

        for rank_idx, c in enumerate(candidates, start=1):
            c["rank"] = rank_idx

        return candidates

    def assign_substitute(
        self,
        user_session: UserSession,
        leave_application_id: int,
        original_faculty_id: int,
        substitute_faculty_id: int,
        department_id: int,
        assignment_date: str,
        start_time: str,
        end_time: str,
        class_details: str,
        remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a substitute assignment for a lecture session.
        Enforces collision validation and Admin/HOD authorization.
        """
        if not user_session or not (user_session.is_admin() or user_session.is_hod()):
            raise BusinessLogicError("Unauthorized: Only Administrators and HODs can assign substitutes.")

        if original_faculty_id == substitute_faculty_id:
            raise ValidationError("Original faculty on leave cannot be assigned as their own substitute.")

        if not class_details or len(class_details.strip()) < 3:
            raise ValidationError("Class details (e.g. 'MCA 1st Sem - Data Structures') are required.")

        # Timetable collision check
        if self.sub_repo.has_schedule_conflict(
            faculty_id=substitute_faculty_id,
            assignment_date=assignment_date,
            start_time=start_time,
            end_time=end_time,
        ):
            raise ValidationError(
                f"Schedule Collision Warning: Substitute candidate (ID #{substitute_faculty_id}) "
                f"already has an active assignment on {assignment_date} between {start_time} and {end_time}."
            )

        payload = {
            "leave_application_id": leave_application_id,
            "original_faculty_id": original_faculty_id,
            "substitute_faculty_id": substitute_faculty_id,
            "department_id": department_id,
            "assignment_date": assignment_date,
            "start_time": start_time,
            "end_time": end_time,
            "class_details": class_details.strip(),
            "assigned_by_user_id": user_session.user_id,
            "remarks": remarks.strip() if remarks else None,
        }

        created = self.sub_repo.create_assignment(payload)

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action="ASSIGN_SUBSTITUTE",
            entity_type="SUBSTITUTE_ASSIGNMENT",
            entity_id=str(created.get("id", "")),
            details=f"Assigned substitute (Faculty #{substitute_faculty_id}) for {class_details} on {assignment_date}.",
        )

        created["success"] = True
        return created

    def respond_to_assignment(
        self,
        user_session: UserSession,
        assignment_id: int,
        response_action: str,
        remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes substitute response decision ('ACCEPT', 'REJECT', or 'COMPLETE').
        """
        if not user_session:
            raise BusinessLogicError("Authentication required.")

        clean_act = response_action.strip().upper()
        status_map = {
            "ACCEPT": "ACCEPTED",
            "REJECT": "REJECTED",
            "COMPLETE": "COMPLETED",
        }
        if clean_act not in status_map:
            raise ValidationError("Invalid response action. Must be 'ACCEPT', 'REJECT', or 'COMPLETE'.")

        target_status = status_map[clean_act]

        if clean_act == "REJECT" and (not remarks or len(remarks.strip()) < 3):
            raise ValidationError("Remarks (minimum 3 characters) are required when declining a substitute duty.")

        succ = self.sub_repo.update_assignment_status(
            assignment_id=assignment_id, status=target_status, remarks=remarks
        )

        if not succ:
            raise BusinessLogicError("Failed to update substitute assignment status.")

        self.audit_repo.log_event(
            user_id=user_session.user_id,
            action=f"SUBSTITUTE_{clean_act}",
            entity_type="SUBSTITUTE_ASSIGNMENT",
            entity_id=str(assignment_id),
            details=f"Substitute duty #{assignment_id} status updated to {target_status}. Remarks: {remarks}",
        )

        return self.sub_repo.get_assignment_by_id(assignment_id) or {}

    def list_substitute_assignments(
        self,
        user_session: UserSession,
        department_id: Optional[int] = None,
        faculty_id: Optional[int] = None,
        date_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists substitute assignments applying RBAC scoping."""
        if not user_session:
            return []

        target_dept = department_id
        target_sub_fac = faculty_id

        if user_session.is_faculty():
            target_sub_fac = user_session.faculty_id or user_session.user_id
        elif user_session.is_hod():
            target_dept = user_session.department_id

        return self.sub_repo.get_assignments(
            department_id=target_dept,
            substitute_faculty_id=target_sub_fac,
            date_filter=date_filter,
            status_filter=status_filter,
        )


substitute_service = SubstituteService()
