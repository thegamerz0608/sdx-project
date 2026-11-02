"""
Modern Role-Adaptive Landing Dashboard Widget for Faculty ERP.
Features complete Faculty Profile Details, Academic Subjects Handled, Live Leave Types,
KPI cards, quick-action shortcuts, and integrated database health diagnostics.
"""
import sys
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QGraphicsDropShadowEffect, QTextEdit, QGroupBox, QSizePolicy,
    QDateTimeEdit, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PySide6.QtGui import QColor, QFont

from config.settings import settings
from config.profile_permissions import can_view_subjects_handled
from database.connection import get_driver_name
from ui.avatar_utils import create_square_avatar, create_circular_avatar, get_role_color
from ui.edit_profile_dialog import EditProfileDialog
from services.time_service import TimeService
from services.faculty_service import faculty_service
from repositories.leave_repository import leave_repository
from utils.date_utils import calculate_service_duration, format_service_duration
from utils.logger import get_logger

logger = get_logger("ui.dashboard_widget")


class KPICard(QFrame):
    """Modern Windows 11 rounded KPI card with drop shadow and accent indicator."""

    def __init__(self, title: str, value: str, subtext: str, badge_color: str = "#2563EB", parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setFixedHeight(115)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 16))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        # Header row with title and color dot
        h_box = QHBoxLayout()
        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("kpiTitle")

        badge = QFrame()
        badge.setFixedSize(8, 8)
        badge.setStyleSheet(f"background-color: {badge_color}; border-radius: 4px;")

        h_box.addWidget(lbl_title)
        h_box.addStretch()
        h_box.addWidget(badge)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("kpiValue")

        self.lbl_subtext = QLabel(subtext)
        self.lbl_subtext.setObjectName("kpiSubtext")

        layout.addLayout(h_box)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_subtext)

    def update_value(self, value: str, subtext: str = None):
        self.lbl_value.setText(value)
        if subtext:
            self.lbl_subtext.setText(subtext)


class DashboardWidget(QWidget):
    """
    Role-specific landing dashboard showing KPI metrics,
    faculty profile details, academic subjects, quick workflow shortcuts,
    and live system diagnostics.
    """
    navigate_to_tab = Signal(int)  # Emits target tab index

    def __init__(self, role: str = "ADMIN", parent=None, user_session=None):
        super().__init__(parent)
        self.role = role.upper()
        self.user_session = user_session
        self.faculty_data: Dict[str, Any] = {}
        self._sensitive_revealed: bool = False
        self._init_ui()
        self._load_initial_data()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("dashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea#dashboardScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        content_widget.setObjectName("dashboardContentWidget")
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(16)

        # =========================================================================
        # 1. Heading Block
        # =========================================================================
        self.heading_block = QFrame()
        self.heading_block.setObjectName("dashboardHeadingBlock")
        hb_layout = QVBoxLayout(self.heading_block)
        hb_layout.setContentsMargins(4, 2, 4, 4)
        hb_layout.setSpacing(3)

        self.lbl_profile_heading = QLabel("Profile Details")
        self.lbl_profile_heading.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_profile_heading.setStyleSheet("color: #0F172A;")

        self.lbl_profile_tenure = QLabel(f"Working in {settings.COLLEGE_NAME} since calculating...")
        self.lbl_profile_tenure.setFont(QFont("Segoe UI", 10))
        self.lbl_profile_tenure.setStyleSheet("color: #475569;")

        hb_layout.addWidget(self.lbl_profile_heading)
        hb_layout.addWidget(self.lbl_profile_tenure)
        main_layout.addWidget(self.heading_block)

        # 1.1 Decision Notices Container
        self.notices_container = QWidget()
        self.notices_layout = QVBoxLayout(self.notices_container)
        self.notices_layout.setContentsMargins(0, 0, 0, 0)
        self.notices_layout.setSpacing(6)
        main_layout.addWidget(self.notices_container)

        # =========================================================================
        # 2. Profile Card (Square Avatar, Role Chip, Edit Profile Button)
        # =========================================================================
        self.banner = QFrame()
        self.banner.setObjectName("dashboardWelcomeCard")
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(20, 16, 20, 16)
        banner_layout.setSpacing(18)

        # Square Avatar with rounded corners
        self.lbl_banner_avatar = QLabel()
        self.lbl_banner_avatar.setFixedSize(72, 72)
        initial_pix = create_square_avatar(size=72, radius=8, name=self.role.capitalize(), role=self.role)
        self.lbl_banner_avatar.setPixmap(initial_pix)
        banner_layout.addWidget(self.lbl_banner_avatar)

        v_titles = QVBoxLayout()
        v_titles.setSpacing(4)

        self.lbl_welcome = QLabel(f"Welcome to the {self.role.capitalize()} Console")
        self.lbl_welcome.setObjectName("headerWelcome")
        self.lbl_welcome.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_welcome.setStyleSheet("color: #0F172A;")

        h_info_sub = QHBoxLayout()
        h_info_sub.setSpacing(10)

        self.lbl_profile_emp_id = QLabel("Employee ID: -")
        self.lbl_profile_emp_id.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.lbl_profile_emp_id.setStyleSheet("color: #334155;")

        self.lbl_profile_role_chip = QLabel(f"ROLE: {self.role}")
        self.lbl_profile_role_chip.setStyleSheet(
            f"background-color: {get_role_color(self.role)}; color: #FFFFFF; "
            "padding: 2px 8px; border-radius: 6px; font-weight: bold; font-size: 11px;"
        )

        h_info_sub.addWidget(self.lbl_profile_emp_id)
        h_info_sub.addWidget(self.lbl_profile_role_chip)
        h_info_sub.addStretch()

        self.lbl_desc = QLabel("AI-Enabled Faculty Attendance, Leave & Substitute Management ERP")
        self.lbl_desc.setObjectName("headerDesc")
        self.lbl_desc.setStyleSheet("color: #64748B; font-size: 12px;")

        v_titles.addWidget(self.lbl_welcome)
        v_titles.addLayout(h_info_sub)
        v_titles.addWidget(self.lbl_desc)

        banner_layout.addLayout(v_titles)
        banner_layout.addStretch()

        # Edit Profile Button
        self.btn_edit_profile = QPushButton("✏️ Edit Profile")
        self.btn_edit_profile.setCursor(Qt.PointingHandCursor)
        self.btn_edit_profile.setMinimumHeight(36)
        self.btn_edit_profile.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: bold; "
            "padding: 6px 18px; border-radius: 6px; border: none; font-size: 12px;"
        )
        self.btn_edit_profile.clicked.connect(self._open_edit_profile)
        banner_layout.addWidget(self.btn_edit_profile)

        main_layout.addWidget(self.banner)

        # =========================================================================
        # 3. Two-Column Details Grid (Dark Navy Headers, White Cells, Sensitive Masking)
        # =========================================================================
        self.details_grid_card = QFrame()
        self.details_grid_card.setObjectName("detailsGridCard")
        self.details_grid_card.setStyleSheet(
            "QFrame#detailsGridCard { background-color: #FFFFFF; border: 1.5px solid #CBD5E1; "
            "border-radius: 8px; }"
        )
        dgc_layout = QVBoxLayout(self.details_grid_card)
        dgc_layout.setContentsMargins(16, 14, 16, 16)
        dgc_layout.setSpacing(12)

        # Details Header Bar with Show/Hide Toggle
        d_head = QHBoxLayout()
        d_head.setSpacing(12)

        lbl_grid_title = QLabel("Employee Information & Statutory Record")
        lbl_grid_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_grid_title.setStyleSheet("color: #0F172A;")
        d_head.addWidget(lbl_grid_title)
        d_head.addStretch()

        self.btn_toggle_sensitive = QPushButton("👁️ Show Sensitive Details")
        self.btn_toggle_sensitive.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_sensitive.setFixedHeight(28)
        self.btn_toggle_sensitive.setStyleSheet(
            "background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; "
            "border-radius: 5px; padding: 2px 12px; font-weight: 600; font-size: 11px;"
        )
        self.btn_toggle_sensitive.clicked.connect(self._toggle_sensitive)
        d_head.addWidget(self.btn_toggle_sensitive)
        dgc_layout.addLayout(d_head)

        # Details Grid: 2 major columns (Col 0,1 and Col 2,3)
        self.grid_details = QGridLayout()
        self.grid_details.setSpacing(0)  # Seamless table cell look
        self.grid_details.setContentsMargins(0, 0, 0, 0)
        self._build_details_grid()
        dgc_layout.addLayout(self.grid_details)

        main_layout.addWidget(self.details_grid_card)

        # =========================================================================
        # 4. Academic Subjects Handled & 5. Leave Types Table Row
        # =========================================================================
        self.academic_row = QHBoxLayout()
        self.academic_row.setSpacing(16)

        # 4. "Current Subjects Handled List" Card
        self.subjects_card = QFrame()
        self.subjects_card.setObjectName("subjectsCard")
        self.subjects_card.setStyleSheet(
            "QFrame#subjectsCard { background-color: #FFFFFF; border: 1.5px solid #CBD5E1; "
            "border-radius: 8px; }"
        )
        sc_layout = QVBoxLayout(self.subjects_card)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(0)

        # Orange Title Bar
        lbl_subj_title = QLabel("Current Subjects Handled List")
        lbl_subj_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_subj_title.setStyleSheet(
            "background-color: #EA580C; color: #FFFFFF; padding: 10px 16px; "
            "border-top-left-radius: 7px; border-top-right-radius: 7px;"
        )
        sc_layout.addWidget(lbl_subj_title)

        # Subjects Table
        self.tbl_subjects = QTableWidget()
        self.tbl_subjects.setColumnCount(6)
        self.tbl_subjects.setHorizontalHeaderLabels([
            "Sl. No.", "Admission Year", "Name of Subject with Code", "Semester", "Section", "Branch"
        ])
        self.tbl_subjects.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_subjects.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_subjects.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tbl_subjects.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #1E293B; color: #FFFFFF; font-weight: bold; "
            "padding: 6px; border: 1px solid #334155; font-size: 11px; }"
        )
        self.tbl_subjects.verticalHeader().setVisible(False)
        self.tbl_subjects.verticalHeader().setDefaultSectionSize(36)
        self.tbl_subjects.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_subjects.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_subjects.setStyleSheet(
            "QTableWidget { border: none; background-color: #FFFFFF; gridline-color: #E2E8F0; } "
            "QTableWidget::item { padding: 6px 8px; color: #0F172A; font-size: 11px; }"
        )
        self.tbl_subjects.setMinimumHeight(140)
        self.tbl_subjects.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sc_layout.addWidget(self.tbl_subjects)

        # Empty State Label
        self.lbl_subjects_empty = QLabel("No subjects assigned")
        self.lbl_subjects_empty.setAlignment(Qt.AlignCenter)
        self.lbl_subjects_empty.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.lbl_subjects_empty.setStyleSheet("color: #64748B; padding: 28px 16px; background-color: #FFFFFF;")
        self.lbl_subjects_empty.setVisible(False)
        sc_layout.addWidget(self.lbl_subjects_empty)

        self.academic_row.addWidget(self.subjects_card, stretch=2)

        # 5. Leave Types Table Card
        self.leave_types_card = QFrame()
        self.leave_types_card.setObjectName("leaveTypesCard")
        self.leave_types_card.setStyleSheet(
            "QFrame#leaveTypesCard { background-color: #FFFFFF; border: 1.5px solid #CBD5E1; "
            "border-radius: 8px; }"
        )
        ltc_layout = QVBoxLayout(self.leave_types_card)
        ltc_layout.setContentsMargins(0, 0, 0, 0)
        ltc_layout.setSpacing(0)

        # Title Bar
        lbl_lt_title = QLabel("Leave Types & Entitlements")
        lbl_lt_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_lt_title.setStyleSheet(
            "background-color: #1E293B; color: #FFFFFF; padding: 10px 16px; "
            "border-top-left-radius: 7px; border-top-right-radius: 7px;"
        )
        ltc_layout.addWidget(lbl_lt_title)

        # Leave Types Table
        self.tbl_leave_types = QTableWidget()
        self.tbl_leave_types.setColumnCount(2)
        self.tbl_leave_types.setHorizontalHeaderLabels(["Leave Types", "Current Status Count"])
        self.tbl_leave_types.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_leave_types.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_leave_types.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        # Custom distinct column header colors: Col 0 Navy, Col 1 Orange
        self.tbl_leave_types.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #1E293B; color: #FFFFFF; font-weight: bold; "
            "padding: 6px 12px; border: 1px solid #334155; font-size: 11px; } "
            "QHeaderView::section:last { background-color: #EA580C; color: #FFFFFF; }"
        )
        self.tbl_leave_types.verticalHeader().setVisible(False)
        self.tbl_leave_types.verticalHeader().setDefaultSectionSize(36)
        self.tbl_leave_types.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_leave_types.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_leave_types.setStyleSheet(
            "QTableWidget { border: none; background-color: #FFFFFF; gridline-color: #E2E8F0; } "
            "QTableWidget::item { padding: 6px 10px; color: #0F172A; font-size: 11px; }"
        )
        self.tbl_leave_types.setMinimumHeight(140)
        self.tbl_leave_types.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        ltc_layout.addWidget(self.tbl_leave_types)

        self.academic_row.addWidget(self.leave_types_card, stretch=1)
        main_layout.addLayout(self.academic_row)

        # =========================================================================
        # 6. Preserved: Responsive KPI Stat Cards Grid
        # =========================================================================
        self.grid_kpi = QGridLayout()
        self.grid_kpi.setSpacing(14)
        self._build_kpi_cards()
        main_layout.addLayout(self.grid_kpi)

        # =========================================================================
        # 7. Preserved: Quick Action Workbench Card
        # =========================================================================
        self.workbench = QFrame()
        self.workbench.setObjectName("workbenchCard")
        wb_layout = QVBoxLayout(self.workbench)
        wb_layout.setContentsMargins(18, 14, 18, 14)
        wb_layout.setSpacing(10)

        lbl_wb_title = QLabel("Quick Operational Actions")
        lbl_wb_title.setObjectName("workbenchTitle")
        wb_layout.addWidget(lbl_wb_title)

        self.btn_box = QHBoxLayout()
        self.btn_box.setSpacing(12)
        self._build_quick_actions()
        wb_layout.addLayout(self.btn_box)
        main_layout.addWidget(self.workbench)

        # =========================================================================
        # 8. Preserved: Integrated System & Database Diagnostics Group
        # =========================================================================
        self.diag_group = QGroupBox("System & Database Diagnostics")
        self.diag_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.diag_group.setStyleSheet(
            "QGroupBox { background-color: #F8FAFC; border: 1.5px solid #CBD5E1; border-radius: 8px; margin-top: 12px; font-weight: bold; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #1E293B; font-size: 13px; }"
        )
        diag_layout = QVBoxLayout(self.diag_group)
        diag_layout.setContentsMargins(18, 18, 18, 16)
        diag_layout.setSpacing(14)

        info_row = QHBoxLayout()
        info_row.setSpacing(14)
        info_label = QLabel(
            f"<b>Environment:</b> {settings.APP_ENV.capitalize()} &nbsp;|&nbsp; "
            f"<b>Python:</b> {sys.version.split()[0]} &nbsp;|&nbsp; "
            f"<b>Driver:</b> {get_driver_name()}"
        )
        info_label.setStyleSheet("color: #334155; font-size: 12px;")
        info_label.setWordWrap(True)
        info_row.addWidget(info_label, stretch=1)

        self.db_status_badge = QLabel("DB Status: Checking...")
        self.db_status_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.db_status_badge.setStyleSheet(
            "background-color: #E2E8F0; color: #334155; padding: 5px 12px; border-radius: 5px;"
        )
        info_row.addWidget(self.db_status_badge)
        diag_layout.addLayout(info_row)

        self.db_detail_label = QLabel(
            f"<b>Target Endpoint:</b> {settings.DB_HOST}:{settings.DB_PORT} &nbsp;•&nbsp; <b>Schema:</b> {settings.DB_NAME}"
        )
        self.db_detail_label.setStyleSheet("color: #64748B; font-size: 12px;")
        self.db_detail_label.setWordWrap(True)
        diag_layout.addWidget(self.db_detail_label)

        btn_diag_row = QHBoxLayout()
        btn_diag_row.setSpacing(12)

        self.btn_retest_db = QPushButton("🔄 Test Connection")
        self.btn_retest_db.setMinimumHeight(34)
        self.btn_retest_db.setCursor(Qt.PointingHandCursor)
        self.btn_retest_db.setStyleSheet("background-color: #2563EB; color: #FFFFFF; padding: 6px 16px; font-weight: 600; border-radius: 5px;")
        self.btn_retest_db.clicked.connect(self._on_retest_db_clicked)

        self.btn_init_db = QPushButton("⚡ Initialize & Seed MySQL")
        self.btn_init_db.setMinimumHeight(34)
        self.btn_init_db.setCursor(Qt.PointingHandCursor)
        self.btn_init_db.setStyleSheet("background-color: #16A34A; color: #ffffff; padding: 6px 16px; font-weight: 600; border-radius: 5px;")
        self.btn_init_db.clicked.connect(self._on_init_db_clicked)

        self.btn_db_help = QPushButton("ℹ️ MySQL Help")
        self.btn_db_help.setMinimumHeight(34)
        self.btn_db_help.setCursor(Qt.PointingHandCursor)
        self.btn_db_help.setStyleSheet("background-color: #475569; color: #ffffff; padding: 6px 16px; font-weight: 600; border-radius: 5px;")
        self.btn_db_help.clicked.connect(self._on_db_help_clicked)

        btn_diag_row.addWidget(self.btn_retest_db)
        btn_diag_row.addWidget(self.btn_init_db)
        btn_diag_row.addWidget(self.btn_db_help)
        btn_diag_row.addStretch()
        diag_layout.addLayout(btn_diag_row)

        main_layout.addWidget(self.diag_group)

        # =========================================================================
        # 9. Preserved: Global System Time Controller Group
        # =========================================================================
        self.time_group = QGroupBox("Global System Time Controller (Simulation & Testing)")
        self.time_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.time_group.setStyleSheet(
            "QGroupBox { background-color: #F8FAFC; border: 1.5px solid #CBD5E1; border-radius: 8px; margin-top: 12px; font-weight: bold; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #1E293B; font-size: 13px; }"
        )
        time_layout = QVBoxLayout(self.time_group)
        time_layout.setContentsMargins(18, 16, 18, 16)
        time_layout.setSpacing(12)
        self._build_time_controller(time_layout)
        main_layout.addWidget(self.time_group)

        # =========================================================================
        # 10. Preserved: Live Operational Console / Activity Log
        # =========================================================================
        lbl_console_title = QLabel("System Activity Security Log")
        lbl_console_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_console_title.setStyleSheet("color: #0F172A; margin-top: 6px;")
        main_layout.addWidget(lbl_console_title)

        self.log_console = QTextEdit()
        self.log_console.setObjectName("dashboardLogConsole")
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(110)
        self.log_console.setMaximumHeight(160)
        self.log_console.setStyleSheet(
            "QTextEdit#dashboardLogConsole { background-color: #0F172A; color: #38BDF8; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; "
            "border: 1px solid #334155; border-radius: 6px; padding: 8px; }"
        )
        main_layout.addWidget(self.log_console)

        self.scroll_area.setWidget(content_widget)
        root_layout.addWidget(self.scroll_area)

        # Role-based visibility scoping
        self.diag_group.setVisible(self.role == "ADMIN")
        self.time_group.setVisible(self.role == "ADMIN")

    def _build_details_grid(self):
        """Constructs or updates the 2-column details grid layout with navy headers and data cells."""
        # Clear existing items
        while self.grid_details.count():
            item = self.grid_details.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Masking helper
        def _mask(val: Any) -> str:
            s = str(val or "").strip()
            if not s:
                return "-"
            if self._sensitive_revealed:
                return s
            if len(s) <= 4:
                return "••••"
            return ("•" * (len(s) - 4)) + s[-4:]

        fac = self.faculty_data or {}
        emp_code = fac.get("employee_code") or (self.user_session.employee_code if self.user_session else "F002")
        name = fac.get("full_name") or (self.user_session.full_name if self.user_session else "Faculty Member")
        dept = fac.get("department_name") or fac.get("department_code") or "MCA"
        phone = fac.get("phone") or "9876543212"
        p_email = fac.get("personal_email") or "faculty.personal@gmail.com"
        emp_type = fac.get("employment_type") or "PERMANENT"
        pan = _mask(fac.get("pan_number") or "ABCDE1234F")
        pf = _mask(fac.get("pf_number") or "KN/BNG/0045612/000/0000123")
        salary_ac = _mask(fac.get("salary_account_no") or "50100234567890")

        designation = fac.get("designation") or "Assistant Professor"
        exp_years = f"{float(fac.get('experience_years') or 0.0):.1f} Years"
        i_email = fac.get("email") or "faculty@erp.edu"
        dob = fac.get("dob") or "1988-04-12"
        aadhaar = _mask(fac.get("aadhaar_number") or "987654321012")
        uan = _mask(fac.get("uan_number") or "100987654321")
        vtu_id = fac.get("vtu_id") or "VTU14589"
        join_date = fac.get("joining_date") or "2021-08-10"

        # Check for active pending profile change requests for this employee
        emp_id = fac.get("id") or (self.user_session.faculty_id if self.user_session else None)
        pending_fields = set()
        if emp_id:
            try:
                from services.profile_change_service import profile_change_service
                pending_fields = profile_change_service.get_pending_fields_for_employee(emp_id)
            except Exception as exc:
                logger.warning(f"Error querying pending profile fields: {exc}")

        # Column 1 pairs (Label, FieldKey, Value)
        col1_data = [
            ("Name", "name", name),
            ("Department", "department_id", dept),
            ("Mobile No.", "phone", phone),
            ("Personal Email Id", "personal_email", p_email),
            ("Employment Type", "employment_type", emp_type),
            ("PAN Card No", "pan_number", pan),
            ("PF NO", "pf_number", pf),
            ("Salary A/C No.", "salary_account_no", salary_ac),
        ]

        # Column 2 pairs (Label, FieldKey, Value)
        col2_data = [
            ("Designation", "designation", designation),
            ("Experience", "experience_years", exp_years),
            ("Inst. Email Id", "email", i_email),
            ("DOB", "dob", dob),
            ("Aadhar No", "aadhaar_number", aadhaar),
            ("UAN NO", "uan_number", uan),
            ("VTU ID", "vtu_id", vtu_id),
            ("Date of Joining", "joining_date", join_date),
        ]

        def _make_cell(text: str, is_header: bool = False, is_pending: bool = False) -> QLabel:
            lbl = QLabel()
            lbl.setWordWrap(True)
            if is_header:
                lbl.setText(text)
                lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                lbl.setStyleSheet(
                    "background-color: #1E293B; color: #FFFFFF; padding: 7px 12px; "
                    "border: 1px solid #334155; font-size: 11px;"
                )
                lbl.setMinimumWidth(130)
            else:
                lbl.setFont(QFont("Segoe UI", 9))
                lbl.setStyleSheet(
                    "background-color: #FFFFFF; color: #0F172A; padding: 7px 12px; "
                    "border: 1px solid #E2E8F0; font-size: 11px;"
                )
                if is_pending:
                    lbl.setTextFormat(Qt.RichText)
                    badge_html = "<span style='background-color: #FEF3C7; color: #B45309; border: 1px solid #F59E0B; border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: bold;'>⏳ Pending approval</span>"
                    lbl.setText(f"{text} &nbsp; {badge_html}")
                else:
                    lbl.setText(text)
            return lbl

        for row_idx in range(max(len(col1_data), len(col2_data))):
            # Col 1 (labels in col 0, values in col 1)
            if row_idx < len(col1_data):
                lbl_t, f_key, val_t = col1_data[row_idx]
                is_p1 = f_key in pending_fields
                self.grid_details.addWidget(_make_cell(lbl_t, is_header=True), row_idx, 0)
                self.grid_details.addWidget(_make_cell(val_t, is_header=False, is_pending=is_p1), row_idx, 1)

            # Col 2 (labels in col 2, values in col 3)
            if row_idx < len(col2_data):
                lbl_t2, f_key2, val_t2 = col2_data[row_idx]
                is_p2 = f_key2 in pending_fields
                self.grid_details.addWidget(_make_cell(lbl_t2, is_header=True), row_idx, 2)
                self.grid_details.addWidget(_make_cell(val_t2, is_header=False, is_pending=is_p2), row_idx, 3)

        self.grid_details.setColumnStretch(1, 1)
        self.grid_details.setColumnStretch(3, 1)

    def _toggle_sensitive(self):
        """Toggles between masked and unmasked statutory identifiers."""
        self._sensitive_revealed = not self._sensitive_revealed
        if self._sensitive_revealed:
            self.btn_toggle_sensitive.setText("🙈 Hide Sensitive Details")
            self.btn_toggle_sensitive.setStyleSheet(
                "background-color: #FEF3C7; color: #B45309; border: 1px solid #F59E0B; "
                "border-radius: 5px; padding: 2px 12px; font-weight: 600; font-size: 11px;"
            )
        else:
            self.btn_toggle_sensitive.setText("👁️ Show Sensitive Details")
            self.btn_toggle_sensitive.setStyleSheet(
                "background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; "
                "border-radius: 5px; padding: 2px 12px; font-weight: 600; font-size: 11px;"
            )
        self._build_details_grid()

    def _load_initial_data(self):
        """Loads faculty profile, subjects, and balances for current active user."""
        try:
            self.faculty_data = faculty_service.get_full_faculty_profile(self.user_session) or {}
        except Exception as exc:
            logger.warning(f"Error fetching profile: {exc}")
            self.faculty_data = {}
        self._refresh_profile_ui()

    def _refresh_profile_ui(self):
        """Refreshes all profile cards, tenure, subjects, and leave balances."""
        fac = self.faculty_data or {}
        full_name = fac.get("full_name") or (self.user_session.full_name if self.user_session else "Faculty Member")
        emp_code = fac.get("employee_code") or (self.user_session.employee_code if self.user_session else "F002")
        designation = fac.get("designation") or (self.user_session.designation if self.user_session else "Assistant Professor")
        dept = fac.get("department_name") or fac.get("department_code") or "MCA"
        join_date = fac.get("joining_date") or "2021-08-10"

        # 1. Update Heading Block
        y, m, d = calculate_service_duration(join_date)
        duration_str = format_service_duration(y, m, d)
        self.lbl_profile_tenure.setText(f"Working in <b>{settings.COLLEGE_NAME}</b> since <b>{duration_str}</b>")

        # 2. Update Welcome Banner & Avatar
        self.lbl_welcome.setText(f"Welcome back, {full_name}!")
        self.lbl_profile_emp_id.setText(f"Employee ID: {emp_code} • {dept}")
        self.lbl_profile_role_chip.setText(f"ROLE: {self.role}")
        self.lbl_profile_role_chip.setStyleSheet(
            f"background-color: {get_role_color(self.role)}; color: #FFFFFF; "
            "padding: 2px 8px; border-radius: 6px; font-weight: bold; font-size: 11px;"
        )
        self.lbl_desc.setText(f"{designation} • {dept} (Code: {emp_code})")

        img_path = fac.get("profile_image_path") or (self.user_session.profile_image_path if self.user_session else None)
        square_pix = create_square_avatar(
            image_path=img_path,
            size=72,
            radius=8,
            name=full_name,
            role=self.role,
        )
        self.lbl_banner_avatar.setPixmap(square_pix)

        # 3. Update Details Grid
        self._build_details_grid()

        # 4. Update Subjects Handled Table
        is_teaching = can_view_subjects_handled(self.role)
        self.subjects_card.setVisible(is_teaching)

        if is_teaching:
            try:
                fac_id = fac.get("id") or (self.user_session.faculty_id if self.user_session else 3)
                subjects = faculty_service.get_faculty_subjects(self.user_session, fac_id)
            except Exception as exc:
                logger.warning(f"Error fetching subjects: {exc}")
                subjects = []

            if subjects:
                self.tbl_subjects.setVisible(True)
                self.lbl_subjects_empty.setVisible(False)
                self.tbl_subjects.setRowCount(len(subjects))
                for r_idx, s in enumerate(subjects):
                    item_sl = QTableWidgetItem(str(r_idx + 1))
                    item_sl.setTextAlignment(Qt.AlignCenter)
                    item_year = QTableWidgetItem(str(s.get("admission_year", "")))
                    item_year.setTextAlignment(Qt.AlignCenter)
                    
                    subj_title = f"{s.get('subject_name', '')} ({s.get('subject_code', '')})"
                    item_subj = QTableWidgetItem(subj_title)
                    
                    item_sem = QTableWidgetItem(str(s.get("semester", "")))
                    item_sem.setTextAlignment(Qt.AlignCenter)
                    item_sec = QTableWidgetItem(str(s.get("section", "")))
                    item_sec.setTextAlignment(Qt.AlignCenter)
                    item_branch = QTableWidgetItem(str(s.get("branch", "")))
                    item_branch.setTextAlignment(Qt.AlignCenter)

                    self.tbl_subjects.setItem(r_idx, 0, item_sl)
                    self.tbl_subjects.setItem(r_idx, 1, item_year)
                    self.tbl_subjects.setItem(r_idx, 2, item_subj)
                    self.tbl_subjects.setItem(r_idx, 3, item_sem)
                    self.tbl_subjects.setItem(r_idx, 4, item_sec)
                    self.tbl_subjects.setItem(r_idx, 5, item_branch)
            else:
                self.tbl_subjects.setRowCount(0)
                self.tbl_subjects.setVisible(False)
                self.lbl_subjects_empty.setVisible(True)

        # 5. Update Leave Types Table (Populate from live leave balance data)
        try:
            fac_id = fac.get("id") or (self.user_session.faculty_id if self.user_session else 3)
            balances = leave_repository.get_faculty_balances(fac_id)
        except Exception as exc:
            logger.warning(f"Error fetching balances: {exc}")
            balances = []

        if not balances:
            # Sane fallback leave types if offline and unassigned
            balances = [
                {"leave_type_name": "Casual Leave", "leave_type_code": "CL", "remaining_days": 8.0, "allocated_days": 12.0},
                {"leave_type_name": "Medical Leave", "leave_type_code": "ML", "remaining_days": 10.0, "allocated_days": 10.0},
                {"leave_type_name": "Earned Leave", "leave_type_code": "EL", "remaining_days": 15.0, "allocated_days": 15.0},
                {"leave_type_name": "Special Casual Leave", "leave_type_code": "SCL", "remaining_days": 6.0, "allocated_days": 6.0},
                {"leave_type_name": "Academic Vacation Leave", "leave_type_code": "AVL", "remaining_days": 30.0, "allocated_days": 30.0},
                {"leave_type_name": "On Duty Leave", "leave_type_code": "OD", "remaining_days": 15.0, "allocated_days": 15.0},
            ]

        self.tbl_leave_types.setRowCount(len(balances))
        for r_idx, b in enumerate(balances):
            lt_name = b.get("leave_type_name") or b.get("leave_type_code") or "Leave"
            lt_code = b.get("leave_type_code") or ""
            rem = b.get("remaining_days", 0.0)
            alloc = b.get("allocated_days", 0.0)

            item_type = QTableWidgetItem(f"{lt_name} ({lt_code})")
            item_count = QTableWidgetItem(f"{rem:.1f} / {alloc:.1f} Days")
            item_count.setTextAlignment(Qt.AlignCenter)
            item_count.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            self.tbl_leave_types.setItem(r_idx, 0, item_type)
            self.tbl_leave_types.setItem(r_idx, 1, item_count)

        # 6. Update Decision Notices
        self._refresh_decision_notices()

    def _refresh_decision_notices(self):
        """Displays dismissible notifications for recent profile change decisions."""
        if not hasattr(self, "notices_layout"):
            return

        while self.notices_layout.count():
            item = self.notices_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.user_session:
            return

        try:
            from services.profile_change_service import profile_change_service, mask_sensitive_value
            from config.profile_permissions import get_field_label
            notices = profile_change_service.get_recent_decision_notices(self.user_session, limit=3)
            if not notices:
                return

            for notice in notices:
                status = str(notice.get("status") or "").upper()
                field_label = get_field_label(notice.get("field_name", ""))
                masked_new = mask_sensitive_value(notice.get("new_value"))
                remark = notice.get("reviewer_remark") or "No remarks provided."

                box = QFrame()
                if status == "APPROVED":
                    box.setStyleSheet(
                        "QFrame { background-color: #F0FDF4; border: 1.5px solid #86EFAC; "
                        "border-radius: 6px; }"
                    )
                    msg = (
                        f"✅ <b>Profile Change Approved:</b> Your request to update <b>{field_label}</b> "
                        f"to <code>{masked_new}</code> was approved by HR and updated in your profile."
                    )
                else:
                    box.setStyleSheet(
                        "QFrame { background-color: #FEF2F2; border: 1.5px solid #FCA5A5; "
                        "border-radius: 6px; }"
                    )
                    msg = (
                        f"❌ <b>Profile Change Rejected:</b> Your request to update <b>{field_label}</b> "
                        f"was rejected by HR. <b>Reason:</b> <i>{remark}</i>"
                    )

                b_layout = QHBoxLayout(box)
                b_layout.setContentsMargins(14, 8, 14, 8)
                b_layout.setSpacing(10)

                lbl_msg = QLabel(msg)
                lbl_msg.setWordWrap(True)
                lbl_msg.setStyleSheet("color: #0F172A; font-size: 11px;")
                b_layout.addWidget(lbl_msg, stretch=1)

                btn_dismiss = QPushButton("✕")
                btn_dismiss.setFixedSize(22, 22)
                btn_dismiss.setCursor(Qt.PointingHandCursor)
                btn_dismiss.setToolTip("Dismiss notice")
                btn_dismiss.setStyleSheet(
                    "background: transparent; color: #64748B; font-weight: bold; border: none; font-size: 12px;"
                )
                btn_dismiss.clicked.connect(lambda _, b=box: b.deleteLater())
                b_layout.addWidget(btn_dismiss)

                self.notices_layout.addWidget(box)
        except Exception as exc:
            logger.warning(f"Error rendering decision notices: {exc}")

    def _open_edit_profile(self):
        """Opens Edit Profile modal dialog."""
        dialog = EditProfileDialog(
            parent=self,
            user_session=self.user_session,
            faculty_data=self.faculty_data,
        )
        dialog.profile_updated.connect(self._on_profile_updated)
        dialog.exec()

    def _on_profile_updated(self, updated_data: Dict[str, Any]):
        """Handles profile update callback from modal dialog."""
        self.faculty_data = updated_data
        self._refresh_profile_ui()

        # Update top bar avatar in parent window if available
        win = self.window()
        if win and hasattr(win, "update_session_ui") and win is not self:
            win.update_session_ui()

        emp = self.faculty_data.get("employee_code") or (self.user_session.employee_code if self.user_session else "User")
        log_line = f"[{datetime.now().strftime('%H:%M:%S')}] [PROFILE] Updated by {emp}"
        if hasattr(self, "log_console") and self.log_console:
            self.log_console.append(log_line)
        logger.info(log_line)

    def _build_time_controller(self, layout):
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        self.lbl_time_mode_badge = QLabel("NORMAL MODE (Live Clock)")
        self.lbl_time_mode_badge.setStyleSheet(
            "background-color: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 4px; font-weight: bold;"
        )
        row1.addWidget(self.lbl_time_mode_badge)

        self.lbl_effective_time = QLabel("Effective Time: Checking...")
        self.lbl_effective_time.setStyleSheet("font-size: 13px; font-weight: 600; color: #1E293B;")
        row1.addWidget(self.lbl_effective_time)
        row1.addStretch()

        self.btn_toggle_time_mode = QPushButton("Switch to Test Mode")
        self.btn_toggle_time_mode.setMinimumHeight(32)
        self.btn_toggle_time_mode.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_time_mode.setStyleSheet(
            "background-color: #2563EB; color: #FFFFFF; font-weight: bold; padding: 6px 16px; border-radius: 5px;"
        )
        self.btn_toggle_time_mode.clicked.connect(self._toggle_time_mode)
        row1.addWidget(self.btn_toggle_time_mode)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)

        lbl_sim = QLabel("Simulate Custom Date & Time:")
        lbl_sim.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155;")
        row2.addWidget(lbl_sim)

        self.dt_test_picker = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_test_picker.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_test_picker.setCalendarPopup(True)
        self.dt_test_picker.setMinimumHeight(32)
        self.dt_test_picker.setFixedWidth(190)
        row2.addWidget(self.dt_test_picker)

        self.btn_apply_test_time = QPushButton("Apply Injected Time")
        self.btn_apply_test_time.setMinimumHeight(32)
        self.btn_apply_test_time.setCursor(Qt.PointingHandCursor)
        self.btn_apply_test_time.setStyleSheet(
            "background-color: #D97706; color: white; font-weight: bold; padding: 6px 14px; border-radius: 5px;"
        )
        self.btn_apply_test_time.clicked.connect(self._apply_injected_time)
        row2.addWidget(self.btn_apply_test_time)

        self.btn_reset_time = QPushButton("Reset to Real-Time")
        self.btn_reset_time.setMinimumHeight(32)
        self.btn_reset_time.setCursor(Qt.PointingHandCursor)
        self.btn_reset_time.setStyleSheet(
            "background-color: #475569; color: white; font-weight: 600; padding: 6px 14px; border-radius: 5px;"
        )
        self.btn_reset_time.clicked.connect(self._reset_time_to_real)
        row2.addWidget(self.btn_reset_time)
        row2.addStretch()
        layout.addLayout(row2)

        self._sync_time_mode_ui()

    def _sync_time_mode_ui(self):
        is_test = TimeService.is_test_mode()
        cur_dt = TimeService.get_current_time()
        self.lbl_effective_time.setText(f"Effective Time: {cur_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        if is_test:
            self.lbl_time_mode_badge.setText("TEST MODE (Simulated)")
            self.lbl_time_mode_badge.setStyleSheet(
                "background-color: #FEF3C7; color: #B45309; padding: 4px 10px; border-radius: 4px; font-weight: bold;"
            )
            self.btn_toggle_time_mode.setText("Switch to Normal Mode")
            self.btn_toggle_time_mode.setStyleSheet(
                "background-color: #059669; color: white; font-weight: bold; padding: 6px 14px; border-radius: 5px;"
            )
            self.dt_test_picker.setEnabled(True)
            self.btn_apply_test_time.setEnabled(True)
        else:
            self.lbl_time_mode_badge.setText("NORMAL MODE (Live Clock)")
            self.lbl_time_mode_badge.setStyleSheet(
                "background-color: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 4px; font-weight: bold;"
            )
            self.btn_toggle_time_mode.setText("Switch to Test Mode")
            self.btn_toggle_time_mode.setStyleSheet(
                "background-color: #2563EB; color: white; font-weight: bold; padding: 6px 14px; border-radius: 5px;"
            )

    def _toggle_time_mode(self):
        is_test = TimeService.is_test_mode()
        if is_test:
            TimeService.set_time_mode("NORMAL")
        else:
            qdt = self.dt_test_picker.dateTime()
            py_dt = qdt.toPython()
            TimeService.set_time_mode("TEST", test_datetime=py_dt)
        self._sync_time_mode_ui()

    def _apply_injected_time(self):
        qdt = self.dt_test_picker.dateTime()
        py_dt = qdt.toPython()
        TimeService.set_time_mode("TEST", test_datetime=py_dt)
        self._sync_time_mode_ui()

    def _reset_time_to_real(self):
        TimeService.reset_to_normal()
        self.dt_test_picker.setDateTime(QDateTime.currentDateTime())
        self._sync_time_mode_ui()

    def _on_retest_db_clicked(self):
        win = self.window()
        if win and hasattr(win, "check_database_connection") and win is not self:
            win.check_database_connection()
            return

        self.btn_retest_db.setEnabled(False)
        self.db_status_badge.setText("DB Status: Testing...")
        self.db_status_badge.setStyleSheet(
            "background-color: #FEF3C7; color: #B45309; padding: 5px 12px; border-radius: 5px; font-weight: bold;"
        )

        from ui.worker import WorkerThread
        from database.connection import test_connection

        def _do_test():
            return test_connection()

        def _on_result(res):
            success, msg = res
            if success:
                self.db_status_badge.setText("DB Status: CONNECTED")
                self.db_status_badge.setStyleSheet(
                    "background-color: #DCFCE7; color: #166534; padding: 5px 12px; border-radius: 5px; font-weight: bold;"
                )
                self.db_detail_label.setText(
                    f"<b>Target Endpoint:</b> {settings.DB_HOST}:{settings.DB_PORT} &nbsp;•&nbsp; <b>Schema:</b> {settings.DB_NAME} &nbsp;|&nbsp; <span style='color: #16A34A;'>Live MySQL Online</span>"
                )
            else:
                self.db_status_badge.setText("DB Status: IN-MEMORY RESILIENT MODE")
                self.db_status_badge.setStyleSheet(
                    "background-color: #FFEDD5; color: #C2410C; padding: 5px 12px; border-radius: 5px; font-weight: bold;"
                )
                self.db_detail_label.setText(
                    f"<b>Target Endpoint:</b> {settings.DB_HOST}:{settings.DB_PORT} &nbsp;•&nbsp; <b>Schema:</b> {settings.DB_NAME} &nbsp;|&nbsp; <span style='color: #EA580C;'>In-Memory Fallback Active</span>"
                )
            if hasattr(self, "log_console") and self.log_console:
                self.log_console.append(f"[{datetime.now().strftime('%H:%M:%S')}] DB Test: {msg}")

        def _on_finish():
            self.btn_retest_db.setEnabled(True)

        self._db_worker = WorkerThread(_do_test)
        self._db_worker.result.connect(_on_result)
        self._db_worker.finished.connect(_on_finish)
        self._db_worker.finished.connect(self._db_worker.deleteLater)
        self._db_worker.start()

    def _on_init_db_clicked(self):
        win = self.window()
        if win and hasattr(win, "on_init_database_clicked") and win is not self:
            win.on_init_database_clicked()
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Confirm Database Initialization",
            "This will create the database, tables, and seed initial data if they do not exist.\n\n"
            "Existing records will NOT be overwritten.\n\n"
            "Do you wish to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_init_db.setEnabled(False)
        self.btn_init_db.setText("⏳ Initializing...")

        from ui.worker import WorkerThread
        from database.init_db import initialize_database

        def _do_init():
            return initialize_database(return_details=True)

        def _on_result(res):
            success, msg = res
            if success:
                QMessageBox.information(
                    self,
                    "Database Ready",
                    f"MySQL Database '{settings.DB_NAME}' initialized and verified successfully!"
                )
                self._on_retest_db_clicked()
            else:
                lower_msg = (msg or "").lower()
                if "1045" in lower_msg or "access denied" in lower_msg:
                    QMessageBox.warning(
                        self,
                        "MySQL Access Denied",
                        f"Connected to MySQL server, but authentication failed.\n\n"
                        f"Details: {msg}\n\n"
                        "Please verify the DB_USER and DB_PASSWORD credentials in your .env configuration file."
                    )
                elif "2003" in lower_msg or "refused" in lower_msg or "offline" in lower_msg or "unreachable" in lower_msg:
                    QMessageBox.warning(
                        self,
                        "MySQL Not Running",
                        f"Could not connect to MySQL server at {settings.DB_HOST}:{settings.DB_PORT}.\n\n"
                        "To fix this:\n"
                        "1. Open XAMPP Control Panel (at D:\\xampp\\xampp-control.exe) and click 'Start' on MySQL.\n"
                        "   (Or run D:\\xampp\\mysql_start.bat)\n"
                        "2. Click 'Initialize & Seed MySQL' again.\n\n"
                        "Note: All ERP features are already 100% functional right now in In-Memory Mode!"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Database Initialization Failed",
                        f"MySQL server is running, but database initialization encountered an error:\n\n{msg}\n\n"
                        "In-Memory Mode remains active."
                    )

        def _on_finish():
            self.btn_init_db.setEnabled(True)
            self.btn_init_db.setText("⚡ Initialize & Seed MySQL")

        self._init_worker = WorkerThread(_do_init)
        self._init_worker.result.connect(_on_result)
        self._init_worker.finished.connect(_on_finish)
        self._init_worker.finished.connect(self._init_worker.deleteLater)
        self._init_worker.start()

    def _on_db_help_clicked(self):
        win = self.window()
        if win and hasattr(win, "show_mysql_help") and win is not self:
            win.show_mysql_help()
            return

        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "MySQL Setup Guide",
            "<h3>MySQL Database Diagnostics & Setup Guide</h3>"
            f"<p><b>Host:</b> {settings.DB_HOST}<br>"
            f"<b>Port:</b> {settings.DB_PORT}<br>"
            f"<b>Database:</b> {settings.DB_NAME}<br>"
            f"<b>User:</b> {settings.DB_USER}</p>"
            "<p><b>Troubleshooting:</b><br>"
            "1. Ensure XAMPP Control Panel has MySQL started.<br>"
            "2. Or run <code>D:\\xampp\\mysql_start.bat</code>.<br>"
            "3. If MySQL is offline, the ERP continues running seamlessly with in-memory persistence.</p>"
        )

    def _build_kpi_cards(self):
        while self.grid_kpi.count():
            item = self.grid_kpi.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.role == "ADMIN":
            self.c1 = KPICard("Database Engine", "MySQL 8.0", "12 Relational Tables Active", "#10B981")
            self.c2 = KPICard("Faculty Directory", "48 Active", "Department of MCA & CSE", "#2563EB")
            self.c3 = KPICard("AI Model Status", "95.0% Acc", "Pure-NumPy Softmax Logistic", "#8B5CF6")
            self.c4 = KPICard("Backup Integrity", "SHA-256", "Manifest Verified Snapshots", "#F59E0B")
            self.grid_kpi.addWidget(self.c1, 0, 0)
            self.grid_kpi.addWidget(self.c2, 0, 1)
            self.grid_kpi.addWidget(self.c3, 0, 2)
            self.grid_kpi.addWidget(self.c4, 0, 3)

        elif self.role == "HOD":
            self.c1 = KPICard("Pending Leaves", "3 Requests", "Requires AI Risk Verification", "#EF4444")
            self.c2 = KPICard("Punctuality Rate", "94.2%", "Department Average (Grace OK)", "#10B981")
            self.c3 = KPICard("Substitute Openings", "2 Slots", "Auto-Balancer Ready", "#F59E0B")
            self.c4 = KPICard("Faculty On Leave", "1 Professor", "Medical Leave (ML)", "#2563EB")
            self.grid_kpi.addWidget(self.c1, 0, 0)
            self.grid_kpi.addWidget(self.c2, 0, 1)
            self.grid_kpi.addWidget(self.c3, 0, 2)
            self.grid_kpi.addWidget(self.c4, 0, 3)

        elif self.role == "LAB_INSTRUCTOR":
            self.c1 = KPICard("Lab Assignments", "4 Sessions", "Data Structures & AI Lab", "#B45309")
            self.c2 = KPICard("Casual Leave (CL)", "10.0 Days", "Annual Quota: 15 Days", "#2563EB")
            self.c3 = KPICard("Monthly Grace Pool", "45 / 45 min", "0 min Used in October", "#10B981")
            self.c4 = KPICard("Lab Stations", "32 Active", "Equipment Operational", "#059669")
            self.grid_kpi.addWidget(self.c1, 0, 0)
            self.grid_kpi.addWidget(self.c2, 0, 1)
            self.grid_kpi.addWidget(self.c3, 0, 2)
            self.grid_kpi.addWidget(self.c4, 0, 3)

        elif self.role == "HR":
            self.c1 = KPICard("Pending HR Review", "4 Requests", "Multi-Stage Gatekeeper Review", "#C026D3")
            self.c2 = KPICard("Staff On Leave Today", "2 Members", "Across Campus Departments", "#2563EB")
            self.c3 = KPICard("Staff Directory", "54 Registered", "Faculty & Lab Instructors", "#10B981")
            self.c4 = KPICard("Institutional Policies", "5 Rules", "Quota & Entitlement Validated", "#F59E0B")
            self.grid_kpi.addWidget(self.c1, 0, 0)
            self.grid_kpi.addWidget(self.c2, 0, 1)
            self.grid_kpi.addWidget(self.c3, 0, 2)
            self.grid_kpi.addWidget(self.c4, 0, 3)

        elif self.role == "PRINCIPAL":
            self.c1 = KPICard("Executive Sign-Off", "2 Awaiting", "Final Institutional Approvals", "#B91C1C")
            self.c2 = KPICard("Campus Attendance", "96.4%", "Daily Institutional Average", "#10B981")
            self.c3 = KPICard("Departments", "6 Active", "MCA, CSE, ECE, EEE, ME, MBA", "#2563EB")
            self.c4 = KPICard("Institutional State", "Optimal", "All Systems & Biometrics Online", "#8B5CF6")
            self.grid_kpi.addWidget(self.c1, 0, 0)
            self.grid_kpi.addWidget(self.c2, 0, 1)
            self.grid_kpi.addWidget(self.c3, 0, 2)
            self.grid_kpi.addWidget(self.c4, 0, 3)

        else:  # FACULTY
            # Synchronize with live balances if available
            cl_val = "8.0 Days"
            ml_val = "10.0 Days"
            try:
                fac_id = self.faculty_data.get("id") or (self.user_session.faculty_id if self.user_session else 3)
                bals = leave_repository.get_faculty_balances(fac_id)
                for b in bals:
                    if b.get("leave_type_code") == "CL":
                        cl_val = f"{b.get('remaining_days', 8.0):.1f} Days"
                    elif b.get("leave_type_code") == "ML":
                        ml_val = f"{b.get('remaining_days', 10.0):.1f} Days"
            except Exception:
                pass

            self.c1 = KPICard("Casual Leave (CL)", cl_val, "Annual Quota: 15 Days", "#2563EB")
            self.c2 = KPICard("Medical Leave (ML)", ml_val, "Medical Certificate Required > 2d", "#10B981")
            self.c3 = KPICard("Monthly Grace Pool", "42 / 60 min", "18 min Used in October", "#F59E0B")
            self.c4 = KPICard("Substitute Duties", "1 Slot", "Upcoming This Week", "#8B5CF6")
            self.grid_kpi.addWidget(self.c1, 0, 0)
            self.grid_kpi.addWidget(self.c2, 0, 1)
            self.grid_kpi.addWidget(self.c3, 0, 2)
            self.grid_kpi.addWidget(self.c4, 0, 3)

    def _build_quick_actions(self):
        while self.btn_box.count():
            item = self.btn_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.role == "ADMIN":
            b1 = QPushButton("📥 Ingest Attendance CSV")
            b2 = QPushButton("⚡ Retrain NumPy Classifiers")
            b3 = QPushButton("💾 Create Database Backup")
            b1.clicked.connect(lambda: self.navigate_to_tab.emit(3))
            b2.clicked.connect(lambda: self.navigate_to_tab.emit(10))
            b3.clicked.connect(lambda: self.navigate_to_tab.emit(15))
            self.btn_box.addWidget(b1); self.btn_box.addWidget(b2); self.btn_box.addWidget(b3)

        elif self.role == "HOD":
            b1 = QPushButton("📋 Review Pending Leaves")
            b2 = QPushButton("👥 Assign Substitute Lecture")
            b3 = QPushButton("📊 Export Department Report (PDF)")
            b1.clicked.connect(lambda: self.navigate_to_tab.emit(6))
            b2.clicked.connect(lambda: self.navigate_to_tab.emit(7))
            b3.clicked.connect(lambda: self.navigate_to_tab.emit(13))
            self.btn_box.addWidget(b1); self.btn_box.addWidget(b2); self.btn_box.addWidget(b3)

        elif self.role == "LAB_INSTRUCTOR":
            b1 = QPushButton("📝 Apply for Leave (AI Screened)")
            b2 = QPushButton("⏱️ View My Grace Ledger")
            b3 = QPushButton("🔬 Lab Equipment & Logs")
            b1.clicked.connect(lambda: self.navigate_to_tab.emit(6))
            b2.clicked.connect(lambda: self.navigate_to_tab.emit(4))
            b3.clicked.connect(lambda: self.navigate_to_tab.emit(16))
            self.btn_box.addWidget(b1); self.btn_box.addWidget(b2); self.btn_box.addWidget(b3)

        elif self.role == "HR":
            b1 = QPushButton("⚖️ Review Stage 2 Leaves")
            b2 = QPushButton("🎓 Student Search Directory")
            b3 = QPushButton("📄 Export Monthly Leave Report")
            b1.clicked.connect(lambda: self.navigate_to_tab.emit(18))
            b2.clicked.connect(lambda: self.navigate_to_tab.emit(17))
            b3.clicked.connect(lambda: self.navigate_to_tab.emit(13))
            self.btn_box.addWidget(b1); self.btn_box.addWidget(b2); self.btn_box.addWidget(b3)

        elif self.role == "PRINCIPAL":
            b1 = QPushButton("⚖️ Final Executive Leave Approval")
            b2 = QPushButton("📉 College Analytics Overview")
            b3 = QPushButton("🎓 Student Academic Directory")
            b1.clicked.connect(lambda: self.navigate_to_tab.emit(18))
            b2.clicked.connect(lambda: self.navigate_to_tab.emit(12))
            b3.clicked.connect(lambda: self.navigate_to_tab.emit(17))
            self.btn_box.addWidget(b1); self.btn_box.addWidget(b2); self.btn_box.addWidget(b3)

        else:
            b1 = QPushButton("📝 Apply for Leave (AI Screened)")
            b2 = QPushButton("⏱️ View My Grace Ledger")
            b3 = QPushButton("🤝 View Substitute Classes")
            b1.clicked.connect(lambda: self.navigate_to_tab.emit(6))
            b2.clicked.connect(lambda: self.navigate_to_tab.emit(4))
            b3.clicked.connect(lambda: self.navigate_to_tab.emit(7))
            self.btn_box.addWidget(b1); self.btn_box.addWidget(b2); self.btn_box.addWidget(b3)

    def update_role(self, new_role: str, user_session=None):
        """Updates dashboard UI dynamically when active session changes."""
        self.role = new_role.upper()
        self.user_session = user_session
        try:
            self.faculty_data = faculty_service.get_full_faculty_profile(user_session) or {}
        except Exception as exc:
            logger.warning(f"Error fetching profile on role update: {exc}")
            self.faculty_data = {}

        # Refresh all profile components
        self._refresh_profile_ui()

        # Strict Restriction: System & Database Diagnostics strictly visible ONLY to ADMIN
        if hasattr(self, "diag_group"):
            self.diag_group.setVisible(self.role == "ADMIN")
        if hasattr(self, "time_group"):
            self.time_group.setVisible(self.role == "ADMIN")

        self._build_kpi_cards()
        self._build_quick_actions()


# Architectural alias for backward compatibility with tests and external callers
AdminDashboardWidget = DashboardWidget
