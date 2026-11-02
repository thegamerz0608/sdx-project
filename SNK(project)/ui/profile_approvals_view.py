"""
Profile Change Approvals Management View (PySide6)
Accessible exclusively to HR, Principal, and Administrator roles.
Features filtered request grid, document inspection, side-by-side comparison,
atomic single-transaction approvals, mandatory rejection remarks, and bulk operations.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QFont, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QDialog,
    QTextEdit,
    QCheckBox,
    QSizePolicy,
)

from services.auth_service import auth_service, UserSession
from services.profile_change_service import (
    profile_change_service,
    mask_sensitive_value,
)
from repositories.department_repository import DepartmentRepository
from config.profile_permissions import (
    get_field_label,
    can_review_specific_request,
)
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("ui.profile_approvals_view")


class ProfileRequestReviewDialog(QDialog):
    """Modal dialog displaying old vs new comparison, reason, proof viewer, and approval actions."""
    decision_made = Signal()

    def __init__(self, parent=None, request_data: Optional[Dict[str, Any]] = None, reviewer_session: Optional[UserSession] = None):
        super().__init__(parent)
        self.req = request_data or {}
        self.reviewer_session = reviewer_session or auth_service.current_user
        self.setWindowTitle(f"Review Profile Change Request #{self.req.get('id', '')}")
        self.setMinimumSize(620, 560)
        self.resize(680, 600)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #1E293B; border-bottom: 2px solid #0F172A;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 14, 20, 14)

        lbl_title = QLabel(f"Profile Change Request #{self.req.get('id', '')}")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #FFFFFF;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        status = self.req.get("status", "PENDING").upper()
        lbl_status = QLabel(f"STATUS: {status}")
        lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        if status == "PENDING":
            lbl_status.setStyleSheet("background-color: #FEF3C7; color: #B45309; padding: 4px 10px; border-radius: 6px;")
        elif status == "APPROVED":
            lbl_status.setStyleSheet("background-color: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 6px;")
        elif status == "REJECTED":
            lbl_status.setStyleSheet("background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 6px;")
        else:
            lbl_status.setStyleSheet("background-color: #F1F5F9; color: #64748B; padding: 4px 10px; border-radius: 6px;")
        h_layout.addWidget(lbl_status)
        root_layout.addWidget(header)

        # Content Card
        content_widget = QWidget()
        c_layout = QVBoxLayout(content_widget)
        c_layout.setContentsMargins(22, 18, 22, 18)
        c_layout.setSpacing(16)

        # 1. Requester Info Card
        emp_card = QFrame()
        emp_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px;")
        ec_layout = QGridLayout(emp_card)
        ec_layout.setContentsMargins(16, 12, 16, 12)
        ec_layout.setHorizontalSpacing(16)
        ec_layout.setVerticalSpacing(6)

        def _info_pair(row, col, lbl_t, val_t):
            l = QLabel(f"<b>{lbl_t}:</b>")
            l.setStyleSheet("color: #475569; font-size: 11px;")
            v = QLabel(str(val_t or "-"))
            v.setStyleSheet("color: #0F172A; font-weight: 600; font-size: 12px;")
            ec_layout.addWidget(l, row, col * 2)
            ec_layout.addWidget(v, row, col * 2 + 1)

        _info_pair(0, 0, "Employee Name", self.req.get("employee_name"))
        _info_pair(0, 1, "Employee ID", self.req.get("employee_code"))
        _info_pair(1, 0, "Department", self.req.get("department_name") or self.req.get("department_code"))
        _info_pair(1, 1, "Requested On", self.req.get("requested_at"))

        c_layout.addWidget(emp_card)

        # 2. Side-by-Side Comparison Box
        field_key = self.req.get("field_name", "")
        field_label = get_field_label(field_key)

        comp_box = QFrame()
        comp_box.setStyleSheet("background-color: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 8px;")
        comp_layout = QVBoxLayout(comp_box)
        comp_layout.setContentsMargins(18, 14, 18, 14)
        comp_layout.setSpacing(10)

        lbl_target_field = QLabel(f"Field Requested for Modification: <b>{field_label}</b>")
        lbl_target_field.setStyleSheet("color: #1E293B; font-size: 12px;")
        comp_layout.addWidget(lbl_target_field)

        grid_comp = QGridLayout()
        grid_comp.setHorizontalSpacing(16)
        grid_comp.setVerticalSpacing(6)

        lbl_old_hdr = QLabel("Current / Old Value (Active Profile)")
        lbl_old_hdr.setStyleSheet("background-color: #F1F5F9; color: #475569; font-weight: bold; padding: 6px 10px; border-radius: 4px;")
        lbl_new_hdr = QLabel("Requested New Value (Pending Approval)")
        lbl_new_hdr.setStyleSheet("background-color: #EFF6FF; color: #1D4ED8; font-weight: bold; padding: 6px 10px; border-radius: 4px;")

        grid_comp.addWidget(lbl_old_hdr, 0, 0)
        grid_comp.addWidget(lbl_new_hdr, 0, 1)

        old_val_display = mask_sensitive_value(self.req.get("old_value"))
        new_val_display = mask_sensitive_value(self.req.get("new_value"))

        lbl_old_val = QLabel(old_val_display)
        lbl_old_val.setStyleSheet("background-color: #F8FAFC; color: #334155; padding: 10px; border: 1px solid #E2E8F0; border-radius: 6px; font-size: 13px; font-family: monospace;")
        lbl_new_val = QLabel(new_val_display)
        lbl_new_val.setStyleSheet("background-color: #F0FDF4; color: #15803D; font-weight: bold; padding: 10px; border: 1.5px solid #86EFAC; border-radius: 6px; font-size: 13px; font-family: monospace;")

        grid_comp.addWidget(lbl_old_val, 1, 0)
        grid_comp.addWidget(lbl_new_val, 1, 1)

        comp_layout.addLayout(grid_comp)
        c_layout.addWidget(comp_box)

        # 3. Justification & Proof Row
        just_card = QFrame()
        just_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;")
        jc_layout = QVBoxLayout(just_card)
        jc_layout.setContentsMargins(16, 12, 16, 12)
        jc_layout.setSpacing(6)

        lbl_reason_title = QLabel("Reason for Change Request (Provided by Requester):")
        lbl_reason_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_reason_title.setStyleSheet("color: #334155;")
        jc_layout.addWidget(lbl_reason_title)

        lbl_reason_text = QLabel(self.req.get("reason") or "No justification provided.")
        lbl_reason_text.setWordWrap(True)
        lbl_reason_text.setStyleSheet("color: #0F172A; font-size: 12px; background-color: #F8FAFC; padding: 8px; border-radius: 5px; border: 1px solid #E2E8F0;")
        jc_layout.addWidget(lbl_reason_text)

        # Proof File Action
        proof_path = self.req.get("proof_path")
        h_proof = QHBoxLayout()
        h_proof.setSpacing(10)
        lbl_proof_caption = QLabel("Supporting Document / Proof:")
        lbl_proof_caption.setStyleSheet("color: #475569; font-size: 11px; font-weight: 600;")
        h_proof.addWidget(lbl_proof_caption)

        if proof_path:
            btn_open_proof = QPushButton("📄 View Attached Document")
            btn_open_proof.setCursor(Qt.PointingHandCursor)
            btn_open_proof.setStyleSheet("background-color: #2563EB; color: #FFFFFF; padding: 4px 12px; border-radius: 4px; font-weight: 600;")
            btn_open_proof.clicked.connect(lambda: self._open_proof_file(proof_path))
            h_proof.addWidget(btn_open_proof)
        else:
            lbl_no_proof = QLabel("No document attached")
            lbl_no_proof.setStyleSheet("color: #94A3B8; font-style: italic; font-size: 11px;")
            h_proof.addWidget(lbl_no_proof)
        h_proof.addStretch()
        jc_layout.addLayout(h_proof)

        c_layout.addWidget(just_card)

        # 4. Reviewer Remark Input (Mandatory on reject)
        c_layout.addWidget(QLabel("Reviewer Remark (Mandatory if Rejecting):"))
        self.txt_remark = QTextEdit()
        self.txt_remark.setPlaceholderText("Enter review feedback or reason for decision...")
        self.txt_remark.setFixedHeight(65)
        self.txt_remark.setStyleSheet(
            "QTextEdit { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 6px; font-size: 12px; } "
            "QTextEdit:focus { border: 1.5px solid #2563EB; }"
        )
        if self.req.get("reviewer_remark"):
            self.txt_remark.setText(self.req.get("reviewer_remark"))
        if status != "PENDING":
            self.txt_remark.setReadOnly(True)
        c_layout.addWidget(self.txt_remark)

        root_layout.addWidget(content_widget)

        # Bottom Actions Bar
        actions_bar = QFrame()
        actions_bar.setStyleSheet("background-color: #FFFFFF; border-top: 1px solid #E2E8F0;")
        ab_layout = QHBoxLayout(actions_bar)
        ab_layout.setContentsMargins(20, 14, 20, 14)
        ab_layout.setSpacing(12)

        self.btn_close = QPushButton("Close")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedHeight(34)
        self.btn_close.setStyleSheet("background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 16px; font-weight: 600;")
        self.btn_close.clicked.connect(self.reject)
        ab_layout.addWidget(self.btn_close)
        ab_layout.addStretch()

        if status == "PENDING":
            # Protocol check for self-approval or role mismatch
            allowed, rule_msg = can_review_specific_request(
                reviewer_role=self.reviewer_session.role if self.reviewer_session else "HR",
                reviewer_user_id=self.reviewer_session.user_id if self.reviewer_session else 0,
                requester_user_id=self.req.get("requester_user_id") or 0,
                requester_role=self.req.get("requester_role", "FACULTY"),
            )

            self.btn_reject = QPushButton("❌ Reject Request")
            self.btn_reject.setCursor(Qt.PointingHandCursor)
            self.btn_reject.setFixedHeight(34)
            self.btn_reject.setStyleSheet("background-color: #DC2626; color: #FFFFFF; border: none; border-radius: 6px; padding: 4px 18px; font-weight: bold;")
            self.btn_reject.clicked.connect(self._do_reject)

            self.btn_approve = QPushButton("✅ Approve & Apply Change")
            self.btn_approve.setCursor(Qt.PointingHandCursor)
            self.btn_approve.setFixedHeight(34)
            self.btn_approve.setStyleSheet("background-color: #16A34A; color: #FFFFFF; border: none; border-radius: 6px; padding: 4px 20px; font-weight: bold;")
            self.btn_approve.clicked.connect(self._do_approve)

            if not allowed:
                self.btn_approve.setEnabled(False)
                self.btn_reject.setEnabled(False)
                self.btn_approve.setToolTip(rule_msg)
                self.btn_reject.setToolTip(rule_msg)
                lbl_blocked = QLabel(f"⚠️ {rule_msg}")
                lbl_blocked.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: bold;")
                ab_layout.addWidget(lbl_blocked)

            ab_layout.addWidget(self.btn_reject)
            ab_layout.addWidget(self.btn_approve)

        root_layout.addWidget(actions_bar)

    def _open_proof_file(self, rel_path: str):
        """Opens supporting document in native desktop handler."""
        base_dir = Path(__file__).resolve().parent.parent
        p = base_dir / rel_path
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
        else:
            QMessageBox.warning(self, "Document Missing", f"Proof document not found at: {p}")

    def _do_approve(self):
        """Approves request via service with atomic profile update."""
        remark = self.txt_remark.toPlainText().strip() or "Approved by reviewer."
        reply = QMessageBox.question(
            self,
            "Confirm Profile Update",
            f"Are you sure you want to approve this change for {self.req.get('employee_name')}?\n\n"
            f"Field: {get_field_label(self.req.get('field_name'))}\n"
            "This will update the active employee record in the database immediately.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success = profile_change_service.approve_request(
                reviewer_session=self.reviewer_session,
                request_id=self.req["id"],
                reviewer_remark=remark,
            )
            if success:
                QMessageBox.information(
                    self,
                    "Approval Completed",
                    "The profile change request was APPROVED.\n"
                    "The employee record has been updated and an audit trail entry was recorded."
                )
                self.decision_made.emit()
                self.accept()
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Validation Error", str(err))
        except Exception as exc:
            logger.error(f"Approval error: {exc}")
            QMessageBox.critical(self, "Approval Failed", f"Failed to approve request:\n{exc}")

    def _do_reject(self):
        """Rejects request with mandatory remark."""
        remark = self.txt_remark.toPlainText().strip()
        if len(remark) < 4:
            QMessageBox.warning(
                self,
                "Remark Required",
                "Please enter a reviewer remark explaining why this request is being rejected (min 4 characters)."
            )
            self.txt_remark.setFocus()
            return

        try:
            success = profile_change_service.reject_request(
                reviewer_session=self.reviewer_session,
                request_id=self.req["id"],
                reviewer_remark=remark,
            )
            if success:
                QMessageBox.information(
                    self,
                    "Request Rejected",
                    "The profile change request has been REJECTED.\n"
                    "The employee's profile remains unchanged."
                )
                self.decision_made.emit()
                self.accept()
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Validation Error", str(err))
        except Exception as exc:
            logger.error(f"Rejection error: {exc}")
            QMessageBox.critical(self, "Rejection Failed", f"Failed to reject request:\n{exc}")


class ProfileApprovalsView(QWidget):
    """
    Management console for reviewing, approving, and rejecting faculty profile change requests.
    Supports filtering by status, department, and field, plus bulk transactions.
    """
    requests_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dept_repo = DepartmentRepository()
        self.cached_requests: List[Dict[str, Any]] = []
        self._init_ui()
        self.load_requests()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # 1. Header Banner
        head_box = QFrame()
        head_box.setStyleSheet("background-color: #1E293B; border-radius: 8px;")
        hb_layout = QHBoxLayout(head_box)
        hb_layout.setContentsMargins(20, 16, 20, 16)

        v_head = QVBoxLayout()
        v_head.setSpacing(3)
        lbl_title = QLabel("🛡️ Profile Change Approvals Management")
        lbl_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #FFFFFF;")

        lbl_desc = QLabel("Review, approve, or reject employee profile modification requests with atomic transactions and cryptographic auditing.")
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        v_head.addWidget(lbl_title)
        v_head.addWidget(lbl_desc)

        hb_layout.addLayout(v_head)
        hb_layout.addStretch()

        self.lbl_pending_badge = QLabel("0 Pending")
        self.lbl_pending_badge.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_pending_badge.setStyleSheet("background-color: #EA580C; color: #FFFFFF; padding: 6px 14px; border-radius: 6px;")
        hb_layout.addWidget(self.lbl_pending_badge)

        main_layout.addWidget(head_box)

        # 2. Filter Toolbar Card
        filter_card = QFrame()
        filter_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;")
        fc_layout = QHBoxLayout(filter_card)
        fc_layout.setContentsMargins(14, 10, 14, 10)
        fc_layout.setSpacing(12)

        # Status Filter
        fc_layout.addWidget(QLabel("Status:"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["PENDING", "ALL", "APPROVED", "REJECTED", "CANCELLED"])
        self.cmb_status.setFixedHeight(30)
        self.cmb_status.currentIndexChanged.connect(self.load_requests)
        fc_layout.addWidget(self.cmb_status)

        # Department Filter
        fc_layout.addWidget(QLabel("Department:"))
        self.cmb_dept = QComboBox()
        self.cmb_dept.addItem("All Departments", None)
        depts = self.dept_repo.get_all()
        for d in depts:
            self.cmb_dept.addItem(f"{d.get('code')} - {d.get('name')}", d.get("id"))
        self.cmb_dept.setFixedHeight(30)
        self.cmb_dept.currentIndexChanged.connect(self.load_requests)
        fc_layout.addWidget(self.cmb_dept)

        # Field Filter
        fc_layout.addWidget(QLabel("Field:"))
        self.cmb_field = QComboBox()
        self.cmb_field.addItem("All Fields", "ALL")
        self.cmb_field.addItem("PAN Card No.", "pan_number")
        self.cmb_field.addItem("Salary A/C No.", "salary_account_no")
        self.cmb_field.addItem("Aadhar No.", "aadhaar_number")
        self.cmb_field.addItem("PF NO", "pf_number")
        self.cmb_field.addItem("UAN NO", "uan_number")
        self.cmb_field.addItem("DOB", "dob")
        self.cmb_field.addItem("Full Name", "name")
        self.cmb_field.setFixedHeight(30)
        self.cmb_field.currentIndexChanged.connect(self.load_requests)
        fc_layout.addWidget(self.cmb_field)

        # Search box
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by employee code or name...")
        self.txt_search.setFixedHeight(30)
        self.txt_search.textChanged.connect(self.load_requests)
        fc_layout.addWidget(self.txt_search, stretch=1)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.setStyleSheet("background-color: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 5px; font-weight: 600; padding: 4px 12px;")
        self.btn_refresh.clicked.connect(self.load_requests)
        fc_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(filter_card)

        # 3. Batch Action Bar
        batch_bar = QHBoxLayout()
        batch_bar.setSpacing(10)

        self.btn_select_all = QPushButton("☑ Select All")
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.setFixedHeight(30)
        self.btn_select_all.setStyleSheet("background-color: #F8FAFC; color: #475569; border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 12px; font-weight: 600; font-size: 11px;")
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        batch_bar.addWidget(self.btn_select_all)

        self.btn_bulk_approve = QPushButton("✅ Bulk Approve Selected")
        self.btn_bulk_approve.setCursor(Qt.PointingHandCursor)
        self.btn_bulk_approve.setFixedHeight(30)
        self.btn_bulk_approve.setStyleSheet("background-color: #16A34A; color: white; border: none; border-radius: 5px; padding: 4px 14px; font-weight: bold; font-size: 11px;")
        self.btn_bulk_approve.clicked.connect(self._do_bulk_approve)
        batch_bar.addWidget(self.btn_bulk_approve)

        self.btn_bulk_reject = QPushButton("❌ Bulk Reject Selected")
        self.btn_bulk_reject.setCursor(Qt.PointingHandCursor)
        self.btn_bulk_reject.setFixedHeight(30)
        self.btn_bulk_reject.setStyleSheet("background-color: #DC2626; color: white; border: none; border-radius: 5px; padding: 4px 14px; font-weight: bold; font-size: 11px;")
        self.btn_bulk_reject.clicked.connect(self._do_bulk_reject)
        batch_bar.addWidget(self.btn_bulk_reject)

        batch_bar.addStretch()

        self.btn_review_selected = QPushButton("🔍 Review Details")
        self.btn_review_selected.setCursor(Qt.PointingHandCursor)
        self.btn_review_selected.setFixedHeight(30)
        self.btn_review_selected.setStyleSheet("background-color: #2563EB; color: white; border: none; border-radius: 5px; padding: 4px 16px; font-weight: bold; font-size: 11px;")
        self.btn_review_selected.clicked.connect(self._open_selected_review)
        batch_bar.addWidget(self.btn_review_selected)

        main_layout.addLayout(batch_bar)

        # 4. Requests Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Select", "Req ID", "Employee", "Department", "Field Name",
            "Current Value", "Requested Value", "Reason", "Proof", "Requested On", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
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
            "QTableWidget { border: 1.5px solid #CBD5E1; border-radius: 8px; background-color: #FFFFFF; gridline-color: #E2E8F0; } "
            "QTableWidget::item { padding: 4px 8px; color: #0F172A; font-size: 11px; }"
        )
        self.table.doubleClicked.connect(self._open_selected_review)
        main_layout.addWidget(self.table, stretch=1)

    def load_requests(self):
        """Fetches requests matching current filter settings and populates table."""
        status = self.cmb_status.currentText()
        dept_id = self.cmb_dept.currentData()
        field_name = self.cmb_field.currentData()
        search = self.txt_search.text().strip()

        try:
            reqs = profile_change_service.change_repo.get_all_requests(
                status=status,
                department_id=dept_id,
                field_name=field_name,
                search_term=search,
            )
        except Exception as exc:
            logger.warning(f"Error fetching requests: {exc}")
            reqs = []

        self.cached_requests = reqs
        pending_total = profile_change_service.change_repo.get_pending_count()
        self.lbl_pending_badge.setText(f"{pending_total} Pending")

        self.table.setRowCount(len(reqs))
        for row_idx, r in enumerate(reqs):
            # Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setCheckState(Qt.Unchecked)
            chk_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, chk_item)

            # Req ID
            id_item = QTableWidgetItem(f"#{r.get('id', '')}")
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 1, id_item)

            # Employee
            emp_str = f"{r.get('employee_name', '')} ({r.get('employee_code', '')})"
            self.table.setItem(row_idx, 2, QTableWidgetItem(emp_str))

            # Department
            dept_str = r.get("department_code") or r.get("department_name") or "MCA"
            dept_item = QTableWidgetItem(dept_str)
            dept_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, dept_item)

            # Field Name
            field_lbl = get_field_label(r.get("field_name", ""))
            self.table.setItem(row_idx, 4, QTableWidgetItem(field_lbl))

            # Current Value (Masked)
            old_masked = mask_sensitive_value(r.get("old_value"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(old_masked))

            # Requested Value (Masked)
            new_masked = mask_sensitive_value(r.get("new_value"))
            new_item = QTableWidgetItem(new_masked)
            new_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 6, new_item)

            # Reason
            self.table.setItem(row_idx, 7, QTableWidgetItem(r.get("reason", "")))

            # Proof
            proof_str = "📄 Attached" if r.get("proof_path") else "-"
            proof_item = QTableWidgetItem(proof_str)
            proof_item.setTextAlignment(Qt.AlignCenter)
            if r.get("proof_path"):
                proof_item.setForeground(QColor("#2563EB"))
            self.table.setItem(row_idx, 8, proof_item)

            # Requested On
            date_str = str(r.get("requested_at", ""))[:16]
            self.table.setItem(row_idx, 9, QTableWidgetItem(date_str))

            # Status Pill
            st = str(r.get("status", "PENDING")).upper()
            status_item = QTableWidgetItem(st)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if st == "PENDING":
                status_item.setBackground(QColor("#FEF3C7"))
                status_item.setForeground(QColor("#B45309"))
            elif st == "APPROVED":
                status_item.setBackground(QColor("#DCFCE7"))
                status_item.setForeground(QColor("#166534"))
            elif st == "REJECTED":
                status_item.setBackground(QColor("#FEE2E2"))
                status_item.setForeground(QColor("#991B1B"))
            else:
                status_item.setBackground(QColor("#F1F5F9"))
                status_item.setForeground(QColor("#64748B"))
            self.table.setItem(row_idx, 10, status_item)

    def _get_selected_request_ids(self) -> List[int]:
        """Returns list of request IDs corresponding to checked rows."""
        ids = []
        for r_idx in range(self.table.rowCount()):
            chk = self.table.item(r_idx, 0)
            if chk and chk.checkState() == Qt.Checked:
                req = self.cached_requests[r_idx]
                ids.append(req["id"])
        return ids

    def _toggle_select_all(self):
        """Toggles check state of all visible rows."""
        any_unchecked = False
        for r_idx in range(self.table.rowCount()):
            chk = self.table.item(r_idx, 0)
            if chk and chk.checkState() != Qt.Checked:
                any_unchecked = True
                break

        target_state = Qt.Checked if any_unchecked else Qt.Unchecked
        for r_idx in range(self.table.rowCount()):
            chk = self.table.item(r_idx, 0)
            if chk:
                chk.setCheckState(target_state)

    def _open_selected_review(self):
        """Opens review dialog for the currently selected row."""
        sel_row = self.table.currentRow()
        if sel_row < 0 or sel_row >= len(self.cached_requests):
            QMessageBox.information(self, "Select Row", "Please select a request row to review.")
            return

        req = self.cached_requests[sel_row]
        dlg = ProfileRequestReviewDialog(parent=self, request_data=req, reviewer_session=auth_service.current_user)
        dlg.decision_made.connect(self._on_decision_completed)
        dlg.exec()

    def _do_bulk_approve(self):
        """Executes bulk approval on all checked rows."""
        ids = self._get_selected_request_ids()
        if not ids:
            QMessageBox.warning(self, "No Rows Selected", "Please select at least one request row using the checkbox.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Bulk Approval",
            f"Are you sure you want to approve {len(ids)} selected profile change requests?\n\n"
            "This will apply all updates atomically to their respective faculty records.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        user = auth_service.current_user
        if not user:
            QMessageBox.warning(self, "Auth Required", "You must be authenticated as HR or Principal.")
            return

        res = profile_change_service.bulk_approve(reviewer_session=user, request_ids=ids)
        msg = f"Bulk Approval Finished.\n\nSuccessfully Approved: {res['approved_count']} of {res['total_requested']}"
        if res["skipped"]:
            msg += f"\nSkipped: {len(res['skipped'])} (Self-requests or rule conflicts)"
        QMessageBox.information(self, "Bulk Result", msg)
        self._on_decision_completed()

    def _do_bulk_reject(self):
        """Executes bulk rejection on all checked rows with mandatory remark."""
        ids = self._get_selected_request_ids()
        if not ids:
            QMessageBox.warning(self, "No Rows Selected", "Please select at least one request row using the checkbox.")
            return

        from PySide6.QtWidgets import QInputDialog
        remark, ok = QInputDialog.getText(
            self,
            "Bulk Rejection Remark",
            "Please enter a mandatory remark for rejecting the selected requests:"
        )
        if not ok or len(str(remark).strip()) < 4:
            QMessageBox.warning(self, "Remark Required", "A remark of at least 4 characters is required to reject requests.")
            return

        user = auth_service.current_user
        if not user:
            return

        res = profile_change_service.bulk_reject(reviewer_session=user, request_ids=ids, reviewer_remark=remark)
        QMessageBox.information(
            self,
            "Bulk Rejection Completed",
            f"Successfully Rejected: {res['rejected_count']} of {res['total_requested']}"
        )
        self._on_decision_completed()

    def _on_decision_completed(self):
        """Refreshes table and notifies system."""
        self.load_requests()
        self.requests_updated.emit()
        win = self.window()
        if win and hasattr(win, "update_session_ui") and win is not self:
            win.update_session_ui()
