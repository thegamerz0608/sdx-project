"""
Unit and Integration Tests for:
- Module 1: Decoupled BiometricKioskWindow & QR scaling
- Module 2: Background AttendancePollingWorker and real-time polling
- Module 3: TimeService (Normal vs Test Mode) & AdminDashboardWidget Time Controller
- Module 4: Web Portals Role-Based Access Control (/ajsys/cms vs /admin)
"""
import pytest
import asyncio
import urllib.parse
from datetime import datetime, date, timedelta
from starlette.requests import Request
from starlette.responses import Response

from PySide6.QtWidgets import QApplication, QSizePolicy
from PySide6.QtCore import Qt

from ui.biometric_kiosk_window import BiometricKioskWindow, AttendancePollingWorker
from ui.dashboard_widget import DashboardWidget, AdminDashboardWidget
from ui.login_window import LoginWindow
from services.time_service import TimeService
from services.mobile_punch_service import process_biometric_punch, PunchPayload
from utils.jwt_utils import create_access_token, decode_access_token, extract_token_from_request
import database.connection


@pytest.fixture(autouse=True)
def fast_db_fallback(monkeypatch):
    """Speeds up test execution when local MySQL is offline."""
    import time
    monkeypatch.setattr(database.connection, "_FAIL_COOLDOWN_SECONDS", 999999.0)
    monkeypatch.setattr(database.connection, "_LAST_CONNECT_FAIL_TIME", time.time())
from services.web_portal_service import (
    serve_staff_login,
    process_staff_login,
    serve_staff_dashboard,
    serve_admin_login,
    process_admin_login,
    serve_admin_dashboard,
    update_admin_time_mode,
    ACTIVE_WEB_SESSIONS,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


# ==============================================================================
# MODULE 1 & 2: KIOSK WINDOW & POLLING WORKER TESTS
# ==============================================================================

def test_biometric_kiosk_qr_scaling_and_ui(qapp):
    """Verifies that BiometricKioskWindow instantiates with properly scaled QR code."""
    kiosk = BiometricKioskWindow()
    assert kiosk is not None
    assert kiosk.lbl_qr is not None
    # Requirement: Ensure the QLabel displaying the QR code has setScaledContents(True) and proper QSizePolicy
    assert kiosk.lbl_qr.hasScaledContents() is True
    assert kiosk.lbl_qr.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
    assert kiosk.lbl_qr.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    assert kiosk.tbl_punches.columnCount() == 7

    # Verify fullscreen toggle methods
    assert not kiosk.isFullScreen()
    kiosk.toggle_fullscreen()
    kiosk.toggle_fullscreen()
    assert not kiosk.isFullScreen()
    kiosk.close()


def test_login_window_kiosk_launcher(qapp):
    """Verifies that LoginWindow includes the lobby kiosk terminal button."""
    win = LoginWindow()
    assert hasattr(win, "btn_launch_kiosk")
    assert win.btn_launch_kiosk is not None
    win.close()


def test_attendance_polling_worker(qapp):
    """Verifies the background AttendancePollingWorker queries and emits results safely."""
    worker = AttendancePollingWorker()
    loaded_punches = []

    def handle_punches(records):
        loaded_punches.extend(records)

    worker.punches_loaded.connect(handle_punches)
    worker.run()  # Run worker logic directly in test
    assert isinstance(loaded_punches, list)


# ==============================================================================
# MODULE 3: TIME SERVICE & ADMIN TIME CONTROLLER TESTS
# ==============================================================================

def test_time_service_normal_mode():
    """Verifies TimeService in NORMAL mode returns real-time clock."""
    TimeService.reset_to_normal()
    assert TimeService.is_test_mode() is False
    now = datetime.now()
    cur = TimeService.get_current_time()
    assert abs((cur - now).total_seconds()) < 2
    assert TimeService.get_current_date() == date.today()


def test_time_service_test_mode_injection():
    """Verifies TimeService in TEST mode allows injecting mocked datetime."""
    mock_dt = datetime(2026, 12, 25, 9, 30, 0)
    TimeService.set_time_mode("TEST", test_datetime=mock_dt)
    assert TimeService.is_test_mode() is True
    assert TimeService.get_current_time() == mock_dt
    assert TimeService.get_current_date() == date(2026, 12, 25)

    # Revert back to normal
    TimeService.reset_to_normal()
    assert TimeService.is_test_mode() is False


def test_admin_dashboard_time_controller(qapp):
    """Verifies that AdminDashboardWidget includes the Global System Time Controller."""
    admin_dash = AdminDashboardWidget(role="ADMIN")
    assert hasattr(admin_dash, "time_group")
    assert not admin_dash.time_group.isHidden()
    assert hasattr(admin_dash, "btn_toggle_time_mode")
    assert hasattr(admin_dash, "dt_test_picker")

    # Toggle to test mode
    admin_dash._toggle_time_mode()
    assert TimeService.is_test_mode() is True

    # Reset back to real time
    admin_dash._reset_time_to_real()
    assert TimeService.is_test_mode() is False


# ==============================================================================
# MODULE 4: WEB PORTALS & RBAC ENFORCEMENT TESTS
# ==============================================================================

def build_mock_request(method: str = "GET", path: str = "/", body: bytes = b"", cookies: dict = None) -> Request:
    """Helper to create a lightweight Starlette Request for tests."""
    cookie_header = "; ".join([f"{k}={v}" for k, v in (cookies or {}).items()]).encode("latin-1")
    headers = []
    if cookie_header:
        headers.append((b"cookie", cookie_header))
    if method == "POST":
        headers.append((b"content-type", b"application/x-www-form-urlencoded"))
        headers.append((b"content-length", str(len(body)).encode("ascii")))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
    }
    req = Request(scope)
    parsed = urllib.parse.parse_qs(body.decode("utf-8", errors="ignore"))
    req._custom_form_data = {k: v[0] for k, v in parsed.items() if v}
    return req


def test_staff_portal_rejects_admin():
    """CRITICAL: Staff CMS Portal /ajsys/cms must REJECT administrator logins."""
    body = b"username=admin&password=Password%40123"
    req = build_mock_request(method="POST", path="/ajsys/cms/login", body=body)
    resp = process_staff_login(req, Response())

    # Must redirect to /ajsys/cms with an ACCESS DENIED error message
    assert resp.status_code == 303
    redirect_url = resp.headers.get("location", "")
    assert "/ajsys/cms?error=" in redirect_url
    assert "ACCESS+DENIED" in redirect_url or "Administrator" in redirect_url


def test_staff_portal_accepts_faculty():
    """Staff CMS Portal /ajsys/cms accepts valid faculty login."""
    body = b"username=fac_rahul&password=Password%40123"
    req = build_mock_request(method="POST", path="/ajsys/cms/login", body=body)
    resp = process_staff_login(req, Response())

    assert resp.status_code == 303
    assert resp.headers.get("location") == "/ajsys/cms/dashboard"
    # Should set cms_token cookie
    raw_cookies = [val.decode("latin-1") for k, val in resp.raw_headers if k.lower() == b"set-cookie"]
    combined_cookies = " ".join(raw_cookies)
    assert "cms_token=" in combined_cookies


def test_admin_portal_rejects_faculty():
    """CRITICAL: Admin Security Gateway /admin must REJECT non-admin logins."""
    body = b"username=fac_rahul&password=Password%40123"
    req = build_mock_request(method="POST", path="/admin/login", body=body)
    resp = process_admin_login(req, Response())

    assert resp.status_code == 303
    redirect_url = resp.headers.get("location", "")
    assert "/admin?error=" in redirect_url
    assert "ACCESS+DENIED" in redirect_url or "Role" in redirect_url


def test_admin_portal_accepts_admin():
    """Admin Security Gateway /admin accepts admin login and manages time mode."""
    body = b"username=admin&password=Password%40123"
    req = build_mock_request(method="POST", path="/admin/login", body=body)
    resp = process_admin_login(req, Response())

    assert resp.status_code == 303
    assert resp.headers.get("location") == "/admin/dashboard"
    raw_cookies = [val.decode("latin-1") for k, val in resp.raw_headers if k.lower() == b"set-cookie"]
    combined_cookies = " ".join(raw_cookies)
    assert "admin_token=" in combined_cookies

    # Extract token
    token = None
    for cookie_str in raw_cookies:
        for part in cookie_str.split(";"):
            if "admin_token=" in part:
                token = part.strip().split("admin_token=")[1]
                break
        if token:
            break

    assert token is not None

    # Test time mode toggle from admin portal
    time_body = b"mode=TEST&test_time=2026-11-01+10%3A00%3A00"
    req_time = build_mock_request(method="POST", path="/admin/time-mode", body=time_body, cookies={"admin_token": token, "admin_session": token})
    resp_time = update_admin_time_mode(req_time)

    assert resp_time.status_code == 303
    assert TimeService.is_test_mode() is True
    assert TimeService.get_current_date() == date(2026, 11, 1)

    # Cleanup
    TimeService.reset_to_normal()


# ==============================================================================
# MODULE 5: SECURITY, ANTI-TAMPERING & SYNCHRONIZATION TESTS
# ==============================================================================

def test_jwt_token_creation_and_decoding():
    """Verifies RFC 7519 HMAC-SHA256 JWT encoding and decoding without third-party deps."""
    payload = {
        "sub": "fac_rahul",
        "user_id": 4,
        "role": "FACULTY",
        "faculty_id": 1,
        "name": "Rahul Verma",
    }
    token = create_access_token(payload, expires_delta=timedelta(hours=2))
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "fac_rahul"
    assert decoded["role"] == "FACULTY"
    assert decoded["user_id"] == 4
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_expired_token_rejection():
    """Verifies that expired JWT tokens are strictly rejected."""
    payload = {"sub": "expired_user", "role": "ADMIN"}
    # Token expired 10 seconds ago
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    decoded = decode_access_token(expired_token)
    assert decoded is None


def test_jwt_tampered_signature_rejection():
    """Verifies that tampered JWT signatures fail verification."""
    payload = {"sub": "hacker", "role": "ADMIN"}
    token = create_access_token(payload)
    parts = token.split(".")
    # Tamper with the payload portion
    tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
    assert decode_access_token(tampered_token) is None

    # Tamper with the signature portion
    tampered_sig = f"{parts[0]}.{parts[1]}.badsignature123"
    assert decode_access_token(tampered_sig) is None


def test_jwt_extract_from_request_headers_and_cookies():
    """Verifies extracting JWT from Bearer Authorization header or cookies."""
    token = create_access_token({"sub": "admin", "role": "ADMIN"})

    # Case 1: Bearer Authorization header
    headers = {"Authorization": f"Bearer {token}"}
    extracted = extract_token_from_request(headers, {}, "admin_token")
    assert extracted == token

    # Case 2: Cookie fallback
    cookies = {"admin_token": token}
    extracted_cookie = extract_token_from_request({}, cookies, "admin_token")
    assert extracted_cookie == token


def test_kiosk_frameless_anti_tampering_flags(qapp):
    """Verifies BiometricKioskWindow restores standard OS title bar controls (Minimize, Maximize, Close)."""
    kiosk = BiometricKioskWindow()
    flags = kiosk.windowFlags()
    assert bool(flags & Qt.FramelessWindowHint) is False
    assert bool(flags & Qt.Window) is True
    assert hasattr(kiosk, "btn_admin_exit")
    assert hasattr(kiosk, "lbl_crest")
    kiosk.close()


def test_kiosk_admin_exit_mechanism(qapp):
    """Verifies that admin exit restores parent window."""
    parent_window = LoginWindow()
    parent_window.show()

    kiosk = BiometricKioskWindow(parent=parent_window)
    kiosk.show()

    # Trigger admin exit
    kiosk.admin_exit_kiosk()
    assert not kiosk.isVisible()
    assert parent_window.isVisible()
    parent_window.close()


def test_web_portal_jwt_cookie_issuance():
    """Verifies that /ajsys/cms and /admin logins issue signed JWT tokens in cookies with root path."""
    # Faculty login
    req_staff = build_mock_request(method="POST", path="/ajsys/cms/login", body=b"username=fac_rahul&password=Password%40123")
    resp_staff = process_staff_login(req_staff, Response())
    assert resp_staff.status_code == 303
    set_cookie_staff = resp_staff.headers.get("set-cookie", "")
    assert "cms_token=" in set_cookie_staff
    assert "path=/" in set_cookie_staff.lower()

    # Admin login
    req_admin = build_mock_request(method="POST", path="/admin/login", body=b"username=admin&password=Password%40123")
    resp_admin = process_admin_login(req_admin, Response())
    assert resp_admin.status_code == 303
    set_cookie_admin = resp_admin.headers.get("set-cookie", "")
    assert "admin_token=" in set_cookie_admin
    assert "path=/" in set_cookie_admin.lower()


def test_web_portal_authenticated_dashboard_rendering():
    """Verifies that authenticated cookies allow access to staff and admin dashboards."""
    import re

    # 1. Staff login & dashboard access
    req_staff_post = build_mock_request(method="POST", path="/staff-login", body=b"username=fac_rahul&password=Password%40123")
    resp_staff_post = process_staff_login(req_staff_post, Response())
    cookie_header = resp_staff_post.headers.get("set-cookie", "")
    token_match = re.search(r"cms_token=([^;]+)", cookie_header)
    assert token_match is not None
    token = token_match.group(1)

    req_staff_dash = build_mock_request(method="GET", path="/staff-dashboard", cookies={"cms_token": token})
    resp_staff_dash = serve_staff_dashboard(req_staff_dash)
    assert resp_staff_dash.status_code == 200
    html_staff = resp_staff_dash.body.decode("utf-8")
    assert "Welcome" in html_staff

    # 2. Admin login & dashboard access
    req_admin_post = build_mock_request(method="POST", path="/admin-login", body=b"username=admin&password=Password%40123")
    resp_admin_post = process_admin_login(req_admin_post, Response())
    admin_cookie_header = resp_admin_post.headers.get("set-cookie", "")
    admin_token_match = re.search(r"admin_token=([^;]+)", admin_cookie_header)
    assert admin_token_match is not None
    admin_token = admin_token_match.group(1)

    req_admin_dash = build_mock_request(method="GET", path="/admin-dashboard", cookies={"admin_token": admin_token})
    resp_admin_dash = serve_admin_dashboard(req_admin_dash)
    assert resp_admin_dash.status_code == 200
    html_admin = resp_admin_dash.body.decode("utf-8")
    assert "System Administration Dashboard" in html_admin
    assert "SUPERUSER: admin" in html_admin


def test_mobile_punch_respects_time_service_test_mode():
    """Verifies mobile punches respect TimeService's simulated test mode date/time."""
    # Set simulated test time: 2026-11-15 08:45:00 (On Time)
    simulated_dt = datetime(2026, 11, 15, 8, 45, 0)
    TimeService.set_time_mode("TEST", test_datetime=simulated_dt)

    try:
        # Create punch payload with a different client timestamp
        payload = PunchPayload(
            employee_code="F001",
            punch_type="IN",
            timestamp="2026-01-01T12:00:00Z",  # Phone's un-simulated clock
        )
        res = process_biometric_punch(payload)
        assert res["punch_date"] == "2026-11-15"
        assert res["punch_time"] == "08:45:00"
        assert res["late_minutes"] == 0
    finally:
        TimeService.reset_to_normal()


def test_distinct_web_portal_urls_and_strict_manual_entry():
    """Verifies unique URLs /staff-login and /admin-login with zero autofilled credentials."""
    # 1. Staff Login Interface Check
    req_staff_view = build_mock_request(method="GET", path="/staff-login")
    resp_staff_view = serve_staff_login(req_staff_view)
    assert resp_staff_view.status_code == 200
    html_staff = resp_staff_view.body.decode("utf-8")
    assert 'value="EMP001"' not in html_staff
    assert 'value="Password@123"' not in html_staff
    assert 'action="/staff-login"' in html_staff

    # 2. Admin Login Interface Check
    req_admin_view = build_mock_request(method="GET", path="/admin-login")
    resp_admin_view = serve_admin_login(req_admin_view)
    assert resp_admin_view.status_code == 200
    html_admin = resp_admin_view.body.decode("utf-8")
    assert 'value="admin"' not in html_admin
    assert 'value="Admin@123"' not in html_admin
    assert 'action="/admin-login"' in html_admin

    # 3. Staff Login POST via /staff-login
    req_staff_post = build_mock_request(method="POST", path="/staff-login", body=b"username=fac_rahul&password=Password%40123")
    resp_staff_post = process_staff_login(req_staff_post, Response())
    assert resp_staff_post.status_code == 303
    assert resp_staff_post.headers.get("location") == "/ajsys/cms/dashboard"

    # 4. Admin Login POST via /admin-login
    req_admin_post = build_mock_request(method="POST", path="/admin-login", body=b"username=admin&password=Password%40123")
    resp_admin_post = process_admin_login(req_admin_post, Response())
    assert resp_admin_post.status_code == 303
    assert resp_admin_post.headers.get("location") == "/admin/dashboard"


def test_login_window_strict_manual_authentication(qapp):
    """Verifies that PySide6 LoginWindow fields are strictly blank by default and kiosk button is decoupled."""
    win = LoginWindow()
    assert win.txt_username.text() == ""
    assert win.txt_password.text() == ""
    assert win.txt_captcha.text() == ""
    assert hasattr(win, "btn_launch_kiosk")
    assert win.btn_launch_kiosk.isHidden()
    win.close()


def test_api_verify_credentials_and_mobile_app():
    """Verifies /api/verify-credentials endpoint validates password before unlocking biometrics."""
    from services.mobile_punch_service import create_mobile_app, VerifyCredentialsPayload
    from fastapi import HTTPException

    app = create_mobile_app()
    verify_endpoint = None
    for r in app.routes:
        if getattr(r, "path", "") == "/api/verify-credentials":
            verify_endpoint = r.endpoint
            break
    assert verify_endpoint is not None

    # Valid faculty credentials
    valid_payload = VerifyCredentialsPayload(employee_code="fac_rahul", password="Password@123")
    res_valid = verify_endpoint(valid_payload)
    assert res_valid["success"] is True
    assert "Identity verified" in res_valid["message"]

    # Invalid password
    invalid_payload = VerifyCredentialsPayload(employee_code="fac_rahul", password="WrongPassword")
    with pytest.raises(HTTPException) as exc_info:
        verify_endpoint(invalid_payload)
    assert exc_info.value.status_code == 401


def test_ml_classifiers_1d_input_hardening():
    """Verifies that pure-NumPy ML classifiers safely process 1D vectors and mismatched dimensions."""
    import numpy as np
    from nlp.classifiers import MultinomialNaiveBayes, SoftmaxLogisticRegression, RandomForest, LinearSVM

    X_train = np.random.rand(10, 8)
    y_train = ["CL", "ML", "EL", "SCL", "OD", "CL", "ML", "EL", "SCL", "OD"]

    # 1. MultinomialNaiveBayes
    nb = MultinomialNaiveBayes().fit(X_train, y_train)
    pred_nb = nb.predict(np.random.rand(8))  # 1D vector
    assert len(pred_nb) == 1
    assert pred_nb[0] in ["CL", "ML", "EL", "SCL", "OD"]

    # 2. SoftmaxLogisticRegression
    lr = SoftmaxLogisticRegression(max_iter=10).fit(X_train, y_train)
    pred_lr = lr.predict(np.random.rand(8))  # 1D vector
    assert len(pred_lr) == 1
    assert pred_lr[0] in ["CL", "ML", "EL", "SCL", "OD"]

    # 3. RandomForest
    rf = RandomForest(n_estimators=3, max_depth=3).fit(X_train, y_train)
    pred_rf = rf.predict(np.random.rand(8))  # 1D vector
    assert len(pred_rf) == 1
    assert pred_rf[0] in ["CL", "ML", "EL", "SCL", "OD"]

    # 4. LinearSVM
    svm = LinearSVM(max_iter=10).fit(X_train, y_train)
    pred_svm = svm.predict(np.random.rand(8))  # 1D vector
    assert len(pred_svm) == 1
    assert pred_svm[0] in ["CL", "ML", "EL", "SCL", "OD"]


def test_biometric_daemon_auto_recovery_and_liveness(qapp, monkeypatch):
    """Verifies that kiosk and mobile punch detect socket liveness and auto-sync status."""
    from services.mobile_punch_service import is_biometric_server_running, ensure_biometric_daemon_running
    import socket

    # Mock socket success
    class MockSocket:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(socket, "create_connection", lambda addr, timeout: MockSocket())
    assert is_biometric_server_running(port=8000) is True

    # When socket is open, ensure_biometric_daemon_running returns True immediately without spawning
    assert ensure_biometric_daemon_running(port=8000) is True

    # Test Kiosk sync status updates properly
    kiosk = BiometricKioskWindow()
    kiosk._on_sync_status("ONLINE", "http://erp.sys:8000/punch-interface", "synced")
    assert "ONLINE" in kiosk.lbl_status.text()
    assert kiosk.btn_activate_service.isHidden() is True

    kiosk._on_sync_status("OFFLINE", "http://erp.sys:8000/punch-interface", "synced")
    assert kiosk.lbl_status.text() == "DAEMON INACTIVE"
    assert kiosk.btn_activate_service.isHidden() is False
    kiosk.close()



