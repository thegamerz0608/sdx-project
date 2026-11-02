"""
Phase 1 Foundation Unit Tests
Verifies core environment loading, logger, exception hierarchy, database module, and PySide6 UI shell.
"""
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from config.settings import settings
from utils.exceptions import ERPBaseException, DatabaseConnectionError, ConfigurationError
from utils.logger import logger, get_logger
from database.connection import test_connection as db_test_connection, get_driver_name
from ui.main_window import MainWindow


def test_settings_loading():
    """Verify that settings are loaded cleanly with defaults."""
    assert settings.APP_NAME == "Faculty Attendance & Leave ERP"
    assert settings.DB_HOST is not None
    assert isinstance(settings.DB_PORT, int)
    db_config = settings.get_db_config()
    assert "host" in db_config
    assert "port" in db_config
    assert "user" in db_config
    assert "password" in db_config
    assert "database" in db_config


def test_custom_exceptions():
    """Verify exception hierarchy and formatting."""
    exc = DatabaseConnectionError("Test database connection failure", original_error=ValueError("Invalid port"))
    assert exc.message == "Test database connection failure"
    assert isinstance(exc, ERPBaseException)
    assert "Test database connection failure" in str(exc)
    assert "Invalid port" in str(exc)


def test_logger_file_and_console():
    """Verify logger setup and log file creation."""
    test_logger = get_logger("test_module")
    test_logger.info("Executing test log entry for Phase 1 verification.")
    
    log_file = settings.LOG_DIR / "app.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Executing test log entry for Phase 1 verification" in content


def test_database_connection_module():
    """Verify database connection test returns boolean tuple without throwing uncaught exceptions."""
    driver = get_driver_name()
    assert isinstance(driver, str)
    
    success, msg = db_test_connection()
    assert isinstance(success, bool)
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_pyside6_app_shell():
    """Verify PySide6 Application Shell initializes correctly in off-screen mode."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = MainWindow()
    assert window is not None
    assert "Faculty Attendance & Leave ERP" in window.windowTitle()
    assert window.db_status_badge is not None
