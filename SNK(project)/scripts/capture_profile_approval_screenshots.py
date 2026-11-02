"""
Captures high-resolution offscreen screenshots for the 4 Profile Change Approval scenes:
1. faculty_editing_sensitive_field.png
2. pending_approval_badge_dashboard.png
3. hr_profile_approvals_management.png
4. post_approval_updated_profile.png
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from services.auth_service import UserSession, auth_service
from services.faculty_service import faculty_service
from repositories.profile_change_repository import (
    DEMO_PROFILE_CHANGE_REQUESTS,
    DEMO_PROFILE_CHANGE_AUDITS,
)
from ui.edit_profile_dialog import EditProfileDialog
from ui.dashboard_widget import DashboardWidget
from ui.main_window import MainWindow


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    out_dir = Path("docs/screenshots/bugfix")
    out_dir.mkdir(parents=True, exist_ok=True)

    fac_user = UserSession(
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
    fac_data = {
        "id": 2,
        "user_id": 2,
        "employee_code": "F002",
        "full_name": "Dr. Sarah Jenkins",
        "phone": "9876543212",
        "personal_email": "sarah.personal@gmail.com",
        "department_name": "Computer Applications",
        "department_code": "MCA",
        "designation": "Associate Professor",
        "pan_number": "ABCDE1234F",
        "salary_account_no": "50100234567890",
        "aadhaar_number": "987654321012",
        "pf_number": "KN/BNG/0045612/000/0000123",
        "uan_number": "100987654321",
        "vtu_id": "VTU14589",
        "dob": "1988-04-12",
        "joining_date": "2021-08-10",
        "employment_type": "PERMANENT",
        "experience_years": 8.5,
    }

    # -------------------------------------------------------------------------
    # Scene 1: Faculty editing sensitive field
    # -------------------------------------------------------------------------
    dlg = EditProfileDialog(user_session=fac_user, faculty_data=fac_data)
    dlg.txt_pan.setText("ABCDE9999Z")
    dlg.txt_change_reason.setText("Updated PAN card to reflect corrected spelling as per Income Tax portal.")
    dlg.lbl_proof_file.setText("Selected: pan_card_copy.pdf (142.5 KB)")
    dlg.lbl_proof_file.setStyleSheet("color: #15803D; font-weight: bold; font-size: 11px;")
    dlg.btn_clear_proof.setVisible(True)
    dlg.resize(740, 680)
    dlg.show()
    app.processEvents()
    pix1 = dlg.grab()
    p1 = out_dir / "faculty_editing_sensitive_field.png"
    pix1.save(str(p1))
    dlg.close()
    print(f"Captured: {p1}")

    # -------------------------------------------------------------------------
    # Scene 2: Profile showing old value with orange "Pending approval" badge
    # -------------------------------------------------------------------------
    DEMO_PROFILE_CHANGE_REQUESTS.clear()
    DEMO_PROFILE_CHANGE_REQUESTS.append({
        "id": 101,
        "employee_id": 2,
        "field_name": "pan_number",
        "old_value": "ABCDE1234F",
        "new_value": "ABCDE9999Z",
        "reason": "Updated PAN card to reflect corrected spelling as per Income Tax portal.",
        "proof_path": "uploads/proofs/proof_emp2_pan_number.pdf",
        "status": "PENDING",
        "requested_at": "2026-10-31 11:20:00",
        "reviewed_by": None,
        "reviewed_at": None,
        "reviewer_remark": None,
        "employee_code": "F002",
        "employee_name": "Dr. Sarah Jenkins",
        "department_code": "MCA",
        "department_name": "Computer Applications",
        "requester_user_id": 2,
        "requester_role": "FACULTY",
    })

    dash = DashboardWidget(role="FACULTY", user_session=fac_user)
    dash.faculty_data = fac_data
    dash._sensitive_revealed = True
    dash._refresh_profile_ui()
    dash.resize(1200, 750)
    dash.show()
    app.processEvents()
    pix2 = dash.grab()
    p2 = out_dir / "pending_approval_badge_dashboard.png"
    pix2.save(str(p2))
    dash.close()
    print(f"Captured: {p2}")

    # -------------------------------------------------------------------------
    # Scene 3: HR/Principal "Profile Approvals" table with a request, filters, and pending badge on sidebar
    # -------------------------------------------------------------------------
    hr_user = UserSession(
        user_id=10,
        username="hr_head",
        role="HR",
        status="ACTIVE",
        first_name="Hema",
        last_name="Rao",
        faculty_id=10,
        employee_code="HR001",
        department_code="HR",
    )
    auth_service._current_session = hr_user
    main_win = MainWindow()
    main_win.update_session_ui()
    main_win.switch_to_tab(21)  # Tab 21: Profile Approvals
    main_win.profile_approvals_view.load_requests()
    main_win.resize(1366, 768)
    main_win.show()
    app.processEvents()
    pix3 = main_win.grab()
    p3 = out_dir / "hr_profile_approvals_management.png"
    pix3.save(str(p3))
    main_win.close()
    print(f"Captured: {p3}")

    # -------------------------------------------------------------------------
    # Scene 4: Profile updated after approval (with notification banner)
    # -------------------------------------------------------------------------
    DEMO_PROFILE_CHANGE_REQUESTS[0]["status"] = "APPROVED"
    DEMO_PROFILE_CHANGE_REQUESTS[0]["reviewed_by"] = 10
    DEMO_PROFILE_CHANGE_REQUESTS[0]["reviewer_remark"] = "Approved after verifying with IT department."

    updated_fac_data = dict(fac_data)
    updated_fac_data["pan_number"] = "ABCDE9999Z"

    dash_approved = DashboardWidget(role="FACULTY", user_session=fac_user)
    dash_approved.faculty_data = updated_fac_data
    dash_approved._sensitive_revealed = True
    dash_approved._refresh_profile_ui()
    dash_approved.resize(1200, 750)
    dash_approved.show()
    app.processEvents()
    pix4 = dash_approved.grab()
    p4 = out_dir / "post_approval_updated_profile.png"
    pix4.save(str(p4))
    dash_approved.close()
    print(f"Captured: {p4}")

    print("All 4 screenshots captured successfully!")


if __name__ == "__main__":
    main()
