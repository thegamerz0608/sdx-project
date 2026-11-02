"""
Unit Test Suite for Phase 18: Standalone Packaging, Launch Scripts & Production Release.
Verifies spec file integrity, runtime resource presence, script configurations, and release readiness.
"""
import os
import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent

def test_spec_file_integrity():
    """Verifies that faculty_erp.spec exists and contains required asset mappings."""
    spec_path = BASE_DIR / "faculty_erp.spec"
    assert spec_path.exists(), "faculty_erp.spec must exist"
    
    content = spec_path.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "database" in content
    assert "models" in content
    assert "diagrams" in content
    assert "PySide6" in content
    assert "reportlab" in content
    assert "FacultyERP" in content

def test_launcher_scripts_presence():
    """Verifies that all automated Windows launcher and build scripts exist."""
    run_app_bat = BASE_DIR / "run_app.bat"
    run_bat = BASE_DIR / "run.bat"
    launch_all_bat = BASE_DIR / "launch_all.bat"
    setup_bat = BASE_DIR / "setup_environment.bat"
    build_bat = BASE_DIR / "build_exe.bat"
    
    assert run_app_bat.exists(), "run_app.bat must exist"
    assert run_bat.exists(), "run.bat must exist"
    assert launch_all_bat.exists(), "launch_all.bat must exist"
    assert setup_bat.exists(), "setup_environment.bat must exist"
    assert build_bat.exists(), "build_exe.bat must exist"
    
    assert "main.py" in run_app_bat.read_text(encoding="utf-8")
    assert "main.py" in run_bat.read_text(encoding="utf-8")
    assert "biometric_daemon.py" in launch_all_bat.read_text(encoding="utf-8")
    assert "requirements.txt" in setup_bat.read_text(encoding="utf-8")
    assert "faculty_erp.spec" in build_bat.read_text(encoding="utf-8")

def test_essential_runtime_assets_presence():
    """Verifies all essential runtime models, SQL schemas, and asset files exist."""
    assert (BASE_DIR / "database" / "schema.sql").exists()
    assert (BASE_DIR / "database" / "seed_data.sql").exists()
    assert (BASE_DIR / "models" / "best_leave_classifier.joblib").exists()
    assert (BASE_DIR / "models" / "tfidf_vectorizer.joblib").exists()
    assert (BASE_DIR / "diagrams" / "diagram_context.png").exists()
    assert (BASE_DIR / "diagrams" / "diagram_ml_pipeline.png").exists()
    assert (BASE_DIR / "diagrams" / "ui_dashboard.png").exists()

def test_main_window_release_title():
    """Verifies that MainWindow reflects Production Release v1.0.0."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    from ui.main_window import MainWindow
    window = MainWindow()
    assert "Production Release v1.0.0" in window.windowTitle()
    assert window.tab_widget.count() == 16, "All 16 tabs must be registered"
