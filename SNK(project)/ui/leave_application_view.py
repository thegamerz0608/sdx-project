"""
Leave Applications & Approvals View (PySide6)
Presents end-to-end leave submission forms, document attachment upload, live policy pre-checks, and HOD approval/rejection inbox tools.
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

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
    QGroupBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QHeaderView,
    QDialog,
    QFormLayout,
    QCheckBox,
    QTabWidget,
    QTextEdit,
    QFileDialog,
    QFrame,
    QScrollArea,
    QPlainTextEdit,
    QBoxLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from services.auth_service import auth_service
from services.department_service import department_service
from services.faculty_service import faculty_service
from services.leave_service import leave_service
from services.leave_workflow_service import leave_workflow_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("ui.leave_application_view")


class ReviewRemarksDialog(QDialog):
    """Modal dialog for HOD/Admin to enter review remarks when approving or rejecting a leave application."""

    def __init__(self, parent=None, app_info: dict = None, action: str = "APPROVE"):
        super().__init__(parent)
        self.app_info = app_info or {}
        self.action = action.upper()
        self.setWindowTitle(f"{self.action.capitalize()} Leave Application")
        self.setMinimumSize(480, 300)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        form = QFormLayout()

        lbl_code = QLabel(f"<b>{self.app_info.get('application_code', 'N/A')}</b>")
        form.addRow("Application Code:", lbl_code)

        lbl_fac = QLabel(
            f"<b>{self.app_info.get('faculty_name', 'N/A')}</b> "
            f"({self.app_info.get('employee_code', 'N/A')})"
        )
        form.addRow("Faculty:", lbl_fac)

        lbl_leave = QLabel(
            f"<b>{self.app_info.get('leave_type_code', 'CL')}</b> "
            f"({self.app_info.get('total_days', 1.0)} days: {self.app_info.get('from_date')} to {self.app_info.get('to_date')})"
        )
        form.addRow("Leave Request:", lbl_leave)

        # AI Prediction and Decision Recommendation Row
        ai_code = self.app_info.get("ai_predicted_code") or self.app_info.get("ai_predicted_type_code")
        ai_conf = self.app_info.get("ai_confidence")
        if ai_code:
            conf_str = f"{float(ai_conf) * 100:.1f}%" if ai_conf is not None else "N/A"
            lbl_ai = QLabel(
                f"<span style='background-color: #DCFCE7; color: #166534; font-weight: bold; padding: 2px 8px; border-radius: 4px;'>"
                f"{ai_code}</span> &nbsp;<b>Confidence:</b> {conf_str} (Pure-NumPy Classifier)"
            )
        else:
            lbl_ai = QLabel("<span style='color: #64748B;'>Standard Administrative Screening</span>")
        form.addRow("AI Screening Decision:", lbl_ai)

        self.txt_remarks = QTextEdit()
        self.txt_remarks.setPlaceholderText(
            "Enter reviewer remarks..." + (" (Required for rejection)" if self.action == "REJECT" else " (Optional)")
        )
        form.addRow("HOD Remarks:", self.txt_remarks)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_color = "#2e7d32" if self.action == "APPROVE" else "#c62828"
        btn_action = QPushButton(f"Confirm {self.action.capitalize()}")
        btn_action.setStyleSheet(f"background-color: {btn_color}; color: white; font-weight: bold;")
        btn_action.clicked.connect(self.accept)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_action)
        layout.addLayout(btn_layout)

    def get_remarks(self) -> str:
        return self.txt_remarks.toPlainText().strip()


class LeaveApplicationView(QWidget):
    """PySide6 View managing leave application submission, policy pre-checks, and HOD approval inbox."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_departments()
        self.load_faculty_list()
        self.load_substitute_candidates()
        self.load_applications()
        self.combo_fac.currentIndexChanged.connect(lambda: self.load_substitute_candidates())
        self.txt_from.textChanged.connect(lambda text: self.txt_alt_date.setText(text))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "apply_grid_layout"):
            if self.width() < 1100:
                if self.apply_grid_layout.direction() != QBoxLayout.Direction.TopToBottom:
                    self.apply_grid_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            else:
                if self.apply_grid_layout.direction() != QBoxLayout.Direction.LeftToRight:
                    self.apply_grid_layout.setDirection(QBoxLayout.Direction.LeftToRight)

    def _create_form_label(self, text: str) -> QLabel:
        """Helper to create standardized 190px form row labels."""
        lbl = QLabel(text)
        lbl.setFixedWidth(190)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-weight: 600; color: #334155; font-size: 13px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Apply for Leave
        self.tab_apply = QWidget()
        self._build_apply_tab(self.tab_apply)
        self.sub_tabs.addTab(self.tab_apply, "Apply for Leave")

        # Sub-Tab 2: Applications & Approval Inbox (Stray underscore / mnemonic removed)
        self.tab_inbox = QWidget()
        self._build_inbox_tab(self.tab_inbox)
        self.sub_tabs.addTab(self.tab_inbox, "Applications / Approval Inbox")

        main_layout.addWidget(self.sub_tabs)

    def _build_apply_tab(self, parent_widget: QWidget):
        # Outer layout: wraps the entire tab page in a natural QScrollArea
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 2-column grid layout (1.3fr left form, 1fr right pre-check with 24px gap)
        # Responsive: switches cleanly to TopToBottom on window width < 1100px
        self.apply_grid_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, content_widget)
        self.apply_grid_layout.setContentsMargins(16, 16, 16, 20)
        self.apply_grid_layout.setSpacing(24)
        self.apply_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # -------------------------------------------------------------
        # Left Column: Leave Application Form Card
        # -------------------------------------------------------------
        self.form_card = QFrame()
        self.form_card.setObjectName("leaveFormCard")
        self.form_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.form_card.setMinimumWidth(0)
        self.form_card.setStyleSheet(
            "#leaveFormCard {"
            "  background-color: #FFFFFF;"
            "  border: 1px solid #E2E8F0;"
            "  border-radius: 10px;"
            "}"
        )
        form_card_layout = QVBoxLayout(self.form_card)
        form_card_layout.setContentsMargins(20, 20, 20, 22)
        form_card_layout.setSpacing(16)

        # Clean section header with thin 1px bottom border (no dark box / artifacts)
        form_header = QLabel("Leave Application Form")
        form_header.setWordWrap(True)
        form_header.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #0F172A; "
            "padding-bottom: 12px; border-bottom: 1px solid #E2E8F0;"
        )
        form_card_layout.addWidget(form_header)

        form_layout = QFormLayout()
        form_layout.setSpacing(16)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.combo_fac = QComboBox()
        self.combo_fac.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_fac.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_fac.setMinimumContentsLength(15)
        form_layout.addRow(self._create_form_label("Faculty Member:"), self.combo_fac)

        self.combo_type = QComboBox()
        self.combo_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_type.setMinimumContentsLength(8)
        self.combo_type.addItems(["CL", "EL", "ML", "SCL", "AVL", "OD"])
        form_layout.addRow(self._create_form_label("Leave Type:"), self.combo_type)

        today_str = date.today().strftime("%Y-%m-%d")
        fut_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

        self.txt_from = QLineEdit(today_str)
        self.txt_from.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form_layout.addRow(self._create_form_label("From Date (YYYY-MM-DD):"), self.txt_from)

        self.txt_to = QLineEdit(fut_str)
        self.txt_to.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form_layout.addRow(self._create_form_label("To Date (YYYY-MM-DD):"), self.txt_to)

        self.chk_half = QCheckBox("Half-Day Request (0.5 Day)")
        self.chk_half.setStyleSheet(
            "QCheckBox { font-size: 13px; color: #334155; font-weight: 500; } "
            "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1.5px solid #CBD5E1; background: #FFFFFF; } "
            "QCheckBox::indicator:checked { background: #2563EB; border-color: #2563EB; }"
        )
        form_layout.addRow(self._create_form_label("Duration Option:"), self.chk_half)

        self.txt_reason = QTextEdit()
        self.txt_reason.setPlaceholderText("Provide detailed reason for leave request (min 5 chars)...")
        self.txt_reason.setMinimumHeight(110)
        self.txt_reason.setStyleSheet(
            "QTextEdit {"
            "  background-color: #FFFFFF;"
            "  color: #0F172A;"
            "  border: 1px solid #CBD5E1;"
            "  border-radius: 8px;"
            "  padding: 10px;"
            "  font-family: 'Segoe UI';"
            "  font-size: 13px;"
            "}"
            "QTextEdit:focus { border: 1.5px solid #2563EB; }"
        )
        form_layout.addRow(self._create_form_label("Reason:"), self.txt_reason)

        # AI Intent Screening & Confidence Gating Pill Badge
        self.lbl_ai_prediction = QLabel("AI Screening: Type your reason above for real-time leave category prediction...")
        self.lbl_ai_prediction.setFont(QFont("Segoe UI", 9))
        self.lbl_ai_prediction.setStyleSheet(
            "background-color: #EFF6FF; color: #1E40AF; padding: 10px 14px; border-radius: 8px; border: 1px dashed #93C5FD; font-size: 13px;"
        )
        self.lbl_ai_prediction.setWordWrap(True)
        self.lbl_ai_prediction.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        form_layout.addRow(self._create_form_label("AI Category Intent:"), self.lbl_ai_prediction)

        # Debounced Timer for Zero UI Stutter during typing
        self._last_ai_pred_cat = None
        self._last_ai_confidence = None
        self._ai_timer = QTimer(self)
        self._ai_timer.setSingleShot(True)
        self._ai_timer.setInterval(300)
        self._ai_timer.timeout.connect(self._run_live_nlp_inference)
        self.txt_reason.textChanged.connect(self._on_reason_text_changed)

        # Integrated Alternate Arrangement (Substitute Faculty Duty) Card
        self.alt_card = QFrame()
        self.alt_card.setObjectName("altArrangementCard")
        self.alt_card.setStyleSheet(
            "#altArrangementCard {"
            "  background-color: #F8FAFC;"
            "  border: 1px solid #E2E8F0;"
            "  border-radius: 8px;"
            "}"
        )
        alt_card_layout = QVBoxLayout(self.alt_card)
        alt_card_layout.setContentsMargins(14, 14, 14, 14)
        alt_card_layout.setSpacing(14)

        alt_header = QLabel("Alternate Arrangement (Substitute Faculty Duty)")
        alt_header.setWordWrap(True)
        alt_header.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #1E3A8A; "
            "padding-bottom: 8px; border-bottom: 1px solid #E2E8F0;"
        )
        alt_card_layout.addWidget(alt_header)

        alt_layout = QFormLayout()
        alt_layout.setSpacing(14)
        alt_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        alt_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.combo_substitute = QComboBox()
        self.combo_substitute.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_substitute.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_substitute.setMinimumContentsLength(18)
        alt_layout.addRow(self._create_form_label("Substitute Faculty:"), self.combo_substitute)

        self.txt_alt_date = QLineEdit(today_str)
        self.txt_alt_date.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        alt_layout.addRow(self._create_form_label("Duty Date (YYYY-MM-DD):"), self.txt_alt_date)

        self.txt_alt_time = QLineEdit("10:00 AM - 11:00 AM")
        self.txt_alt_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        alt_layout.addRow(self._create_form_label("Time Slot / Period:"), self.txt_alt_time)

        self.txt_alt_place = QLineEdit("Room 304, Academic Block")
        self.txt_alt_place.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        alt_layout.addRow(self._create_form_label("Classroom Location / Place:"), self.txt_alt_place)

        self.txt_alt_work = QPlainTextEdit()
        self.txt_alt_work.setPlainText("Conduct scheduled lecture/lab & mark student attendance")
        self.txt_alt_work.setMinimumHeight(70)
        self.txt_alt_work.setMaximumHeight(100)
        self.txt_alt_work.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #FFFFFF;"
            "  color: #0F172A;"
            "  border: 1px solid #CBD5E1;"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "  font-family: 'Segoe UI';"
            "  font-size: 13px;"
            "}"
            "QPlainTextEdit:focus { border: 1.5px solid #2563EB; }"
        )
        # Compatibility property for callers/tests that might invoke .text()
        self.txt_alt_work.text = lambda: self.txt_alt_work.toPlainText()
        alt_layout.addRow(self._create_form_label("Work Description:"), self.txt_alt_work)

        alt_card_layout.addLayout(alt_layout)
        form_layout.addRow(self.alt_card)

        # File Attachment Row
        file_lay = QHBoxLayout()
        file_lay.setSpacing(8)
        self.txt_doc = QLineEdit()
        self.txt_doc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.txt_doc.setPlaceholderText("Select supporting document (.pdf, .jpg, .png)...")

        btn_browse = QPushButton("Browse...")
        btn_browse.setStyleSheet(
            "QPushButton {"
            "  background-color: #F1F5F9;"
            "  color: #334155;"
            "  border: 1px solid #CBD5E1;"
            "  padding: 6px 14px;"
            "  border-radius: 6px;"
            "  font-weight: 500;"
            "  font-size: 13px;"
            "}"
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        btn_browse.clicked.connect(self.on_browse_file)
        file_lay.addWidget(self.txt_doc)
        file_lay.addWidget(btn_browse)
        form_layout.addRow(self._create_form_label("Document Attachment:"), file_lay)

        # Action Buttons Row
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(12)
        self.btn_precheck = QPushButton("Pre-Check Policy")
        self.btn_precheck.setStyleSheet(
            "QPushButton {"
            "  background-color: #F1F5F9;"
            "  color: #1E293B;"
            "  border: 1px solid #CBD5E1;"
            "  font-weight: 600;"
            "  padding: 10px 20px;"
            "  border-radius: 8px;"
            "  font-size: 13px;"
            "  min-height: 22px;"
            "}"
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.btn_precheck.clicked.connect(self.on_precheck_click)

        self.btn_submit = QPushButton("Submit Leave Application")
        self.btn_submit.setStyleSheet(
            "QPushButton {"
            "  background-color: #2563EB;"
            "  color: white;"
            "  font-weight: 600;"
            "  padding: 10px 24px;"
            "  border-radius: 8px;"
            "  font-size: 14px;"
            "  border: none;"
            "  min-height: 22px;"
            "}"
            "QPushButton:hover { background-color: #1D4ED8; }"
            "QPushButton:pressed { background-color: #1E40AF; }"
        )
        self.btn_submit.clicked.connect(self.on_submit_click)

        btn_lay.addWidget(self.btn_precheck)
        btn_lay.addWidget(self.btn_submit)
        btn_lay.addStretch()

        form_card_layout.addLayout(form_layout)
        form_card_layout.addLayout(btn_lay)
        self.apply_grid_layout.addWidget(self.form_card, 13)

        # -------------------------------------------------------------
        # Right Column: Policy Pre-Check Feedback Panel Card
        # -------------------------------------------------------------
        self.pre_card = QFrame()
        self.pre_card.setObjectName("precheckCard")
        self.pre_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pre_card.setMinimumWidth(0)
        self.pre_card.setStyleSheet(
            "#precheckCard {"
            "  background-color: #F8FAFC;"
            "  border: 1px solid #E2E8F0;"
            "  border-radius: 10px;"
            "  min-height: 160px;"
            "}"
        )
        pre_card_layout = QVBoxLayout(self.pre_card)
        pre_card_layout.setContentsMargins(20, 20, 20, 22)
        pre_card_layout.setSpacing(14)

        pre_header = QLabel("Policy Compliance: Sandwich Rule Pre-Check")
        pre_header.setWordWrap(True)
        pre_header.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #0F172A; "
            "padding-bottom: 12px; border-bottom: 1px solid #E2E8F0;"
        )
        pre_card_layout.addWidget(pre_header)

        self.lbl_pre_badge = QLabel("PRE-CHECK: NOT EVALUATED")
        self.lbl_pre_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_pre_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pre_badge.setStyleSheet(
            "background-color: #E2E8F0; color: #475569; font-weight: 700; padding: 8px 14px; border-radius: 6px; font-size: 12px;"
        )
        pre_card_layout.addWidget(self.lbl_pre_badge)

        self.txt_pre_details = QTextEdit()
        self.txt_pre_details.setReadOnly(True)
        self.txt_pre_details.setStyleSheet(
            "QTextEdit {"
            "  background-color: #FFFFFF;"
            "  color: #0F172A;"
            "  border: 1px solid #CBD5E1;"
            "  border-radius: 8px;"
            "  padding: 14px;"
            "  font-family: 'Segoe UI';"
            "  font-size: 13px;"
            "  min-height: 220px;"
            "}"
        )
        empty_state_html = (
            "<div style='text-align: center; color: #64748B; padding: 36px 12px;'>"
            "<span style='font-size: 32px;'>📋</span><br><br>"
            "<span style='font-size: 14px; font-weight: 600; color: #334155;'>Select dates and a leave type to run the Sandwich Rule check.</span><br>"
            "<span style='font-size: 12px; color: #94A3B8; margin-top: 6px; display: block;'>Live compliance verification ensures zero payroll or leave balance discrepancies before final submission.</span>"
            "</div>"
        )
        self.txt_pre_details.setHtml(empty_state_html)
        pre_card_layout.addWidget(self.txt_pre_details)

        self.apply_grid_layout.addWidget(self.pre_card, 10)

        page_scroll.setWidget(content_widget)
        tab_layout.addWidget(page_scroll)

    def _build_inbox_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # Filter Panel with two responsive rows
        filter_group = QGroupBox("Filter Inbox Applications")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(10)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(QLabel("<b>Status:</b>"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["ALL", "PENDING", "APPROVED", "REJECTED", "CANCELLED"])
        row1.addWidget(self.combo_status)

        row1.addWidget(QLabel("<b>Department:</b>"))
        self.combo_dept = QComboBox()
        self.combo_dept.setMinimumWidth(120)
        self.combo_dept.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_dept.setMinimumContentsLength(14)
        self.combo_dept.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row1.addWidget(self.combo_dept)

        self.btn_refresh_inbox = QPushButton("Refresh List")
        self.btn_refresh_inbox.clicked.connect(self.load_applications)
        row1.addWidget(self.btn_refresh_inbox)
        row1.addStretch()

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        # Action Buttons
        self.btn_approve = QPushButton("Approve...")
        self.btn_approve.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_approve.clicked.connect(self.on_approve_click)
        row2.addWidget(self.btn_approve)

        self.btn_reject = QPushButton("Reject...")
        self.btn_reject.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_reject.clicked.connect(self.on_reject_click)
        row2.addWidget(self.btn_reject)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.on_cancel_click)
        row2.addWidget(self.btn_cancel)
        row2.addStretch()

        filter_layout.addLayout(row1)
        filter_layout.addLayout(row2)
        tab_layout.addWidget(filter_group)

        # Table Group
        tbl_group = QGroupBox("Leave Applications Inbox")
        tbl_layout = QVBoxLayout(tbl_group)

        self.tbl_apps = QTableWidget()
        self.tbl_apps.setColumnCount(12)
        self.tbl_apps.setHorizontalHeaderLabels(
            [
                "ID",
                "Code",
                "Faculty Name",
                "Department",
                "Requested Type",
                "AI Screening",
                "From Date",
                "To Date",
                "Days",
                "Status",
                "Document",
                "Reviewer Remarks",
            ]
        )
        self.tbl_apps.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_apps.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_apps.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_apps.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_apps.verticalHeader().setDefaultSectionSize(40)
        self.tbl_apps.setAlternatingRowColors(True)

        tbl_layout.addWidget(self.tbl_apps)
        tab_layout.addWidget(tbl_group, stretch=1)

    def load_departments(self):
        self.combo_dept.clear()
        self.combo_dept.addItem("All Departments", None)
        try:
            depts = department_service.list_departments()
            for d in depts:
                self.combo_dept.addItem(f"{d['code']} - {d['name']}", d["id"])
        except Exception as exc:
            logger.warning(f"Failed to load departments in LeaveApplicationView: {exc}")

    def load_faculty_list(self):
        self.combo_fac.clear()
        try:
            session = auth_service.current_user
            faculty_list = faculty_service.list_faculty(session)
            for f in faculty_list:
                self.combo_fac.addItem(f"{f['employee_code']} - {f['full_name']}", f["id"])
        except Exception as exc:
            logger.warning(f"Failed to load faculty list: {exc}")
            self.combo_fac.addItem("F001 - Dr. Suresh Kumar", 1)
            self.combo_fac.addItem("F002 - Rahul Sharma", 2)

    def load_substitute_candidates(self):
        """Loads and ranks candidate substitute faculty members based on department and current workload."""
        current_fac_id = self.combo_fac.currentData() or 1
        self.combo_substitute.clear()

        try:
            from services.substitute_service import substitute_service
            from repositories.faculty_repository import faculty_repository

            # Get applicant's department
            dept_id = None
            fac = faculty_repository.get_by_id(current_fac_id)
            if fac:
                dept_id = fac.get("department_id")

            candidates = substitute_service.recommend_substitutes(
                original_faculty_id=current_fac_id,
                assignment_date=self.txt_from.text().strip() or date.today().strftime("%Y-%m-%d"),
                department_id=dept_id,
            )
            for c in candidates:
                rec_label = " (⭐ Recommended)" if c.get("rank") == 1 else ""
                label = f"{c['faculty_name']} ({c.get('department_code', 'Dept')}) - Load: {c.get('monthly_substitute_count', 0)} duties{rec_label}"
                self.combo_substitute.addItem(label, c["faculty_id"])

            if self.combo_substitute.count() == 0:
                self.combo_substitute.addItem("Dr. Suresh Kumar (MCA) - Load: 0 duties (⭐ Recommended)", 1)
        except Exception as exc:
            logger.debug(f"Substitute dropdown population fallback: {exc}")
            self.combo_substitute.addItem("Dr. Suresh Kumar (MCA) - Load: 0 duties (⭐ Recommended)", 1)
            self.combo_substitute.addItem("Priya Verma (MCA) - Load: 1 duty", 3)
            self.combo_substitute.addItem("Amit Patel (CSE) - Load: 0 duties", 4)

    def load_applications(self):
        """Loads and populates applications table based on status and department filters."""
        status_flt = self.combo_status.currentText()
        dept_id = self.combo_dept.currentData()
        session = auth_service.current_user

        try:
            apps = leave_workflow_service.list_applications(
                user_session=session, status_filter=status_flt, department_id=dept_id
            )

            self.tbl_apps.setRowCount(0)
            for row_idx, a in enumerate(apps):
                self.tbl_apps.insertRow(row_idx)

                item_id = QTableWidgetItem(str(a.get("id", "")))
                item_code = QTableWidgetItem(a.get("application_code", ""))
                item_name = QTableWidgetItem(a.get("faculty_name", ""))
                item_dept = QTableWidgetItem(a.get("department_code", ""))
                item_tcode = QTableWidgetItem(a.get("leave_type_code", ""))

                ai_code = a.get("ai_predicted_code") or a.get("ai_predicted_type_code")
                ai_conf = a.get("ai_confidence")
                if ai_code:
                    conf_pct_str = f"{float(ai_conf) * 100:.1f}%" if ai_conf is not None else "85.0%"
                    item_ai = QTableWidgetItem(f"{ai_code} ({conf_pct_str})")
                    if float(ai_conf or 0.85) >= 0.70:
                        item_ai.setForeground(QColor("#166534"))
                    else:
                        item_ai.setForeground(QColor("#B45309"))
                else:
                    item_ai = QTableWidgetItem("Standard")
                    item_ai.setForeground(QColor("#64748B"))
                item_ai.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                item_from = QTableWidgetItem(str(a.get("from_date", "")))
                item_to = QTableWidgetItem(str(a.get("to_date", "")))
                item_days = QTableWidgetItem(f"{float(a.get('total_days', 1.0)):.1f}")

                status_str = a.get("status", "PENDING")
                item_status = QTableWidgetItem(status_str)
                item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if status_str == "APPROVED":
                    item_status.setBackground(QColor("#d4edda"))
                    item_status.setForeground(QColor("#155724"))
                elif status_str == "PENDING":
                    item_status.setBackground(QColor("#fff3cd"))
                    item_status.setForeground(QColor("#856404"))
                elif status_str == "REJECTED":
                    item_status.setBackground(QColor("#f8d7da"))
                    item_status.setForeground(QColor("#721c24"))
                else:  # CANCELLED
                    item_status.setBackground(QColor("#e2e3e5"))
                    item_status.setForeground(QColor("#383d41"))

                doc_str = "Attached" if a.get("document_path") else "None"
                item_doc = QTableWidgetItem(doc_str)

                remarks_str = a.get("hod_remarks") or "-"
                item_remarks = QTableWidgetItem(remarks_str)

                self.tbl_apps.setItem(row_idx, 0, item_id)
                self.tbl_apps.setItem(row_idx, 1, item_code)
                self.tbl_apps.setItem(row_idx, 2, item_name)
                self.tbl_apps.setItem(row_idx, 3, item_dept)
                self.tbl_apps.setItem(row_idx, 4, item_tcode)
                self.tbl_apps.setItem(row_idx, 5, item_ai)
                self.tbl_apps.setItem(row_idx, 6, item_from)
                self.tbl_apps.setItem(row_idx, 7, item_to)
                self.tbl_apps.setItem(row_idx, 8, item_days)
                self.tbl_apps.setItem(row_idx, 9, item_status)
                self.tbl_apps.setItem(row_idx, 10, item_doc)
                self.tbl_apps.setItem(row_idx, 11, item_remarks)

        except Exception as exc:
            logger.error(f"Failed to load applications: {exc}")
            QMessageBox.warning(self, "Error", f"Could not load applications: {exc}")

    def on_browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Supporting Document", "", "Documents (*.pdf *.png *.jpg *.jpeg *.doc *.docx)"
        )
        if file_path:
            self.txt_doc.setText(file_path)

    def on_precheck_click(self):
        faculty_id = self.combo_fac.currentData() or 1
        tcode = self.combo_type.currentText()
        from_str = self.txt_from.text().strip()
        to_str = self.txt_to.text().strip()
        is_half = self.chk_half.isChecked()
        session = auth_service.current_user

        try:
            val_res = leave_service.validate_leave_application(
                user_session=session,
                faculty_id=faculty_id,
                leave_type_code=tcode,
                from_date_str=from_str,
                to_date_str=to_str,
                is_half_day=is_half,
            )

            is_valid = val_res.get("valid", False)
            has_errors = bool(val_res.get("errors"))
            has_warnings = bool(val_res.get("warnings"))

            if is_valid and not has_errors:
                if has_warnings:
                    self.lbl_pre_badge.setText("PRE-CHECK: WARNING")
                    self.lbl_pre_badge.setStyleSheet(
                        "background-color: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; font-weight: 700; padding: 8px 14px; border-radius: 6px; font-size: 12px;"
                    )
                else:
                    self.lbl_pre_badge.setText("PRE-CHECK: PASS / COMPLIANT")
                    self.lbl_pre_badge.setStyleSheet(
                        "background-color: #DCFCE7; color: #166534; border: 1px solid #86EFAC; font-weight: 700; padding: 8px 14px; border-radius: 6px; font-size: 12px;"
                    )
            else:
                self.lbl_pre_badge.setText("PRE-CHECK: VIOLATION")
                self.lbl_pre_badge.setStyleSheet(
                    "background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; font-weight: 700; padding: 8px 14px; border-radius: 6px; font-size: 12px;"
                )

            # Build structured HTML report
            lines = [
                "<div style='font-family: Segoe UI, sans-serif; font-size: 13px; line-height: 1.5; color: #0F172A;'>",
                "<table style='width: 100%; border-collapse: collapse; margin-bottom: 12px;'>",
                f"<tr style='border-bottom: 1px solid #F1F5F9;'><td style='padding: 6px 0; color: #64748B;'><b>Requested Days:</b></td><td style='text-align: right; font-weight: 600;'>{val_res['requested_days']}</td></tr>",
                f"<tr style='border-bottom: 1px solid #F1F5F9;'><td style='padding: 6px 0; color: #64748B;'><b>Sandwich Days:</b></td><td style='text-align: right; font-weight: 600;'>{val_res['sandwich_days']}</td></tr>",
                f"<tr style='border-bottom: 1px solid #F1F5F9;'><td style='padding: 6px 0; color: #64748B;'><b>Document Required:</b></td><td style='text-align: right; font-weight: 600;'>{'YES' if val_res['requires_document'] else 'NO'}</td></tr>",
                f"<tr style='border-bottom: 1px solid #F1F5F9;'><td style='padding: 6px 0; color: #64748B;'><b>Remaining Balance:</b></td><td style='text-align: right; font-weight: 600;'>{val_res['remaining_balance']} days</td></tr>",
                "</table>",
            ]

            warnings = val_res.get("warnings", [])
            if warnings:
                lines.append("<div style='margin-top: 10px; padding: 10px 12px; background-color: #FEF3C7; border: 1px solid #FDE68A; border-radius: 6px;'>")
                lines.append("<b style='color: #92400E;'>Policy Warnings:</b><ul style='margin: 4px 0 0 16px; padding: 0; color: #78350F;'>")
                for w in warnings:
                    lines.append(f"<li>{w}</li>")
                lines.append("</ul></div>")
            else:
                lines.append("<div style='color: #166534; font-size: 12px; margin-top: 6px;'>✓ No policy warnings detected.</div>")

            errors = val_res.get("errors", [])
            if errors:
                lines.append("<div style='margin-top: 10px; padding: 10px 12px; background-color: #FEE2E2; border: 1px solid #FCA5A5; border-radius: 6px;'>")
                lines.append("<b style='color: #991B1B;'>Rule Violations / Errors:</b><ul style='margin: 4px 0 0 16px; padding: 0; color: #7F1D1D;'>")
                for e in errors:
                    lines.append(f"<li>{e}</li>")
                lines.append("</ul></div>")
            else:
                lines.append("<div style='color: #166534; font-size: 12px; margin-top: 4px;'>✓ No rule violations found.</div>")

            lines.append("</div>")
            self.txt_pre_details.setHtml("".join(lines))

        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Pre-Check Error", str(err))

    def _on_reason_text_changed(self):
        """Debounces user keystrokes before triggering live pure-NumPy NLP leave classification."""
        if hasattr(self, "_ai_timer"):
            self._ai_timer.start(300)

    def _run_live_nlp_inference(self):
        """Executes real-time leave reason classification and updates AI recommendation badge with confidence gating."""
        reason_text = self.txt_reason.toPlainText().strip()
        if len(reason_text) < 5:
            self.lbl_ai_prediction.setText("AI Screening: Type your reason above for real-time leave category prediction...")
            self.lbl_ai_prediction.setStyleSheet(
                "background-color: #EFF6FF; color: #1E40AF; padding: 10px 14px; border-radius: 8px; border: 1px dashed #93C5FD; font-size: 13px;"
            )
            self._last_ai_pred_cat = None
            self._last_ai_confidence = None
            return

        try:
            from services.model_training_service import model_training_service
            from nlp.dataset_generator import LEAVE_CATEGORIES

            metadata = {
                "requested_days": 0.5 if self.chk_half.isChecked() else 1.0,
                "notice_period_days": 0.0,
                "has_medical_doc": bool(self.txt_doc.text().strip()),
                "is_sandwich_leave": False,
            }
            res = model_training_service.predict_leave_reason(reason_text, metadata)
            pred_cat = res.get("predicted_category", "CL")
            cat_name = LEAVE_CATEGORIES.get(pred_cat, res.get("category_name", pred_cat))
            conf = float(res.get("confidence_score", 0.0))
            conf_pct = res.get("confidence_percentage", f"{conf * 100:.1f}%")

            self._last_ai_pred_cat = pred_cat
            self._last_ai_confidence = conf

            if res.get("is_oov") or pred_cat == "UNCERTAIN":
                self.lbl_ai_prediction.setText(
                    f"⚠ AI Screening: Text is uninformative / out-of-vocabulary ({res.get('oov_reason', 'Uncertain')}) — Manual Selection Enforced"
                )
                self.lbl_ai_prediction.setStyleSheet(
                    "background-color: #FEF3C7; color: #92400E; font-weight: 600; padding: 10px 14px; border-radius: 8px; border: 1px solid #FDE68A; font-size: 13px;"
                )
            # Configurable Low Confidence Handling (70% threshold gating)
            elif conf >= 0.70:
                self.lbl_ai_prediction.setText(
                    f"✓ AI Predicted: {pred_cat} ({cat_name})  |  Confidence: {conf_pct} (High Confidence — Auto-Selected)"
                )
                self.lbl_ai_prediction.setStyleSheet(
                    "background-color: #DCFCE7; color: #166534; font-weight: 600; padding: 10px 14px; border-radius: 8px; border: 1px solid #86EFAC; font-size: 13px;"
                )
                # Auto-select high-confidence prediction in dropdown
                idx = self.combo_type.findText(pred_cat)
                if idx >= 0:
                    self.combo_type.setCurrentIndex(idx)
            else:
                self.lbl_ai_prediction.setText(
                    f"⚠ AI Suggestion: {pred_cat} ({cat_name})  |  Confidence: {conf_pct} (< 70% — Manual Selection Enforced)"
                )
                self.lbl_ai_prediction.setStyleSheet(
                    "background-color: #FEF3C7; color: #92400E; font-weight: 600; padding: 10px 14px; border-radius: 8px; border: 1px solid #FDE68A; font-size: 13px;"
                )
        except Exception as exc:
            logger.debug(f"Live NLP inference skipped: {exc}")

    def on_submit_click(self):
        faculty_id = self.combo_fac.currentData() or 1
        tcode = self.combo_type.currentText()
        from_str = self.txt_from.text().strip()
        to_str = self.txt_to.text().strip()
        is_half = self.chk_half.isChecked()
        reason = self.txt_reason.toPlainText().strip()
        doc_path = self.txt_doc.text().strip() or None
        session = auth_service.current_user

        # Integrated Alternate Arrangement parameters
        sub_id = self.combo_substitute.currentData()
        alt_date = self.txt_alt_date.text().strip() or from_str
        alt_time = self.txt_alt_time.text().strip() or "10:00 AM - 11:00 AM"
        alt_place = self.txt_alt_place.text().strip()
        alt_work = (
            self.txt_alt_work.toPlainText().strip()
            if hasattr(self.txt_alt_work, "toPlainText")
            else self.txt_alt_work.text().strip()
        )

        if not sub_id:
            QMessageBox.warning(self, "Alternate Arrangement Required", "Please select a Substitute Faculty member from the dropdown for duty coverage.")
            return

        if not alt_place or len(alt_place) < 2:
            QMessageBox.warning(self, "Alternate Arrangement Required", "Please enter the Classroom Location / Place for the substitute faculty.")
            return

        if not alt_work or len(alt_work) < 3:
            QMessageBox.warning(self, "Alternate Arrangement Required", "Please enter the Work Description for the substitute assignment.")
            return

        try:
            res = leave_workflow_service.submit_leave_application(
                user_session=session,
                faculty_id=faculty_id,
                requested_leave_type_code=tcode,
                from_date_str=from_str,
                to_date_str=to_str,
                reason=reason,
                is_half_day=is_half,
                document_path=doc_path,
                ai_predicted_type_code=getattr(self, "_last_ai_pred_cat", None),
                ai_confidence=getattr(self, "_last_ai_confidence", None),
                substitute_faculty_id=sub_id,
                alternate_date=alt_date,
                alternate_time=alt_time,
                alternate_place=alt_place,
                alternate_work_description=alt_work,
            )
            QMessageBox.information(
                self,
                "Submission Success",
                f"Leave application submitted successfully!\n"
                f"Application Code: {res.get('application_code')}\n"
                f"Alternate Arrangement linked to substitute faculty.\n"
                f"Workflow approval emails queued.",
            )
            self.txt_reason.clear()
            self.txt_doc.clear()
            self._last_ai_pred_cat = None
            self._last_ai_confidence = None
            if hasattr(self, "lbl_ai_prediction"):
                self.lbl_ai_prediction.setText("AI Screening: Type your reason above for real-time leave category prediction...")
                self.lbl_ai_prediction.setStyleSheet(
                    "background-color: #EFF6FF; color: #1E40AF; padding: 10px 14px; border-radius: 8px; border: 1px dashed #93C5FD; font-size: 13px;"
                )
            self.load_applications()
            self.sub_tabs.setCurrentIndex(1)
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Submission Failed", str(err))

    def _get_selected_app(self) -> tuple[Optional[dict], int]:
        selected_rows = self.tbl_apps.selectionModel().selectedRows()
        if not selected_rows:
            return None, -1
        row_idx = selected_rows[0].row()
        app_id = int(self.tbl_apps.item(row_idx, 0).text())
        app_code = self.tbl_apps.item(row_idx, 1).text()
        fac_name = self.tbl_apps.item(row_idx, 2).text()
        tcode = self.tbl_apps.item(row_idx, 4).text()
        from_d = self.tbl_apps.item(row_idx, 5).text()
        to_d = self.tbl_apps.item(row_idx, 6).text()
        days = float(self.tbl_apps.item(row_idx, 7).text())
        app_info = {
            "id": app_id,
            "application_code": app_code,
            "faculty_name": fac_name,
            "leave_type_code": tcode,
            "from_date": from_d,
            "to_date": to_d,
            "total_days": days,
        }
        return app_info, app_id

    def on_approve_click(self):
        selected_rows = self.tbl_apps.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Application", "Please select an application row in the inbox table first.")
            return

        row_idx = selected_rows[0].row()
        app_id = int(self.tbl_apps.item(row_idx, 0).text())
        app_info = {
            "id": app_id,
            "application_code": self.tbl_apps.item(row_idx, 1).text(),
            "faculty_name": self.tbl_apps.item(row_idx, 2).text(),
            "leave_type_code": self.tbl_apps.item(row_idx, 4).text(),
            "from_date": self.tbl_apps.item(row_idx, 5).text(),
            "to_date": self.tbl_apps.item(row_idx, 6).text(),
            "total_days": float(self.tbl_apps.item(row_idx, 7).text()),
        }

        dlg = ReviewRemarksDialog(self, app_info=app_info, action="APPROVE")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            remarks = dlg.get_remarks()
            try:
                session = auth_service.current_user
                res = leave_workflow_service.review_leave_application(
                    user_session=session, application_id=app_id, action="APPROVE", remarks=remarks
                )
                QMessageBox.information(self, "Approved", f"Application {res.get('application_code')} approved successfully!")
                self.load_applications()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Approval Error", str(err))

    def on_reject_click(self):
        selected_rows = self.tbl_apps.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Application", "Please select an application row in the inbox table first.")
            return

        row_idx = selected_rows[0].row()
        app_id = int(self.tbl_apps.item(row_idx, 0).text())
        app_info = {
            "id": app_id,
            "application_code": self.tbl_apps.item(row_idx, 1).text(),
            "faculty_name": self.tbl_apps.item(row_idx, 2).text(),
            "leave_type_code": self.tbl_apps.item(row_idx, 4).text(),
            "from_date": self.tbl_apps.item(row_idx, 5).text(),
            "to_date": self.tbl_apps.item(row_idx, 6).text(),
            "total_days": float(self.tbl_apps.item(row_idx, 7).text()),
        }

        dlg = ReviewRemarksDialog(self, app_info=app_info, action="REJECT")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            remarks = dlg.get_remarks()
            try:
                session = auth_service.current_user
                res = leave_workflow_service.review_leave_application(
                    user_session=session, application_id=app_id, action="REJECT", remarks=remarks
                )
                QMessageBox.information(self, "Rejected", f"Application {res.get('application_code')} rejected.")
                self.load_applications()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Rejection Error", str(err))

    def on_cancel_click(self):
        selected_rows = self.tbl_apps.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Application", "Please select an application row in the inbox table first.")
            return

        row_idx = selected_rows[0].row()
        app_id = int(self.tbl_apps.item(row_idx, 0).text())
        confirm = QMessageBox.question(
            self, "Confirm Cancel", f"Are you sure you want to cancel leave application #{app_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                session = auth_service.current_user
                leave_workflow_service.cancel_leave_application(session, app_id)
                QMessageBox.information(self, "Cancelled", "Leave application cancelled.")
                self.load_applications()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Cancel Error", str(err))
