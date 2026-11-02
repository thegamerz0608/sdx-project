"""
Role-Based Access Control (RBAC) Permissions Configuration for
Faculty Profile Details, Academic Subject Assignments, and
Profile Change Approval Workflows.
"""
from typing import Set, Dict, Tuple

# Roles permitted to view academic teaching assignments (Subjects Handled)
TEACHING_ROLES: Set[str] = {"FACULTY", "HOD"}

# Roles with full administrative permission to modify locked profile & statutory fields directly
ADMIN_PROFILE_EDITORS: Set[str] = {"ADMIN", "HR", "PRINCIPAL"}

# Roles authorized to review and approve/reject profile change requests
PROFILE_REVIEWER_ROLES: Set[str] = {"ADMIN", "HR", "PRINCIPAL"}

# =============================================================================
# 1. FIELD CLASSIFICATION MATRIX
# =============================================================================

# Category A: Direct edit by faculty with immediate save, no approval required
DIRECT_EDIT_FIELDS: Set[str] = {
    "phone",
    "personal_email",
    "profile_image_path",
}

# Category B: Sensitive fields editable as change requests, requiring HR/Principal approval
APPROVAL_REQUIRED_FIELDS: Set[str] = {
    "salary_account_no",
    "pan_number",
    "aadhaar_number",
    "pf_number",
    "uan_number",
    "dob",
    "name",
    "first_name",
    "last_name",
}

# Category C: Locked fields strictly restricted to HR and Principal direct updates
LOCKED_ADMIN_ONLY_FIELDS: Set[str] = {
    "employee_code",
    "department_id",
    "designation",
    "joining_date",
    "employment_type",
    "vtu_id",
}

# Backward compatibility alias
FACULTY_SELF_EDITABLE_FIELDS: Set[str] = DIRECT_EDIT_FIELDS | APPROVAL_REQUIRED_FIELDS

# Human-readable labels for profile fields
FIELD_LABELS: Dict[str, str] = {
    "phone": "Mobile No.",
    "personal_email": "Personal Email Id",
    "profile_image_path": "Profile Photo",
    "salary_account_no": "Salary A/C No.",
    "pan_number": "PAN Card No.",
    "aadhaar_number": "Aadhar No.",
    "pf_number": "PF NO",
    "uan_number": "UAN NO",
    "dob": "DOB",
    "name": "Full Name",
    "first_name": "First Name",
    "last_name": "Last Name",
    "employee_code": "Employee ID",
    "department_id": "Department",
    "designation": "Designation",
    "joining_date": "Date of Joining",
    "employment_type": "Employment Type",
    "vtu_id": "VTU ID",
    "experience_years": "Experience",
}


def get_field_label(field_name: str) -> str:
    """Returns human-friendly display label for a profile field."""
    return FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())


def is_direct_edit_field(field_name: str) -> bool:
    """Returns True if the field can be updated directly without approval."""
    return field_name in DIRECT_EDIT_FIELDS


def is_approval_required_field(field_name: str) -> bool:
    """Returns True if the field requires HR/Principal approval before taking effect."""
    return field_name in APPROVAL_REQUIRED_FIELDS


def is_locked_field(field_name: str) -> bool:
    """Returns True if the field is strictly locked for regular users."""
    return field_name in LOCKED_ADMIN_ONLY_FIELDS


def can_view_subjects_handled(role: str) -> bool:
    """Returns True if the role is a teaching role that handles subjects."""
    return (role or "").upper() in TEACHING_ROLES


def can_edit_all_fields(role: str) -> bool:
    """Returns True if the role has administrative rights to edit all profile fields directly."""
    return (role or "").upper() in ADMIN_PROFILE_EDITORS


def can_review_profile_changes(role: str) -> bool:
    """Returns True if the user role has authority to review profile change requests."""
    return (role or "").upper() in PROFILE_REVIEWER_ROLES


def can_review_specific_request(
    reviewer_role: str,
    reviewer_user_id: int,
    requester_user_id: int,
    requester_role: str = "FACULTY",
) -> Tuple[bool, str]:
    """
    Validates whether a specific reviewer can approve/reject a specific request.
    Rules:
      1. Reviewer role must be HR, PRINCIPAL, or ADMIN.
      2. A user cannot approve their own request (self-approval forbidden).
      3. HR's own requests must be reviewed by the Principal.
      4. Principal's own requests must be reviewed by HR or Admin.
    """
    rev_role = (reviewer_role or "").upper()
    req_role = (requester_role or "").upper()

    if rev_role not in PROFILE_REVIEWER_ROLES:
        return False, "Unauthorized: Only HR, Principal, or Administrator can review profile change requests."

    if reviewer_user_id == requester_user_id:
        return False, "Self-approval is forbidden: You cannot review or approve your own profile change request."

    if req_role == "HR" and rev_role != "PRINCIPAL" and rev_role != "ADMIN":
        return False, "Protocol violation: HR change requests must be reviewed by the Principal."

    if req_role == "PRINCIPAL" and rev_role not in {"HR", "ADMIN"}:
        return False, "Protocol violation: Principal change requests must be reviewed by HR or Admin."

    return True, ""
