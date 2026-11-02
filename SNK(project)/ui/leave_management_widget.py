"""
Multi-Stage Leave Review & Management Console (PySide6)
Provides dedicated HR and Principal dashboards for reviewing, approving, suspending,
modifying dates, and granting final executive sign-off on faculty leave applications.
"""
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QMessageBox,
    QGroupBox,
    QFrame,
    QDateEdit,
    QDoubleSpinBox,
    QTextEdit,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from services.leave_workflow_service import leave_workflow_service
from services.department_service import department_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger
from ui.empty_state import EmptyStateWidget
from ui.styles import style_table_cell_badge

logger = get_logger("ui.leave_management_widget")


class ModifyDatesDialog(QDialog):
    """HR Special Power Modal Dialog for Modifying Requested Leave Dates & Duration."""

    def __init__(self, application: dict, parent=None):
        super().__init__(parent)
        self.app = application
        self.setWindowTitle(f"HR Date Adjustment - {application.get('application_code')}")
        self.setMinimumSize(440, 360)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        info = QLabel(
            f"<b>Applicant:</b> {self.app.get('faculty_name')} ({self.app.get('employee_code')})<br>"
            f"<b>Leave Type:</b> {self.app.get('leave_type_name')} ({self.app.get('leave_type_code')})"
        )
        info.setStyleSheet("background-color: #EFF6FF; padding: 10px; border-radius: 8px;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        try:
            self.dt_from.setDate(QDate.fromString(str(self.app.get("from_date")), "yyyy-MM-dd"))
        except Exception:
            self.dt_from.setDate(QDate.currentDate())
        form.addRow("<b>Adjusted From Date:</b>", self.dt_from)

        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        try:
            self.dt_to.setDate(QDate.fromString(str(self.app.get("to_date")), "yyyy-MM-dd"))
        except Exception:
            self.dt_to.setDate(QDate.currentDate())
        form.addRow("<b>Adjusted To Date:</b>", self.dt_to)

        self.spin_days = QDoubleSpinBox()
        self.spin_days.setRange(0.5, 365.0)
        self.spin_days.setSingleStep(0.5)
        self.spin_days.setValue(float(self.app.get("total_days", 1.0)))
        form.addRow("<b>Adjusted Total Days:</b>", self.spin_days)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("HR reason for date modification...")
        form.addRow("<b>HR Note:</b>", self.txt_reason)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Save Adjusted Dates")
        btn_save.clicked.connect(self._handle_save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #F1F5F9; color: #475569;")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _handle_save(self):
        user = auth_service.current_user
        from_str = self.dt_from.date().toString("yyyy-MM-dd")
        to_str = self.dt_to.date().toString("yyyy-MM-dd")
        days = self.spin_days.value()
        remarks = self.txt_reason.text().strip() or "Dates adjusted by HR"

        try:
            leave_workflow_service.hr_review_application(
                user_session=user,
                application_id=self.app["id"],
                action="MODIFY",
                remarks=remarks,
                new_from_date=from_str,
                new_to_date=to_str,
                new_days=days,
            )
            QMessageBox.information(self, "Dates Modified", "Application dates adjusted successfully.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not modify dates: {exc}")


class LeaveManagementWidget(QWidget):
    """
    Dedicated Multi-Stage Leave Review Console for HR, Principal, and Admin.
    Enforces multi-stage state transitions with special HR modification powers.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_app = None
        self._init_ui()
        self.load_applications()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Title Banner
        banner = QFrame()
        banner.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #4F46E5); "
            "border-radius: 10px; padding: 14px;"
        )
        b_layout = QHBoxLayout(banner)
        v_title = QVBoxLayout()
        title = QLabel("⚖️ Multi-Stage Leave Review & Approval Console")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        subtitle = QLabel("Multi-Tier State Machine: PENDING_HOD ➔ PENDING_HR ➔ PENDING_PRINCIPAL ➔ APPROVED")
        subtitle.setStyleSheet("color: #C7D2FE; font-size: 11px;")
        v_title.addWidget(title)
        v_title.addWidget(subtitle)
        b_layout.addLayout(v_title)
        b_layout.addStretch()

        self.lbl_stage_badge = QLabel("STAGE GATEKEEPER")
        self.lbl_stage_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_stage_badge.setStyleSheet(
            "background-color: #312E81; color: #E0E7FF; padding: 6px 14px; border-radius: 8px;"
        )
        b_layout.addWidget(self.lbl_stage_badge)
        layout.addWidget(banner)

        # Toolbar Filter Controls
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        toolbar.addWidget(QLabel("<b>Review Stage / Status:</b>"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItem("All Applications", "ALL")
        self.cmb_status.addItem("Pending HR Review", "PENDING_HR")
        self.cmb_status.addItem("Pending Principal", "PENDING_PRINCIPAL")
        self.cmb_status.addItem("Suspended Applications", "SUSPENDED")
        self.cmb_status.addItem("Pending HOD", "PENDING")
        self.cmb_status.addItem("Approved", "APPROVED")
        self.cmb_status.addItem("Rejected", "REJECTED")
        self.cmb_status.setMinimumWidth(180)
        self.cmb_status.currentIndexChanged.connect(self.load_applications)
        toolbar.addWidget(self.cmb_status)

        toolbar.addWidget(QLabel("<b>Department:</b>"))
        self.cmb_dept = QComboBox()
        self.cmb_dept.addItem("-- All Departments --", None)
        for d in department_service.list_departments():
            self.cmb_dept.addItem(f"{d['name']} ({d['code']})", d["id"])
        self.cmb_dept.setMinimumWidth(160)
        self.cmb_dept.currentIndexChanged.connect(self.load_applications)
        toolbar.addWidget(self.cmb_dept)
        toolbar.addStretch(1)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.load_applications)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # Applications Data Grid
        self.tbl_apps = QTableWidget()
        self.tbl_apps.setColumnCount(11)
        self.tbl_apps.setHorizontalHeaderLabels([
            "Code", "Faculty Member", "Dept", "Leave Type", "From Date", "To Date", "Days",
            "HOD Status", "HR Status", "Principal Status", "Overall Status"
        ])
        header = self.tbl_apps.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_apps.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_apps.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_apps.setAlternatingRowColors(True)
        self.tbl_apps.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_apps.verticalHeader().setDefaultSectionSize(40)
        self.tbl_apps.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tbl_apps, stretch=1)

        # Empty State Placeholder
        self.empty_state = EmptyStateWidget(
            icon="⚖️",
            title="No Applications In This Stage",
            message="There are currently no leave requests awaiting action under this review filter.",
            action_text="Refresh Queue",
            action_callback=self.load_applications,
        )
        layout.addWidget(self.empty_state, stretch=1)
        self.empty_state.hide()

        # Action Control Panel
        action_card = QGroupBox("Workflow Decision Controls (Selected Application)")
        a_layout = QHBoxLayout(action_card)
        a_layout.setSpacing(10)

        self.lbl_selected_info = QLabel("No application selected.")
        self.lbl_selected_info.setStyleSheet("color: #64748B; font-weight: bold;")
        a_layout.addWidget(self.lbl_selected_info, stretch=1)

        # HR Action Buttons
        self.btn_hr_approve = QPushButton("✅ HR Approve & Forward")
        self.btn_hr_approve.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_hr_approve.clicked.connect(self._on_hr_approve)
        a_layout.addWidget(self.btn_hr_approve)

        self.btn_hr_suspend = QPushButton("⏸️ Suspend")
        self.btn_hr_suspend.setStyleSheet("background-color: #F59E0B; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_hr_suspend.clicked.connect(self._on_hr_suspend)
        a_layout.addWidget(self.btn_hr_suspend)

        self.btn_hr_modify = QPushButton("✏️ Modify Dates")
        self.btn_hr_modify.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_hr_modify.clicked.connect(self._on_hr_modify)
        a_layout.addWidget(self.btn_hr_modify)

        # Principal Action Button
        self.btn_prin_approve = QPushButton("🎓 Principal Sign-Off")
        self.btn_prin_approve.setStyleSheet("background-color: #B91C1C; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_prin_approve.clicked.connect(self._on_principal_approve)
        a_layout.addWidget(self.btn_prin_approve)

        # Rejection button
        self.btn_reject = QPushButton("❌ Reject")
        self.btn_reject.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 7px 14px;")
        self.btn_reject.clicked.connect(self._on_reject)
        a_layout.addWidget(self.btn_reject)

        layout.addWidget(action_card)
        self._update_action_state(None)

    def load_applications(self):
        """Fetches and displays applications according to active filters."""
        user = auth_service.current_user
        status_filter = self.cmb_status.currentData()
        dept_id = self.cmb_dept.currentData()

        # Update stage badge based on active user role
        if user:
            self.lbl_stage_badge.setText(f"ACTIVE ROLE: {user.role}")

        apps = leave_workflow_service.list_applications(
            user_session=user,
            department_id=dept_id,
            status_filter=status_filter if status_filter != "ALL" else None,
        )

        self.loaded_apps = apps
        self.tbl_apps.setRowCount(0)

        if len(apps) == 0:
            self.tbl_apps.hide()
            self.empty_state.show()
        else:
            self.empty_state.hide()
            self.tbl_apps.show()

        for row, a in enumerate(apps):
            self.tbl_apps.insertRow(row)

            c0 = QTableWidgetItem(a.get("application_code", ""))
            c0.setData(Qt.UserRole, a)
            c0.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.tbl_apps.setItem(row, 0, c0)

            c1 = QTableWidgetItem(f"{a.get('faculty_name', '')} ({a.get('employee_code', '')})")
            self.tbl_apps.setItem(row, 1, c1)

            c2 = QTableWidgetItem(a.get("department_code", "MCA"))
            self.tbl_apps.setItem(row, 2, c2)

            c3 = QTableWidgetItem(a.get("leave_type_code", "CL"))
            self.tbl_apps.setItem(row, 3, c3)

            c4 = QTableWidgetItem(str(a.get("from_date", "")))
            self.tbl_apps.setItem(row, 4, c4)

            c5 = QTableWidgetItem(str(a.get("to_date", "")))
            self.tbl_apps.setItem(row, 5, c5)

            c6 = QTableWidgetItem(str(a.get("total_days", 1.0)))
            self.tbl_apps.setItem(row, 6, c6)

            # Stage statuses
            hod_st = a.get("hod_status") or ("APPROVED" if a.get("status") in ["PENDING_HR", "PENDING_PRINCIPAL", "APPROVED"] else "PENDING")
            hr_st = a.get("hr_status") or ("APPROVED" if a.get("status") in ["PENDING_PRINCIPAL", "APPROVED"] else ("SUSPENDED" if a.get("status") == "SUSPENDED" else "PENDING"))
            prin_st = a.get("principal_status") or ("APPROVED" if a.get("status") == "APPROVED" else "PENDING")

            c7 = QTableWidgetItem(hod_st)
            style_table_cell_badge(c7, hod_st)
            self.tbl_apps.setItem(row, 7, c7)

            c8 = QTableWidgetItem(hr_st)
            style_table_cell_badge(c8, hr_st)
            self.tbl_apps.setItem(row, 8, c8)

            c9 = QTableWidgetItem(prin_st)
            style_table_cell_badge(c9, prin_st)
            self.tbl_apps.setItem(row, 9, c9)

            status_val = a.get("status", "PENDING")
            c10 = QTableWidgetItem(status_val)
            style_table_cell_badge(c10, status_val)
            self.tbl_apps.setItem(row, 10, c10)

        self._update_action_state(None)

    def _on_selection_changed(self):
        sel_items = self.tbl_apps.selectedItems()
        if not sel_items:
            self._update_action_state(None)
            return

        row = sel_items[0].row()
        item = self.tbl_apps.item(row, 0)
        app_data = item.data(Qt.UserRole)
        self._update_action_state(app_data)

    def _update_action_state(self, app_data: dict = None):
        self.selected_app = app_data
        user = auth_service.current_user
        if not app_data:
            self.lbl_selected_info.setText("Select an application from the table to review.")
            self.btn_hr_approve.setEnabled(False)
            self.btn_hr_suspend.setEnabled(False)
            self.btn_hr_modify.setEnabled(False)
            self.btn_prin_approve.setEnabled(False)
            self.btn_reject.setEnabled(False)
            return

        self.lbl_selected_info.setText(
            f"Selected: {app_data.get('application_code')} - {app_data.get('faculty_name')} ({app_data.get('total_days')}d) | Status: {app_data.get('status')}"
        )

        is_admin = user and user.is_admin()
        is_hr = user and (user.is_hr() or is_admin)
        is_prin = user and (user.is_principal() or is_admin)
        st = app_data.get("status", "")

        # HR can approve if in PENDING or PENDING_HR or SUSPENDED
        can_hr_act = is_hr and st in ["PENDING", "PENDING_HR", "SUSPENDED"]
        self.btn_hr_approve.setEnabled(can_hr_act)
        self.btn_hr_suspend.setEnabled(can_hr_act and st != "SUSPENDED")
        self.btn_hr_modify.setEnabled(is_hr and st not in ["APPROVED", "REJECTED"])

        # Principal can approve if in PENDING_PRINCIPAL (or Admin can sign off)
        self.btn_prin_approve.setEnabled(is_prin and st in ["PENDING_PRINCIPAL", "PENDING_HR", "PENDING"])
        self.btn_reject.setEnabled((is_hr or is_prin) and st not in ["APPROVED", "REJECTED"])

    def _on_hr_approve(self):
        if not self.selected_app: return
        user = auth_service.current_user
        try:
            leave_workflow_service.hr_review_application(
                user_session=user,
                application_id=self.selected_app["id"],
                action="APPROVE",
                remarks="Verified and approved by HR. Forwarded to Principal.",
            )
            QMessageBox.information(self, "HR Approved", "Leave request verified and advanced to Principal for final sign-off.")
            self.load_applications()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to process HR approval: {exc}")

    def _on_hr_suspend(self):
        if not self.selected_app: return
        user = auth_service.current_user
        try:
            leave_workflow_service.hr_review_application(
                user_session=user,
                application_id=self.selected_app["id"],
                action="SUSPEND",
                remarks="Application suspended by HR pending administrative review.",
            )
            QMessageBox.information(self, "Application Suspended", "Leave request suspended.")
            self.load_applications()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not suspend application: {exc}")

    def _on_hr_modify(self):
        if not self.selected_app: return
        dlg = ModifyDatesDialog(self.selected_app, self)
        if dlg.exec() == QDialog.Accepted:
            self.load_applications()

    def _on_principal_approve(self):
        if not self.selected_app: return
        user = auth_service.current_user
        try:
            leave_workflow_service.principal_review_application(
                user_session=user,
                application_id=self.selected_app["id"],
                action="APPROVE",
                remarks="Executive approval granted by Principal.",
            )
            QMessageBox.information(self, "Executive Approval Granted", "Leave request granted final executive approval.")
            self.load_applications()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to execute Principal approval: {exc}")

    def _on_reject(self):
        if not self.selected_app: return
        user = auth_service.current_user
        try:
            if user.is_principal():
                leave_workflow_service.principal_review_application(
                    user_session=user,
                    application_id=self.selected_app["id"],
                    action="REJECT",
                    remarks="Rejected by Principal.",
                )
            else:
                leave_workflow_service.hr_review_application(
                    user_session=user,
                    application_id=self.selected_app["id"],
                    action="REJECT",
                    remarks="Rejected by HR.",
                )
            QMessageBox.information(self, "Application Rejected", "Leave application rejected.")
            self.load_applications()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not reject application: {exc}")
