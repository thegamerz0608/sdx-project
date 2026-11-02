"""
Multi-Tier Automated Email Workflow Service (SMTP & Audit Logger)
Handles asynchronous email dispatch for the institutional leave approval chain:
1. Faculty applies for leave -> Email sent to HOD.
2. HOD approves -> Email sent to HR.
3. HR approves -> Email sent to Principal.
4. Principal approves -> Final confirmation email sent to Faculty.
5. Final approval -> Alternate arrangement duty email dispatched to Substitute Faculty.

Uses environment variables SENDER_EMAIL, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT.
Includes safe offline mock fallback and persistent audit logging to logs/email_audit.log.
"""
import os
import sys
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("services.email_service")

# Dedicated email audit log file
BASE_DIR = Path(__file__).resolve().parent.parent
EMAIL_AUDIT_LOG = BASE_DIR / "logs" / "email_audit.log"


class EmailService:
    """Enterprise SMTP Email Notification Service with Asynchronous Dispatch & Audit Logging."""

    def __init__(self):
        # Environment variables with institutional defaults
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply.erp.faculty@gmail.com")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

        # In-memory sent email history for verification, diagnostics, and testing
        self.sent_emails: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        EMAIL_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    def is_smtp_configured(self) -> bool:
        """Checks if real SMTP credentials are provided in the environment."""
        return bool(self.sender_email and self.smtp_password and len(self.smtp_password.strip()) > 3)

    def _write_audit_log(self, recipient: str, subject: str, status: str, mode: str, details: str = ""):
        """Appends an immutable record to logs/email_audit.log."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = (
                f"[{timestamp}] [STATUS: {status}] [MODE: {mode}] "
                f"TO: {recipient} | SUBJECT: {subject} | DETAILS: {details}\n"
            )
            with open(EMAIL_AUDIT_LOG, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as exc:
            logger.debug(f"Could not write to email audit log: {exc}")

    def send_email_async(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        notification_type: str = "GENERAL",
    ) -> Dict[str, Any]:
        """
        Dispatches an email in a background daemon thread to eliminate UI blocking or API latency.
        Records the dispatch in self.sent_emails and logs/email_audit.log immediately.
        """
        email_record = {
            "id": len(self.sent_emails) + 1,
            "to_email": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "notification_type": notification_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "QUEUED",
            "mode": "SMTP" if self.is_smtp_configured() else "MOCK_LOG",
        }

        with self._lock:
            self.sent_emails.append(email_record)

        # Launch background dispatch thread
        thread = threading.Thread(
            target=self._dispatch_worker,
            args=(email_record,),
            daemon=True,
            name=f"EmailDispatch-{email_record['id']}",
        )
        thread.start()

        return {
            "success": True,
            "status": "QUEUED",
            "mode": email_record["mode"],
            "recipient": to_email,
            "subject": subject,
            "record_id": email_record["id"],
        }

    def _dispatch_worker(self, record: Dict[str, Any]):
        """Internal worker executed in background thread."""
        to_email = record["to_email"]
        subject = record["subject"]
        body_text = record["body_text"]
        body_html = record.get("body_html")

        if not self.is_smtp_configured():
            # Safe local development mode: record to logger & audit file
            record["status"] = "SENT_MOCK"
            self._write_audit_log(
                recipient=to_email,
                subject=subject,
                status="SENT_MOCK",
                mode="LOCAL_FALLBACK",
                details="Mock dispatch (SMTP_PASSWORD not set). Logged for verification.",
            )
            logger.info(f"[EMAIL MOCK] Dispatched '{subject}' to <{to_email}>")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.sender_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # Plain text part
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            # HTML part if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            # Connect and send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.sender_email, self.smtp_password)
                server.sendmail(self.sender_email, [to_email], msg.as_string())

            record["status"] = "SENT_LIVE"
            self._write_audit_log(
                recipient=to_email,
                subject=subject,
                status="SENT_LIVE",
                mode="LIVE_SMTP",
                details=f"Delivered via {self.smtp_server}:{self.smtp_port}",
            )
            logger.info(f"[EMAIL LIVE] Successfully delivered '{subject}' to <{to_email}>")

        except Exception as exc:
            record["status"] = "FAILED"
            record["error"] = str(exc)
            self._write_audit_log(
                recipient=to_email,
                subject=subject,
                status="FAILED",
                mode="LIVE_SMTP",
                details=f"SMTP Error: {exc}",
            )
            logger.warning(f"[EMAIL ERROR] Failed to send email to <{to_email}>: {exc}")

    # =========================================================================
    # Multi-Tier Workflow Methods
    # =========================================================================

    def send_leave_submission_to_hod(
        self,
        hod_email: str,
        applicant_name: str,
        employee_code: str,
        app_code: str,
        leave_type_name: str,
        from_date: str,
        to_date: str,
        total_days: float,
        reason: str,
        alternate_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Tier 1: Faculty applies for leave -> Email sent to HOD."""
        subject = f"[ERP Leave Request] Application {app_code} from {applicant_name}"
        
        alt_text = "None specified"
        if alternate_info and alternate_info.get("substitute_name"):
            alt_text = (
                f"\n  - Substitute Faculty: {alternate_info.get('substitute_name')} ({alternate_info.get('substitute_code', 'N/A')})"
                f"\n  - Date: {alternate_info.get('date', from_date)}"
                f"\n  - Time: {alternate_info.get('time', 'Class Hours')}"
                f"\n  - Place / Room: {alternate_info.get('place', 'Assigned Classroom')}"
                f"\n  - Work Description: {alternate_info.get('work_description', 'Conduct scheduled lecture/lab')}"
            )

        body_text = (
            f"Dear Head of Department,\n\n"
            f"A new leave application has been submitted and awaits your review:\n\n"
            f"• Application Code: {app_code}\n"
            f"• Faculty Member: {applicant_name} ({employee_code})\n"
            f"• Leave Category: {leave_type_name}\n"
            f"• Period: {from_date} to {to_date} ({total_days} day(s))\n"
            f"• Reason: {reason}\n\n"
            f"• Alternate Arrangement (Substitute):{alt_text}\n\n"
            f"Please log in to the Institutional ERP Portal to review and recommend this request.\n\n"
            f"Regards,\n"
            f"AI-Enabled Faculty ERP Workflow System"
        )

        return self.send_email_async(
            to_email=hod_email,
            subject=subject,
            body_text=body_text,
            notification_type="TIER1_HOD_SUBMISSION",
        )

    def send_hod_approval_to_hr(
        self,
        hr_email: str,
        applicant_name: str,
        employee_code: str,
        app_code: str,
        leave_type_name: str,
        from_date: str,
        to_date: str,
        total_days: float,
        hod_name: str,
        hod_remarks: Optional[str] = None,
        alternate_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Tier 2: HOD approves -> Email sent to HR."""
        subject = f"[ERP Leave Review] HOD Approved: {applicant_name} ({app_code})"
        
        alt_text = ""
        if alternate_info and alternate_info.get("substitute_name"):
            alt_text = f"\n• Assigned Substitute: {alternate_info.get('substitute_name')} ({alternate_info.get('place', '')})"

        body_text = (
            f"Dear HR Department,\n\n"
            f"The following leave application has been verified and recommended by HOD {hod_name}:\n\n"
            f"• Application Code: {app_code}\n"
            f"• Faculty Member: {applicant_name} ({employee_code})\n"
            f"• Leave Category: {leave_type_name}\n"
            f"• Dates: {from_date} to {to_date} ({total_days} day(s))\n"
            f"• HOD Remarks: {hod_remarks or 'Recommended by HOD'}{alt_text}\n\n"
            f"Please inspect faculty leave quotas, supporting documents, and advance the request to the Principal.\n\n"
            f"Regards,\n"
            f"AI-Enabled Faculty ERP Workflow System"
        )

        return self.send_email_async(
            to_email=hr_email,
            subject=subject,
            body_text=body_text,
            notification_type="TIER2_HR_REVIEW",
        )

    def send_hr_approval_to_principal(
        self,
        principal_email: str,
        applicant_name: str,
        employee_code: str,
        app_code: str,
        leave_type_name: str,
        from_date: str,
        to_date: str,
        total_days: float,
        hr_remarks: Optional[str] = None,
        alternate_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Tier 3: HR approves -> Email sent to Principal."""
        subject = f"[ERP Leave Sanction] Pending Principal Approval: {applicant_name} ({app_code})"

        alt_text = ""
        if alternate_info and alternate_info.get("substitute_name"):
            alt_text = f"\n• Alternate Arrangement: {alternate_info.get('substitute_name')} ({alternate_info.get('place', '')})"

        body_text = (
            f"Dear Principal / Executive Office,\n\n"
            f"The following faculty leave application has completed Departmental and HR verifications:\n\n"
            f"• Application Code: {app_code}\n"
            f"• Faculty Member: {applicant_name} ({employee_code})\n"
            f"• Leave Category: {leave_type_name}\n"
            f"• Requested Period: {from_date} to {to_date} ({total_days} day(s))\n"
            f"• HR Verification Remarks: {hr_remarks or 'Verified and quota confirmed'}{alt_text}\n\n"
            f"Please log in to the Executive Console to grant final executive sanction.\n\n"
            f"Regards,\n"
            f"AI-Enabled Faculty ERP Workflow System"
        )

        return self.send_email_async(
            to_email=principal_email,
            subject=subject,
            body_text=body_text,
            notification_type="TIER3_PRINCIPAL_SANCTION",
        )

    def send_final_approval_to_faculty(
        self,
        faculty_email: str,
        applicant_name: str,
        app_code: str,
        leave_type_name: str,
        from_date: str,
        to_date: str,
        total_days: float,
        principal_remarks: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tier 4: Principal approves -> Final confirmation email sent back to Faculty."""
        subject = f"[ERP Leave Approved] Your Leave Application {app_code} has been Sanctioned"
        body_text = (
            f"Dear {applicant_name},\n\n"
            f"We are pleased to inform you that your leave application has received final executive sanction:\n\n"
            f"• Application Code: {app_code}\n"
            f"• Leave Category: {leave_type_name}\n"
            f"• Approved Dates: {from_date} to {to_date} ({total_days} day(s))\n"
            f"• Executive Remarks: {principal_remarks or 'Approved by Principal'}\n"
            f"• Status: APPROVED\n\n"
            f"Your leave balance has been updated accordingly in the Institutional ERP.\n\n"
            f"Regards,\n"
            f"Office of the Principal & Faculty Administration"
        )

        return self.send_email_async(
            to_email=faculty_email,
            subject=subject,
            body_text=body_text,
            notification_type="TIER4_FACULTY_APPROVED",
        )

    def send_substitute_assignment_notification(
        self,
        substitute_email: str,
        substitute_name: str,
        applicant_name: str,
        app_code: str,
        assignment_date: str,
        start_time: str,
        end_time: str,
        classroom_location: str,
        work_description: str,
    ) -> Dict[str, Any]:
        """Tier 5: Final approval -> Automated email dispatched to assigned Substitute Faculty."""
        subject = f"[ERP Duty Assignment] Alternate Arrangement for {applicant_name} ({assignment_date})"
        body_text = (
            f"Dear {substitute_name},\n\n"
            f"This is an automated institutional notification regarding an approved alternate arrangement duty:\n\n"
            f"• Colleague on Leave: {applicant_name} (Leave Ref: {app_code})\n"
            f"• Duty Date: {assignment_date}\n"
            f"• Time Slot: {start_time} - {end_time}\n"
            f"• Classroom / Location: {classroom_location}\n"
            f"• Assigned Work Description: {work_description}\n\n"
            f"Please ensure timely attendance to cover the designated lecture / laboratory session.\n\n"
            f"Regards,\n"
            f"Department Academic Timetable Committee & Office of the Principal"
        )

        return self.send_email_async(
            to_email=substitute_email,
            subject=subject,
            body_text=body_text,
            notification_type="TIER5_SUBSTITUTE_ASSIGNMENT",
        )


email_service = EmailService()
