import sys
from pathlib import Path

# Automatically ensure venv site-packages is in sys.path if running with system python
BASE_DIR = Path(__file__).resolve().parent
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from PySide6.QtWidgets import QApplication, QMessageBox
from config.settings import settings
from utils.logger import logger
from utils.exceptions import ERPBaseException
from ui.login_window import LoginWindow
from ui.biometric_kiosk_window import BiometricKioskWindow
from ui.main_window import MainWindow, ModernMainWindow
from ui.styles import apply_enterprise_theme
from services.mobile_punch_service import ensure_biometric_daemon_running


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to capture unhandled exceptions gracefully."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical(
        "Unhandled exception encountered in application thread",
        exc_info=(exc_type, exc_value, exc_traceback),
    )

    err_msg = f"An unexpected system error occurred:\n\n{exc_value}"
    if isinstance(exc_value, ERPBaseException):
        err_msg = f"ERP System Error: {exc_value.message}"

    # Display error box if QApplication is active
    if QApplication.instance():
        QMessageBox.critical(
            None,
            "Faculty ERP - System Error",
            err_msg,
        )


def main():
    """Main execution function for Phase 1 application shell."""
    sys.excepthook = handle_uncaught_exception

    logger.info("==================================================")
    logger.info(f"Starting {settings.APP_NAME} (Phase 1 Foundation)")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info("==================================================")

    # Initialize PySide6 QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    app.setOrganizationName("MCA Project")

    # Apply enterprise styling, modern typography, web data grids & sleek scrollbars globally
    apply_enterprise_theme(app)

    # Automatically ensure Biometric Microservice daemon is running
    ensure_biometric_daemon_running(port=8000)

    # Boot Biometric Terminal (Kiosk Mode) automatically on startup simultaneously
    kiosk_window = BiometricKioskWindow()
    kiosk_window.show()

    # Workflow: Boot into dedicated LoginWindow
    login_window = LoginWindow()
    login_window.kiosk_window = kiosk_window
    login_window.show()

    logger.info("Biometric Terminal (Kiosk Mode) and LoginWindow launched successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
