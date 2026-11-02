"""
Centralized Logging System for Faculty ERP
Provides console and file logging.
"""
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.settings import settings


def setup_logger(name: str = "FacultyERP") -> logging.Logger:
    """Configures and returns a logger instance with console and rotating file handlers."""
    logger_inst = logging.getLogger(name)

    # Set level based on settings
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logger_inst.setLevel(log_level)

    # Prevent duplicate handlers if re-initialized
    if logger_inst.handlers:
        return logger_inst

    # Formatter definition
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger_inst.addHandler(console_handler)

    # Rotating File Handler (Max 5MB per log file, up to 5 backups)
    log_file_path: Path = settings.LOG_DIR / "app.log"
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger_inst.addHandler(file_handler)

    return logger_inst


# Global singleton logger instance
logger = setup_logger("FacultyERP")


def get_logger(module_name: str) -> logging.Logger:
    """Returns a child logger for a specific module."""
    return logger.getChild(module_name)
