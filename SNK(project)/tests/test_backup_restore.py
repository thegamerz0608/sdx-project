"""
Unit Tests for Phase 17: System Backup, Restore, Archival & Diagnostics
"""
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from services.backup_service import backup_service, BackupService
from services.auth_service import auth_service
from ui.backup_view import BackupView


@pytest.fixture(scope="module")
def qapp():
    """Provides single QApplication instance for PySide6 GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_backup_creation_and_manifest():
    """Tests creating a full system backup snapshot with valid manifest.json."""
    service = BackupService()
    auth_service.login("admin", "Password@123")

    result = service.create_backup(backup_name="test_snapshot", include_models=True)
    assert result["success"] is True
    assert "backup_path" in result
    assert Path(result["backup_path"]).exists()
    assert result["total_records"] > 0
    assert "system_settings" in result["table_counts"]


def test_list_backups_metadata():
    """Tests scanning and parsing backup archives."""
    service = BackupService()
    backups = service.list_backups()
    assert isinstance(backups, list)
    assert len(backups) >= 1

    first = backups[0]
    assert "backup_id" in first
    assert "created_at" in first
    assert "file_size_formatted" in first
    assert "table_counts" in first


def test_restore_backup_verification():
    """Tests point-in-time restore from a created backup archive."""
    service = BackupService()
    auth_service.login("admin", "Password@123")

    # Create fresh backup to restore
    b_res = service.create_backup(backup_name="restore_test", include_models=False)
    backup_file = b_res["backup_path"]

    # Restore from it
    r_res = service.restore_backup(backup_file)
    assert r_res["success"] is True
    assert r_res["restored_tables"] > 0
    assert r_res["restored_records"] > 0
    assert r_res["restored_by"] == "admin"


def test_data_archival_and_listing():
    """Tests cold data archival and archive bundle listing."""
    service = BackupService()
    auth_service.login("admin", "Password@123")

    # Execute archival
    arch_res = service.archive_records(older_than_months=6)
    assert arch_res["success"] is True
    assert Path(arch_res["archive_path"]).exists()
    assert arch_res["total_records"] >= 0

    # List archives
    archives = service.list_archives()
    assert isinstance(archives, list)
    assert len(archives) >= 1
    assert "archive_id" in archives[0]


def test_system_diagnostics_health_metrics():
    """Tests running system diagnostics check."""
    service = BackupService()
    diag = service.run_system_diagnostics()

    assert "health_status" in diag
    assert "python_version" in diag
    assert "mysql_driver" in diag
    assert "total_tables" in diag
    assert diag["total_tables"] == 12
    assert "storage_usage" in diag
    assert "ml_status" in diag


def test_backup_view_pyside6_instantiation(qapp):
    """Tests PySide6 BackupView widget creation, sub-tabs setup, and table population."""
    auth_service.login("admin", "Password@123")

    view = BackupView()
    assert view is not None
    assert view.tabs.count() == 3
    assert view.backup_table.columnCount() == 7
    assert view.archive_table.columnCount() == 6
    assert view.table_stats_widget.columnCount() == 2

    # Check that backup table loaded rows
    assert view.backup_table.rowCount() >= 1

    # Check diagnostics loaded
    assert view.table_stats_widget.rowCount() == 12
