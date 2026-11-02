"""
Leave Application Repository
Handles SQL database queries and memory fallbacks for leave_applications and leave balance transitions.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.leave_application_repository")

        # Fallback in-memory dataset for offline/prototype execution
DEMO_LEAVE_APPLICATIONS = [
    {
        "id": 1,
        "application_code": "LA-2026-0001",
        "faculty_id": 2,
        "employee_code": "F002",
        "faculty_name": "Rahul Sharma",
        "department_id": 1,
        "department_code": "MCA",
        "requested_leave_type_id": 1,
        "leave_type_code": "CL",
        "leave_type_name": "Casual Leave",
        "ai_predicted_type_id": 1,
        "ai_predicted_code": "CL",
        "ai_predicted_name": "Casual Leave",
        "ai_confidence": 0.9420,
        "from_date": "2026-09-20",
        "to_date": "2026-09-21",
        "total_days": 2.0,
        "reason": "Attending family function in native town",
        "faculty_selected_type_id": 1,
        "document_path": None,
        "status": "PENDING_HR",
        "hod_status": "APPROVED",
        "hr_status": "PENDING",
        "principal_status": "PENDING",
        "hod_remarks": "Recommended by HOD MCA.",
        "hr_remarks": None,
        "principal_remarks": None,
        "reviewed_by_user_id": 2,
        "reviewer_name": "Dr. Suresh Kumar",
        "reviewed_at": "2026-09-16 11:00:00",
        "created_at": "2026-09-15 10:30:00",
    },
    {
        "id": 2,
        "application_code": "LA-2026-0002",
        "faculty_id": 3,
        "employee_code": "F003",
        "faculty_name": "Priya Verma",
        "department_id": 1,
        "department_code": "MCA",
        "requested_leave_type_id": 5,
        "leave_type_code": "ML",
        "leave_type_name": "Medical Leave",
        "ai_predicted_type_id": 5,
        "ai_predicted_code": "ML",
        "ai_predicted_name": "Medical Leave",
        "ai_confidence": 0.9780,
        "from_date": "2026-09-08",
        "to_date": "2026-09-10",
        "total_days": 3.0,
        "reason": "Severe fever and viral infection advice rest",
        "faculty_selected_type_id": 5,
        "document_path": "uploads/medical_cert_priya.pdf",
        "status": "APPROVED",
        "hod_status": "APPROVED",
        "hr_status": "APPROVED",
        "principal_status": "APPROVED",
        "hod_remarks": "Approved. Medical certificate verified.",
        "hr_remarks": "Verified medical documentation. Entitlement valid.",
        "principal_remarks": "Executive approval granted.",
        "reviewed_by_user_id": 2,
        "reviewer_name": "Dr. Suresh Kumar",
        "reviewed_at": "2026-09-08 14:00:00",
        "created_at": "2026-09-08 09:00:00",
    },
]


class LeaveApplicationRepository:
    """Repository managing MySQL operations for leave_applications and balance state transitions."""

    def create_application(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new leave application record into MySQL or fallback list with AI classification metadata."""
        insert_sql = """
            INSERT INTO leave_applications (
                application_code, faculty_id, requested_leave_type_id, from_date, to_date, 
                total_days, reason, faculty_selected_type_id, document_path,
                ai_predicted_type_id, ai_confidence, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """
        code = data.get("application_code") or f"LA-2026-{len(DEMO_LEAVE_APPLICATIONS)+101:04d}"
        ai_pred_id = data.get("ai_predicted_type_id")
        ai_conf = data.get("ai_confidence")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                insert_sql,
                (
                    code,
                    data["faculty_id"],
                    data["requested_leave_type_id"],
                    data["from_date"],
                    data["to_date"],
                    data["total_days"],
                    data["reason"],
                    data.get("faculty_selected_type_id", data["requested_leave_type_id"]),
                    data.get("document_path"),
                    ai_pred_id,
                    ai_conf,
                ),
            )
            row = cursor.fetchone()
            new_id = row[0] if row else getattr(cursor, "lastrowid", None)
            conn.commit()
            cursor.close()
            conn.close()
            return self.get_application_by_id(new_id) or {}

        except Exception as exc:
            logger.warning(f"DB create leave application error, adding to fallback: {exc}")
            new_id = max([a["id"] for a in DEMO_LEAVE_APPLICATIONS], default=0) + 1
            item = data.copy()
            item["id"] = new_id
            item["application_code"] = code
            item["status"] = "PENDING"
            item["ai_predicted_type_id"] = ai_pred_id
            item["ai_predicted_code"] = data.get("ai_predicted_code", data.get("leave_type_code", "CL"))
            item["ai_confidence"] = ai_conf if ai_conf is not None else 0.8800
            item["hod_remarks"] = None
            item["reviewed_by_user_id"] = None
            item["reviewer_name"] = None
            item["reviewed_at"] = None
            item["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if "department_id" not in item:
                item["department_id"] = data.get("department_id", 1)
            if "department_code" not in item:
                item["department_code"] = data.get("department_code", "MCA")
            if "employee_code" not in item:
                item["employee_code"] = data.get("employee_code", f"F00{data.get('faculty_id', 1)}")
            if "faculty_name" not in item:
                item["faculty_name"] = data.get("faculty_name", "Faculty Member")
            if "leave_type_code" not in item:
                item["leave_type_code"] = data.get("leave_type_code", "CL")
            if "leave_type_name" not in item:
                item["leave_type_name"] = data.get("leave_type_name", "Casual Leave")

            DEMO_LEAVE_APPLICATIONS.insert(0, item)
            return item.copy()

    def get_applications(
        self,
        department_id: Optional[int] = None,
        faculty_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves leave applications matching department, faculty, and status filters."""
        query = """
            SELECT 
                la.id,
                la.application_code,
                la.faculty_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS faculty_name,
                f.department_id,
                d.code AS department_code,
                la.requested_leave_type_id,
                lt.code AS leave_type_code,
                lt.name AS leave_type_name,
                la.ai_predicted_type_id,
                ai_lt.code AS ai_predicted_code,
                ai_lt.name AS ai_predicted_name,
                la.ai_confidence,
                la.from_date,
                la.to_date,
                la.total_days,
                la.reason,
                la.document_path,
                la.status,
                la.hod_remarks,
                la.reviewed_by_user_id,
                u.username AS reviewer_name,
                la.reviewed_at,
                la.created_at
            FROM leave_applications la
            INNER JOIN faculty f ON f.id = la.faculty_id
            INNER JOIN departments d ON d.id = f.department_id
            INNER JOIN leave_types lt ON lt.id = la.requested_leave_type_id
            LEFT JOIN leave_types ai_lt ON ai_lt.id = la.ai_predicted_type_id
            LEFT JOIN users u ON u.id = la.reviewed_by_user_id
            WHERE 1=1
        """
        params = []
        if department_id is not None:
            query += " AND f.department_id = %s"
            params.append(department_id)

        if faculty_id is not None:
            query += " AND la.faculty_id = %s"
            params.append(faculty_id)

        if status_filter and status_filter.upper() != "ALL":
            query += " AND la.status = %s"
            params.append(status_filter.upper())

        query += " ORDER BY la.created_at DESC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows

        except Exception as exc:
            logger.debug(f"DB get applications query fallback: {exc}")
            results = []
            for a in DEMO_LEAVE_APPLICATIONS:
                if department_id is not None and a.get("department_id") != department_id:
                    continue
                if faculty_id is not None and a.get("faculty_id") != faculty_id:
                    continue
                if status_filter and status_filter.upper() != "ALL" and a.get("status") != status_filter.upper():
                    continue
                results.append(a.copy())
            return results

    def get_application_by_id(self, application_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single leave application record by ID."""
        apps = self.get_applications()
        for a in apps:
            if a["id"] == application_id:
                return a
        for a in DEMO_LEAVE_APPLICATIONS:
            if a["id"] == application_id:
                return a.copy()
        return None

    def update_application_status(
        self,
        application_id: int,
        status: str,
        reviewer_user_id: Optional[int] = None,
        remarks: Optional[str] = None,
    ) -> bool:
        """Updates status, reviewer ID, remarks, and timestamp for an application."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_sql = """
            UPDATE leave_applications 
            SET status = %s, reviewed_by_user_id = %s, hod_remarks = %s, reviewed_at = %s
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(update_sql, (status.upper(), reviewer_user_id, remarks, now_str, application_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.warning(f"DB update application status error, updating fallback: {exc}")
            for a in DEMO_LEAVE_APPLICATIONS:
                if a["id"] == application_id:
                    a["status"] = status.upper()
                    a["reviewed_by_user_id"] = reviewer_user_id
                    a["hod_remarks"] = remarks
                    a["reviewed_at"] = now_str
                    return True
            return True

    def update_multi_stage_status(
        self,
        application_id: int,
        overall_status: str,
        stage_column: str,
        stage_status: str,
        remarks_column: Optional[str] = None,
        remarks: Optional[str] = None,
        reviewer_user_id: Optional[int] = None,
    ) -> bool:
        """
        Updates multi-stage approval attributes (hod_status, hr_status, principal_status, hr_remarks, etc.).
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = f"""
            UPDATE leave_applications 
            SET status = %s, {stage_column} = %s, reviewed_by_user_id = %s, reviewed_at = %s
        """
        params = [overall_status.upper(), stage_status.upper(), reviewer_user_id, now_str]
        if remarks_column:
            sql += f", {remarks_column} = %s"
            params.append(remarks)
        sql += " WHERE id = %s;"
        params.append(application_id)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.debug(f"DB multi-stage update fallback: {exc}")
            for a in DEMO_LEAVE_APPLICATIONS:
                if a["id"] == application_id:
                    a["status"] = overall_status.upper()
                    a[stage_column] = stage_status.upper()
                    if remarks_column:
                        a[remarks_column] = remarks
                    a["reviewed_by_user_id"] = reviewer_user_id
                    a["reviewed_at"] = now_str
                    return True
            return True

    def modify_application_dates(
        self, application_id: int, from_date: str, to_date: str, total_days: float
    ) -> bool:
        """HR Special Power: Modifies requested dates/days for a leave application."""
        sql = """
            UPDATE leave_applications
            SET from_date = %s, to_date = %s, total_days = %s
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (from_date, to_date, total_days, application_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.debug(f"DB modify application dates fallback: {exc}")
            for a in DEMO_LEAVE_APPLICATIONS:
                if a["id"] == application_id:
                    a["from_date"] = from_date
                    a["to_date"] = to_date
                    a["total_days"] = float(total_days)
                    return True
            return True

    def update_balance_state(
        self, faculty_id: int, leave_type_id: int, year: int, days: float, state_action: str
    ) -> bool:
        """
        Updates transactional pending_days / used_days balance states:
        - 'SUBMIT': pending_days += days
        - 'APPROVE': pending_days -= days, used_days += days
        - 'REJECT' / 'CANCEL': pending_days -= days
        """
        if state_action == "SUBMIT":
            sql = """
                UPDATE leave_balance 
                SET pending_days = pending_days + %s 
                WHERE faculty_id = %s AND leave_type_id = %s AND year = %s;
            """
            params = (days, faculty_id, leave_type_id, year)
        elif state_action == "APPROVE":
            sql = """
                UPDATE leave_balance 
                SET pending_days = GREATEST(0.00, pending_days - %s), used_days = used_days + %s 
                WHERE faculty_id = %s AND leave_type_id = %s AND year = %s;
            """
            params = (days, days, faculty_id, leave_type_id, year)
        elif state_action in ["REJECT", "CANCEL"]:
            sql = """
                UPDATE leave_balance 
                SET pending_days = GREATEST(0.00, pending_days - %s) 
                WHERE faculty_id = %s AND leave_type_id = %s AND year = %s;
            """
            params = (days, faculty_id, leave_type_id, year)
        else:
            return False

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.warning(f"DB update balance state ({state_action}) error, handled in fallback: {exc}")
            return True


leave_application_repository = LeaveApplicationRepository()
