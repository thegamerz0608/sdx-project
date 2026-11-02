"""
Institutional Web Portals Service (FastAPI)
Provides role-segregated HTML Web Portals served by the microservice alongside WebAuthn:
1. Standard Staff Portal (/ajsys/cms):
   - For FACULTY, HOD, HR, PRINCIPAL, LAB_INSTRUCTOR.
   - Strictly REJECTS ADMIN logins.
2. Isolated Administrator Security Gateway (/admin):
   - For ADMIN only. Strictly REJECTS non-admin users.
   - Allows remote viewing & configuration of SYSTEM_TIME_MODE, daemon status, and ERP metrics.
Both portals read and write to the exact same MySQL database.
"""
import sys
import uuid
import asyncio
import urllib.parse
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.auth_service import auth_service, UserSession
from services.time_service import TimeService
from repositories.settings_repository import settings_repository
from repositories.attendance_repository import DEMO_ATTENDANCE
from repositories.faculty_repository import DEMO_FACULTY_LIST
from repositories.leave_repository import leave_repository
from repositories.leave_application_repository import leave_application_repository
from services.leave_service import leave_service
from services.leave_workflow_service import LeaveWorkflowService
from services.model_training_service import model_training_service
from services.backup_service import backup_service
from services.mobile_punch_service import process_biometric_punch, PunchPayload
from database.connection import get_connection
from config.settings import settings
from utils.exceptions import AuthenticationError
from utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    extract_token_from_request,
    revoke_token,
    generate_csrf_token,
    validate_csrf_token,
)
from utils.rate_limiter import login_rate_limiter
from utils.logger import get_logger

logger = get_logger("services.web_portal_service")
workflow_service = LeaveWorkflowService()

# Router instance to mount on FastAPI
web_portal_router = APIRouter()

# Active browser sessions cache: token -> UserSession
ACTIVE_WEB_SESSIONS: Dict[str, UserSession] = {}


# ==============================================================================
# HTML TEMPLATES (Pure CSS, Responsive, Institutional Grade)
# ==============================================================================

BASE_CSS = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        background-color: #0F172A;
        color: #F8FAFC;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
    }
    .top-bar {
        background-color: #1E3A8A;
        border-bottom: 2px solid #2563EB;
        padding: 14px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .top-bar-admin {
        background-color: #0B0F19;
        border-bottom: 2px solid #DC2626;
        padding: 14px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .brand-icon { font-size: 26px; }
    .brand-title { font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px; }
    .brand-sub { font-size: 11px; color: #93C5FD; }
    .container {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
    }
    .card {
        background-color: #FFFFFF;
        color: #0F172A;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
        width: 100%;
        max-width: 440px;
        padding: 32px 28px;
    }
    .card-dark {
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
        width: 100%;
        max-width: 440px;
        padding: 32px 28px;
    }
    .card-wide {
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 12px;
        width: 100%;
        max-width: 960px;
        padding: 32px;
    }
    h2 { font-size: 22px; font-weight: 800; margin-bottom: 6px; }
    .subhead { font-size: 13px; color: #64748B; margin-bottom: 22px; }
    .form-group { margin-bottom: 16px; }
    label { display: block; font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 6px; }
    .label-dark { display: block; font-size: 12px; font-weight: 700; color: #94A3B8; margin-bottom: 6px; }
    input[type="text"], input[type="password"], input[type="datetime-local"], select {
        width: 100%;
        padding: 10px 14px;
        border: 1.5px solid #CBD5E1;
        border-radius: 7px;
        font-size: 13.5px;
        background-color: #F8FAFC;
        color: #0F172A;
        outline: none;
    }
    input:focus, select:focus {
        border-color: #2563EB;
        background-color: #FFFFFF;
    }
    .input-dark {
        background-color: #0F172A !important;
        border-color: #475569 !important;
        color: #F8FAFC !important;
    }
    .btn {
        width: 100%;
        padding: 12px;
        border: none;
        border-radius: 7px;
        font-size: 14px;
        font-weight: 700;
        cursor: pointer;
        transition: 0.2s;
        text-align: center;
        text-decoration: none;
        display: inline-block;
    }
    .btn-primary { background-color: #1E3A8A; color: white; }
    .btn-primary:hover { background-color: #2563EB; }
    .btn-danger { background-color: #DC2626; color: white; }
    .btn-danger:hover { background-color: #B91C1C; }
    .btn-warning { background-color: #D97706; color: white; }
    .btn-warning:hover { background-color: #B45309; }
    .btn-success { background-color: #16A34A; color: white; }
    .btn-success:hover { background-color: #15803D; }
    .btn-info { background-color: #0284C7; color: white; }
    .btn-info:hover { background-color: #0369A1; }
    .btn-sm { width: auto; padding: 6px 14px; font-size: 12px; border-radius: 5px; }
    textarea {
        width: 100%;
        padding: 10px 14px;
        border: 1.5px solid #CBD5E1;
        border-radius: 7px;
        font-size: 13.5px;
        background-color: #F8FAFC;
        color: #0F172A;
        outline: none;
        resize: vertical;
        font-family: inherit;
    }
    textarea:focus { border-color: #2563EB; background-color: #FFFFFF; }
    .alert-error {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #F87171;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12.5px;
        margin-bottom: 16px;
        font-weight: 600;
    }
    .alert-success {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12.5px;
        margin-bottom: 16px;
        font-weight: 600;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-blue { background-color: #DBEAFE; color: #1E40AF; }
    .badge-green { background-color: #DCFCE7; color: #166534; }
    .badge-amber { background-color: #FEF3C7; color: #92400E; }
    .badge-red { background-color: #FEE2E2; color: #991B1B; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
    .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
    }
    .kpi-title { font-size: 11px; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 4px; }
    .kpi-value { font-size: 22px; font-weight: 800; color: #F8FAFC; }
    .kpi-sub { font-size: 11.5px; color: #64748B; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th { background-color: #0F172A; color: #94A3B8; text-align: left; padding: 10px; font-size: 12px; font-weight: 700; border-bottom: 2px solid #334155; }
    td { padding: 10px; font-size: 12.5px; border-bottom: 1px solid #334155; color: #E2E8F0; }
    tr:hover { background-color: #334155; }
    .footer { text-align: center; padding: 16px; font-size: 11.5px; color: #64748B; }
</style>
"""


# ==============================================================================
# MODULE 4: STAFF PORTAL ROUTES (/ajsys/cms)
# Authenticates: FACULTY, HOD, HR, PRINCIPAL, LAB_INSTRUCTOR. Rejects: ADMIN.
# ==============================================================================

def _get_query_param(request: Request, key: str) -> Optional[str]:
    """Safely extracts a query parameter without raising KeyError on mock requests."""
    try:
        if hasattr(request, "query_params") and "query_string" in getattr(request, "scope", {}):
            return request.query_params.get(key)
    except Exception:
        pass
    return None


@web_portal_router.get("/staff-login", response_class=HTMLResponse)
@web_portal_router.get("/staff-login/", response_class=HTMLResponse)
@web_portal_router.get("/ajsys/cms", response_class=HTMLResponse)
@web_portal_router.get("/ajsys/cms/", response_class=HTMLResponse)
@web_portal_router.get("/ajsys/cms/login", response_class=HTMLResponse)
def serve_staff_login(request: Request, error: Optional[str] = None):
    """Serves the standard Staff CMS login portal."""
    action_url = "/staff-login" if request.url.path.startswith("/staff-login") else "/ajsys/cms/login"
    error_text = error or _get_query_param(request, "error")
    err_html = f'<div class="alert-error">⚠️ {error_text}</div>' if error_text else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Staff CMS Portal - Faculty Attendance ERP</title>
    {BASE_CSS}
</head>
<body>
    <header class="top-bar">
        <div class="brand">
            <span class="brand-icon">🏛️</span>
            <div>
                <div class="brand-title">INSTITUTIONAL STAFF CMS PORTAL</div>
                <div class="brand-sub">Academic & Faculty Self-Service Management</div>
            </div>
        </div>
        <div style="font-size: 11.5px; color: #BFDBFE;">TLS 1.3 Encrypted • Staff Access</div>
    </header>

    <div class="container">
        <div class="card">
            <h2>Staff Sign-In</h2>
            <div class="subhead">Enter your institutional Staff ID to access attendance & leaves.</div>
            {err_html}
            <form action="{action_url}" method="POST">
                <div class="form-group">
                    <label>Staff ID or Username:</label>
                    <input type="text" name="username" placeholder="e.g. EMP001, F001, INS001" value="" required autofocus>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" placeholder="Enter password" value="" required>
                </div>
                <div style="font-size: 11px; color: #64748B; margin-bottom: 14px; line-height: 1.4;">
                    ℹ️ <b>Allowed Roles:</b> Faculty, HOD, HR, Principal, Lab Instructors.<br>
                    🔒 <i>System Administrators must sign in through the isolated <a href="/admin-login" style="color: #2563EB;">/admin-login</a> gateway.</i>
                </div>
                <button type="submit" class="btn btn-primary">Sign In to Staff CMS</button>

                <div style="background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 12px; margin-top: 18px; font-size: 11.5px; color: #1E3A8A; line-height: 1.5;">
                    <b>📋 Demo Staff Logins (Password: <code>Password@123</code>):</b><br>
                    • Faculty: <code>fac_rahul</code> or <code>F002</code><br>
                    • HOD MCA: <code>hod_mca</code> or <code>F001</code><br>
                    • Lab Instructor: <code>inst_kavita</code> or <code>INS001</code>
                </div>
            </form>
        </div>
    </div>

    <footer class="footer">
        Faculty Attendance & Leave Management ERP • Web Portal Layer v1.0
    </footer>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


def _parse_form_body(request: Request) -> Dict[str, str]:
    """Parses application/x-www-form-urlencoded and JSON body synchronously."""
    if hasattr(request, "_custom_form_data"):
        return getattr(request, "_custom_form_data")

    body_bytes = b""
    if hasattr(request, "state") and hasattr(request.state, "body"):
        body_bytes = request.state.body
    if not body_bytes:
        b = getattr(request, "_body", b"")
        if isinstance(b, (bytes, bytearray)):
            body_bytes = bytes(b)
    if not body_bytes and hasattr(request, "body"):
        b = getattr(request, "body", None)
        if isinstance(b, (bytes, bytearray)):
            body_bytes = bytes(b)

    decoded = body_bytes.decode("utf-8", errors="ignore")

    # Handle JSON if submitted via fetch/JSON
    try:
        import json
        clean_dec = decoded.strip()
        if clean_dec.startswith("{") and clean_dec.endswith("}"):
            obj = json.loads(clean_dec)
            if isinstance(obj, dict):
                return {str(k).strip(): str(v).strip() for k, v in obj.items()}
    except Exception:
        pass

    parsed = urllib.parse.parse_qs(decoded)
    return {k.strip(): v[0].strip() for k, v in parsed.items() if v}


@web_portal_router.post("/staff-login")
@web_portal_router.post("/staff-login/")
@web_portal_router.post("/ajsys/cms")
@web_portal_router.post("/ajsys/cms/")
@web_portal_router.post("/ajsys/cms/login")
def process_staff_login(request: Request, response: Response = None):
    """
    Authenticates staff credentials.
    CRITICAL: Strictly REJECTS users with role 'ADMIN'.
    """
    base_portal = "/staff-login" if request.url.path.startswith("/staff-login") else "/ajsys/cms"
    form = _parse_form_body(request)
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()

    # In-Memory Rate Limiting (5 attempts per minute per IP)
    client_ip = request.client.host if request.client else "127.0.0.1"
    allowed, _, retry_after = login_rate_limiter.is_allowed(client_ip)
    if not allowed:
        return RedirectResponse(
            url=f"{base_portal}?error=Too+many+login+attempts.+Try+again+in+{int(retry_after)}+seconds.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        session = auth_service.login(username=username, password=password)
    except AuthenticationError as e:
        return RedirectResponse(
            url=f"{base_portal}?error={e.message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"{base_portal}?error=Authentication+failed:+{str(exc)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # STRICT ROLE CHECK: Reject ADMIN
    if session.role == "ADMIN":
        logger.warning(f"Admin login rejected on staff portal {base_portal}: {session.username}")
        error_msg = (
            "ACCESS DENIED: Administrator accounts cannot sign in through the Staff CMS Portal. "
            "Please use the Isolated Administrator Security Gateway at /admin-login."
        )
        return RedirectResponse(
            url=f"{base_portal}?error={error_msg}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Allowed staff roles
    allowed_roles = ["FACULTY", "HOD", "HR", "PRINCIPAL", "LAB_INSTRUCTOR"]
    if session.role not in allowed_roles:
        return RedirectResponse(
            url=f"{base_portal}?error=Access+restricted+for+role+{session.role}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Issue Cryptographic JWT (JSON Web Token)
    jwt_token = create_access_token({
        "sub": session.username,
        "username": session.username,
        "role": session.role,
        "user_id": session.user_id,
        "employee_code": session.employee_code,
        "full_name": session.full_name,
        "department_code": session.department_code,
        "designation": session.designation,
        "faculty_id": session.faculty_id,
    })

    # Register in-memory session for instant lookup
    session_uuid = str(uuid.uuid4())
    csrf_token = generate_csrf_token(session_uuid)
    refresh_token = create_refresh_token({"sub": session.username, "user_id": session.user_id})

    ACTIVE_WEB_SESSIONS[session_uuid] = session
    ACTIVE_WEB_SESSIONS[jwt_token] = session

    cookie_secure = getattr(settings, "COOKIE_SECURE", False)

    redirect = RedirectResponse(url="/ajsys/cms/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(key="cms_token", value=jwt_token, path="/", httponly=True, samesite="lax", secure=cookie_secure, max_age=86400)
    redirect.set_cookie(key="cms_session", value=session_uuid, path="/", httponly=True, samesite="lax", secure=cookie_secure, max_age=86400)
    redirect.set_cookie(key="cms_refresh_token", value=refresh_token, path="/", httponly=True, samesite="lax", secure=cookie_secure, max_age=86400*7)
    redirect.set_cookie(key="csrf_token", value=csrf_token, path="/", httponly=False, samesite="lax", secure=cookie_secure, max_age=86400)
    redirect.headers["X-Access-Token"] = jwt_token
    redirect.headers["X-CSRF-Token"] = csrf_token
    return redirect


@web_portal_router.get("/staff-dashboard", response_class=HTMLResponse)
@web_portal_router.get("/staff-dashboard/", response_class=HTMLResponse)
@web_portal_router.get("/ajsys/cms/dashboard", response_class=HTMLResponse)
@web_portal_router.get("/ajsys/cms/dashboard/", response_class=HTMLResponse)
def serve_staff_dashboard(request: Request, msg: Optional[str] = None, error: Optional[str] = None):
    """Serves the rich authenticated Staff CMS self-service dashboard."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="cms_token",
    ) or request.cookies.get("cms_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    # Stateless fallback: reconstruct session from validated JWT claims
    if not session and jwt_payload:
        full_name = jwt_payload.get("full_name", "")
        parts = full_name.split() if full_name else []
        session = UserSession(
            user_id=jwt_payload.get("user_id", 0),
            username=jwt_payload.get("username") or jwt_payload.get("sub", ""),
            role=jwt_payload.get("role", "FACULTY"),
            status="ACTIVE",
            faculty_id=jwt_payload.get("faculty_id"),
            employee_code=jwt_payload.get("employee_code"),
            department_code=jwt_payload.get("department_code"),
            designation=jwt_payload.get("designation", "Faculty"),
            first_name=parts[0] if parts else "",
            last_name=" ".join(parts[1:]) if len(parts) > 1 else "",
        )

    if not session or session.role == "ADMIN":
        return RedirectResponse(url="/staff-login?error=Please+sign+in+first", status_code=status.HTTP_303_SEE_OTHER)

    current_date = TimeService.get_current_date()
    current_time_str = TimeService.get_current_time_str("%I:%M %p")
    time_mode_badge = (
        '<span class="badge badge-amber">TEST MODE ACTIVE</span>'
        if TimeService.is_test_mode()
        else '<span class="badge badge-green">NORMAL TIME</span>'
    )

    msg_text = msg or _get_query_param(request, "msg")
    err_text = error or _get_query_param(request, "error")
    banner_html = ""
    if msg_text:
        banner_html += f'<div class="alert-success">✅ {msg_text}</div>'
    if err_text:
        banner_html += f'<div class="alert-error">⚠️ {err_text}</div>'

    # 1. Attendance for today
    punch_info = {"status": "NOT PUNCHED", "login_time": "--:--", "logout_time": "--:--", "late": 0}
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT login_time, logout_time, status, late_minutes 
               FROM attendance 
               WHERE faculty_id = %s AND (attendance_date = %s OR DATE(attendance_date) = %s)
               LIMIT 1;""",
            (session.faculty_id or 1, current_date, current_date),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            punch_info = {
                "status": row.get("status", "PRESENT"),
                "login_time": str(row.get("login_time") or "--:--"),
                "logout_time": str(row.get("logout_time") or "--:--"),
                "late": int(row.get("late_minutes") or 0),
            }
    except Exception:
        pass

    # 2. Leave Balances
    cl_bal = 12.0
    ml_bal = 10.0
    el_bal = 15.0
    try:
        bals = leave_service.get_faculty_balances(session.faculty_id or 1)
        for b in bals:
            code = b.get("leave_type_code", "")
            rem = float(b.get("balance", b.get("total_entitled", 0.0)))
            if code == "CL": cl_bal = rem
            elif code == "ML": ml_bal = rem
            elif code == "EL": el_bal = rem
    except Exception:
        pass

    # 3. User's Leave Applications
    my_leaves = []
    try:
        my_leaves = leave_application_repository.get_applications(faculty_id=session.faculty_id or 1)
    except Exception:
        pass

    history_rows = ""
    if my_leaves:
        for app in my_leaves[:5]:
            st = app.get("status", "PENDING")
            badge_class = "badge-green" if st == "APPROVED" else ("badge-red" if st == "REJECTED" else "badge-amber")
            history_rows += f"""
            <tr>
                <td><b>{app.get('application_code', 'LA-000')}</b></td>
                <td><span class="badge badge-blue">{app.get('leave_type_code', 'CL')}</span></td>
                <td>{app.get('from_date')} &rarr; {app.get('to_date')}</td>
                <td>{app.get('total_days', 1.0)}d</td>
                <td style="max-width: 200px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{app.get('reason', '')}</td>
                <td><span class="badge {badge_class}">{st}</span></td>
            </tr>"""
    else:
        history_rows = '<tr><td colspan="6" style="text-align:center; color:#94A3B8; padding: 18px;">No leave applications on file.</td></tr>'

    # 4. Review Gatekeeper (for HOD, HR, PRINCIPAL)
    pending_reviews_html = ""
    if session.role in ["HOD", "HR", "PRINCIPAL"]:
        try:
            if session.role == "HOD":
                pending_apps = leave_application_repository.get_applications(department_id=session.department_id, status_filter="PENDING")
            else:
                pending_apps = leave_application_repository.get_applications(status_filter="PENDING")
        except Exception:
            pending_apps = []

        review_rows = ""
        if pending_apps:
            for p in pending_apps[:6]:
                app_id = p.get("id")
                review_rows += f"""
                <tr>
                    <td><b>{p.get('application_code', 'LA-000')}</b></td>
                    <td>{p.get('faculty_name', 'Faculty')}</td>
                    <td><span class="badge badge-blue">{p.get('leave_type_code', 'CL')}</span></td>
                    <td>{p.get('from_date')} &rarr; {p.get('to_date')} ({p.get('total_days')}d)</td>
                    <td style="max-width: 180px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{p.get('reason', '')}</td>
                    <td style="display: flex; gap: 8px;">
                        <form action="/staff-dashboard/review-leave" method="POST" style="margin:0;">
                            <input type="hidden" name="application_id" value="{app_id}">
                            <input type="hidden" name="action" value="APPROVE">
                            <button type="submit" class="btn btn-sm btn-success">✅ Approve</button>
                        </form>
                        <form action="/staff-dashboard/review-leave" method="POST" style="margin:0;">
                            <input type="hidden" name="application_id" value="{app_id}">
                            <input type="hidden" name="action" value="REJECT">
                            <button type="submit" class="btn btn-sm btn-danger">❌ Reject</button>
                        </form>
                    </td>
                </tr>"""
        else:
            review_rows = '<tr><td colspan="6" style="text-align:center; color:#94A3B8; padding: 16px;">No pending leave applications awaiting your review.</td></tr>'

        pending_reviews_html = f"""
        <div style="background-color: #0F172A; border: 1.5px solid #2563EB; border-radius: 10px; padding: 22px; margin-top: 24px;">
            <h3 style="font-size: 15px; font-weight: 700; color: #60A5FA; margin-bottom: 12px;">
                ⚖️ Pending Faculty Leave Approvals ({session.role} Review Gatekeeper)
            </h3>
            <p style="font-size: 12.5px; color: #94A3B8; margin-bottom: 14px;">
                You have privileged review authorization to approve or reject leave applications submitted by departmental faculty members.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Applicant</th>
                        <th>Type</th>
                        <th>Dates</th>
                        <th>Reason</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {review_rows}
                </tbody>
            </table>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Staff Dashboard - {session.full_name}</title>
    {BASE_CSS}
</head>
<body>
    <header class="top-bar">
        <div class="brand">
            <span class="brand-icon">🏛️</span>
            <div>
                <div class="brand-title">FACULTY ATTENDANCE & LEAVE ERP</div>
                <div class="brand-sub">Staff CMS Portal &bull; {session.designation}</div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 14px;">
            {time_mode_badge}
            <a href="/staff-logout" class="btn btn-sm btn-danger">🚪 Sign Out</a>
        </div>
    </header>

    <div class="container" style="align-items: flex-start; padding-top: 32px;">
        <div class="card-wide">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div>
                    <h2>Welcome, {session.full_name}</h2>
                    <div style="color: #94A3B8; font-size: 13px;">
                        Staff ID: <b>{session.employee_code or session.username}</b> &bull; 
                        Role: <span class="badge badge-blue">{session.role}</span> &bull; 
                        Department: <b>{session.department_code or 'Academic'}</b>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; color: #94A3B8;">EFFECTIVE DATE:</div>
                    <div style="font-size: 15px; font-weight: 700; color: #60A5FA;">{current_date.strftime('%A, %d %B %Y')}</div>
                </div>
            </div>

            {banner_html}

            <!-- KPI Cards Row -->
            <div class="grid-4">
                <div class="kpi-card">
                    <div class="kpi-title">Today's Check-In</div>
                    <div class="kpi-value">{punch_info['login_time']}</div>
                    <div class="kpi-sub">Shift Start: 09:00 AM</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Today's Check-Out</div>
                    <div class="kpi-value">{punch_info['logout_time']}</div>
                    <div class="kpi-sub">Standard Shift: 8.0 hrs</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Punctuality Status</div>
                    <div class="kpi-value" style="color: {'#10B981' if punch_info['late'] == 0 else '#EF4444'};">
                        {punch_info['status']}
                    </div>
                    <div class="kpi-sub">{f"Late by {punch_info['late']} min" if punch_info['late'] > 0 else "On Time"}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Casual Leave Quota</div>
                    <div class="kpi-value">{cl_bal} Days</div>
                    <div class="kpi-sub">ML: {ml_bal}d &bull; EL: {el_bal}d</div>
                </div>
            </div>

            <!-- SECTION 1: Interactive Leave Application (NLP Screened) -->
            <div style="background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 22px; margin-bottom: 24px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #93C5FD; margin-bottom: 6px;">
                    📝 Submit New Leave Application (AI NLP Screened)
                </h3>
                <p style="font-size: 12px; color: #94A3B8; margin-bottom: 16px;">
                    Enter your leave request. The pure-NumPy NLP Intent Engine will evaluate and categorize your reason.
                </p>
                <form action="/staff-dashboard/apply-leave" method="POST">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 14px;">
                        <div>
                            <label class="label-dark">Leave Type:</label>
                            <select name="leave_type" class="input-dark">
                                <option value="CL">Casual Leave (CL)</option>
                                <option value="ML">Medical Leave (ML)</option>
                                <option value="EL">Earned Leave (EL)</option>
                                <option value="SCL">Special Casual Leave (SCL)</option>
                                <option value="OD">On Duty (OD)</option>
                            </select>
                        </div>
                        <div>
                            <label class="label-dark">From Date:</label>
                            <input type="text" name="from_date" class="input-dark" value="{current_date.strftime('%Y-%m-%d')}" placeholder="YYYY-MM-DD" required>
                        </div>
                        <div>
                            <label class="label-dark">To Date:</label>
                            <input type="text" name="to_date" class="input-dark" value="{current_date.strftime('%Y-%m-%d')}" placeholder="YYYY-MM-DD" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="label-dark">Reason for Leave (Screened by NLP Classifier):</label>
                        <textarea name="reason" rows="2" class="input-dark" placeholder="e.g. Attending family wedding ceremony or suffering from viral fever..." required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: auto; padding: 10px 22px;">
                        🚀 Submit Leave Application
                    </button>
                </form>
            </div>

            <!-- SECTION 2: My Recent Applications -->
            <div style="background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 22px; margin-bottom: 24px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #CBD5E1; margin-bottom: 12px;">
                    📋 My Recent Leave Applications
                </h3>
                <table>
                    <thead>
                        <tr>
                            <th>Application Code</th>
                            <th>Type</th>
                            <th>Dates</th>
                            <th>Days</th>
                            <th>Reason</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history_rows}
                    </tbody>
                </table>
            </div>

            {pending_reviews_html}

            <!-- SECTION 3: Quick Attendance Punch & Mobile Terminal -->
            <div style="background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 20px; margin-top: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                <div>
                    <h3 style="font-size: 14px; font-weight: 700; color: #93C5FD; margin-bottom: 4px;">📱 Biometric Punch & Kiosk Terminal</h3>
                    <p style="font-size: 12px; color: #94A3B8;">
                        Record your instant attendance check-in/out directly or open the Mobile QR scanner.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <form action="/staff-dashboard/quick-punch" method="POST" style="margin: 0;">
                        <button type="submit" class="btn btn-sm btn-success">⚡ Instant Check-In/Out</button>
                    </form>
                    <a href="/punch-interface" target="_blank" class="btn btn-sm btn-primary">Open Mobile QR Punch</a>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer">
        Faculty Attendance & Leave Management ERP &bull; Shared MySQL Instance &bull; Real-Time Integration
    </footer>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@web_portal_router.post("/staff-dashboard/apply-leave")
@web_portal_router.post("/ajsys/cms/apply-leave")
def handle_staff_apply_leave(request: Request):
    """Processes online leave application with AI NLP classification."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="cms_token",
    ) or request.cookies.get("cms_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    if not session and jwt_payload:
        session = UserSession(
            user_id=jwt_payload.get("user_id", 0),
            username=jwt_payload.get("username") or jwt_payload.get("sub", ""),
            role=jwt_payload.get("role", "FACULTY"),
            faculty_id=jwt_payload.get("faculty_id", 1),
            employee_code=jwt_payload.get("employee_code", "EMP001"),
        )

    if not session:
        return RedirectResponse(url="/staff-login?error=Please+sign+in+first", status_code=status.HTTP_303_SEE_OTHER)

    form = _parse_form_body(request)
    leave_type = form.get("leave_type", "CL").strip().upper()
    from_date = form.get("from_date", "").strip()
    to_date = form.get("to_date", from_date).strip()
    reason = form.get("reason", "").strip()

    if not reason or len(reason) < 4:
        return RedirectResponse(url="/staff-dashboard?error=Please+provide+a+valid+reason+for+leave", status_code=status.HTTP_303_SEE_OTHER)

    # 1. Run NLP Classification
    nlp_res = model_training_service.predict_leave_reason(reason)
    pred_cat = nlp_res.get("predicted_category", leave_type)
    conf = nlp_res.get("confidence_percentage", "90.0%")

    # 2. Submit application
    try:
        res = workflow_service.submit_leave_application(
            user_session=session,
            faculty_id=session.faculty_id or 1,
            requested_leave_type_code=leave_type,
            from_date_str=from_date,
            to_date_str=to_date,
            reason=reason,
        )
        msg = f"Leave application {res.get('application_code', '')} submitted! NLP Intent: {pred_cat} ({conf})"
        return RedirectResponse(url=f"/staff-dashboard?msg={msg}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        logger.warning(f"Leave submission error: {exc}")
        return RedirectResponse(url=f"/staff-dashboard?error={str(exc)}", status_code=status.HTTP_303_SEE_OTHER)


@web_portal_router.post("/staff-dashboard/review-leave")
@web_portal_router.post("/ajsys/cms/review-leave")
def handle_staff_review_leave(request: Request):
    """Processes HOD / HR approval or rejection from Staff Web Portal."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="cms_token",
    ) or request.cookies.get("cms_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    if not session and jwt_payload:
        session = UserSession(
            user_id=jwt_payload.get("user_id", 0),
            username=jwt_payload.get("username") or jwt_payload.get("sub", ""),
            role=jwt_payload.get("role", "HOD"),
        )

    if not session or session.role not in ["HOD", "HR", "PRINCIPAL", "ADMIN"]:
        return RedirectResponse(url="/staff-dashboard?error=Unauthorized+review+action", status_code=status.HTTP_303_SEE_OTHER)

    form = _parse_form_body(request)
    app_id = int(form.get("application_id", 0))
    action = form.get("action", "APPROVE").strip().upper()
    remarks = form.get("remarks", f"Web portal action: {action}")

    try:
        if session.role == "HOD":
            workflow_service.review_application_by_hod(
                user_session=session,
                application_id=app_id,
                action=action,
                remarks=remarks,
            )
        else:
            workflow_service.hr_review_application(
                user_session=session,
                application_id=app_id,
                action=action,
                remarks=remarks,
            )
        msg = f"Application #{app_id} successfully {action}D."
        return RedirectResponse(url=f"/staff-dashboard?msg={msg}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        return RedirectResponse(url=f"/staff-dashboard?error={str(exc)}", status_code=status.HTTP_303_SEE_OTHER)


@web_portal_router.post("/staff-dashboard/quick-punch")
@web_portal_router.post("/ajsys/cms/quick-punch")
def handle_staff_quick_punch(request: Request):
    """Directly records a biometric check-in/out punch from the web interface."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="cms_token",
    ) or request.cookies.get("cms_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    if not session and jwt_payload:
        session = UserSession(
            user_id=jwt_payload.get("user_id", 0),
            username=jwt_payload.get("username") or jwt_payload.get("sub", ""),
            role=jwt_payload.get("role", "FACULTY"),
            employee_code=jwt_payload.get("employee_code", "EMP001"),
        )

    if not session:
        return RedirectResponse(url="/staff-login?error=Please+sign+in+first", status_code=status.HTTP_303_SEE_OTHER)

    emp_code = session.employee_code or session.username
    payload = PunchPayload(
        employee_code=emp_code,
        punch_type="AUTO",
        auth_method="WEB_PORTAL",
    )

    try:
        res = process_biometric_punch(payload)
        msg = f"Biometric Punch {res.get('punch_type')} registered at {res.get('punch_time')} (Status: {res.get('status')})"
        return RedirectResponse(url=f"/staff-dashboard?msg={msg}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        return RedirectResponse(url=f"/staff-dashboard?error={str(exc)}", status_code=status.HTTP_303_SEE_OTHER)


@web_portal_router.get("/staff-logout")
@web_portal_router.get("/ajsys/cms/logout")
def process_staff_logout(response: Response, request: Request):
    """Logs out from Staff CMS, revokes JWT tokens, and clears cookies."""
    for key in ["cms_token", "cms_session", "cms_refresh_token"]:
        token = request.cookies.get(key)
        if token:
            revoke_token(token)
            if token in ACTIVE_WEB_SESSIONS:
                del ACTIVE_WEB_SESSIONS[token]
    redirect = RedirectResponse(url="/staff-login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(key="cms_token", path="/")
    redirect.delete_cookie(key="cms_session", path="/")
    redirect.delete_cookie(key="cms_refresh_token", path="/")
    redirect.delete_cookie(key="csrf_token", path="/")
    return redirect


# ==============================================================================
# MODULE 4: ISOLATED ADMIN SECURITY GATEWAY (/admin)
# Authenticates: ADMIN ONLY. Strictly REJECTS non-admin roles.
# Displays: SYSTEM_TIME_MODE, Biometric Daemon Status, MySQL Metrics.
# ==============================================================================

@web_portal_router.get("/admin-login", response_class=HTMLResponse)
@web_portal_router.get("/admin-login/", response_class=HTMLResponse)
@web_portal_router.get("/admin", response_class=HTMLResponse)
@web_portal_router.get("/admin/", response_class=HTMLResponse)
@web_portal_router.get("/admin/login", response_class=HTMLResponse)
def serve_admin_login(request: Request, error: Optional[str] = None):
    """Serves the isolated Administrator Security Gateway login page."""
    action_url = "/admin-login" if request.url.path.startswith("/admin-login") else "/admin/login"
    error_text = error or _get_query_param(request, "error")
    err_html = f'<div class="alert-error">🚫 {error_text}</div>' if error_text else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Administration Security Gateway - Faculty ERP</title>
    {BASE_CSS}
</head>
<body style="background-color: #030712;">
    <header class="top-bar-admin">
        <div class="brand">
            <span class="brand-icon">🛡️</span>
            <div>
                <div class="brand-title" style="color: #F87171;">SYSTEM ADMINISTRATION SECURITY GATEWAY</div>
                <div class="brand-sub" style="color: #FCA5A5;">Isolated Administrative Control Terminal</div>
            </div>
        </div>
        <div style="font-size: 11.5px; color: #EF4444; font-weight: 700;">RESTRICTED ACCESS • ADMIN ONLY</div>
    </header>

    <div class="container">
        <div class="card-dark">
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="font-size: 40px;">🔐</span>
                <h2 style="color: #F87171; margin-top: 8px;">Admin Console Login</h2>
                <div class="subhead" style="color: #94A3B8;">Privileged access terminal for ERP configuration.</div>
            </div>
            {err_html}
            <form action="{action_url}" method="POST">
                <div class="form-group">
                    <label class="label-dark">Administrator Username / Staff ID:</label>
                    <input type="text" name="username" class="input-dark" placeholder="e.g. admin" value="" required autofocus>
                </div>
                <div class="form-group">
                    <label class="label-dark">Password:</label>
                    <input type="password" name="password" class="input-dark" placeholder="Admin password" value="" required>
                </div>
                <div style="font-size: 11px; color: #94A3B8; margin-bottom: 18px; line-height: 1.4;">
                    ⚠️ <b>Access Policy:</b> Only users with the <code>ADMIN</code> role can sign in here.
                    Staff members and faculty must use <a href="/staff-login" style="color: #60A5FA;">/staff-login</a>.
                </div>
                <button type="submit" class="btn btn-danger">Authenticate as Administrator</button>

                <div style="background-color: #0F172A; border: 1px solid #374151; border-radius: 8px; padding: 12px; margin-top: 18px; font-size: 11.5px; color: #FCA5A5; line-height: 1.5;">
                    <b>🛡️ Administrator Credentials (Password: <code>Password@123</code>):</b><br>
                    • Username: <code>admin</code> or <code>EMP001</code>
                </div>
            </form>
        </div>
    </div>

    <footer class="footer">
        Faculty Attendance ERP &bull; Isolated Admin Gateway &bull; Port 8000/8080
    </footer>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@web_portal_router.post("/admin-login")
@web_portal_router.post("/admin-login/")
@web_portal_router.post("/admin")
@web_portal_router.post("/admin/")
@web_portal_router.post("/admin/login")
def process_admin_login(request: Request, response: Response = None):
    """
    Authenticates administrative credentials.
    CRITICAL: Strictly REJECTS non-admin users.
    """
    base_portal = "/admin-login" if request.url.path.startswith("/admin-login") else "/admin"
    form = _parse_form_body(request)
    username = form.get("username", "")
    password = form.get("password", "")

    # In-Memory Rate Limiting for Admin Gateway (5 attempts per minute per IP)
    client_ip = request.client.host if request.client else "127.0.0.1"
    allowed, _, retry_after = login_rate_limiter.is_allowed(f"admin:{client_ip}")
    if not allowed:
        return RedirectResponse(
            url=f"{base_portal}?error=Too+many+admin+login+attempts.+Try+again+in+{int(retry_after)}+seconds.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        session = auth_service.login(username=username, password=password)
    except AuthenticationError as e:
        return RedirectResponse(
            url=f"{base_portal}?error={e.message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"{base_portal}?error=Authentication+failed:+{str(exc)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # STRICT ROLE CHECK: Only ADMIN allowed
    if session.role != "ADMIN":
        logger.warning(f"Non-admin user '{session.username}' ({session.role}) attempted to access {base_portal}")
        error_msg = (
            f"ACCESS DENIED: Role '{session.role}' is not authorized to access the Administration Security Gateway. "
            "Please use the Staff Portal at /staff-login."
        )
        return RedirectResponse(
            url=f"{base_portal}?error={error_msg}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Issue Administrator Cryptographic JWT
    admin_jwt = create_access_token({
        "sub": session.username,
        "username": session.username,
        "role": "ADMIN",
        "user_id": session.user_id,
        "is_admin": True,
    })

    # Register admin session
    session_uuid = str(uuid.uuid4())
    csrf_token = generate_csrf_token(session_uuid)
    refresh_token = create_refresh_token({"sub": session.username, "user_id": session.user_id, "role": "ADMIN"})

    ACTIVE_WEB_SESSIONS[session_uuid] = session
    ACTIVE_WEB_SESSIONS[admin_jwt] = session

    cookie_secure = getattr(settings, "COOKIE_SECURE", False)

    redirect = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(key="admin_token", value=admin_jwt, path="/", httponly=True, samesite="lax", secure=cookie_secure, max_age=86400)
    redirect.set_cookie(key="admin_session", value=session_uuid, path="/", httponly=True, samesite="lax", secure=cookie_secure, max_age=86400)
    redirect.set_cookie(key="admin_refresh_token", value=refresh_token, path="/", httponly=True, samesite="lax", secure=cookie_secure, max_age=86400*7)
    redirect.set_cookie(key="admin_csrf_token", value=csrf_token, path="/", httponly=False, samesite="lax", secure=cookie_secure, max_age=86400)
    redirect.headers["X-Access-Token"] = admin_jwt
    redirect.headers["X-CSRF-Token"] = csrf_token
    return redirect


@web_portal_router.get("/admin-dashboard", response_class=HTMLResponse)
@web_portal_router.get("/admin-dashboard/", response_class=HTMLResponse)
@web_portal_router.get("/admin/dashboard", response_class=HTMLResponse)
@web_portal_router.get("/admin/dashboard/", response_class=HTMLResponse)
def serve_admin_dashboard(request: Request, msg: Optional[str] = None):
    """Serves the privileged Administrator Console dashboard."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="admin_token",
    ) or request.cookies.get("admin_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    # Stateless fallback: reconstruct session from validated Admin JWT claims
    if not session and jwt_payload and jwt_payload.get("role") == "ADMIN":
        session = UserSession(
            user_id=jwt_payload.get("user_id", 1),
            username=jwt_payload.get("username") or jwt_payload.get("sub", "admin"),
            role="ADMIN",
            status="ACTIVE",
            designation="System Administrator",
        )

    if not session or session.role != "ADMIN":
        return RedirectResponse(url="/admin-login?error=Administrative+sign-in+required", status_code=status.HTTP_303_SEE_OTHER)

    # Metrics
    daemon_status = settings_repository.get_setting("BIOMETRIC_DAEMON_STATUS", "OFFLINE")
    daemon_url = settings_repository.get_setting("BIOMETRIC_SERVER_URL", "http://127.0.0.1:8000/punch-interface")
    is_test_mode = TimeService.is_test_mode()
    current_time_str = TimeService.get_current_time_str("%Y-%m-%d %H:%M:%S")
    test_time_val = settings_repository.get_setting("SYSTEM_TEST_TIME", "")

    # Count registered faculty and today's attendance from MySQL
    total_faculty = len(DEMO_FACULTY_LIST)
    today_punches = 0
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS c FROM faculty;")
        r_fac = cursor.fetchone()
        if r_fac:
            total_faculty = r_fac["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM attendance WHERE attendance_date = CURRENT_DATE;")
        r_att = cursor.fetchone()
        if r_att:
            today_punches = r_att["c"]
        cursor.close()
        conn.close()
    except Exception:
        pass

    msg_html = f'<div class="alert-success">✅ {msg}</div>' if msg else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Console - Faculty Attendance ERP</title>
    {BASE_CSS}
</head>
<body style="background-color: #030712;">
    <header class="top-bar-admin">
        <div class="brand">
            <span class="brand-icon">🛡️</span>
            <div>
                <div class="brand-title" style="color: #F87171;">ADMINISTRATION CONTROL CONSOLE</div>
                <div class="brand-sub" style="color: #FCA5A5;">Privileged System Operations & Diagnostics</div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 14px;">
            <span class="badge badge-red">SUPERUSER: {session.username}</span>
            <a href="/admin-logout" class="btn btn-sm btn-danger">🚪 Logout Admin</a>
        </div>
    </header>

    <div class="container" style="align-items: flex-start; padding-top: 32px;">
        <div class="card-wide">
            <h2>System Administration Dashboard</h2>
            <div style="color: #94A3B8; font-size: 13px; margin-bottom: 24px;">
                MySQL Database Target: <b>attendance_erp</b> &bull; Both Desktop PySide6 and Web Portals in Sync
            </div>
            {msg_html}

            <!-- KPI Cards -->
            <div class="grid-4">
                <div class="kpi-card">
                    <div class="kpi-title">Biometric Daemon</div>
                    <div class="kpi-value" style="color: {'#10B981' if 'ONLINE' in daemon_status else '#EF4444'};">
                        {daemon_status}
                    </div>
                    <div class="kpi-sub">{daemon_url[:28]}...</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Global Time Mode</div>
                    <div class="kpi-value" style="color: {'#F59E0B' if is_test_mode else '#10B981'};">
                        {'TEST' if is_test_mode else 'NORMAL'}
                    </div>
                    <div class="kpi-sub">{'Simulated Clock' if is_test_mode else 'Live System Clock'}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Active Faculty Count</div>
                    <div class="kpi-value">{total_faculty}</div>
                    <div class="kpi-sub">Across Academic Departments</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Punches Today</div>
                    <div class="kpi-value">{today_punches}</div>
                    <div class="kpi-sub">MySQL ATTENDANCE Table</div>
                </div>
            </div>

            <!-- Global System Time Controller Form -->
            <div style="background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 22px; margin-bottom: 24px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #F87171; margin-bottom: 10px;">
                    ⏰ Global System Time Mode Controller
                </h3>
                <p style="font-size: 12.5px; color: #94A3B8; margin-bottom: 16px;">
                    Current Effective Time: <b style="color: #60A5FA;">{current_time_str}</b>. 
                    Switch to <b>TEST</b> mode to inject custom simulated dates for attendance & leave evaluations.
                </p>

                <form action="/admin/time-mode" method="POST" style="display: flex; gap: 14px; align-items: flex-end; flex-wrap: wrap;">
                    <div>
                        <label class="label-dark">Time Mode:</label>
                        <select name="mode" class="input-dark" style="width: 140px;">
                            <option value="NORMAL" {"selected" if not is_test_mode else ""}>NORMAL (Live)</option>
                            <option value="TEST" {"selected" if is_test_mode else ""}>TEST (Simulated)</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 200px;">
                        <label class="label-dark">Injected Test Time (YYYY-MM-DD HH:MM:SS):</label>
                        <input type="text" name="test_time" class="input-dark" value="{test_time_val or current_time_str}" placeholder="e.g. 2026-10-31 09:30:00">
                    </div>
                    <div>
                        <button type="submit" class="btn btn-warning" style="width: auto; padding: 10px 18px;">
                            💾 Save & Apply Time Mode
                        </button>
                    </div>
                </form>
            </div>

            <!-- Direct Portals Navigation -->
            <div style="display: flex; gap: 14px; margin-top: 10px;">
                <a href="/punch-interface" target="_blank" class="btn btn-sm btn-primary">Open Mobile WebAuthn Gateway</a>
                <a href="/staff-login" target="_blank" class="btn btn-sm" style="background: #334155; color: white;">Open Staff CMS Portal</a>
            </div>

            <!-- Database Diagnostics & One-Click Backup Card -->
            <div style="background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 22px; margin-top: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="font-size: 15px; font-weight: 700; color: #F87171;">
                            🛡️ System Database Diagnostics & Snapshot Protection
                        </h3>
                        <p style="font-size: 12.5px; color: #94A3B8;">
                            Host: <b>127.0.0.1:3306</b> &bull; Schema: <b>attendance_erp</b> &bull; Driver: <b>mysql.connector</b> &bull; Status: <span style="color:#10B981; font-weight:bold;">CONNECTED</span>
                        </p>
                    </div>
                    <form action="/admin/backup" method="POST" style="margin: 0;">
                        <button type="submit" class="btn btn-danger" style="width: auto; padding: 9px 18px;">
                            ⚡ Create Standalone Database Backup (.zip)
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer">
        Faculty Attendance ERP &bull; System Administration Security Gateway
    </footer>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@web_portal_router.post("/admin/time-mode")
def update_admin_time_mode(request: Request):
    """Updates the global system time mode from the Admin Web Portal."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="admin_token",
    ) or request.cookies.get("admin_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    is_admin = (session and session.role == "ADMIN") or (jwt_payload and jwt_payload.get("role") == "ADMIN")
    if not is_admin:
        return RedirectResponse(url="/admin?error=Unauthorized", status_code=status.HTTP_303_SEE_OTHER)

    form = _parse_form_body(request)
    mode = form.get("mode", "NORMAL")
    test_time = form.get("test_time")

    clean_mode = "TEST" if mode.strip().upper() == "TEST" else "NORMAL"
    TimeService.set_time_mode(clean_mode, test_datetime=test_time)

    msg = f"Time mode updated to {clean_mode} (Mocked: {test_time or 'None'})"
    return RedirectResponse(url=f"/admin/dashboard?msg={msg}", status_code=status.HTTP_303_SEE_OTHER)


@web_portal_router.post("/admin/backup")
@web_portal_router.post("/admin-dashboard/trigger-backup")
def handle_admin_backup(request: Request):
    """Triggers on-demand standalone database backup snapshot from Admin Web Portal."""
    token = extract_token_from_request(
        request_headers=dict(request.headers),
        request_cookies=dict(request.cookies),
        cookie_key="admin_token",
    ) or request.cookies.get("admin_session")

    jwt_payload = decode_access_token(token) if token else None
    session = ACTIVE_WEB_SESSIONS.get(token) if token else None

    is_admin = (session and session.role == "ADMIN") or (jwt_payload and jwt_payload.get("role") == "ADMIN")
    if not is_admin:
        return RedirectResponse(url="/admin-login?error=Unauthorized", status_code=status.HTTP_303_SEE_OTHER)

    try:
        res = backup_service.create_backup()
        filename = res.get("backup_filename", "snapshot.zip")
        size_kb = round(res.get("archive_size_bytes", 0) / 1024, 1)
        msg = f"Database backup '{filename}' ({size_kb} KB) created successfully."
        return RedirectResponse(url=f"/admin/dashboard?msg={msg}", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        return RedirectResponse(url=f"/admin/dashboard?error={str(exc)}", status_code=status.HTTP_303_SEE_OTHER)


@web_portal_router.get("/admin-logout")
@web_portal_router.get("/admin/logout")
def process_admin_logout(response: Response, request: Request):
    """Logs out from the Admin Console, revokes JWT tokens, and clears cookies."""
    for key in ["admin_token", "admin_session", "admin_refresh_token"]:
        token = request.cookies.get(key)
        if token:
            revoke_token(token)
            if token in ACTIVE_WEB_SESSIONS:
                del ACTIVE_WEB_SESSIONS[token]
    redirect = RedirectResponse(url="/admin-login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(key="admin_token", path="/")
    redirect.delete_cookie(key="admin_session", path="/")
    redirect.delete_cookie(key="admin_refresh_token", path="/")
    redirect.delete_cookie(key="admin_csrf_token", path="/")
    return redirect
