"""
Edit Profile Dialog
Modal form allowing faculty to self-update contact information and photo,
request changes to sensitive profile fields via HR/Principal approval workflow,
and administrative role direct editing.
"""
from pathlib import Path
import os
import re
import time
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QWidget,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from services.auth_service import UserSession
from services.faculty_service import faculty_service
from services.profile_change_service import (
    profile_change_service,
    mask_sensitive_value,
)
from config.profile_permissions import (
    can_edit_all_fields,
    is_direct_edit_field,
    is_approval_required_field,
    is_locked_field,
    get_field_label,
)
from ui.avatar_utils import create_square_avatar
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("ui.edit_profile_dialog")


class MyChangeRequestsDialog(QDialog):
    """Modal dialog displaying personal change requests and allowing cancellation of pending submissions."""

    def __init__(self, parent=None, user_session: Optional[UserSession] = None, employee_id: Optional[int] = None):
        super().__init__(parent)
        self.user_session = user_session
        self.employee_id = employee_id or (user_session.faculty_id if user_session else 1)
        self.setWindowTitle("My Profile Change Requests")
        self.setMinimumSize(780, 480)
        self.resize(840, 520)
        self.setModal(True)
        self._init_ui()
        self.load_requests()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #1E293B; border-bottom: 2px solid #0F172A;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 14, 20, 14)

        lbl = QLabel("📋 My Profile Change Requests")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #FFFFFF;")
        h_layout.addWidget(lbl)
        h_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            "background-color: #334155; color: #FFFFFF; border: 1px solid #475569; "
            "border-radius: 5px; padding: 4px 12px; font-weight: 600;"
        )
        self.btn_refresh.clicked.connect(self.load_requests)
        h_layout.addWidget(self.btn_refresh)
        root.addWidget(header)

        # Content Table
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(20, 16, 20, 16)
        c_layout.setSpacing(12)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Req ID", "Field", "Current Value", "Requested Value", "Status", "Reason", "Reviewer Remark", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #1E293B; color: #FFFFFF; font-weight: bold; "
            "padding: 6px; border: 1px solid #334155; font-size: 11px; }"
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setStyleSheet(
            "QTableWidget { border: 1px solid #CBD5E1; border-radius: 6px; background-color: #FFFFFF; gridline-color: #E2E8F0; } "
            "QTableWidget::item { padding: 4px 8px; color: #0F172A; font-size: 11px; }"
        )
        c_layout.addWidget(self.table, stretch=1)
        root.addWidget(content)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background-color: #FFFFFF; border-top: 1px solid #E2E8F0;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 12, 20, 12)
        f_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedHeight(32)
        btn_close.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; "
            "border-radius: 5px; padding: 4px 18px; font-weight: 600;"
        )
        btn_close.clicked.connect(self.accept)
        f_layout.addWidget(btn_close)
        root.addWidget(footer)

    def load_requests(self):
        reqs = profile_change_service.change_repo.get_requests_by_employee(self.employee_id)
        self.table.setRowCount(len(reqs))
        for row_idx, r in enumerate(reqs):
            req_id = r.get("id")
            status = r.get("status", "PENDING").upper()

            # ID
            id_item = QTableWidgetItem(f"#{req_id}")
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, id_item)

            # Field
            field_name = r.get("field_name", "")
            f_item = QTableWidgetItem(get_field_label(field_name))
            f_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 1, f_item)

            # Current (Old) Value (masked)
            old_val = mask_sensitive_value(r.get("old_value"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(old_val))

            # Requested (New) Value (masked)
            new_val = mask_sensitive_value(r.get("new_value"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(new_val))

            # Status with badge
            s_item = QTableWidgetItem(status)
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if status == "PENDING":
                s_item.setForeground(QColor("#D97706"))
            elif status == "APPROVED":
                s_item.setForeground(QColor("#16A34A"))
            elif status == "REJECTED":
                s_item.setForeground(QColor("#DC2626"))
            else:
                s_item.setForeground(QColor("#64748B"))
            self.table.setItem(row_idx, 4, s_item)

            # Reason
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(r.get("reason") or "")))

            # Reviewer Remark
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(r.get("reviewer_remark") or "-")))

            # Action: Cancel Request button if PENDING
            if status == "PENDING":
                btn_cancel = QPushButton("Cancel")
                btn_cancel.setCursor(Qt.PointingHandCursor)
                btn_cancel.setStyleSheet(
                    "background-color: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; "
                    "border-radius: 4px; padding: 2px 8px; font-weight: 600; font-size: 11px;"
                )
                btn_cancel.clicked.connect(lambda _, rid=req_id: self._cancel_request(rid))
                self.table.setCellWidget(row_idx, 7, btn_cancel)
            else:
                lbl_done = QLabel("Resolved")
                lbl_done.setAlignment(Qt.AlignCenter)
                lbl_done.setStyleSheet("color: #94A3B8; font-size: 11px;")
                self.table.setCellWidget(row_idx, 7, lbl_done)

    def _cancel_request(self, req_id: int):
        reply = QMessageBox.question(
            self,
            "Confirm Cancellation",
            "Are you sure you want to cancel this pending change request?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                profile_change_service.cancel_request(self.user_session, req_id)
                QMessageBox.information(self, "Request Cancelled", "The change request was successfully cancelled.")
                self.load_requests()
            except Exception as exc:
                QMessageBox.warning(self, "Cancellation Failed", str(exc))


class EditProfileDialog(QDialog):
    """Modal dialog for editing faculty profile information with change request workflow."""
    profile_updated = Signal(dict)

    def __init__(self, parent=None, user_session: Optional[UserSession] = None, faculty_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.user_session = user_session
        self.faculty_data = faculty_data or {}
        self.faculty_id = self.faculty_data.get("id") or (user_session.faculty_id if user_session else 1)
        self.role = (user_session.role if user_session else "FACULTY").upper()
        self.is_admin = can_edit_all_fields(self.role)
        self.selected_photo_path: Optional[str] = None
        self.selected_proof_path: Optional[str] = None

        # Fetch active pending fields for this employee
        self.pending_fields = profile_change_service.get_pending_fields_for_employee(self.faculty_id)

        self.setWindowTitle(f"Edit Profile - {self.faculty_data.get('full_name', 'Faculty')}")
        self.setMinimumSize(700, 640)
        self.resize(740, 680)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Dialog Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #1E293B; border-bottom: 2px solid #0F172A;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 14, 20, 14)

        lbl_title = QLabel("Edit Profile Details")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #FFFFFF;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        # "My Change Requests" Button
        self.btn_my_requests = QPushButton("📋 My Change Requests")
        self.btn_my_requests.setCursor(Qt.PointingHandCursor)
        self.btn_my_requests.setFixedHeight(28)
        self.btn_my_requests.setStyleSheet(
            "background-color: #334155; color: #FFFFFF; border: 1px solid #475569; "
            "border-radius: 5px; padding: 2px 10px; font-weight: 600; font-size: 11px;"
        )
        self.btn_my_requests.clicked.connect(self._open_my_requests)
        h_layout.addWidget(self.btn_my_requests)

        if self.is_admin:
            lbl_perm = QLabel("🛡️ Admin Mode (Direct Edit)")
            lbl_perm.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600; margin-left: 8px;")
        else:
            lbl_perm = QLabel("🔒 Sensitive Fields Require HR Approval")
            lbl_perm.setStyleSheet("color: #FBBF24; font-size: 11px; font-weight: 600; margin-left: 8px;")
        h_layout.addWidget(lbl_perm)
        root_layout.addWidget(header)

        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: #F8FAFC;")

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(24, 20, 24, 20)
        form_layout.setSpacing(18)

        # 1. Profile Photo Row
        photo_box = QFrame()
        photo_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;")
        pb_layout = QHBoxLayout(photo_box)
        pb_layout.setContentsMargins(16, 14, 16, 14)
        pb_layout.setSpacing(18)

        self.lbl_photo_preview = QLabel()
        self.lbl_photo_preview.setFixedSize(80, 80)
        initial_pix = create_square_avatar(
            image_path=self.faculty_data.get("profile_image_path"),
            size=80,
            radius=8,
            name=self.faculty_data.get("full_name", "Faculty"),
            role=self.role,
        )
        self.lbl_photo_preview.setPixmap(initial_pix)
        pb_layout.addWidget(self.lbl_photo_preview)

        v_photo_info = QVBoxLayout()
        v_photo_info.setSpacing(6)
        lbl_photo_heading = QLabel("Profile Photo")
        lbl_photo_heading.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_photo_heading.setStyleSheet("color: #0F172A;")

        lbl_photo_hint = QLabel("Upload a square JPG or PNG image (Max file size: 2 MB). Direct save, no approval required.")
        lbl_photo_hint.setStyleSheet("color: #64748B; font-size: 11px;")

        self.btn_choose_photo = QPushButton("📷 Choose Photo...")
        self.btn_choose_photo.setCursor(Qt.PointingHandCursor)
        self.btn_choose_photo.setFixedHeight(30)
        self.btn_choose_photo.setStyleSheet(
            "background-color: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; "
            "border-radius: 5px; padding: 4px 12px; font-weight: 600;"
        )
        self.btn_choose_photo.clicked.connect(self._choose_photo)

        v_photo_info.addWidget(lbl_photo_heading)
        v_photo_info.addWidget(lbl_photo_hint)
        v_photo_info.addWidget(self.btn_choose_photo, alignment=Qt.AlignLeft)
        pb_layout.addLayout(v_photo_info)
        pb_layout.addStretch()

        form_layout.addWidget(photo_box)

        # 2. Form Fields Grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;")
        g_box = QVBoxLayout(grid_frame)
        g_box.setContentsMargins(18, 16, 18, 16)
        g_box.setSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)

        # Helper to create styled field with approval badges
        def _add_field(row, col, field_key, label_text, value):
            is_pending = field_key in self.pending_fields

            # Label markup with badges
            if self.is_admin:
                badge_markup = ""
                is_editable = True
            elif is_direct_edit_field(field_key):
                badge_markup = " <span style='color: #2563EB; font-size: 10px; font-weight: bold;'>(Direct)</span>"
                is_editable = True
            elif is_approval_required_field(field_key):
                if is_pending:
                    badge_markup = " <span style='background-color: #FEF3C7; color: #D97706; border: 1px solid #F59E0B; border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;'>⏳ Pending approval</span>"
                else:
                    badge_markup = " <span style='background-color: #FEF3C7; color: #B45309; border: 1px solid #F59E0B; border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;'>⚠️ Requires HR approval</span>"
                is_editable = True
            else:
                badge_markup = " <span style='background-color: #F1F5F9; color: #64748B; border-radius: 4px; padding: 1px 5px; font-size: 10px;'>🔒 Locked</span>"
                is_editable = False

            lbl = QLabel(f"{label_text}{badge_markup}")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            lbl.setStyleSheet("color: #334155;")

            edit = QLineEdit(str(value or ""))
            edit.setMinimumHeight(32)
            if is_editable:
                edit.setEnabled(True)
                edit.setStyleSheet(
                    "QLineEdit { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
                    "border-radius: 6px; padding: 4px 10px; font-size: 12px; } "
                    "QLineEdit:focus { border: 1.5px solid #2563EB; background-color: #F0F7FF; }"
                )
            else:
                edit.setEnabled(False)
                edit.setStyleSheet(
                    "QLineEdit { background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; "
                    "border-radius: 6px; padding: 4px 10px; font-size: 12px; font-style: italic; }"
                )

            if is_pending:
                edit.setToolTip("A change request for this field is currently pending HR review.")

            grid.addWidget(lbl, row * 2, col)
            grid.addWidget(edit, row * 2 + 1, col)
            return edit

        # Column 1 (col=0)
        self.txt_emp_code = _add_field(0, 0, "employee_code", "Employee ID", self.faculty_data.get("employee_code"))
        self.txt_name = _add_field(1, 0, "name", "Full Name", self.faculty_data.get("full_name"))
        self.txt_dept = _add_field(2, 0, "department_id", "Department", self.faculty_data.get("department_name") or self.faculty_data.get("department_code"))
        self.txt_mobile = _add_field(3, 0, "phone", "Mobile No.", self.faculty_data.get("phone"))
        self.txt_personal_email = _add_field(4, 0, "personal_email", "Personal Email Id", self.faculty_data.get("personal_email"))
        self.txt_employment_type = _add_field(5, 0, "employment_type", "Employment Type", self.faculty_data.get("employment_type", "PERMANENT"))
        self.txt_pan = _add_field(6, 0, "pan_number", "PAN Card No", self.faculty_data.get("pan_number"))
        self.txt_pf = _add_field(7, 0, "pf_number", "PF NO", self.faculty_data.get("pf_number"))

        # Column 2 (col=1)
        self.txt_designation = _add_field(0, 1, "designation", "Designation", self.faculty_data.get("designation"))
        self.txt_experience = _add_field(1, 1, "experience_years", "Experience (Years)", self.faculty_data.get("experience_years", "0.0"))
        self.txt_inst_email = _add_field(2, 1, "email", "Inst. Email Id", self.faculty_data.get("email"))
        self.txt_dob = _add_field(3, 1, "dob", "DOB (YYYY-MM-DD)", self.faculty_data.get("dob"))
        self.txt_aadhaar = _add_field(4, 1, "aadhaar_number", "Aadhar No", self.faculty_data.get("aadhaar_number"))
        self.txt_uan = _add_field(5, 1, "uan_number", "UAN NO", self.faculty_data.get("uan_number"))
        self.txt_vtu_id = _add_field(6, 1, "vtu_id", "VTU ID", self.faculty_data.get("vtu_id"))
        self.txt_salary_ac = _add_field(7, 1, "salary_account_no", "Salary A/C No.", self.faculty_data.get("salary_account_no"))

        g_box.addLayout(grid)
        form_layout.addWidget(grid_frame)

        # 3. Change Request Details Card (Reason & Proof Upload)
        self.request_box = QFrame()
        self.request_box.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;")
        req_box_layout = QVBoxLayout(self.request_box)
        req_box_layout.setContentsMargins(18, 14, 18, 14)
        req_box_layout.setSpacing(10)

        lbl_req_hdr = QLabel("Change Request Details (Mandatory if modifying approval-required fields)")
        lbl_req_hdr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_req_hdr.setStyleSheet("color: #1E293B;")
        req_box_layout.addWidget(lbl_req_hdr)

        lbl_reason_prompt = QLabel("Reason for change * (Why is this sensitive profile field being updated?)")
        lbl_reason_prompt.setStyleSheet("color: #475569; font-size: 11px; font-weight: 600;")
        req_box_layout.addWidget(lbl_reason_prompt)

        self.txt_change_reason = QLineEdit()
        self.txt_change_reason.setPlaceholderText("e.g., Updated salary account to new bank branch / corrected PAN spelling")
        self.txt_change_reason.setMinimumHeight(32)
        self.txt_change_reason.setStyleSheet(
            "QLineEdit { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 4px 10px; font-size: 12px; } "
            "QLineEdit:focus { border: 1.5px solid #2563EB; background-color: #F0F7FF; }"
        )
        req_box_layout.addWidget(self.txt_change_reason)

        # Proof Document Picker Row
        h_proof = QHBoxLayout()
        h_proof.setSpacing(10)

        self.btn_choose_proof = QPushButton("📎 Choose Proof Document...")
        self.btn_choose_proof.setCursor(Qt.PointingHandCursor)
        self.btn_choose_proof.setFixedHeight(30)
        self.btn_choose_proof.setStyleSheet(
            "background-color: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; "
            "border-radius: 5px; padding: 4px 12px; font-weight: 600; font-size: 11px;"
        )
        self.btn_choose_proof.clicked.connect(self._choose_proof)
        h_proof.addWidget(self.btn_choose_proof)

        self.lbl_proof_file = QLabel("No document selected (Optional - JPG, PNG, PDF up to 2 MB)")
        self.lbl_proof_file.setStyleSheet("color: #64748B; font-size: 11px;")
        h_proof.addWidget(self.lbl_proof_file, stretch=1)

        self.btn_clear_proof = QPushButton("✖")
        self.btn_clear_proof.setFixedSize(26, 26)
        self.btn_clear_proof.setCursor(Qt.PointingHandCursor)
        self.btn_clear_proof.setStyleSheet("background-color: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; border-radius: 13px; font-weight: bold;")
        self.btn_clear_proof.setVisible(False)
        self.btn_clear_proof.clicked.connect(self._clear_proof)
        h_proof.addWidget(self.btn_clear_proof)

        req_box_layout.addLayout(h_proof)
        form_layout.addWidget(self.request_box)

        scroll.setWidget(form_widget)
        root_layout.addWidget(scroll)

        # Bottom Actions Bar
        actions_bar = QFrame()
        actions_bar.setStyleSheet("background-color: #FFFFFF; border-top: 1px solid #E2E8F0;")
        ab_layout = QHBoxLayout(actions_bar)
        ab_layout.setContentsMargins(20, 14, 20, 14)
        ab_layout.setSpacing(12)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 4px 18px; font-weight: 600;"
        )
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 Save Changes")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(34)
        self.btn_save.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; border: none; "
            "border-radius: 6px; padding: 4px 22px; font-weight: bold;"
        )
        self.btn_save.clicked.connect(self._save_profile)

        ab_layout.addStretch()
        ab_layout.addWidget(self.btn_cancel)
        ab_layout.addWidget(self.btn_save)
        root_layout.addWidget(actions_bar)

    def _open_my_requests(self):
        """Opens My Change Requests modal view."""
        dlg = MyChangeRequestsDialog(self, user_session=self.user_session, employee_id=self.faculty_id)
        dlg.exec()
        # Refresh pending fields
        self.pending_fields = profile_change_service.get_pending_fields_for_employee(self.faculty_id)

    def _choose_proof(self):
        """Allows user to select supporting proof file (JPG, PNG, PDF <= 2 MB)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Supporting Proof Document",
            "",
            "Documents & Images (*.jpg *.jpeg *.png *.pdf)"
        )
        if not file_path:
            return

        p = Path(file_path)
        if not p.exists():
            return

        ext = p.suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".pdf"]:
            QMessageBox.warning(self, "Invalid Format", "Only JPG, PNG, and PDF files are accepted.")
            return

        size_bytes = p.stat().st_size
        if size_bytes > 2 * 1024 * 1024:
            QMessageBox.warning(
                self,
                "File Too Large",
                f"Selected proof document size is {size_bytes / (1024 * 1024):.2f} MB.\n"
                "Maximum permitted file size is 2.0 MB."
            )
            return

        self.selected_proof_path = file_path
        self.lbl_proof_file.setText(f"Selected: {p.name} ({size_bytes / 1024:.1f} KB)")
        self.lbl_proof_file.setStyleSheet("color: #15803D; font-weight: bold; font-size: 11px;")
        self.btn_clear_proof.setVisible(True)

    def _clear_proof(self):
        self.selected_proof_path = None
        self.lbl_proof_file.setText("No document selected (Optional - JPG, PNG, PDF up to 2 MB)")
        self.lbl_proof_file.setStyleSheet("color: #64748B; font-size: 11px;")
        self.btn_clear_proof.setVisible(False)

    def _choose_photo(self):
        """Opens file dialog, checks file format and <= 2 MB limit, and previews square crop."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Photo",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return

        p = Path(file_path)
        if not p.exists():
            return

        ext = p.suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            QMessageBox.warning(self, "Invalid Format", "Please select a JPG or PNG image file.")
            return

        size_bytes = p.stat().st_size
        if size_bytes > 2 * 1024 * 1024:
            QMessageBox.warning(
                self,
                "File Too Large",
                f"Selected image size is {size_bytes / (1024 * 1024):.2f} MB.\n"
                "Maximum permitted profile image size is 2.0 MB."
            )
            return

        try:
            base_dir = Path(__file__).resolve().parent.parent
            avatar_dir = base_dir / "uploads" / "avatars"
            avatar_dir.mkdir(parents=True, exist_ok=True)

            emp_code = self.faculty_data.get("employee_code") or "faculty"
            target_filename = f"{emp_code}_{int(time.time())}.png"
            target_path = avatar_dir / target_filename

            src_pix = QPixmap(str(p))
            if src_pix.isNull():
                QMessageBox.warning(self, "Corrupted File", "Could not read the selected image file.")
                return

            side = min(src_pix.width(), src_pix.height())
            x = (src_pix.width() - side) // 2
            y = (src_pix.height() - side) // 2
            cropped = src_pix.copy(x, y, side, side)
            cropped.save(str(target_path), "PNG")

            rel_path = f"uploads/avatars/{target_filename}"
            self.selected_photo_path = rel_path

            preview_pix = create_square_avatar(
                image_path=str(target_path),
                size=80,
                radius=8,
                name=self.faculty_data.get("full_name", "Faculty"),
                role=self.role,
            )
            self.lbl_photo_preview.setPixmap(preview_pix)
            logger.info(f"Loaded and cropped new profile photo to {rel_path}")
        except Exception as exc:
            logger.error(f"Error processing selected photo: {exc}")
            QMessageBox.critical(self, "Image Error", f"Failed to process selected photo:\n{exc}")

    def _save_profile(self):
        """
        Validates inputs, executes direct updates for immediate fields,
        and submits approval change requests for sensitive fields.
        """
        mobile = self.txt_mobile.text().strip()
        personal_email = self.txt_personal_email.text().strip().lower()

        # Direct edit validation
        if mobile and not re.match(r"^\d{10}$", mobile):
            QMessageBox.warning(self, "Validation Error", "Mobile Number must be exactly 10 numeric digits.")
            self.txt_mobile.setFocus()
            return

        if personal_email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", personal_email):
            QMessageBox.warning(self, "Validation Error", "Please enter a valid personal email address.")
            self.txt_personal_email.setFocus()
            return

        # If Administrative Role: Direct update to everything
        if self.is_admin:
            pan = self.txt_pan.text().strip().upper()
            if pan and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
                QMessageBox.warning(self, "Validation Error", "PAN Card format must match ABCDE1234F.")
                self.txt_pan.setFocus()
                return

            aadhaar = self.txt_aadhaar.text().strip()
            if aadhaar and not re.match(r"^\d{12}$", aadhaar):
                QMessageBox.warning(self, "Validation Error", "Aadhaar Number must be exactly 12 numeric digits.")
                self.txt_aadhaar.setFocus()
                return

            payload = {
                "phone": mobile,
                "personal_email": personal_email,
                "salary_account_no": self.txt_salary_ac.text().strip(),
                "pan_number": pan,
                "aadhaar_number": aadhaar,
                "pf_number": self.txt_pf.text().strip(),
                "uan_number": self.txt_uan.text().strip(),
                "vtu_id": self.txt_vtu_id.text().strip(),
                "designation": self.txt_designation.text().strip(),
                "employment_type": self.txt_employment_type.text().strip() or "PERMANENT",
            }
            if self.selected_photo_path:
                payload["profile_image_path"] = self.selected_photo_path

            try:
                payload["experience_years"] = float(self.txt_experience.text().strip() or 0.0)
            except ValueError:
                payload["experience_years"] = 0.0

            dob_val = self.txt_dob.text().strip()
            if dob_val:
                payload["dob"] = dob_val

            try:
                updated_fac = faculty_service.update_profile(
                    user_session=self.user_session,
                    faculty_id=self.faculty_id,
                    profile_data=payload,
                )
                if self.user_session and self.selected_photo_path:
                    self.user_session.profile_image_path = self.selected_photo_path

                QMessageBox.information(
                    self,
                    "Profile Updated",
                    "Administrative profile changes have been saved directly to the database."
                )
                self.profile_updated.emit(updated_fac)
                self.accept()
            except Exception as exc:
                logger.error(f"Error updating profile: {exc}")
                QMessageBox.critical(self, "Update Error", f"Failed to save profile changes:\n{exc}")
            return

        # Standard Faculty Mode: Separate direct updates from approval-required changes
        # 1. Identify changed approval-required fields
        approval_inputs = {
            "name": self.txt_name.text().strip(),
            "salary_account_no": self.txt_salary_ac.text().strip(),
            "pan_number": self.txt_pan.text().strip().upper(),
            "aadhaar_number": self.txt_aadhaar.text().strip(),
            "pf_number": self.txt_pf.text().strip(),
            "uan_number": self.txt_uan.text().strip(),
            "dob": self.txt_dob.text().strip(),
        }

        changed_approval_fields = {}
        for field, new_val in approval_inputs.items():
            if field == "name":
                old_val = str(self.faculty_data.get("full_name") or "").strip()
            else:
                old_val = str(self.faculty_data.get(field) or "").strip()

            if new_val != old_val:
                changed_approval_fields[field] = (old_val, new_val)

        # 2. Check if any changed field is already pending
        for field in changed_approval_fields:
            if field in self.pending_fields:
                QMessageBox.warning(
                    self,
                    "Request Already Pending",
                    f"A change request for '{get_field_label(field)}' is already pending HR review.\n\n"
                    "Only one pending request per field is permitted. Please wait for review or cancel the pending request first."
                )
                return

        # 3. If approval fields are modified, reason is mandatory
        reason = self.txt_change_reason.text().strip()
        if changed_approval_fields:
            if len(reason) < 5:
                QMessageBox.warning(
                    self,
                    "Reason Required",
                    "Please enter a reason for change (at least 5 characters) in the Change Request Details section."
                )
                self.txt_change_reason.setFocus()
                return

            # Validate formats for all changed fields
            for field, (old_val, new_val) in changed_approval_fields.items():
                try:
                    profile_change_service.validate_field_value(field, new_val)
                except ValidationError as v_err:
                    QMessageBox.warning(self, "Validation Error", str(v_err))
                    return

        # 4. Check changed direct fields
        old_mobile = str(self.faculty_data.get("phone") or "").strip()
        old_email = str(self.faculty_data.get("personal_email") or "").strip().lower()

        direct_payload = {}
        if mobile != old_mobile:
            direct_payload["phone"] = mobile
        if personal_email != old_email:
            direct_payload["personal_email"] = personal_email
        if self.selected_photo_path:
            direct_payload["profile_image_path"] = self.selected_photo_path

        if not direct_payload and not changed_approval_fields:
            QMessageBox.information(self, "No Changes", "No profile modifications were detected.")
            self.accept()
            return

        # 5. Apply direct updates
        direct_updated_ok = False
        latest_fac_record = self.faculty_data
        if direct_payload:
            try:
                latest_fac_record = faculty_service.update_profile(
                    user_session=self.user_session,
                    faculty_id=self.faculty_id,
                    profile_data=direct_payload,
                )
                if self.user_session and self.selected_photo_path:
                    self.user_session.profile_image_path = self.selected_photo_path
                direct_updated_ok = True
            except Exception as exc:
                logger.error(f"Direct update failed: {exc}")
                QMessageBox.critical(self, "Update Failed", f"Failed to update contact info:\n{exc}")
                return

        # 6. Submit approval change requests
        submitted_fields = []
        submission_errors = []
        if changed_approval_fields:
            for field, (old_val, new_val) in changed_approval_fields.items():
                try:
                    profile_change_service.submit_change_request(
                        user_session=self.user_session,
                        field_name=field,
                        new_value=new_val,
                        reason=reason,
                        proof_file_path=self.selected_proof_path,
                    )
                    submitted_fields.append(get_field_label(field))
                except Exception as exc:
                    logger.error(f"Change request submission failed for {field}: {exc}")
                    submission_errors.append(f"{get_field_label(field)}: {exc}")

        # 7. Inform user of outcomes
        if submission_errors:
            QMessageBox.critical(
                self,
                "Submission Error",
                "Some requests could not be submitted:\n\n" + "\n".join(submission_errors)
            )

        if submitted_fields and direct_updated_ok:
            QMessageBox.information(
                self,
                "Changes Processed",
                f"Contact details were saved immediately.\n\n"
                f"Change request(s) for {', '.join(submitted_fields)} were submitted for HR approval.\n"
                "Your profile will retain current statutory values until approved."
            )
        elif submitted_fields:
            QMessageBox.information(
                self,
                "Change Request Submitted",
                f"Change request(s) for {', '.join(submitted_fields)} were submitted for HR approval.\n\n"
                "Your profile will retain current values with a 'Pending approval' badge until reviewed."
            )
        elif direct_updated_ok:
            QMessageBox.information(
                self,
                "Profile Updated",
                "Your contact details have been updated successfully."
            )

        self.profile_updated.emit(latest_fac_record)
        self.accept()
