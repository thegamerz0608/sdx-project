"""
Attendance Repository
Handles SQL database queries for attendance logging, batch imports, grace minute deductions, and flagged conflict management.
"""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.attendance_repository")

# Fallback prototype demo attendance records when DB is offline
DEMO_ATTENDANCE = [
    {
        "id": 1,
        "faculty_id": 2,
        "employee_code": "F001",
        "faculty_name": "Dr. Suresh Kumar",
        "department_id": 1,
        "department_code": "MCA",
        "attendance_date": "2026-09-01",
        "login_time": "08:55:00",
        "logout_time": "17:05:00",
        "status": "PRESENT",
        "late_minutes": 0,
        "working_hours": 8.16,
        "early_departure_minutes": 0,
        "is_flagged": 0,
        "flag_reason": None,
    },
    {
        "id": 2,
        "faculty_id": 3,
        "employee_code": "F002",
        "faculty_name": "Rahul Sharma",
        "department_id": 1,
        "department_code": "MCA",
        "attendance_date": "2026-09-01",
        "login_time": "09:12:00",
        "logout_time": "17:00:00",
        "status": "PRESENT",
        "late_minutes": 12,
        "working_hours": 7.80,
        "early_departure_minutes": 0,
        "is_flagged": 0,
        "flag_reason": None,
    },
    {
        "id": 3,
        "faculty_id": 3,
        "employee_code": "F002",
        "faculty_name": "Rahul Sharma",
        "department_id": 1,
        "department_code": "MCA",
        "attendance_date": "2026-09-02",
        "login_time": "09:05:00",
        "logout_time": "16:30:00",
        "status": "PRESENT",
        "late_minutes": 5,
        "working_hours": 7.41,
        "early_departure_minutes": 0,
        "is_flagged": 0,
        "flag_reason": None,
    },
    {
        "id": 4,
        "faculty_id": 4,
        "employee_code": "F003",
        "faculty_name": "Priya Verma",
        "department_id": 1,
        "department_code": "MCA",
        "attendance_date": "2026-09-01",
        "login_time": "09:00:00",
        "logout_time": "17:00:00",
        "status": "PRESENT",
        "late_minutes": 0,
        "working_hours": 8.00,
        "early_departure_minutes": 0,
        "is_flagged": 0,
        "flag_reason": None,
    },
]


class AttendanceRepository:
    """Repository managing SQL database operations for the attendance table."""

    def get_all(
        self,
        department_id: Optional[int] = None,
        faculty_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves attendance logs with department, faculty profile, late minutes, and working hours.
        Supports filtering by department, faculty, and date range.
        """
        query = """
            SELECT 
                a.id,
                a.faculty_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS faculty_name,
                f.department_id,
                d.code AS department_code,
                a.attendance_date,
                a.login_time,
                a.logout_time,
                a.status,
                a.late_minutes,
                a.working_hours,
                a.early_departure_minutes,
                a.import_batch_id,
                a.is_flagged,
                a.flag_reason
            FROM attendance a
            INNER JOIN faculty f ON f.id = a.faculty_id
            INNER JOIN departments d ON d.id = f.department_id
            WHERE 1=1
        """
        params = []
        if department_id is not None:
            query += " AND f.department_id = %s"
            params.append(department_id)

        if faculty_id is not None:
            query += " AND a.faculty_id = %s"
            params.append(faculty_id)

        if start_date:
            query += " AND a.attendance_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND a.attendance_date <= %s"
            params.append(end_date)

        query += " ORDER BY a.attendance_date DESC, f.employee_code ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB attendance query unavailable, using fallback: {exc}")
            results = []
            for r in DEMO_ATTENDANCE:
                dept_id = r.get("department_id")
                fac_id = r.get("faculty_id")
                att_date = r.get("attendance_date")
                if department_id is not None and dept_id is not None and dept_id != department_id:
                    continue
                if faculty_id is not None and fac_id is not None and fac_id != faculty_id:
                    continue
                if start_date and att_date and att_date < start_date:
                    continue
                if end_date and att_date and att_date > end_date:
                    continue
                results.append(r.copy())
            return results

    def save_imported_records(self, records: List[Dict[str, Any]], batch_id: str) -> int:
        """
        Saves imported valid attendance records to database using ON CONFLICT DO UPDATE.
        Deducts late minutes from monthly grace tracking table.
        """
        if not records:
            return 0

        query = """
            INSERT INTO attendance (
                faculty_id, attendance_date, login_time, logout_time, status,
                late_minutes, working_hours, early_departure_minutes, import_batch_id,
                is_flagged, flag_reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (faculty_id, attendance_date) DO UPDATE SET
                login_time = EXCLUDED.login_time,
                logout_time = EXCLUDED.logout_time,
                status = EXCLUDED.status,
                late_minutes = EXCLUDED.late_minutes,
                working_hours = EXCLUDED.working_hours,
                import_batch_id = EXCLUDED.import_batch_id,
                is_flagged = EXCLUDED.is_flagged,
                flag_reason = EXCLUDED.flag_reason;
        """
        saved_count = 0
        try:
            conn = get_connection()
            cursor = conn.cursor()

            for rec in records:
                cursor.execute(
                    query,
                    (
                        rec["faculty_id"],
                        rec["attendance_date"],
                        rec["login_time"],
                        rec["logout_time"],
                        rec["status"],
                        rec["late_minutes"],
                        rec["working_hours"],
                        rec.get("early_departure_minutes", 0),
                        batch_id,
                        rec.get("is_flagged", 0),
                        rec.get("flag_reason"),
                    ),
                )
                saved_count += 1

                # Update Monthly Grace Minutes if late minutes exist
                if rec["late_minutes"] > 0:
                    month_str = rec["attendance_date"][:7]  # YYYY-MM
                    grace_update_sql = """
                        INSERT INTO grace_minutes (faculty_id, month_year, allowed_minutes, used_minutes)
                        VALUES (%s, %s, 45, %s)
                        ON CONFLICT (faculty_id, month_year) DO UPDATE SET used_minutes = grace_minutes.used_minutes + EXCLUDED.used_minutes;
                    """
                    cursor.execute(grace_update_sql, (rec["faculty_id"], month_str, rec["late_minutes"]))

            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Committed {saved_count} attendance records under batch '{batch_id}'.")
            return saved_count

        except Exception as exc:
            logger.warning(f"DB save imported attendance error, adding to memory fallback: {exc}")
            for rec in records:
                new_id = max([r["id"] for r in DEMO_ATTENDANCE], default=0) + 1
                item = rec.copy()
                item["id"] = new_id
                item["import_batch_id"] = batch_id
                DEMO_ATTENDANCE.insert(0, item)
                saved_count += 1
            return saved_count


attendance_repository = AttendanceRepository()
