"""
Comprehensive Unit Tests for Profile Change Approval Workflow
Covers:
- Duplicate request prevention
- Self-approval blocked
- HR self-request routed strictly to Principal/Admin
- Atomic approval updating profile and audit log
- Rejection with mandatory remark
- Format validators (PAN, Aadhaar, UAN, Account No, DOB)
- Proof upload validator (formats, file size limit)
- Cancellation by requester
"""
import pytest
from datetime import date, timedelta
from pathlib import Path
import tempfile

from services.auth_service import UserSession
from services.profile_change_service import (
    profile_change_service,
    mask_sensitive_value,
)
from repositories.profile_change_repository import (
    profile_change_repository,
    DEMO_PROFILE_CHANGE_REQUESTS,
    DEMO_PROFILE_CHANGE_AUDITS,
)
from repositories.faculty_repository import faculty_repository
from config.profile_permissions import (
    is_direct_edit_field,
    is_approval_required_field,
    is_locked_field,
    can_review_profile_changes,
    can_review_specific_request,
    get_field_label,
)
from utils.exceptions import ValidationError, BusinessLogicError


@pytest.fixture(autouse=True)
def reset_in_memory_data():
    """Resets in-memory test state before each test."""
    DEMO_PROFILE_CHANGE_REQUESTS.clear()
    DEMO_PROFILE_CHANGE_AUDITS.clear()
    # Seed standard test entries
    DEMO_PROFILE_CHANGE_REQUESTS.extend([
        {
            "id": 101,
            "employee_id": 2,
            "field_name": "pan_number",
            "old_value": "ABCDE1234F",
            "new_value": "FGHIJ5678K",
            "reason": "Official PAN name correction as per income tax records.",
            "proof_path": None,
            "status": "PENDING",
            "requested_at": "2026-10-25 10:30:00",
            "reviewed_by": None,
            "reviewed_at": None,
            "reviewer_remark": None,
            "employee_code": "F002",
            "employee_name": "Dr. Sarah Jenkins",
            "department_code": "MCA",
            "department_name": "Computer Applications",
            "requester_user_id": 2,
            "requester_role": "FACULTY",
        },
        {
            "id": 102,
            "employee_id": 3,
            "field_name": "salary_account_no",
            "old_value": "50100234567890",
            "new_value": "60200987654321",
            "reason": "Transferred salary account to home branch.",
            "proof_path": None,
            "status": "PENDING",
            "requested_at": "2026-10-26 14:15:00",
            "reviewed_by": None,
            "reviewed_at": None,
            "reviewer_remark": None,
            "employee_code": "F003",
            "employee_name": "Prof. Rajesh Kumar",
            "department_code": "CSE",
            "department_name": "Computer Science",
            "requester_user_id": 3,
            "requester_role": "FACULTY",
        },
    ])
    yield


# =============================================================================
# 1. FIELD CLASSIFICATION TESTS
# =============================================================================

def test_field_classification_rules():
    """Verifies that profile fields are accurately partitioned into the 3 tiers."""
    # Direct edit fields
    assert is_direct_edit_field("phone")
    assert is_direct_edit_field("personal_email")
    assert is_direct_edit_field("profile_image_path")
    assert not is_direct_edit_field("pan_number")

    # Approval required fields
    assert is_approval_required_field("pan_number")
    assert is_approval_required_field("salary_account_no")
    assert is_approval_required_field("aadhaar_number")
    assert is_approval_required_field("pf_number")
    assert is_approval_required_field("uan_number")
    assert is_approval_required_field("dob")
    assert is_approval_required_field("name")
    assert not is_approval_required_field("phone")
    assert not is_approval_required_field("employee_code")

    # Locked admin only fields
    assert is_locked_field("employee_code")
    assert is_locked_field("department_id")
    assert is_locked_field("designation")
    assert is_locked_field("joining_date")
    assert is_locked_field("employment_type")
    assert is_locked_field("vtu_id")
    assert not is_locked_field("pan_number")


# =============================================================================
# 2. FORMAT VALIDATORS
# =============================================================================

def test_format_validators_pan():
    """Validates PAN format: 5 uppercase letters, 4 digits, 1 uppercase letter."""
    # Valid PAN
    profile_change_service.validate_field_value("pan_number", "ABCDE1234F")

    # Invalid PAN formats
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("pan_number", "abcde1234f")  # Lowercase
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("pan_number", "ABC1234F")    # Too short
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("pan_number", "ABCDE12345")  # Ends with digit


def test_format_validators_aadhaar():
    """Validates Aadhaar format: exactly 12 numeric digits."""
    # Valid Aadhaar
    profile_change_service.validate_field_value("aadhaar_number", "123456789012")

    # Invalid Aadhaar formats
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("aadhaar_number", "12345678901")   # 11 digits
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("aadhaar_number", "1234567890123")  # 13 digits
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("aadhaar_number", "1234ABCD9012")  # Alphanumeric


def test_format_validators_uan():
    """Validates UAN format: exactly 12 numeric digits."""
    profile_change_service.validate_field_value("uan_number", "100987654321")
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("uan_number", "100987654")


def test_format_validators_bank_account():
    """Validates Bank Account format: 9 to 18 numeric digits."""
    profile_change_service.validate_field_value("salary_account_no", "50100234567890")  # 14 digits
    profile_change_service.validate_field_value("salary_account_no", "123456789")       # 9 digits

    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("salary_account_no", "12345678")    # 8 digits (too short)
    with pytest.raises(ValidationError):
        profile_change_service.validate_field_value("salary_account_no", "1234567890123456789")  # 19 digits


def test_format_validators_dob():
    """Validates DOB format: YYYY-MM-DD and not in the future."""
    past_date = (date.today() - timedelta(days=365 * 25)).strftime("%Y-%m-%d")
    profile_change_service.validate_field_value("dob", past_date)

    future_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    with pytest.raises(ValidationError, match="Date of Birth cannot be today or in the future"):
        profile_change_service.validate_field_value("dob", future_date)

    with pytest.raises(ValidationError, match="Invalid Date of Birth format"):
        profile_change_service.validate_field_value("dob", "12-04-1988")


# =============================================================================
# 3. MASKING & SENSITIVE DATA PROTECTION
# =============================================================================

def test_mask_sensitive_value():
    """Verifies that statutory values are masked as XXXXXX1234."""
    assert mask_sensitive_value("ABCDE1234F") == "XXXXXX234F"
    assert mask_sensitive_value("50100234567890") == "XXXXXX7890"
    assert mask_sensitive_value("1234") == "XXXX"
    assert mask_sensitive_value("") == "N/A"
    assert mask_sensitive_value(None) == "N/A"


# =============================================================================
# 4. DUPLICATE PREVENTION & REASON ENFORCEMENT
# =============================================================================

def test_duplicate_pending_request_blocked():
    """Blocks creating a second pending request for a field that already has one."""
    user = UserSession(
        user_id=2,
        username="sarah.jenkins",
        role="FACULTY",
        status="ACTIVE",
        first_name="Sarah",
        last_name="Jenkins",
        faculty_id=2,
        employee_code="F002",
        department_code="MCA",
    )

    # Request 101 for pan_number is already PENDING in fixture
    with pytest.raises(ValidationError, match="already pending HR approval"):
        profile_change_service.submit_change_request(
            user_session=user,
            field_name="pan_number",
            new_value="FGHIJ9999Z",
            reason="Another PAN update attempt.",
        )


def test_mandatory_reason_enforced():
    """Rejects change request submission if reason is empty or under 5 characters."""
    user = UserSession(
        user_id=2,
        username="sarah.jenkins",
        role="FACULTY",
        status="ACTIVE",
        first_name="Sarah",
        last_name="Jenkins",
        faculty_id=2,
        employee_code="F002",
        department_code="MCA",
    )

    with pytest.raises(ValidationError, match="Please provide a specific reason"):
        profile_change_service.submit_change_request(
            user_session=user,
            field_name="aadhaar_number",
            new_value="987654321099",
            reason="",  # Empty
        )

    with pytest.raises(ValidationError, match="Please provide a specific reason"):
        profile_change_service.submit_change_request(
            user_session=user,
            field_name="aadhaar_number",
            new_value="987654321099",
            reason="Fix",  # Less than 5 chars
        )


# =============================================================================
# 5. SELF-APPROVAL & HR/PRINCIPAL ROUTING RULES
# =============================================================================

def test_self_approval_blocked():
    """Verifies that an administrator or HR reviewer cannot approve their own change request."""
    # HR user reviewing their own request
    allowed, reason = can_review_specific_request(
        reviewer_role="HR",
        reviewer_user_id=10,
        requester_user_id=10,
        requester_role="HR",
    )
    assert not allowed
    assert "self-approval is forbidden" in reason.lower()

    # Admin reviewing their own request
    allowed, reason = can_review_specific_request(
        reviewer_role="ADMIN",
        reviewer_user_id=1,
        requester_user_id=1,
        requester_role="ADMIN",
    )
    assert not allowed
    assert "self-approval is forbidden" in reason.lower()


def test_hr_self_request_routed_to_principal():
    """
    Verifies that when an HR member submits a profile change request:
    - Another HR user is NOT allowed to approve it.
    - Only Principal (or Admin) can approve it.
    """
    # Another HR reviewer trying to review HR's request
    allowed_hr, reason_hr = can_review_specific_request(
        reviewer_role="HR",
        reviewer_user_id=11,
        requester_user_id=10,
        requester_role="HR",
    )
    assert not allowed_hr
    assert "principal" in reason_hr.lower()

    # Principal reviewing HR's request
    allowed_princ, _ = can_review_specific_request(
        reviewer_role="PRINCIPAL",
        reviewer_user_id=20,
        requester_user_id=10,
        requester_role="HR",
    )
    assert allowed_princ


def test_principal_self_request_routed_to_hr_or_admin():
    """
    Verifies that when the Principal submits a change request:
    - Principal cannot self-approve.
    - HR or Admin can review it.
    """
    # Principal self-approval blocked
    allowed_self, _ = can_review_specific_request(
        reviewer_role="PRINCIPAL",
        reviewer_user_id=20,
        requester_user_id=20,
        requester_role="PRINCIPAL",
    )
    assert not allowed_self

    # HR reviewing Principal's request
    allowed_hr, _ = can_review_specific_request(
        reviewer_role="HR",
        reviewer_user_id=10,
        requester_user_id=20,
        requester_role="PRINCIPAL",
    )
    assert allowed_hr


# =============================================================================
# 6. ATOMIC APPROVAL & AUDIT LOGGING
# =============================================================================

def test_atomic_approval_workflow():
    """
    Approving a change request:
    - Sets request status to APPROVED with reviewer ID and timestamp
    - Applies new value to employee record
    - Logs event to profile_change_audit
    """
    hr_session = UserSession(
        user_id=99,
        username="hr_manager",
        role="HR",
        status="ACTIVE",
        first_name="HR",
        last_name="Manager",
        faculty_id=99,
        employee_code="HR01",
        department_code="HR",
    )

    req_id = 101  # sarah jenkins pan_number
    success = profile_change_service.approve_request(
        reviewer_session=hr_session,
        request_id=req_id,
        reviewer_remark="Verified against IT department records.",
    )
    assert success

    req = profile_change_repository.get_by_id(req_id)
    assert req["status"] == "APPROVED"
    assert req["reviewed_by"] == 99
    assert req["reviewer_remark"] == "Verified against IT department records."

    # Verify audit log entry exists
    audits = [a for a in DEMO_PROFILE_CHANGE_AUDITS if a["request_id"] == req_id]
    assert len(audits) > 0
    assert any(a["action"] == "APPROVED" for a in audits)


def test_rejection_workflow_requires_remark():
    """
    Rejecting a change request:
    - Requires a mandatory reviewer remark (min 4 chars)
    - Leaves faculty record unchanged
    - Sets request status to REJECTED
    """
    hr_session = UserSession(
        user_id=99,
        username="hr_manager",
        role="HR",
        status="ACTIVE",
        first_name="HR",
        last_name="Manager",
        faculty_id=99,
        employee_code="HR01",
        department_code="HR",
    )

    req_id = 102  # prof rajesh kumar salary account

    # Attempt rejection without remark -> raises ValidationError
    with pytest.raises(ValidationError, match="reviewer remark is mandatory"):
        profile_change_service.reject_request(
            reviewer_session=hr_session,
            request_id=req_id,
            reviewer_remark="",
        )

    # Rejection with valid remark
    success = profile_change_service.reject_request(
        reviewer_session=hr_session,
        request_id=req_id,
        reviewer_remark="Bank passbook copy missing IFSC code.",
    )
    assert success

    req = profile_change_repository.get_by_id(req_id)
    assert req["status"] == "REJECTED"
    assert req["reviewer_remark"] == "Bank passbook copy missing IFSC code."


# =============================================================================
# 7. PROOF DOCUMENT VALIDATION
# =============================================================================

def test_proof_document_validation():
    """Tests file type filtering and 2MB limit on proof uploads."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Valid PDF file
        valid_pdf = tmp_path / "pan_card.pdf"
        valid_pdf.write_bytes(b"%PDF-1.4 test document content")
        stored = profile_change_service.handle_proof_upload(str(valid_pdf), 2, "pan_number")
        assert stored.startswith("uploads/proofs/")
        assert stored.endswith(".pdf")

        # 2. Unsupported format (.exe)
        invalid_exe = tmp_path / "script.exe"
        invalid_exe.write_bytes(b"MZ executable content")
        with pytest.raises(ValidationError, match="Only JPG, PNG, and PDF"):
            profile_change_service.handle_proof_upload(str(invalid_exe), 2, "pan_number")

        # 3. File exceeding 2 MB
        large_file = tmp_path / "large_proof.jpg"
        large_file.write_bytes(b"0" * (3 * 1024 * 1024))  # 3 MB
        with pytest.raises(ValidationError, match="Maximum allowed size is 2.0 MB"):
            profile_change_service.handle_proof_upload(str(large_file), 2, "pan_number")


# =============================================================================
# 8. CANCELLATION BY REQUESTER
# =============================================================================

def test_requester_can_cancel_own_request():
    """Allows requester to cancel their own pending change request."""
    user = UserSession(
        user_id=2,
        username="sarah.jenkins",
        role="FACULTY",
        status="ACTIVE",
        first_name="Sarah",
        last_name="Jenkins",
        faculty_id=2,
        employee_code="F002",
        department_code="MCA",
    )

    req_id = 101
    success = profile_change_service.cancel_request(user, req_id)
    assert success

    req = profile_change_repository.get_by_id(req_id)
    assert req["status"] == "CANCELLED"

    # Cancelling already cancelled request raises BusinessLogicError
    with pytest.raises(BusinessLogicError, match="Cannot cancel request"):
        profile_change_service.cancel_request(user, req_id)
