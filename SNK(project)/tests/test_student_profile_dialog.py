"""
Unit regression tests for StudentProfileDialog.
Verifies asynchronous worker lifecycle, skeleton state transitions,
error boundary with retry recovery, and thread cleanup.
"""
import pytest
import time
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from ui.student_view import StudentProfileDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_student_profile_dialog_success_path(qapp):
    """Verifies that StudentProfileDialog successfully resolves from skeleton to content."""
    student_sample = {
        "id": 999,
        "usn": "1MS23MCA099",
        "name": "Ananya Roy",
        "year": 2,
        "department_code": "MCA",
        "department_name": "Master of Computer Applications",
        "phone_number": "9123456789",
    }

    def _mock_success_fetch():
        time.sleep(0.01)
        return student_sample

    dlg = StudentProfileDialog(student_sample, fetch_fn=_mock_success_fetch)
    dlg.show()

    # Skeleton should be visible initially while worker runs
    qapp.processEvents()

    # Wait for background WorkerThread to complete
    for _ in range(100):
        if dlg.content_container.isVisible():
            break
        qapp.processEvents()
        time.sleep(0.01)

    assert not dlg.skeleton_container.isVisible(), "Skeleton should be hidden on success"
    assert not dlg.error_container.isVisible(), "Error container should be hidden on success"
    assert dlg.content_container.isVisible(), "Content container should be visible on success"
    assert dlg.lbl_name.text() == "Ananya Roy"
    assert "1MS23MCA099" in dlg.lbl_usn.text()
    assert dlg._worker is None or not dlg._worker.isRunning()

    dlg.accept()


def test_student_profile_dialog_error_and_retry_path(qapp):
    """Verifies that StudentProfileDialog handles worker exceptions and can recover via Retry."""
    student_sample = {
        "id": 888,
        "usn": "1MS23MCA088",
        "name": "Failed Student",
    }

    call_count = {"count": 0}

    def _flaky_fetch():
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise ConnectionError("Database cluster unreachable at 10.0.0.1")
        return {
            "id": 888,
            "usn": "1MS23MCA088",
            "name": "Recovered Student",
            "year": 1,
            "department_code": "CS",
            "phone_number": "9998887777",
        }

    dlg = StudentProfileDialog(student_sample, fetch_fn=_flaky_fetch)
    dlg.show()
    qapp.processEvents()

    # Wait for first fetch to fail
    for _ in range(100):
        if dlg.error_container.isVisible():
            break
        qapp.processEvents()
        time.sleep(0.01)

    # Verify error state
    assert not dlg.skeleton_container.isVisible(), "Skeleton must be hidden on error"
    assert dlg.error_container.isVisible(), "Error container must be visible on failure"
    assert not dlg.content_container.isVisible(), "Content container must stay hidden on failure"
    assert "Database cluster unreachable" in dlg.lbl_error_msg.text()
    assert dlg.btn_retry.isVisible(), "Retry button must be accessible"

    # Now click Retry button to recover
    dlg.btn_retry.click()
    qapp.processEvents()

    # Wait for second fetch (success)
    for _ in range(100):
        if dlg.content_container.isVisible():
            break
        qapp.processEvents()
        time.sleep(0.01)

    # Verify recovery state
    assert not dlg.skeleton_container.isVisible()
    assert not dlg.error_container.isVisible()
    assert dlg.content_container.isVisible()
    assert dlg.lbl_name.text() == "Recovered Student"

    dlg.reject()
