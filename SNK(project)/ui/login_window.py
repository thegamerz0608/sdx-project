"""
Dedicated Authentication Window (LoginWindow) — Modern Split Layout
Features a dark blue top banner, left-side welcome & support panel, and right-side white login card
with Staff ID input, password, numerical CAPTCHA verification, and dark blue Submit button.
"""
import sys
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Automatically ensure venv site-packages is in sys.path if present
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QCheckBox,
    QGraphicsDropShadowEffect,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, Slot, QRect
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPen

from config.settings import settings
from services.auth_service import auth_service, UserSession
from utils.exceptions import AuthenticationError
from utils.logger import get_logger

logger = get_logger("ui.login_window")


def generate_captcha_pixmap(code: str, width: int = 140, height: int = 42) -> QPixmap:
    """Renders a numerical CAPTCHA image with subtle distortion lines using pure PySide6."""
    # HiDPI-aware pixmap so the image stays crisp on scaled displays
    dpr = 1.0
    screen = QApplication.primaryScreen()
    if screen is not None:
        dpr = max(1.0, screen.devicePixelRatio())

    pix = QPixmap(int(width * dpr), int(height * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(QColor("#F1F5F9"))

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer border
    painter.setPen(QPen(QColor("#CBD5E1"), 1.5))
    painter.drawRect(0, 0, width - 1, height - 1)

    # Subtle noise lines
    painter.setPen(QPen(QColor("#94A3B8"), 1))
    for _ in range(5):
        x1 = secrets.randbelow(width - 4) + 2
        y1 = secrets.randbelow(height - 4) + 2
        x2 = secrets.randbelow(width - 4) + 2
        y2 = secrets.randbelow(height - 4) + 2
        painter.drawLine(x1, y1, x2, y2)

    # Numerical code with spacing
    font = QFont("Courier New", 18, QFont.Weight.Bold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
    painter.setFont(font)
    painter.setPen(QPen(QColor("#1E3A8A"), 1))
    painter.drawText(QRect(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, code)
    painter.end()
    return pix


class LoginWindow(QMainWindow):
    """
    Dedicated Modern Standalone Login Window with Split Layout & CAPTCHA.
    Acts as the strict primary entry point upon application boot.
    """
    login_successful = Signal(UserSession)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{settings.APP_NAME} - Institutional Portal Sign-In")
        self.resize(960, 700)
        self.setMinimumSize(900, 680)
        self.main_window = None
        self.kiosk_window = None
        self.current_captcha_code = ""

        self._apply_stylesheet()
        self._init_ui()
        self.regenerate_captcha()

    def _apply_stylesheet(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0F172A;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            #topHeaderBanner {
                background-color: #1E3A8A;
                border-bottom: 2px solid #2563EB;
            }
            #bannerTitle {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            #bannerSub {
                color: #93C5FD;
                font-size: 11px;
            }
            #welcomePanel {
                background-color: #1E293B;
                border-radius: 12px;
                border: 1px solid #334155;
            }
            #welcomeHeader {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: 800;
            }
            #welcomeSub {
                color: #94A3B8;
                font-size: 13px;
            }
            #supportCard {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            #supportText {
                color: #CBD5E1;
                font-size: 11.5px;
            }
            #btnLaunchKiosk {
                background-color: #334155;
                color: #FFFFFF;
                border: 1px solid #475569;
                border-radius: 7px;
                padding: 9px;
                font-size: 12px;
                font-weight: 600;
            }
            #btnLaunchKiosk:hover {
                background-color: #475569;
            }
            #loginCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E2E8F0;
            }
            #loginTitle {
                color: #0F172A;
                font-size: 22px;
                font-weight: 800;
            }
            #loginSub {
                color: #64748B;
                font-size: 12.5px;
            }
            #fieldLabel {
                color: #334155;
                font-size: 12px;
                font-weight: 700;
            }
            #inputField {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 7px;
                padding: 8px 12px;
                font-size: 13px;
            }
            #inputField:focus {
                border: 2px solid #2563EB;
                background-color: #FFFFFF;
            }
            #btnRefreshCaptcha {
                background-color: #F1F5F9;
                color: #1E3A8A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            #btnRefreshCaptcha:hover {
                background-color: #E2E8F0;
            }
            #btnSubmit {
                background-color: #1E3A8A;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                padding: 10px;
                font-size: 14px;
                font-weight: 700;
            }
            #btnSubmit:hover {
                background-color: #2563EB;
            }
            #btnSubmit:pressed {
                background-color: #1E40AF;
            }
            #btnSubmit:disabled {
                background-color: #94A3B8;
                color: #E2E8F0;
            }
            #errorLabel {
                background-color: #FEE2E2;
                color: #B91C1C;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            """
        )

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ----------------------------------------------------------------------
        # 1. Top Dark Blue Header Banner
        # ----------------------------------------------------------------------
        top_banner = QFrame()
        top_banner.setObjectName("topHeaderBanner")
        top_banner.setFixedHeight(64)
        banner_layout = QHBoxLayout(top_banner)
        banner_layout.setContentsMargins(24, 0, 24, 0)
        banner_layout.setSpacing(14)

        lbl_crest = QLabel("🏛️")
        lbl_crest.setStyleSheet("font-size: 28px; background: transparent;")
        banner_layout.addWidget(lbl_crest)

        v_btext = QVBoxLayout()
        v_btext.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        v_btext.setSpacing(1)

        lbl_btitle = QLabel("FACULTY ATTENDANCE & LEAVE MANAGEMENT ERP")
        lbl_btitle.setObjectName("bannerTitle")
        lbl_bsub = QLabel("Institutional Academic & Human Resources Enterprise Portal")
        lbl_bsub.setObjectName("bannerSub")
        v_btext.addWidget(lbl_btitle)
        v_btext.addWidget(lbl_bsub)
        banner_layout.addLayout(v_btext)

        banner_layout.addStretch()

        lbl_sec = QLabel("🔒 TLS 1.3 Secure • Institutional Access Only")
        lbl_sec.setStyleSheet(
            "color: #93C5FD; font-size: 11px; font-weight: 600; background: transparent;"
        )
        banner_layout.addWidget(lbl_sec)

        root_layout.addWidget(top_banner)

        # ----------------------------------------------------------------------
        # 2. Main Split Body Area
        # ----------------------------------------------------------------------
        body_container = QWidget()
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(36, 24, 36, 24)
        body_layout.setSpacing(28)

        # --- LEFT SIDE: Welcome Message & Institutional Support ---
        welcome_panel = QFrame()
        welcome_panel.setObjectName("welcomePanel")
        welcome_layout = QVBoxLayout(welcome_panel)
        welcome_layout.setContentsMargins(28, 28, 28, 28)
        welcome_layout.setSpacing(16)

        lbl_whead = QLabel("Welcome to ERP:")
        lbl_whead.setObjectName("welcomeHeader")
        welcome_layout.addWidget(lbl_whead)

        lbl_wsub = QLabel(
            "Welcome to the AI-Enabled Faculty Attendance, Leave & Substitute Management System.\n\n"
            "Please authenticate using your institutional Staff ID and credentials to access your "
            "designated role dashboard."
        )
        lbl_wsub.setObjectName("welcomeSub")
        lbl_wsub.setWordWrap(True)
        welcome_layout.addWidget(lbl_wsub)

        # Key Pillars
        features_box = QVBoxLayout()
        features_box.setSpacing(8)
        for icon, feat in [
            ("⚡", "Real-time Biometric Check-In & Grace Ledger"),
            ("📝", "Multi-Stage Leave Review (HOD → HR → Principal)"),
            ("🧠", "Pure-NumPy NLP Reason Classifier & Softmax ML"),
            ("🛡️", "Strict Role-Based Access Control (RBAC)"),
        ]:
            row = QHBoxLayout()
            lbl_ico = QLabel(icon)
            lbl_ico.setFixedWidth(24)
            lbl_ico.setStyleSheet("font-size: 14px; background: transparent;")
            lbl_txt = QLabel(feat)
            lbl_txt.setStyleSheet(
                "color: #E2E8F0; font-size: 12px; font-weight: 500; background: transparent;"
            )
            lbl_txt.setWordWrap(True)
            row.addWidget(lbl_ico)
            row.addWidget(lbl_txt, stretch=1)
            features_box.addLayout(row)
        welcome_layout.addLayout(features_box)

        welcome_layout.addStretch()

        # Support Information Card
        support_card = QFrame()
        support_card.setObjectName("supportCard")
        sc_layout = QVBoxLayout(support_card)
        sc_layout.setContentsMargins(12, 10, 12, 10)
        sc_layout.setSpacing(4)

        lbl_sc_title = QLabel("<b>Need Support or Staff ID Assistance?</b>")
        lbl_sc_title.setStyleSheet("color: #60A5FA; font-size: 11.5px; background: transparent;")
        sc_layout.addWidget(lbl_sc_title)

        # NOTE: rich text ignores "\n", so <br> is required here
        lbl_sc_info = QLabel(
            "Contact Systems Administration &amp; Registrar Desk:<br>"
            "📧 <code>helpdesk@erp.edu</code> &nbsp;|&nbsp; 📞 Internal Ext. 4001/4002<br>"
            "Room 102, Academic Block A (08:30 – 17:30)"
        )
        lbl_sc_info.setObjectName("supportText")
        lbl_sc_info.setTextFormat(Qt.TextFormat.RichText)
        lbl_sc_info.setWordWrap(True)
        sc_layout.addWidget(lbl_sc_info)
        welcome_layout.addWidget(support_card)

        # Standalone Lobby Biometric Terminal (Kiosk Mode) decoupled from Login page.
        # Hidden by default; call self.btn_launch_kiosk.setVisible(True) to expose it.
        self.btn_launch_kiosk = QPushButton("🖥️ Launch Biometric Terminal (Kiosk Mode)")
        self.btn_launch_kiosk.setObjectName("btnLaunchKiosk")
        self.btn_launch_kiosk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_launch_kiosk.setToolTip(
            "Open full-screen lobby terminal for faculty QR biometric check-in"
        )
        self.btn_launch_kiosk.clicked.connect(self.launch_biometric_kiosk)
        self.btn_launch_kiosk.setVisible(False)
        welcome_layout.addWidget(self.btn_launch_kiosk)

        body_layout.addWidget(welcome_panel, stretch=5)

        # --- RIGHT SIDE: White Login Card with CAPTCHA ---
        login_card = QFrame()
        login_card.setObjectName("loginCard")

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(login_card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        login_card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(32, 24, 32, 24)
        card_layout.setSpacing(6)

        lbl_ltitle = QLabel("Login")
        lbl_ltitle.setObjectName("loginTitle")
        card_layout.addWidget(lbl_ltitle)

        lbl_lsub = QLabel("Sign in with your institutional Staff ID")
        lbl_lsub.setObjectName("loginSub")
        card_layout.addWidget(lbl_lsub)

        # Error notification banner (hidden by default)
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("errorLabel")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        card_layout.addWidget(self.lbl_error)

        # Staff ID Field
        lbl_staff = QLabel("Staff Id:")
        lbl_staff.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_staff)

        self.txt_username = QLineEdit()
        self.txt_username.setObjectName("inputField")
        self.txt_username.setPlaceholderText("Enter Staff ID (e.g. EMP001, HR001)")
        # Backwards-compatible aliases used elsewhere in the app
        self.txt_staff_id = self.txt_username
        self.txt_employee_id = self.txt_username
        self.txt_username.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.txt_username)

        # Password Field
        lbl_pwd = QLabel("Password:")
        lbl_pwd.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_pwd)

        self.txt_password = QLineEdit()
        self.txt_password.setObjectName("inputField")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Enter your password")
        self.txt_password.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.txt_password)

        # Show password checkbox
        self.chk_show = QCheckBox("Show password")
        self.chk_show.setStyleSheet("color: #64748B; font-size: 11px;")
        self.chk_show.toggled.connect(self._toggle_password_visibility)
        card_layout.addWidget(self.chk_show)

        # CAPTCHA Row
        lbl_cap_title = QLabel("Security Code:")
        lbl_cap_title.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_cap_title)

        cap_row = QHBoxLayout()
        cap_row.setSpacing(8)

        self.lbl_captcha_img = QLabel()
        self.lbl_captcha_img.setFixedSize(140, 42)
        self.lbl_captcha_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap_row.addWidget(self.lbl_captcha_img)

        self.btn_refresh_captcha = QPushButton("🔄")
        self.btn_refresh_captcha.setObjectName("btnRefreshCaptcha")
        self.btn_refresh_captcha.setFixedSize(42, 42)
        self.btn_refresh_captcha.setToolTip("Generate new CAPTCHA numbers")
        self.btn_refresh_captcha.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_captcha.clicked.connect(self.regenerate_captcha)
        cap_row.addWidget(self.btn_refresh_captcha)
        cap_row.addStretch()
        card_layout.addLayout(cap_row)

        # Type captcha input
        lbl_type_cap = QLabel("Type captcha:")
        lbl_type_cap.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_type_cap)

        self.txt_captcha = QLineEdit()
        self.txt_captcha.setObjectName("inputField")
        self.txt_captcha.setPlaceholderText("Type the numbers shown above")
        self.txt_captcha.setMaxLength(4)
        self.txt_captcha.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.txt_captcha)

        card_layout.addSpacing(6)

        # Submit Button
        self.btn_login = QPushButton("Submit")
        self.btn_login.setObjectName("btnSubmit")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self.handle_login)
        self.btn_submit = self.btn_login
        card_layout.addWidget(self.btn_login)

        card_layout.addStretch()

        body_layout.addWidget(login_card, stretch=5)
        root_layout.addWidget(body_container, stretch=1)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    def regenerate_captcha(self):
        """Generates a random 4-digit numerical CAPTCHA and renders the image."""
        num = secrets.randbelow(9000) + 1000  # 1000–9999
        self.current_captcha_code = str(num)
        pix = generate_captcha_pixmap(self.current_captcha_code, 140, 42)
        self.lbl_captcha_img.setPixmap(pix)
        # Strict manual entry: CAPTCHA field remains blank by default
        self.txt_captcha.setText("")

    def _toggle_password_visibility(self, checked: bool):
        self.txt_password.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _show_error(self, message: str):
        self.lbl_error.setText(message)
        self.lbl_error.setVisible(True)

    def clear_fields(self):
        """Clears inputs and resets error state upon logout."""
        self.txt_username.setText("")
        self.txt_password.setText("")
        self.txt_captcha.setText("")
        self.chk_show.setChecked(False)
        self.lbl_error.setVisible(False)
        self.regenerate_captcha()
        self.txt_username.setFocus()

    # ----------------------------------------------------------------------
    # Login flow
    # ----------------------------------------------------------------------
    @Slot()
    def handle_login(self):
        """
        Validates CAPTCHA locally before querying database,
        authenticates user credentials, and transitions to ModernMainWindow.
        """
        # Ignore re-entrant triggers (e.g. Enter pressed while authenticating)
        if not self.btn_login.isEnabled():
            return

        staff_id = self.txt_username.text().strip()
        # Passwords must NOT be stripped: spaces can be part of a valid password
        password = self.txt_password.text()
        typed_captcha = self.txt_captcha.text().strip()

        self.lbl_error.setVisible(False)

        # 1. Required field validation
        if not staff_id or not password:
            self._show_error("Please enter both Staff ID and Password.")
            return

        # 2. Local CAPTCHA validation check
        if not typed_captcha or typed_captcha != self.current_captcha_code:
            self._show_error("Incorrect CAPTCHA code. Please type the numbers shown.")
            self.regenerate_captcha()
            self.txt_captcha.setFocus()
            return

        # 3. Authenticate via AuthService (using Staff ID or username)
        session = None
        try:
            self.btn_login.setEnabled(False)
            self.btn_login.setText("Authenticating...")
            QApplication.processEvents()

            session = auth_service.login(staff_id, password)

        except AuthenticationError as exc:
            self._show_error(getattr(exc, "message", None) or str(exc))
            self.regenerate_captcha()
            self.txt_password.selectAll()
            self.txt_password.setFocus()
        except Exception as exc:
            logger.exception("Unexpected error during login")
            self._show_error(f"Login error: {exc}")
            self.regenerate_captcha()
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Submit")

        if session is None:
            return

        logger.info(f"Login successful for {session.username} ({session.role})")
        self._open_main_window(session)

    def _open_main_window(self, session: UserSession):
        """Creates and shows the main window; restores the login screen if that fails."""
        try:
            from ui.main_window import ModernMainWindow

            # Dispose of any previous main window from an earlier session
            if self.main_window is not None:
                self.main_window.close()
                self.main_window.deleteLater()
                self.main_window = None

            self.main_window = ModernMainWindow(login_window=self)
            self.login_successful.emit(session)

            # Don't keep credentials sitting in the form
            self.txt_password.clear()
            self.txt_captcha.clear()
            self.chk_show.setChecked(False)

            self.hide()
            self.main_window.show()
        except Exception as exc:
            logger.exception("Failed to open main window")
            self.main_window = None
            self.show()
            self.regenerate_captcha()
            self._show_error(f"Could not open the dashboard: {exc}")

    def launch_biometric_kiosk(self):
        """Launches the standalone lobby Biometric Attendance Kiosk in frameless full-screen mode."""
        try:
            from ui.biometric_kiosk_window import BiometricKioskWindow

            if self.kiosk_window is None:
                self.kiosk_window = BiometricKioskWindow(self)
            self.hide()
            self.kiosk_window.showFullScreen()
            self.kiosk_window.raise_()
            self.kiosk_window.activateWindow()
        except Exception as exc:
            logger.exception("Failed to launch biometric kiosk")
            self.show()
            self._show_error(f"Could not launch kiosk: {exc}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec())