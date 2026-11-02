"""
Unit Tests for Smartphone Biometric Check-In & WebAuthn QR Bridge.
Verifies LAN IP resolution, shift late-minutes calculation, FastAPI endpoints,
and PySide6 SmartphonePunchWidget.
"""
import sys
import asyncio
from datetime import datetime, time
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.mobile_punch_service import (
    get_local_lan_ip,
    get_all_active_employees,
    find_employee,
    process_biometric_punch,
    PunchPayload,
    create_mobile_app,
    MOBILE_HTML_TEMPLATE,
)
from ui.smartphone_punch_widget import SmartphonePunchWidget


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_get_local_lan_ip():
    """Verify local LAN IP detection returns a valid IPv4 string."""
    ip = get_local_lan_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4
    assert ip != ""


def test_get_all_active_employees():
    """Verify employee directory retrieval returns faculty and lab instructors."""
    emps = get_all_active_employees()
    assert isinstance(emps, list)
    assert len(emps) >= 2
    codes = [e["code"] for e in emps]
    assert "F001" in codes or "EMP001" in codes
    assert any(e.get("role") in ["FACULTY", "LAB_INSTRUCTOR", "ADMIN", "HOD"] for e in emps)


def test_find_employee_resolution():
    """Verify employee lookup resolves both faculty and lab instructors."""
    fac = find_employee("F001")
    assert fac is not None
    assert fac["employee_code"] == "F001"

    inst = find_employee("INS001")
    assert inst is not None
    assert inst["employee_code"] == "INS001"

    non_existent = find_employee("NON_EXISTENT_999")
    assert non_existent is None


def test_process_biometric_punch_checkin_late_calculation():
    """
    Verify Check-In punch calculates late minutes against 09:00:00 shift.
    e.g. 09:15:00 punch should result in 15 late minutes.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    ts_late = f"{today_str}T09:15:00"

    payload = PunchPayload(
        employee_code="F001",
        punch_type="IN",
        timestamp=ts_late,
        biometric_proof="test_webauthn_cred_001",
        auth_method="WEBAUTHN_BIOMETRIC",
    )

    res = process_biometric_punch(payload)
    assert res is not None
    assert res["employee_code"] == "F001"
    assert res["punch_type"] == "CHECK_IN"
    assert res["late_minutes"] == 15
    assert res["status"] == "PRESENT"
    assert res["biometric_verified"] is True


def test_process_biometric_punch_ontime_checkin():
    """Verify Check-In punch at or before 09:00:00 results in 0 late minutes."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    ts_ontime = f"{today_str}T08:55:00"

    payload = PunchPayload(
        employee_code="F002",
        punch_type="IN",
        timestamp=ts_ontime,
        biometric_proof="test_webauthn_cred_002",
        auth_method="WEBAUTHN_BIOMETRIC",
    )

    res = process_biometric_punch(payload)
    assert res is not None
    assert res["late_minutes"] == 0
    assert res["punch_type"] == "CHECK_IN"


def test_process_biometric_punch_checkout():
    """Verify Check-Out punch computes working hours properly."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    ts_out = f"{today_str}T17:30:00"

    payload = PunchPayload(
        employee_code="F001",
        punch_type="OUT",
        timestamp=ts_out,
        biometric_proof="test_webauthn_cred_out",
        auth_method="WEBAUTHN_BIOMETRIC",
    )

    res = process_biometric_punch(payload)
    assert res is not None
    assert res["punch_type"] == "CHECK_OUT"
    assert res["working_hours"] >= 0.0


def test_mobile_html_template_contains_webauthn():
    """Verify the served HTML contains WebAuthn JavaScript and punch endpoints."""
    assert "navigator.credentials" in MOBILE_HTML_TEMPLATE
    assert "/api/punch" in MOBILE_HTML_TEMPLATE
    assert "/api/employees" in MOBILE_HTML_TEMPLATE
    assert "Biometric Check-In Bridge" in MOBILE_HTML_TEMPLATE
    assert "btnBiometric" in MOBILE_HTML_TEMPLATE


def test_fastapi_app_instantiation():
    """Verify FastAPI application instance initializes with routes."""
    app = create_mobile_app()
    assert app is not None
    route_paths = [route.path for route in app.routes]
    assert "/punch-interface" in route_paths
    assert "/api/punch" in route_paths
    assert "/api/employees" in route_paths
    assert "/api/status" in route_paths


def test_smartphone_punch_widget_ui(qapp):
    """Verify PySide6 SmartphonePunchWidget instantiates and creates QR code."""
    widget = SmartphonePunchWidget()
    assert widget is not None
    assert widget.lbl_qr is not None
    assert widget.lbl_qr.pixmap() is not None
    assert not widget.lbl_qr.pixmap().isNull()
    assert "http" in widget.server_url
    assert widget.btn_toggle_server is not None
    assert widget.tbl_live_punches.columnCount() == 7

    # Verify live punch table receiving a signal
    mock_punch = {
        "employee_code": "F001",
        "full_name": "Dr. Suresh Kumar",
        "department": "MCA",
        "punch_type": "CHECK_IN",
        "punch_time": "09:05:00",
        "late_minutes": 5,
        "biometric_verified": True,
    }
    widget.on_punch_received(mock_punch)
    assert widget.tbl_live_punches.rowCount() >= 1
    assert widget.tbl_live_punches.item(0, 1).text() == "F001"


def test_smartphone_punch_widget_signal_and_quick_punch(qapp, monkeypatch):
    """Verify SmartphonePunchWidget emits punch_recorded signal and supports desktop punch."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    widget = SmartphonePunchWidget()
    received_punches = []
    widget.punch_recorded.connect(lambda data: received_punches.append(data))

    assert widget.cmb_quick_emp.count() > 0
    widget.cmb_quick_type.setCurrentText("AUTO")
    widget._on_desktop_quick_punch()

    assert len(received_punches) == 1
    assert "employee_code" in received_punches[0]
    assert widget.tbl_live_punches.rowCount() >= 1


def test_find_employee_by_username():
    """Verify find_employee matches usernames (admin, hod_mca, fac_rahul, inst_kavita)."""
    assert find_employee("admin") is not None
    assert find_employee("hod_mca") is not None
    assert find_employee("fac_rahul") is not None
    assert find_employee("inst_kavita") is not None
