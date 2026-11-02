"""
Audit & Security Log Service
Manages system activity audit trails, RBAC permission verification, and application log file retrieval.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from repositories.audit_repository import audit_repository
from services.auth_service import auth_service
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("services.audit_service")


class AuditService:
    """Service providing audit trail search, system log reading, and RBAC matrix definitions."""

    def __init__(self):
        self.audit_repo = audit_repository

    def log_activity(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: str = "127.0.0.1",
    ):
        """
        Records an audit event with the currently authenticated user's session ID.
        """
        curr_user = auth_service.current_user
        user_id = curr_user.user_id if curr_user else None
        self.audit_repo.log_event(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )

    def get_audit_logs(
        self,
        limit: int = 200,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves audit logs filtered by user, action, entity type, and search term.
        Enforces RBAC: Non-admin users can only view their own audit records.
        """
        curr_user = auth_service.current_user

        # Enforce RBAC scoping
        if curr_user and not curr_user.is_admin():
            user_id = curr_user.user_id

        return self.audit_repo.get_audit_logs(
            limit=limit,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            search_term=search_term,
        )

    def get_rbac_permission_matrix(self) -> List[Dict[str, Any]]:
        """
        Returns the system RBAC (Role-Based Access Control) matrix mapping modules and features
        to permissions for ADMIN, HOD, and FACULTY roles.
        """
        return [
            {
                "module": "System Settings",
                "feature": "Environment & Core System Config",
                "ADMIN": "Full Control (Read/Write)",
                "HOD": "Read Only",
                "FACULTY": "No Access",
            },
            {
                "module": "User Accounts & RBAC",
                "feature": "User Management & Role Assignment",
                "ADMIN": "Full Control (Create/Edit/Delete)",
                "HOD": "No Access",
                "FACULTY": "No Access",
            },
            {
                "module": "Departments",
                "feature": "Department Directory & HOD Assignment",
                "ADMIN": "Full Control",
                "HOD": "View Designated Department",
                "FACULTY": "No Access",
            },
            {
                "module": "Faculty Directory",
                "feature": "Faculty Profile Management",
                "ADMIN": "Full Control (All Faculty)",
                "HOD": "Manage Department Faculty",
                "FACULTY": "View Profile & Directory",
            },
            {
                "module": "Attendance Engine",
                "feature": "CSV Importer & Roster Management",
                "ADMIN": "Upload CSV & Override Roster",
                "HOD": "View Dept Roster",
                "FACULTY": "View Personal Attendance",
            },
            {
                "module": "Grace Ledger Engine",
                "feature": "Monthly Late Minutes & Deduction Ledger",
                "ADMIN": "Process Monthly Grace Ledger",
                "HOD": "View Dept Grace Balances",
                "FACULTY": "View Personal Grace Balance",
            },
            {
                "module": "Leave Rules Policy",
                "feature": "Sandwich Rules & Consecutive Limits",
                "ADMIN": "Configure Leave Rules",
                "HOD": "View Policy Rules",
                "FACULTY": "View Policy Rules",
            },
            {
                "module": "Leave Workflow",
                "feature": "Leave Applications & Approvals",
                "ADMIN": "System Override & Final Audit",
                "HOD": "Approve/Reject Dept Leaves",
                "FACULTY": "Apply & Track Own Leaves",
            },
            {
                "module": "Substitute Recommendation",
                "feature": "Schedule Collision & Workload Ranking",
                "ADMIN": "View & Override Assignments",
                "HOD": "Assign Substitute Faculty",
                "FACULTY": "View Substitution Requests",
            },
            {
                "module": "NLP Leave Engine",
                "feature": "Text Preprocessing & Reason Analysis",
                "ADMIN": "Manage Corpus & Test NLP",
                "HOD": "View Classification Results",
                "FACULTY": "View AI Category Suggestions",
            },
            {
                "module": "TF-IDF Vectorizer",
                "feature": "Vocabulary & Feature Matrix Workbench",
                "ADMIN": "Extract & Inspect Features",
                "HOD": "Read Only",
                "FACULTY": "No Access",
            },
            {
                "module": "ML Classifier Studio",
                "feature": "Model Training & Evaluation Workbench",
                "ADMIN": "Train, Evaluate & Select Best Model",
                "HOD": "Read Model Performance KPIs",
                "FACULTY": "No Access",
            },
            {
                "module": "AI Risk & Recommendation",
                "feature": "Multi-Factor Risk & Auto-Approval Engine",
                "ADMIN": "Configure Risk Weight Thresholds",
                "HOD": "View Risk Score Breakdown",
                "FACULTY": "View Application Risk Level",
            },
            {
                "module": "Attendance Analytics",
                "feature": "KPI Dashboards & Anomaly Detection",
                "ADMIN": "Institution-Wide Analytics",
                "HOD": "Departmental Analytics",
                "FACULTY": "Personal Summary Stats",
            },
            {
                "module": "Report Studio",
                "feature": "Automated PDF & CSV Export",
                "ADMIN": "Generate All System Reports",
                "HOD": "Generate Dept Reports",
                "FACULTY": "Export Personal Statements",
            },
            {
                "module": "Audit Trail & Logs",
                "feature": "Security Audit Log & System App Log Explorer",
                "ADMIN": "Full Explorer & Log Viewer",
                "HOD": "View Own Audit Trail",
                "FACULTY": "View Own Audit Trail",
            },
        ]

    def get_system_logs(
        self, max_lines: int = 200, log_level: Optional[str] = None
    ) -> List[str]:
        """
        Reads recent log entries from the application log file (logs/app.log).
        Optionally filters by log level string (e.g. 'ERROR', 'WARNING', 'INFO').
        """
        log_file: Path = settings.LOG_DIR / "app.log"
        if not log_file.exists():
            return ["No application system log file found at: " + str(log_file)]

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            lines = [line.rstrip() for line in lines if line.strip()]

            if log_level and log_level.upper() != "ALL":
                lvl_tag = f"[{log_level.upper()}]"
                lines = [line for line in lines if lvl_tag in line]

            return lines[-max_lines:]
        except Exception as exc:
            logger.error(f"Error reading app log file: {exc}")
            return [f"Error reading system log file: {exc}"]


audit_service = AuditService()
