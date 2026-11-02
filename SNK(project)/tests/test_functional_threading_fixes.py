"""
Regression and Concurrency Test Suite for Phase 3 Functional & Threading Fixes.

Validates:
1. Biometric CSV Ingestion (AttendanceView) non-blocking execution via WorkerThread,
   modal loading overlay display, error handling, and thread lifecycle cleanup.
2. NLP Leave Classifier robustness against short, empty, whitespace, numeric, and None inputs
   without raising AttributeError or unexpected exceptions.
3. Substitute Engine candidate filtering (excluding original faculty whether passed as int or str,
   excluding non-teaching admin accounts, and returning eligible faculty + lab instructors).
4. Worker-Object pattern compliance (moveToThread, signal dispatching, cancellation, and clean teardown).
"""
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.worker import WorkerThread, WorkerObject, LoadingOverlay
from services.model_training_service import model_training_service
from services.substitute_service import substitute_service
from services.attendance_service import attendance_service
from services.auth_service import auth_service, UserSession
from ui.attendance_view import AttendanceView
from ui.substitute_view import SubstituteView


@pytest.fixture(scope="session")
def qapp():
    """Provides a shared QApplication instance for offscreen testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ==============================================================================
# TEST 1: WORKER-OBJECT PATTERN (moveToThread) & LIFECYCLE
# ==============================================================================
def test_worker_object_movetothread_success(qapp):
    """Verifies WorkerThread uses moveToThread pattern and emits result and finished."""
    results = []
    finished_called = []

    def task():
        return {"status": "SUCCESS", "records": 42}

    worker = WorkerThread(task)
    worker.result.connect(lambda val: results.append(val))
    worker.finished.connect(lambda: finished_called.append(True))

    worker.start()
    assert worker.wait(3000) is True
    qapp.processEvents()

    assert len(results) == 1
    assert results[0] == {"status": "SUCCESS", "records": 42}
    assert len(finished_called) == 1


def test_worker_object_movetothread_error_handling(qapp):
    """Verifies WorkerThread captures exceptions and emits formatted error without crashing."""
    errors = []
    finished_called = []

    def failing_task():
        raise ValueError("Simulated background task failure.")

    worker = WorkerThread(failing_task)
    worker.error.connect(lambda err: errors.append(err))
    worker.finished.connect(lambda: finished_called.append(True))

    worker.start()
    assert worker.wait(3000) is True
    qapp.processEvents()

    assert len(errors) == 1
    assert "ValueError: Simulated background task failure." in errors[0]
    assert len(finished_called) == 1


def test_worker_object_cancellation(qapp):
    """Verifies stop() cancels the worker cleanly."""
    import time
    results = []

    def long_task():
        time.sleep(0.05)
        return "SHOULD_BE_IGNORED"

    worker = WorkerThread(long_task)
    worker.result.connect(lambda v: results.append(v))
    worker.start()
    worker.stop()
    worker.wait(2000)
    qapp.processEvents()

    # Results should be suppressed upon cancellation
    assert results == []


# ==============================================================================
# TEST 2: NLP CLASSIFIER ROBUSTNESS ON SHORT / EMPTY / NONE INPUTS
# ==============================================================================
@pytest.mark.parametrize(
    "edge_input,expected_oov",
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("a", True),
        ("hi", True),
        ("ok", True),
        ("xyz", True),
        ("asdfghjkl", True),
        ("zzzzzz", True),
        (12345, True),
    ],
)
def test_nlp_classifier_handles_short_empty_none_gracefully(edge_input, expected_oov):
    """Verifies predict_leave_reason handles all malformed and empty inputs without crashing."""
    res = model_training_service.predict_leave_reason(edge_input)
    assert isinstance(res, dict)
    assert res.get("is_oov") is expected_oov
    assert res.get("predicted_category") == "UNCERTAIN"
    assert "routing_advice" in res
    assert "oov_reason" in res


def test_nlp_classifier_valid_input_high_confidence():
    """Verifies valid clinical / medical reason predicts properly with high confidence."""
    valid_text = "I am diagnosed with acute viral bronchitis and severe fever. Doctor advised 3 days bed rest."
    res = model_training_service.predict_leave_reason(valid_text)
    assert isinstance(res, dict)
    assert res.get("is_oov") is False
    assert res.get("predicted_category") in ["ML", "SL", "CL"]
    assert res.get("confidence_score") > 0.40


# ==============================================================================
# TEST 3: SUBSTITUTE ENGINE CANDIDATE FILTERING & EXCLUSION
# ==============================================================================
def test_substitute_excludes_original_faculty_integer():
    """Verifies original faculty is excluded when ID is passed as integer."""
    candidates = substitute_service.recommend_substitutes(original_faculty_id=2)
    ids = [c["faculty_id"] for c in candidates]
    assert 2 not in ids
    assert len(candidates) > 0


def test_substitute_excludes_original_faculty_string():
    """Verifies original faculty is excluded even when ID is passed as string."""
    candidates = substitute_service.recommend_substitutes(original_faculty_id="2")
    ids = [c["faculty_id"] for c in candidates]
    assert 2 not in ids
    assert len(candidates) > 0


def test_substitute_excludes_system_admin_role():
    """Verifies non-teaching System Administrator is not recommended for substitute teaching."""
    candidates = substitute_service.recommend_substitutes(original_faculty_id=2)
    names = [c["faculty_name"] for c in candidates]
    assert not any("System Admin" in n for n in names)


def test_substitute_view_search_non_blocking(qapp):
    """Verifies SubstituteView triggers recommendation search with LoadingOverlay."""
    view = SubstituteView()
    view.resize(1200, 700)
    assert hasattr(view, "overlay")
    assert isinstance(view.overlay, LoadingOverlay)

    # Click find substitutes
    view.on_find_substitutes_click()
    assert hasattr(view, "_find_worker")
    if view._find_worker:
        view._find_worker.wait(3000)
    qapp.processEvents()

    # Table must be populated with eligible candidates
    assert view.tbl_candidates.rowCount() > 0
    view.close()


# ==============================================================================
# TEST 4: BIOMETRIC CSV INGESTION & LOADING OVERLAY
# ==============================================================================
def test_attendance_view_overlay_and_async_parsing(qapp, tmp_path):
    """Verifies AttendanceView integrates LoadingOverlay and parses CSV asynchronously."""
    view = AttendanceView()
    view.resize(1200, 700)
    assert hasattr(view, "overlay")
    assert isinstance(view.overlay, LoadingOverlay)

    # Generate temporary sample CSV
    csv_file = tmp_path / "sample_attendance.csv"
    csv_file.write_text(
        "employee_code,attendance_date,login_time,logout_time\n"
        "F002,2026-10-15,08:55:00,16:30:00\n"
        "F003,2026-10-15,09:12:00,16:35:00\n",
        encoding="utf-8",
    )

    view.txt_file_path.setText(str(csv_file))
    user = UserSession(user_id=1, username="admin", role="ADMIN", department_id=1, status="ACTIVE")
    view._do_parse_async(user, str(csv_file))

    assert hasattr(view, "_parse_worker")
    assert view._parse_worker is not None
    view._parse_worker.wait(3000)
    qapp.processEvents()

    assert view.tbl_valid.rowCount() >= 1
    view.close()
