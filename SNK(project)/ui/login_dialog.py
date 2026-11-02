
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Automatically include the virtual environment site-packages if present.
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"

if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QGroupBox,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor

from services.auth_service import auth_service, UserSession
from utils.exceptions import AuthenticationError
from utils.logger import get_logger

logger = get_logger("ui.login_dialog")


class LoginDialog(QDialog):
    """Modal login dialog for the Faculty Attendance ERP."""

    login_successful = Signal(UserSession)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Faculty Attendance ERP - Authentication")
        self.setMinimumSize(500, 580)
        self.setModal(True)

        # Prevent inherited application palettes from making input text
        # unreadable. Explicit widget styles are also applied below.
        self.setAutoFillBackground(True)

        self._apply_stylesheet()
        self._init_ui()

    def _apply_stylesheet(self):
        """Apply the login dialog's enterprise-style theme."""

        self.setStyleSheet("""
            QDialog {
                background-color: #f4f6f9;
                color: #263238;
            }

            QGroupBox {
                font-weight: bold;
                color: #263238;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                margin-top: 12px;
                padding: 12px;
                background-color: #ffffff;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #2c3e50;
            }

            QLabel {
                color: #263238;
            }

            QLineEdit {
                color: #222222;
                background-color: #ffffff;
                selection-color: #ffffff;
                selection-background-color: #2b579a;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 13px;
                min-height: 20px;
            }

            QLineEdit:focus {
                color: #222222;
                background-color: #ffffff;
                border: 2px solid #2b579a;
            }

            QLineEdit:disabled {
                color: #777777;
                background-color: #eeeeee;
            }

            QCheckBox {
                color: #263238;
                spacing: 8px;
            }

            QCheckBox:disabled {
                color: #777777;
            }

            QPushButton {
                background-color: #2b579a;
                color: #ffffff;
                border: none;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #1e3d6e;
            }

            QPushButton:pressed {
                background-color: #152b4e;
            }

            QPushButton:disabled {
                background-color: #aab4c1;
                color: #f5f5f5;
            }

            QPushButton[class="preset-btn"] {
                background-color: #e9ecef;
                color: #2c3e50;
                border: 1px solid #ced4da;
                padding: 7px 8px;
                font-size: 11px;
                font-weight: 600;
            }

            QPushButton[class="preset-btn"]:hover {
                background-color: #dee2e6;
                border-color: #2b579a;
            }

            QLabel[class="error-lbl"] {
                color: #c62828;
                font-weight: bold;
                font-size: 12px;
            }
        """)

    def _configure_input(self, field: QLineEdit):
        """Configure readable, editable input fields."""

        field.setEnabled(True)
        field.setReadOnly(False)
        field.setMinimumHeight(38)

        # Explicit palette provides a fallback for text rendering.
        palette = field.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor("#222222"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#222222"))
        palette.setColor(
            QPalette.ColorRole.Highlight, QColor("#2b579a")
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText, QColor("#ffffff")
        )
        field.setPalette(palette)

        field.setStyleSheet("""
            QLineEdit {
                color: #222222;
                background-color: #ffffff;
                selection-color: #ffffff;
                selection-background-color: #2b579a;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 13px;
            }

            QLineEdit:focus {
                color: #222222;
                background-color: #ffffff;
                border: 2px solid #2b579a;
            }

            QLineEdit:disabled {
                color: #777777;
                background-color: #eeeeee;
            }
        """)

    def _init_ui(self):
        """Construct the login form and its controls."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        # -------------------------------------------------
        # Header banner
        # -------------------------------------------------
        header_frame = QFrame()
        header_frame.setObjectName("loginHeader")
        header_frame.setStyleSheet("""
            QFrame#loginHeader {
                background-color: #1b365d;
                border-radius: 6px;
            }

            QFrame#loginHeader QLabel {
                background-color: transparent;
            }
        """)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)
        header_layout.setSpacing(8)

        title_lbl = QLabel("Faculty ERP Login")
        title_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #ffffff;")

        subtitle_lbl = QLabel("AI-Enabled Attendance & Leave ERP")
        subtitle_lbl.setFont(QFont("Segoe UI", 11))
        subtitle_lbl.setStyleSheet("color: #cfd8dc;")

        header_layout.addWidget(title_lbl)
        header_layout.addSpacing(10)
        header_layout.addWidget(subtitle_lbl)

        layout.addWidget(header_frame)

        # -------------------------------------------------
        # Credentials group
        # -------------------------------------------------
        form_group = QGroupBox("Enter Account Credentials")
        form_layout = QVBoxLayout(form_group)
        form_layout.setContentsMargins(12, 18, 12, 12)
        form_layout.setSpacing(8)

        username_label = QLabel("Username / Employee ID:")
        username_label.setStyleSheet(
            "font-weight: bold; color: #263238;"
        )
        form_layout.addWidget(username_label)

        self.txt_username = QLineEdit()
        self.txt_username.setObjectName("usernameInput")
        self.txt_username.setPlaceholderText(
            "Enter username (e.g. admin, hod_mca, fac_rahul)"
        )
        self._configure_input(self.txt_username)

        form_layout.addWidget(self.txt_username)

        password_label = QLabel("Password:")
        password_label.setStyleSheet(
            "font-weight: bold; color: #263238;"
        )
        form_layout.addWidget(password_label)

        self.txt_password = QLineEdit()
        self.txt_password.setObjectName("passwordInput")
        self.txt_password.setPlaceholderText("Enter password")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._configure_input(self.txt_password)

        form_layout.addWidget(self.txt_password)

        # Show/hide password
        self.chk_show_pass = QCheckBox("Show Password")
        self.chk_show_pass.toggled.connect(
            self._toggle_password_visibility
        )
        form_layout.addWidget(self.chk_show_pass)

        # Login error
        self.lbl_error = QLabel("")
        self.lbl_error.setProperty("class", "error-lbl")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet("""
            color: #c62828;
            font-weight: bold;
            font-size: 12px;
        """)
        form_layout.addWidget(self.lbl_error)

        layout.addWidget(form_group)

        # -------------------------------------------------
        # Strict Manual Authentication Policy (No Autofill)
        # -------------------------------------------------
        auth_note = QLabel("🔒 Strict Manual Authentication: Type your institutional username and password.")
        auth_note.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic; margin-top: 4px;")
        auth_note.setAlignment(Qt.AlignCenter)
        layout.addWidget(auth_note)

        # -------------------------------------------------
        # Cancel and login buttons
        # -------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(15)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: #ffffff;
            }

            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        self.btn_login = QPushButton("Log In")
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self.handle_login)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_login)

        layout.addLayout(btn_row)

        # Keyboard navigation
        self.setTabOrder(self.txt_username, self.txt_password)
        self.setTabOrder(self.txt_password, self.chk_show_pass)
        self.setTabOrder(self.chk_show_pass, btn_cancel)
        self.setTabOrder(btn_cancel, self.btn_login)

        self.txt_username.setFocus(Qt.FocusReason.OtherFocusReason)

    def _toggle_password_visibility(self, checked: bool):
        """Toggle password masking without changing its value."""

        if checked:
            self.txt_password.setEchoMode(
                QLineEdit.EchoMode.Normal
            )
        else:
            self.txt_password.setEchoMode(
                QLineEdit.EchoMode.Password
            )

    def handle_login(self):
        """Authenticate using the existing AuthService."""

        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        self.lbl_error.clear()

        if not username or not password:
            self.lbl_error.setText(
                "Please enter both username and password."
            )
            if not username:
                self.txt_username.setFocus()
            else:
                self.txt_password.setFocus()
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in...")

        try:
            session = auth_service.login(username, password)

            logger.info(
                "Successful login for username '%s'.", username
            )

            self.login_successful.emit(session)
            self.accept()

        except AuthenticationError as exc:
            self.lbl_error.setText(
                f"Login Failed: {exc.message}"
            )
            logger.warning(
                "Login failed for username '%s': %s",
                username,
                exc.message,
            )

        except Exception:
            # Avoid exposing internal exception details to the login user.
            self.lbl_error.setText(
                "A system error occurred. Please try again."
            )
            logger.exception(
                "Unexpected error during login for username '%s'.",
                username,
            )

        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Log In")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    dlg = LoginDialog()

    def on_success(session):
        print(f"Standalone Login Succeeded: {session}")

    dlg.login_successful.connect(on_success)
    dlg.exec()
