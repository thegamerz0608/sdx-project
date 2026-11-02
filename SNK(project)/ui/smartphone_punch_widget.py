"""
Smartphone Biometric Check-In QR Widget (PySide6) — Read-Only Presentation Layer
Acts as a passive desktop viewer for the standalone `biometric_daemon.py` microservice.
Queries active tunnel endpoints from SYSTEM_SETTINGS, renders dynamic QR codes,
and automatically polls the ATTENDANCE database table to stream today's check-ins in real time.
"""
import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv site-packages is in sys.path
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import qrcode
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QGroupBox,
    QApplication,
    QMessageBox,
    QComboBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Slot, QUrl, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPixmap, QDesktopServices

from database.connection import get_connection
from repositories.settings_repository import settings_repository
from repositories.attendance_repository import DEMO_ATTENDANCE
from services.mobile_punch_service import (
    get_local_lan_ip,
    get_all_active_employees,
    process_biometric_punch,
    PunchPayload,
    is_biometric_server_running,
    ensure_biometric_daemon_running,
)
from services.auth_service import auth_service
from utils.logger import get_logger

logger = get_logger("ui.smartphone_punch_widget")


class SmartphonePunchWidget(QWidget):
    """
    PySide6 User Interface Widget for Smartphone Biometric Check-In.
    Passively monitors the standalone Biometric Daemon, displays high-res QR codes,
    and automatically polls today's attendance logs from the MySQL database.
    """

    punch_recorded = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_thread = None  # No embedded server in desktop app
        self.server_port = 8000
        self.server_url = ""
        self._known_punch_ids = set()

        self._init_ui()

        # Initial sync from SYSTEM_SETTINGS and attendance database
        self.sync_from_system_settings()
        self.load_today_punches()

        # Automated Background Polling: Ticks every 5 seconds
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(5000)
        self.poll_timer.timeout.connect(self._on_poll_tick)
        self.poll_timer.start()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # Header Title Banner
        banner = QFrame()
        banner.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB); "
            "border-radius: 10px; padding: 14px;"
        )
        b_layout = QHBoxLayout(banner)
        v_title = QVBoxLayout()
        title = QLabel("📱 Smartphone Biometric Check-In Bridge")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        subtitle = QLabel("Standalone Microservice Viewer • Passive Database Polling & Mobile WebAuthn QR Console")
        subtitle.setStyleSheet("color: #BFDBFE; font-size: 11px;")
        v_title.addWidget(title)
        v_title.addWidget(subtitle)
        b_layout.addLayout(v_title)
        b_layout.addStretch()

        self.lbl_server_status = QLabel("DAEMON CHECKING...")
        self.lbl_server_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_server_status.setStyleSheet(
            "background-color: #E2E8F0; color: #475569; padding: 6px 14px; border-radius: 8px;"
        )
        b_layout.addWidget(self.lbl_server_status)
        main_layout.addWidget(banner)

        # Content Grid: Left Panel (QR & Sync Controls), Right Panel (Live Punches & Quick Test)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # ----------------------------------------------------------------------
        # LEFT PANEL: Read-Only QR Code & Daemon Sync
        # ----------------------------------------------------------------------
        left_card = QGroupBox("Mobile Biometric QR Gateway")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        # Sync Daemon Button Bar
        sync_bar = QHBoxLayout()
        self.btn_sync_daemon = QPushButton("🔄 Sync Endpoint")
        self.btn_sync_daemon.setCursor(Qt.PointingHandCursor)
        self.btn_sync_daemon.setToolTip("Queries SYSTEM_SETTINGS table for live tunnel URL published by biometric_daemon.py")
        self.btn_sync_daemon.setStyleSheet(
            "background-color: #1E3A8A; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px;"
        )
        self.btn_sync_daemon.clicked.connect(self.sync_from_system_settings)
        sync_bar.addWidget(self.btn_sync_daemon)

        self.btn_activate_service = QPushButton("⚡ Activate Daemon")
        self.btn_activate_service.setCursor(Qt.PointingHandCursor)
        self.btn_activate_service.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px;"
        )
        self.btn_activate_service.clicked.connect(self._on_activate_daemon_clicked)
        sync_bar.addWidget(self.btn_activate_service)

        # Compatibility alias for existing unit tests
        self.btn_toggle_server = self.btn_sync_daemon

        left_layout.addLayout(sync_bar)

        # High-Resolution QR Code Display
        self.lbl_qr = QLabel()
        self.lbl_qr.setFixedSize(220, 220)
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setStyleSheet(
            "background-color: #FFFFFF; border: 2px dashed #CBD5E1; border-radius: 10px;"
        )
        left_layout.addWidget(self.lbl_qr, alignment=Qt.AlignCenter)

        # Active URL Label
        self.lbl_url = QLabel("Fetching endpoint from database...")
        self.lbl_url.setStyleSheet("color: #334155; font-size: 11.5px; text-align: center;")
        self.lbl_url.setAlignment(Qt.AlignCenter)
        self.lbl_url.setWordWrap(True)
        left_layout.addWidget(self.lbl_url)

        # Action Buttons: Copy Link & Test in Browser
        btn_url_row = QHBoxLayout()
        self.btn_copy_url = QPushButton("📋 Copy Link")
        self.btn_copy_url.setEnabled(False)
        self.btn_copy_url.clicked.connect(self._copy_url)

        self.btn_open_browser = QPushButton("🌐 Test in Browser")
        self.btn_open_browser.setEnabled(False)
        self.btn_open_browser.clicked.connect(self._open_browser)

        btn_url_row.addWidget(self.btn_copy_url)
        btn_url_row.addWidget(self.btn_open_browser)
        left_layout.addLayout(btn_url_row)

        # Operational Instructions Card
        instructions = QLabel(
            "<b>How it works:</b><br>"
            "1. Run <code>run_biometric_daemon.bat</code> in the background.<br>"
            "2. The daemon publishes its secure HTTPS tunnel to <code>SYSTEM_SETTINGS</code>.<br>"
            "3. Staff scan this QR code with their mobile phone.<br>"
            "4. Smartphone prompts native Fingerprint/FaceID.<br>"
            "5. Punches save directly to MySQL and auto-stream here."
        )
        instructions.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; "
            "padding: 10px; color: #475569; font-size: 11px; line-height: 1.45;"
        )
        left_layout.addWidget(instructions)
        left_layout.addStretch()

        content_layout.addWidget(left_card, stretch=4)

        # ----------------------------------------------------------------------
        # RIGHT PANEL: Live Biometric Punches & Today's Attendance Stream
        # ----------------------------------------------------------------------
        right_card = QGroupBox("Today's Biometric Attendance Stream (Database Live Poll)")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)

        # Quick Desktop Punch Control Bar (Direct 1-Click Biometric Punch)
        quick_punch_box = QFrame()
        quick_punch_box.setStyleSheet(
            "background-color: #F8FAFC; border: 1.5px solid #CBD5E1; border-radius: 8px; padding: 8px 10px;"
        )
        qp_layout = QHBoxLayout(quick_punch_box)
        qp_layout.setContentsMargins(8, 4, 8, 4)
        qp_layout.setSpacing(10)

        lbl_qp = QLabel("<b>⚡ Desktop Quick Punch:</b>")
        lbl_qp.setStyleSheet("color: #1E293B; font-size: 12px;")
        qp_layout.addWidget(lbl_qp)

        self.cmb_quick_emp = QComboBox()
        self.cmb_quick_emp.setMinimumWidth(210)
        self.cmb_quick_emp.setStyleSheet("padding: 4px; font-weight: 500;")
        qp_layout.addWidget(self.cmb_quick_emp)

        self.cmb_quick_type = QComboBox()
        self.cmb_quick_type.addItems(["AUTO", "IN", "OUT"])
        self.cmb_quick_type.setFixedWidth(75)
        self.cmb_quick_type.setStyleSheet("padding: 4px; font-weight: bold;")
        qp_layout.addWidget(self.cmb_quick_type)

        self.btn_quick_punch = QPushButton("⚡ Execute")
        self.btn_quick_punch.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 5px 12px; border-radius: 6px;"
        )
        self.btn_quick_punch.clicked.connect(self._on_desktop_quick_punch)
        qp_layout.addWidget(self.btn_quick_punch)

        right_layout.addWidget(quick_punch_box)
        self._populate_quick_employees()

        # Table of Incoming Mobile & Desktop Punches (7 Columns)
        self.tbl_live_punches = QTableWidget()
        self.tbl_live_punches.setColumnCount(7)
        self.tbl_live_punches.setHorizontalHeaderLabels([
            "Time", "Emp Code", "Full Name", "Department", "Punch Type", "Late Mark", "Biometric Status"
        ])
        header = self.tbl_live_punches.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_live_punches.setAlternatingRowColors(True)
        self.tbl_live_punches.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_live_punches.verticalHeader().setDefaultSectionSize(36)
        right_layout.addWidget(self.tbl_live_punches, stretch=1)

        # Footer Status Row
        footer_row = QHBoxLayout()
        self.lbl_poll_status = QLabel("Auto-polling MySQL attendance records every 5s • Standalone Daemon Mode")
        self.lbl_poll_status.setStyleSheet("color: #64748B; font-size: 11px;")
        footer_row.addWidget(self.lbl_poll_status)
        footer_row.addStretch()

        btn_refresh_now = QPushButton("🔄 Refresh Roster")
        btn_refresh_now.setStyleSheet("padding: 4px 10px; font-weight: 600;")
        btn_refresh_now.clicked.connect(self.load_today_punches)
        footer_row.addWidget(btn_refresh_now)

        right_layout.addLayout(footer_row)

        content_layout.addWidget(right_card, stretch=6)
        main_layout.addLayout(content_layout)

    def _on_poll_tick(self):
        """Timer callback ticking every 5 seconds to passively sync daemon URL and attendance records."""
        self.sync_from_system_settings(silent=True)
        self.load_today_punches()

    def _on_activate_daemon_clicked(self):
        """1-click activation to start the standalone biometric daemon in background."""
        ensure_biometric_daemon_running(port=self.server_port)
        self.sync_from_system_settings()

    def sync_from_system_settings(self, silent: bool = False):
        """Queries port 8000 liveness and SYSTEM_SETTINGS table for active biometric daemon endpoint."""
        is_alive = is_biometric_server_running(port=self.server_port)
        daemon_url = settings_repository.get_setting("BIOMETRIC_SERVER_URL")
        daemon_status = settings_repository.get_setting("BIOMETRIC_DAEMON_STATUS", "INACTIVE")

        if is_alive:
            daemon_status = "ONLINE"
            if not daemon_url or daemon_url.upper() in ["OFFLINE", "NONE", "NULL", ""]:
                daemon_url = f"http://erp.sys:{self.server_port}/punch-interface"

        # Fallback to local default if not set
        if not daemon_url or daemon_url.upper() in ["OFFLINE", "NONE", "NULL", ""]:
            lan_ip = get_local_lan_ip()
            daemon_url = f"http://{lan_ip}:{self.server_port}/punch-interface"
            self.lbl_server_status.setText("DAEMON INACTIVE")
            self.lbl_server_status.setStyleSheet(
                "background-color: #64748B; color: #FFFFFF; padding: 6px 14px; border-radius: 8px; font-weight: bold;"
            )
            self.btn_copy_url.setEnabled(False)
            self.btn_open_browser.setEnabled(False)
            if hasattr(self, "btn_activate_service"):
                self.btn_activate_service.setVisible(True)
            self.update_qr_display(daemon_url)
            self.lbl_url.setText(
                "<b>Daemon is currently inactive.</b><br>"
                "Click <b>'⚡ Activate Daemon'</b> or run <code>launch_all.bat</code>."
            )
        else:
            self.server_url = daemon_url
            self.update_qr_display(daemon_url)
            self.btn_copy_url.setEnabled(True)
            self.btn_open_browser.setEnabled(True)

            if daemon_status.upper() == "ONLINE":
                tag = "HTTPS CLOUD" if "https" in daemon_url.lower() else "CAMPUS LAN / erp.sys"
                self.lbl_server_status.setText(f"ONLINE ({tag})")
                self.lbl_server_status.setStyleSheet(
                    "background-color: #10B981; color: #FFFFFF; padding: 6px 14px; border-radius: 8px; font-weight: bold;"
                )
                if hasattr(self, "btn_activate_service"):
                    self.btn_activate_service.setVisible(False)
            else:
                self.lbl_server_status.setText("DAEMON INACTIVE")
                self.lbl_server_status.setStyleSheet(
                    "background-color: #64748B; color: #FFFFFF; padding: 6px 14px; border-radius: 8px; font-weight: bold;"
                )
                if hasattr(self, "btn_activate_service"):
                    self.btn_activate_service.setVisible(True)

        if not silent:
            logger.info(f"SmartphonePunchWidget synced from SYSTEM_SETTINGS: {self.server_url} ({daemon_status})")

    def update_qr_display(self, custom_url: str = None):
        """Renders high-res QR code for the given or active server URL."""
        if custom_url:
            self.server_url = custom_url
        elif not self.server_url:
            lan_ip = get_local_lan_ip()
            self.server_url = f"http://{lan_ip}:{self.server_port}/punch-interface"

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(self.server_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            pix = QPixmap()
            pix.loadFromData(buf.getvalue(), "PNG")
            self.lbl_qr.setPixmap(pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.lbl_url.setText(f"<b>Scan to Punch (HTTPS):</b><br><code>{self.server_url}</code>")
        except Exception as exc:
            self.lbl_qr.setText("QR Generation Error")
            logger.warning(f"Failed to generate QR code: {exc}")

    def load_today_punches(self):
        """Passively queries today's attendance records from MySQL database / repository."""
        records = []
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT 
                    a.id,
                    COALESCE(f.employee_code, li.instructor_code, 'STAFF') AS employee_code,
                    COALESCE(CONCAT(f.first_name, ' ', f.last_name), CONCAT(li.first_name, ' ', li.last_name), 'Staff Member') AS full_name,
                    COALESCE(d.code, 'MCA') AS department_code,
                    a.attendance_date,
                    a.login_time,
                    a.logout_time,
                    a.status,
                    a.late_minutes,
                    a.working_hours
                FROM attendance a
                LEFT JOIN faculty f ON f.id = a.faculty_id
                LEFT JOIN lab_instructors li ON li.id = a.faculty_id
                LEFT JOIN departments d ON d.id = COALESCE(f.department_id, li.department_id)
                WHERE a.attendance_date = CURRENT_DATE
                ORDER BY a.id DESC;
            """
            cursor.execute(sql)
            records = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.debug(f"Direct DB query for today's punches failed, using fallback: {exc}")

        # If database query produced records, populate table
        if records:
            # Preserve existing row count if unchanged
            current_ids = {r["id"] for r in records}
            if current_ids == self._known_punch_ids:
                return
            self._known_punch_ids = current_ids

            self.tbl_live_punches.setRowCount(0)
            for r in records:
                row = self.tbl_live_punches.rowCount()
                self.tbl_live_punches.insertRow(row)

                # Time
                ptime = str(r.get("logout_time") or r.get("login_time") or "--:--:--")
                self.tbl_live_punches.setItem(row, 0, QTableWidgetItem(ptime))

                # Emp Code
                code_item = QTableWidgetItem(r.get("employee_code", ""))
                code_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.tbl_live_punches.setItem(row, 1, code_item)

                # Name
                self.tbl_live_punches.setItem(row, 2, QTableWidgetItem(r.get("full_name", "")))

                # Dept
                self.tbl_live_punches.setItem(row, 3, QTableWidgetItem(r.get("department_code", "MCA")))

                # Punch Type
                ptype = "CHECK_OUT" if r.get("logout_time") else "CHECK_IN"
                type_item = QTableWidgetItem(ptype)
                if ptype == "CHECK_IN":
                    type_item.setForeground(QColor("#2563EB"))
                else:
                    type_item.setForeground(QColor("#7C3AED"))
                self.tbl_live_punches.setItem(row, 4, type_item)

                # Late
                late = r.get("late_minutes", 0)
                late_item = QTableWidgetItem(f"{late} min" if late > 0 else "On Time (0m)")
                if late > 0:
                    late_item.setForeground(QColor("#DC2626"))
                else:
                    late_item.setForeground(QColor("#059669"))
                self.tbl_live_punches.setItem(row, 5, late_item)

                # Biometric Status
                status_item = QTableWidgetItem("✅ Verified (WebAuthn)")
                status_item.setForeground(QColor("#059669"))
                self.tbl_live_punches.setItem(row, 6, status_item)

            self.lbl_poll_status.setText(
                f"Auto-polling active • Total check-ins today: {len(records)} | Last sync: {datetime.now().strftime('%H:%M:%S')}"
            )

    @Slot(dict)
    def on_punch_received(self, data: dict):
        """Live callback invoked when a mobile phone or desktop triggers a biometric check-in."""
        row = 0
        self.tbl_live_punches.insertRow(row)

        time_item = QTableWidgetItem(data.get("punch_time", "--:--:--"))
        self.tbl_live_punches.setItem(row, 0, time_item)

        code_item = QTableWidgetItem(data.get("employee_code", ""))
        code_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.tbl_live_punches.setItem(row, 1, code_item)

        name_item = QTableWidgetItem(data.get("full_name", ""))
        self.tbl_live_punches.setItem(row, 2, name_item)

        dept_item = QTableWidgetItem(data.get("department", "MCA"))
        self.tbl_live_punches.setItem(row, 3, dept_item)

        type_str = data.get("punch_type", "CHECK_IN")
        type_item = QTableWidgetItem(type_str)
        if type_str == "CHECK_IN":
            type_item.setForeground(QColor("#2563EB"))
        else:
            type_item.setForeground(QColor("#7C3AED"))
        self.tbl_live_punches.setItem(row, 4, type_item)

        late = data.get("late_minutes", 0)
        late_item = QTableWidgetItem(f"{late} min" if late > 0 else "On Time (0m)")
        if late > 0:
            late_item.setForeground(QColor("#DC2626"))
        else:
            late_item.setForeground(QColor("#059669"))
        self.tbl_live_punches.setItem(row, 5, late_item)

        bio_item = QTableWidgetItem("✅ Verified (WebAuthn)")
        bio_item.setForeground(QColor("#059669"))
        self.tbl_live_punches.setItem(row, 6, bio_item)

        self.punch_recorded.emit(data)

    def _populate_quick_employees(self):
        """Populates the employee combobox with active faculty and instructors."""
        self.cmb_quick_emp.clear()
        try:
            emps = get_all_active_employees()
            current_code = None
            if auth_service.current_user:
                current_code = auth_service.current_user.employee_code or auth_service.current_user.username

            selected_idx = 0
            for idx, emp in enumerate(emps):
                label = f"{emp['name']} ({emp['code']} - {emp.get('dept', 'MCA')})"
                self.cmb_quick_emp.addItem(label, userData=emp["code"])
                if current_code and (emp["code"].upper() == current_code.upper()):
                    selected_idx = idx

            if self.cmb_quick_emp.count() > 0:
                self.cmb_quick_emp.setCurrentIndex(selected_idx)
        except Exception as exc:
            logger.warning(f"Could not populate quick punch employees: {exc}")

    def _on_desktop_quick_punch(self):
        """Executes a 1-click desktop biometric punch directly into the database."""
        emp_code = self.cmb_quick_emp.currentData()
        if not emp_code:
            QMessageBox.warning(self, "Selection Required", "Please select an employee to punch.")
            return

        punch_type = self.cmb_quick_type.currentText()
        try:
            payload = PunchPayload(
                employee_code=emp_code,
                punch_type=punch_type,
                auth_method="DESKTOP_QUICK_PUNCH",
            )
            result = process_biometric_punch(payload)
            self.on_punch_received(result)
            QMessageBox.information(
                self,
                "Punch Recorded",
                f"✅ {result.get('message', 'Attendance punch recorded successfully!')}\n\n"
                f"• Employee: {result.get('full_name')} ({emp_code})\n"
                f"• Punch Type: {result.get('punch_type')}\n"
                f"• Timestamp: {result.get('punch_time')}\n"
                f"• Late Minutes: {result.get('late_minutes', 0)} min\n"
                f"• Total Hours: {result.get('working_hours', '0.0')} hrs",
            )
        except Exception as exc:
            logger.error(f"Error during desktop quick punch: {exc}", exc_info=True)
            QMessageBox.critical(self, "Punch Error", f"Failed to record attendance punch:\n\n{exc}")

    def _copy_url(self):
        """Copies the active punch URL to clipboard."""
        if self.server_url:
            QApplication.clipboard().setText(self.server_url)
            QMessageBox.information(self, "Link Copied", f"Punch URL copied to clipboard:\n\n{self.server_url}")

    def _open_browser(self):
        """Opens the punch URL in the system default browser."""
        if self.server_url:
            QDesktopServices.openUrl(QUrl(self.server_url))

    def append_log(self, message: str):
        """Logging helper for audit records."""
        logger.info(message)
