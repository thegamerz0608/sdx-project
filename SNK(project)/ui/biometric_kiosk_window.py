"""
Biometric Attendance Kiosk Window (PySide6)
Standalone, full-screen ready lobby terminal for faculty and staff biometric check-in.
Features:
- Decoupled from Admin login: can boot directly from LoginWindow on lobby displays.
- QR Code display with setScaledContents(True) and responsive QSizePolicy.
- Background QThread worker polling MySQL ATTENDANCE table every 5 seconds.
- Timezone-safe SQL queries aligned with TimeService effective date.
- Safe Signal/Slot GUI updates without freezing or UI lag.
"""
import sys
import io
from pathlib import Path
from datetime import datetime, date, time
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
    QMainWindow,
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
    QSizePolicy,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Slot, QUrl, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QColor, QPixmap, QDesktopServices, QKeySequence, QShortcut

from database.connection import get_connection
from repositories.settings_repository import settings_repository
from repositories.attendance_repository import DEMO_ATTENDANCE
from services.mobile_punch_service import (
    get_local_lan_ip,
    is_biometric_server_running,
    ensure_biometric_daemon_running,
)
from services.time_service import TimeService
from utils.logger import get_logger

logger = get_logger("ui.biometric_kiosk_window")


class AttendancePollingWorker(QThread):
    """
    Background QThread worker that queries the database for today's punches
    and pulls active daemon settings every 5 seconds without blocking the GUI.
    """
    punches_loaded = Signal(list)
    sync_status = Signal(str, str, str)  # status, url, message
    query_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_active = True

    def run(self):
        """Executes in background thread."""
        try:
            # 1. Probe port 8000 liveness and fetch active daemon settings
            is_alive = is_biometric_server_running(port=8000)
            daemon_status = settings_repository.get_setting("BIOMETRIC_DAEMON_STATUS", "OFFLINE")
            daemon_url = settings_repository.get_setting("BIOMETRIC_SERVER_URL", "")

            if is_alive:
                daemon_status = "ONLINE"
                if not daemon_url or daemon_url.upper() in ["OFFLINE", "NONE", "NULL", ""]:
                    daemon_url = "http://erp.sys:8000/punch-interface"
            else:
                if daemon_status.upper() == "ONLINE":
                    daemon_status = "OFFLINE"
                if not daemon_url or daemon_url.upper() in ["OFFLINE", "NONE", "NULL", ""]:
                    daemon_url = "http://erp.sys:8000/punch-interface"

            msg = "Daemon endpoint synced"
            self.sync_status.emit(daemon_status, daemon_url, msg)

            # 2. Fetch today's attendance records using TimeService effective date
            effective_date = TimeService.get_current_date()
            date_str = str(effective_date)
            records: List[Dict[str, Any]] = []

            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                # Timezone-safe date matching on DATE(attendance_date) or string comparison
                sql = """
                    SELECT 
                        a.id,
                        a.faculty_id,
                        COALESCE(f.employee_code, CONCAT('EMP', LPAD(a.faculty_id, 3, '0'))) AS employee_code,
                        COALESCE(CONCAT(f.first_name, ' ', f.last_name), 'Staff Member') AS faculty_name,
                        COALESCE(d.code, 'MCA') AS department_code,
                        a.attendance_date,
                        a.login_time,
                        a.logout_time,
                        a.status,
                        CASE WHEN a.logout_time IS NOT NULL THEN 'CHECK_OUT' ELSE 'CHECK_IN' END AS punch_type,
                        'WEBAUTHN' AS verification_method,
                        COALESCE(a.import_batch_id, 'Mobile Device') AS device_id,
                        '127.0.0.1' AS ip_address,
                        COALESCE(a.late_minutes, 0) AS late_minutes
                    FROM attendance a
                    LEFT JOIN faculty f ON a.faculty_id = f.id
                    LEFT JOIN departments d ON f.department_id = d.id
                    WHERE DATE(a.attendance_date) = %s 
                       OR a.attendance_date = %s
                    ORDER BY a.id DESC;
                """
                cursor.execute(sql, (effective_date, date_str))
                records = cursor.fetchall() or []
                cursor.close()
                conn.close()
            except Exception as db_err:
                logger.debug(f"Kiosk worker DB lookup failed: {db_err}. Using in-memory fallback.")
                # Filter demo records for effective date
                records = []
                for r in DEMO_ATTENDANCE:
                    if str(r.get("attendance_date", "")) == date_str:
                        rec = dict(r)
                        if "punch_type" not in rec:
                            rec["punch_type"] = "CHECK_OUT" if rec.get("logout_time") else "CHECK_IN"
                        records.append(rec)
                records.sort(key=lambda x: x.get("id", 0), reverse=True)

            self.punches_loaded.emit(records)

        except Exception as exc:
            logger.error(f"Error in AttendancePollingWorker: {exc}", exc_info=True)
            self.query_failed.emit(str(exc))


class BiometricKioskWindow(QMainWindow):
    """
    Dedicated Full-Screen Biometric Attendance Kiosk Window.
    Operates in lobby mode without requiring administrative authentication.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Institutional Biometric Attendance Terminal (Kiosk Mode)")
        self.resize(1120, 680)
        self.setMinimumSize(960, 600)

        # Standard desktop window controls (Minimize, Maximize, Close)
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        self.server_url = ""
        self.daemon_status = "OFFLINE"
        self._is_fullscreen = False

        self._init_ui()
        self._setup_shortcuts()
        self._setup_background_worker()

        # Ensure biometric daemon is active
        ensure_biometric_daemon_running(port=8000)

        # Clock timer for top banner (updates every second)
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start()

        # Initial trigger
        self.refresh_kiosk_data()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(14)

        # ----------------------------------------------------------------------
        # 1. TOP HEADER BANNER
        # ----------------------------------------------------------------------
        banner = QFrame()
        banner.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0F172A, stop:1 #1E3A8A); "
            "border-radius: 10px; padding: 12px 18px;"
        )
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(10, 8, 10, 8)
        b_layout.setSpacing(14)

        self.lbl_crest = QLabel("🏛️")
        self.lbl_crest.setStyleSheet("font-size: 32px;")
        b_layout.addWidget(self.lbl_crest)

        v_title = QVBoxLayout()
        v_title.setSpacing(2)
        title = QLabel("INSTITUTIONAL BIOMETRIC ATTENDANCE TERMINAL")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF; letter-spacing: 0.5px;")

        sub = QLabel("Decoupled Mobile WebAuthn Gateway • Automated Background Attendance Stream")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #93C5FD;")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        b_layout.addLayout(v_title)

        b_layout.addStretch()

        # Live Clock & Time Mode Display
        self.lbl_clock = QLabel()
        self.lbl_clock.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_clock.setStyleSheet("color: #F8FAFC; background: #334155; padding: 6px 14px; border-radius: 6px;")
        b_layout.addWidget(self.lbl_clock)
        self._update_clock()

        # Fullscreen Toggle Button
        self.btn_fullscreen = QPushButton("⛶ Fullscreen (F11)")
        self.btn_fullscreen.setCursor(Qt.PointingHandCursor)
        self.btn_fullscreen.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 7px 14px; border-radius: 6px;"
        )
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        b_layout.addWidget(self.btn_fullscreen)

        # Standard OS Title bar handles window closing; keep hidden for backward compatibility
        self.btn_admin_exit = QPushButton("🔒 Admin Exit")
        self.btn_admin_exit.setVisible(False)
        self.btn_admin_exit.clicked.connect(self.admin_exit_kiosk)
        self.btn_close = self.btn_admin_exit

        root_layout.addWidget(banner)

        # ----------------------------------------------------------------------
        # 2. MAIN SPLIT CONTENT LAYOUT
        # ----------------------------------------------------------------------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        # LEFT PANEL: QR Code & Mobile Access Gateway
        left_card = QGroupBox("Mobile Biometric QR Gateway")
        left_card.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 16, 18, 16)
        left_layout.setSpacing(12)

        # Status and Sync Bar
        status_bar = QHBoxLayout()
        self.lbl_status = QLabel("DAEMON CHECKING...")
        self.lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("background-color: #E2E8F0; color: #475569; padding: 4px 10px; border-radius: 6px;")
        status_bar.addWidget(self.lbl_status)
        status_bar.addStretch()

        self.btn_activate_service = QPushButton("⚡ Activate Service")
        self.btn_activate_service.setCursor(Qt.PointingHandCursor)
        self.btn_activate_service.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 5px 12px; border-radius: 5px;"
        )
        self.btn_activate_service.setVisible(False)
        self.btn_activate_service.clicked.connect(self.activate_biometric_service)
        status_bar.addWidget(self.btn_activate_service)

        self.btn_sync = QPushButton("🔄 Sync Endpoint")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold; padding: 5px 12px; border-radius: 5px;")
        self.btn_sync.clicked.connect(self.refresh_kiosk_data)
        status_bar.addWidget(self.btn_sync)
        left_layout.addLayout(status_bar)

        # QR Code Display Container with setScaledContents(True) & QSizePolicy
        qr_frame = QFrame()
        qr_frame.setStyleSheet(
            "background-color: #FFFFFF; border: 2px dashed #94A3B8; border-radius: 12px; padding: 10px;"
        )
        qr_layout = QVBoxLayout(qr_frame)
        qr_layout.setAlignment(Qt.AlignCenter)

        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setScaledContents(True)  # CRITICAL: Ensures perfect scaling without cutoffs
        self.lbl_qr.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_qr.setMinimumSize(220, 220)
        self.lbl_qr.setMaximumSize(300, 300)
        qr_layout.addWidget(self.lbl_qr)

        left_layout.addWidget(qr_frame, alignment=Qt.AlignCenter)

        # Active URL Label
        self.lbl_url = QLabel("Endpoint: Connecting...")
        self.lbl_url.setFont(QFont("Consolas", 10))
        self.lbl_url.setAlignment(Qt.AlignCenter)
        self.lbl_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_url.setStyleSheet(
            "background-color: #F8FAFC; color: #1E3A8A; padding: 8px 10px; "
            "border: 1px solid #CBD5E1; border-radius: 6px;"
        )
        left_layout.addWidget(self.lbl_url)

        # Action Buttons
        url_btns = QHBoxLayout()
        self.btn_copy_url = QPushButton("📋 Copy Link")
        self.btn_copy_url.setCursor(Qt.PointingHandCursor)
        self.btn_copy_url.setStyleSheet("background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px;")
        self.btn_copy_url.clicked.connect(self._copy_url_to_clipboard)

        self.btn_browser = QPushButton("🌐 Test in Browser")
        self.btn_browser.setCursor(Qt.PointingHandCursor)
        self.btn_browser.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; border-radius: 6px; padding: 6px;")
        self.btn_browser.clicked.connect(self._open_in_browser)

        url_btns.addWidget(self.btn_copy_url)
        url_btns.addWidget(self.btn_browser)
        left_layout.addLayout(url_btns)

        # Instructions Card
        instr = QLabel(
            "📱 <b>Faculty Quick Punch Instructions:</b><br>"
            "1. Connect smartphone to institutional Wi-Fi.<br>"
            "2. Scan the QR code above with your camera app.<br>"
            "3. Select your Staff ID and tap <b>'Biometric Verify'</b>.<br>"
            "4. Authenticate via fingerprint or Face ID."
        )
        instr.setStyleSheet("background-color: #EFF6FF; color: #1E3A8A; padding: 10px; border-radius: 8px; font-size: 11px;")
        instr.setWordWrap(True)
        left_layout.addWidget(instr)
        left_layout.addStretch()

        content_layout.addWidget(left_card, stretch=4)

        # RIGHT PANEL: Real-Time Live Attendance Punches Table
        right_card = QGroupBox("Today's Live Biometric Punches (Real-Time)")
        right_card.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # Table Header Action Row
        tbl_top_bar = QHBoxLayout()
        self.lbl_punch_count = QLabel("Punches Today: 0")
        self.lbl_punch_count.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_punch_count.setStyleSheet("color: #2563EB;")
        tbl_top_bar.addWidget(self.lbl_punch_count)
        tbl_top_bar.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh Now")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 10px;")
        self.btn_refresh.clicked.connect(self.refresh_kiosk_data)
        tbl_top_bar.addWidget(self.btn_refresh)
        right_layout.addLayout(tbl_top_bar)

        # 7-Column QTableWidget
        self.tbl_punches = QTableWidget()
        self.tbl_punches.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_punches.setColumnCount(7)
        self.tbl_punches.setHorizontalHeaderLabels([
            "Time", "Staff ID", "Faculty Name", "Type", "Status", "Method", "Device / IP"
        ])
        self.tbl_punches.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_punches.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_punches.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_punches.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_punches.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_punches.setAlternatingRowColors(True)
        self.tbl_punches.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_punches.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_punches.verticalHeader().setVisible(False)
        self.tbl_punches.setStyleSheet(
            """
            QTableWidget {
                background-color: #FFFFFF;
                gridline-color: #E2E8F0;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #334155;
                font-weight: 700;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #CBD5E1;
            }
            """
        )
        right_layout.addWidget(self.tbl_punches)

        # Footer Status Bar
        footer_layout = QHBoxLayout()
        self.lbl_worker_indicator = QLabel("● Real-Time Stream Active (3s Background Polling)")
        self.lbl_worker_indicator.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11px;")
        footer_layout.addWidget(self.lbl_worker_indicator)
        footer_layout.addStretch()

        self.lbl_time_mode_badge = QLabel("Mode: NORMAL")
        self.lbl_time_mode_badge.setStyleSheet(
            "background-color: #E2E8F0; color: #475569; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;"
        )
        footer_layout.addWidget(self.lbl_time_mode_badge)

        right_layout.addLayout(footer_layout)
        content_layout.addWidget(right_card, stretch=7)

        root_layout.addLayout(content_layout)

    def _setup_shortcuts(self):
        """Keyboard shortcuts for kiosk operation."""
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self, self.admin_exit_kiosk)

    def keyPressEvent(self, event):
        """Anti-Tampering: Intercepts Ctrl+Shift+Q to allow Admin exit."""
        if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_Q:
            self.admin_exit_kiosk()
            return
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
            return
        super().keyPressEvent(event)

    def admin_exit_kiosk(self):
        """Safely exits kiosk full-screen mode and restores the LoginWindow."""
        logger.info("Admin exit triggered on BiometricKioskWindow. Restoring Login Window.")
        self.close()
        if self.parent() and hasattr(self.parent(), "show"):
            self.parent().show()
            self.parent().raise_()
            self.parent().activateWindow()

    def closeEvent(self, event):
        """Clean shutdown of timers and background worker thread upon OS window close."""
        if hasattr(self, "poll_timer") and self.poll_timer.isActive():
            self.poll_timer.stop()
        if hasattr(self, "clock_timer") and self.clock_timer.isActive():
            self.clock_timer.stop()
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
        event.accept()

    def _setup_background_worker(self):
        """Initializes the background QThread polling worker and 5-second QTimer."""
        self.worker = AttendancePollingWorker(self)
        self.worker.punches_loaded.connect(self._on_punches_loaded)
        self.worker.sync_status.connect(self._on_sync_status)
        self.worker.query_failed.connect(self._on_query_failed)

        # QTimer triggering background thread every 3000 ms (3 seconds)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(3000)
        self.poll_timer.timeout.connect(self._on_poll_timer_tick)
        self.poll_timer.start()

    def _update_clock(self):
        """Updates clock display using TimeService (handles simulated test mode)."""
        current_dt = TimeService.get_current_time()
        is_test = TimeService.is_test_mode()
        time_text = current_dt.strftime("%A, %d %B %Y  |  %I:%M:%S %p")
        if is_test:
            self.lbl_clock.setText(f"🧪 [TEST CLOCK] {time_text}")
            self.lbl_clock.setStyleSheet("color: #FBBF24; background: #78350F; padding: 6px 14px; border-radius: 6px; font-weight: bold;")
            if hasattr(self, "lbl_time_mode_badge"):
                self.lbl_time_mode_badge.setText("Mode: TEST (Simulated)")
                self.lbl_time_mode_badge.setStyleSheet("background-color: #FEF3C7; color: #B45309; padding: 3px 8px; border-radius: 4px; font-weight: bold;")
        else:
            self.lbl_clock.setText(f"🕒 {time_text}")
            self.lbl_clock.setStyleSheet("color: #F8FAFC; background: #334155; padding: 6px 14px; border-radius: 6px; font-weight: bold;")
            if hasattr(self, "lbl_time_mode_badge"):
                self.lbl_time_mode_badge.setText("Mode: NORMAL (Live)")
                self.lbl_time_mode_badge.setStyleSheet("background-color: #DCFCE7; color: #166534; padding: 3px 8px; border-radius: 4px; font-weight: bold;")

    @Slot()
    def toggle_fullscreen(self):
        """Toggles between full screen and windowed mode."""
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("⛶ Fullscreen (F11)")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("🗗 Exit Fullscreen (Esc)")

    def _exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("⛶ Fullscreen (F11)")

    @Slot()
    def refresh_kiosk_data(self):
        """Triggers the background worker immediately."""
        if not self.worker.isRunning():
            self.worker.start()

    @Slot()
    def _on_poll_timer_tick(self):
        """Invoked every 3 seconds by QTimer. Refreshes dynamic rotating TOTP-style QR token."""
        try:
            from utils.kiosk_token import generate_kiosk_qr_token
            token_info = generate_kiosk_qr_token(window_seconds=30)
            curr_window = token_info["window"]
            if getattr(self, "_last_qr_window", -1) != curr_window:
                self._last_qr_window = curr_window
                base_url = getattr(self, "server_url", "http://erp.sys:8000/punch-interface")
                clean_base = base_url.split("?")[0]
                full_qr_url = f"{clean_base}?token={token_info['token']}"
                self._render_qr_code(full_qr_url)
        except Exception as e:
            logger.debug(f"Rotating QR tick error: {e}")

        if not self.worker.isRunning():
            self.worker.start()

    @Slot()
    def activate_biometric_service(self):
        """Manually activates or reconnects the biometric daemon service."""
        ensure_biometric_daemon_running(port=8000)
        self.refresh_kiosk_data()

    @Slot(str, str, str)
    def _on_sync_status(self, daemon_status: str, url: str, message: str):
        """Safely updates endpoint and status on the main GUI thread."""
        self.daemon_status = daemon_status.upper()
        if url != self.server_url:
            self.server_url = url
            self.lbl_url.setText(f"URL: {url}")
            self._render_qr_code(url)

        if "ONLINE" in self.daemon_status:
            badge_color = "#10B981"
            tag = "HTTPS CLOUD" if "https" in url.lower() else "CAMPUS LAN / erp.sys"
            self.lbl_status.setText(f"ONLINE ({tag})")
            self.lbl_status.setStyleSheet(
                f"background-color: {badge_color}; color: #FFFFFF; padding: 4px 10px; border-radius: 6px; font-weight: bold;"
            )
            if hasattr(self, "btn_activate_service"):
                self.btn_activate_service.setVisible(False)
        else:
            self.lbl_status.setText("DAEMON INACTIVE")
            self.lbl_status.setStyleSheet(
                "background-color: #EF4444; color: #FFFFFF; padding: 4px 10px; border-radius: 6px; font-weight: bold;"
            )
            if hasattr(self, "btn_activate_service"):
                self.btn_activate_service.setVisible(True)

    def _render_qr_code(self, url: str):
        """Generates a crisp high-res QR code pixmap and sets it on the scaled QLabel."""
        if not url:
            return
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            pix = QPixmap()
            pix.loadFromData(buf.getvalue(), "PNG")
            self.lbl_qr.setPixmap(pix)
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")

    @Slot(list)
    def _on_punches_loaded(self, records: List[Dict[str, Any]]):
        """Safely populates the QTableWidget with today's real-time attendance records."""
        self.tbl_punches.setRowCount(len(records))
        self.lbl_punch_count.setText(f"Punches Today: {len(records)}")

        for row_idx, r in enumerate(records):
            # 0. Time
            login_time = str(r.get("login_time") or "--:--:--")
            logout_time = str(r.get("logout_time") or "")
            punch_type = str(r.get("punch_type") or "CHECK_IN").upper()
            display_time = logout_time if punch_type == "CHECK_OUT" and logout_time else login_time

            item_time = QTableWidgetItem(display_time)
            item_time.setTextAlignment(Qt.AlignCenter)
            item_time.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tbl_punches.setItem(row_idx, 0, item_time)

            # 1. Staff ID
            item_id = QTableWidgetItem(str(r.get("employee_code", "")))
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self.tbl_punches.setItem(row_idx, 1, item_id)

            # 2. Faculty Name
            item_name = QTableWidgetItem(str(r.get("faculty_name", "")))
            self.tbl_punches.setItem(row_idx, 2, item_name)

            # 3. Type (CHECK IN / CHECK OUT)
            item_type = QTableWidgetItem("CHECK OUT" if punch_type == "CHECK_OUT" else "CHECK IN")
            item_type.setTextAlignment(Qt.AlignCenter)
            item_type.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if punch_type == "CHECK_OUT":
                item_type.setForeground(QColor("#7C3AED"))
            else:
                item_type.setForeground(QColor("#0284C7"))
            self.tbl_punches.setItem(row_idx, 3, item_type)

            # 4. Status
            status_val = str(r.get("status") or "PRESENT").upper()
            late_min = int(r.get("late_minutes") or 0)
            status_text = status_val
            if late_min > 0:
                status_text = f"LATE (+{late_min}m)"

            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            item_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if late_min > 0 or status_val == "ABSENT":
                item_status.setForeground(QColor("#DC2626"))
            else:
                item_status.setForeground(QColor("#16A34A"))
            self.tbl_punches.setItem(row_idx, 4, item_status)

            # 5. Method
            method = str(r.get("verification_method") or "WEBAUTHN")
            item_method = QTableWidgetItem("📱 " + method)
            item_method.setTextAlignment(Qt.AlignCenter)
            self.tbl_punches.setItem(row_idx, 5, item_method)

            # 6. Device / IP
            device = str(r.get("device_id") or "Mobile Phone")
            ip = str(r.get("ip_address") or "")
            item_dev = QTableWidgetItem(f"{device} ({ip})" if ip else device)
            self.tbl_punches.setItem(row_idx, 6, item_dev)

    @Slot(str)
    def _on_query_failed(self, error_msg: str):
        """Worker error feedback."""
        logger.warning(f"Kiosk polling worker warning: {error_msg}")

    def _copy_url_to_clipboard(self):
        if self.server_url:
            QApplication.clipboard().setText(self.server_url)
            QMessageBox.information(self, "Link Copied", f"Biometric URL copied to clipboard:\n\n{self.server_url}")

    def _open_in_browser(self):
        if self.server_url:
            QDesktopServices.openUrl(QUrl(self.server_url))

    def closeEvent(self, event):
        """Clean teardown on window close."""
        self.poll_timer.stop()
        self.clock_timer.stop()
        if self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
        super().closeEvent(event)
