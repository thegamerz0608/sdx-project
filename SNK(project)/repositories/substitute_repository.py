"""
Substitute Repository
Handles SQL database queries and memory fallbacks for substitute_assignments and timetable availability checks.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.substitute_repository")

# Fallback dataset for offline execution
DEMO_SUBSTITUTE_ASSIGNMENTS = [
    {
        "id": 1,
        "leave_application_id": 1,
        "application_code": "LA-2026-0001",
        "original_faculty_id": 2,
        "original_faculty_code": "F002",
        "original_faculty_name": "Rahul Sharma",
        "substitute_faculty_id": 3,
        "substitute_faculty_code": "F003",
        "substitute_faculty_name": "Priya Verma",
        "department_id": 1,
        "department_code": "MCA",
        "assignment_date": "2026-09-20",
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "class_details": "MCA 1st Sem - Data Structures Lecture",
        "status": "ASSIGNED",
        "assigned_by_user_id": 2,
        "remarks": "Assigned covering morning lecture",
        "created_at": "2026-09-15 11:00:00",
    },
    {
        "id": 2,
        "leave_application_id": 2,
        "application_code": "LA-2026-0002",
        "original_faculty_id": 3,
        "original_faculty_code": "F003",
        "original_faculty_name": "Priya Verma",
        "substitute_faculty_id": 1,
        "substitute_faculty_code": "F001",
        "substitute_faculty_name": "Dr. Suresh Kumar",
        "department_id": 1,
        "department_code": "MCA",
        "assignment_date": "2026-09-08",
        "start_time": "11:00:00",
        "end_time": "12:00:00",
        "class_details": "MCA 3rd Sem - Database Systems Lab",
        "status": "COMPLETED",
        "assigned_by_user_id": 2,
        "remarks": "Lecture successfully conducted by substitute",
        "created_at": "2026-09-08 09:30:00",
    },
]


class SubstituteRepository:
    """Repository managing MySQL operations for substitute_assignments."""

    def create_assignment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts a new substitute assignment record."""
        insert_sql = """
            INSERT INTO substitute_assignments (
                leave_application_id, original_faculty_id, substitute_faculty_id, department_id,
                assignment_date, start_time, end_time, class_details, status, assigned_by_user_id, remarks
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ASSIGNED', %s, %s)
            RETURNING id;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                insert_sql,
                (
                    data["leave_application_id"],
                    data["original_faculty_id"],
                    data["substitute_faculty_id"],
                    data["department_id"],
                    data["assignment_date"],
                    data["start_time"],
                    data["end_time"],
                    data["class_details"],
                    data.get("assigned_by_user_id"),
                    data.get("remarks"),
                ),
            )
            row = cursor.fetchone()
            new_id = row[0] if row else getattr(cursor, "lastrowid", None)
            conn.commit()
            cursor.close()
            conn.close()
            return self.get_assignment_by_id(new_id) or {}

        except Exception as exc:
            logger.warning(f"DB create substitute assignment error, adding to fallback: {exc}")
            new_id = max([a["id"] for a in DEMO_SUBSTITUTE_ASSIGNMENTS], default=0) + 1
            item = data.copy()
            item["id"] = new_id
            item["status"] = "ASSIGNED"
            item["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            DEMO_SUBSTITUTE_ASSIGNMENTS.insert(0, item)
            return item.copy()

    def get_assignments(
        self,
        department_id: Optional[int] = None,
        substitute_faculty_id: Optional[int] = None,
        date_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves substitute assignments matching department, substitute, date, and status filters."""
        query = """
            SELECT 
                sa.id,
                sa.leave_application_id,
                la.application_code,
                sa.original_faculty_id,
                fo.employee_code AS original_faculty_code,
                CONCAT(fo.first_name, ' ', fo.last_name) AS original_faculty_name,
                sa.substitute_faculty_id,
                fs.employee_code AS substitute_faculty_code,
                CONCAT(fs.first_name, ' ', fs.last_name) AS substitute_faculty_name,
                sa.department_id,
                d.code AS department_code,
                sa.assignment_date,
                sa.start_time,
                sa.end_time,
                sa.class_details,
                sa.status,
                sa.assigned_by_user_id,
                sa.remarks,
                sa.created_at
            FROM substitute_assignments sa
            INNER JOIN faculty fo ON fo.id = sa.original_faculty_id
            INNER JOIN faculty fs ON fs.id = sa.substitute_faculty_id
            INNER JOIN departments d ON d.id = sa.department_id
            LEFT JOIN leave_applications la ON la.id = sa.leave_application_id
            WHERE 1=1
        """
        params = []
        if department_id is not None:
            query += " AND sa.department_id = %s"
            params.append(department_id)

        if substitute_faculty_id is not None:
            query += " AND sa.substitute_faculty_id = %s"
            params.append(substitute_faculty_id)

        if date_filter:
            query += " AND sa.assignment_date = %s"
            params.append(date_filter)

        if status_filter and status_filter.upper() != "ALL":
            query += " AND sa.status = %s"
            params.append(status_filter.upper())

        query += " ORDER BY sa.assignment_date DESC, sa.start_time ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows

        except Exception as exc:
            logger.debug(f"DB get substitute assignments query fallback: {exc}")
            results = []
            for sa in DEMO_SUBSTITUTE_ASSIGNMENTS:
                if department_id is not None and sa.get("department_id") != department_id:
                    continue
                if substitute_faculty_id is not None and sa.get("substitute_faculty_id") != substitute_faculty_id:
                    continue
                if date_filter and sa.get("assignment_date") != date_filter:
                    continue
                if status_filter and status_filter.upper() != "ALL" and sa.get("status") != status_filter.upper():
                    continue
                results.append(sa.copy())
            return results

    def get_assignment_by_id(self, assignment_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single substitute assignment by ID."""
        assignments = self.get_assignments()
        for sa in assignments:
            if sa["id"] == assignment_id:
                return sa
        for sa in DEMO_SUBSTITUTE_ASSIGNMENTS:
            if sa["id"] == assignment_id:
                return sa.copy()
        return None

    def get_assignment_by_leave_id(self, leave_application_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves substitute assignment record linked to a leave application."""
        assignments = self.get_assignments()
        for sa in assignments:
            if sa.get("leave_application_id") == leave_application_id:
                return sa
        for sa in DEMO_SUBSTITUTE_ASSIGNMENTS:
            if sa.get("leave_application_id") == leave_application_id:
                return sa.copy()
        return None

    def get_faculty_monthly_substitute_count(self, faculty_id: int, month_year: str = "2026-09") -> int:
        """Counts cumulative substitute assignments for a faculty member in a month."""
        query = """
            SELECT COUNT(*) AS total_count
            FROM substitute_assignments
            WHERE substitute_faculty_id = %s 
              AND TO_CHAR(assignment_date, 'YYYY-MM') = %s
              AND status IN ('ASSIGNED', 'ACCEPTED', 'COMPLETED');
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (faculty_id, month_year))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row["total_count"] if row else 0
        except Exception as exc:
            logger.debug(f"DB monthly substitute count query fallback: {exc}")
            cnt = 0
            for sa in DEMO_SUBSTITUTE_ASSIGNMENTS:
                if (
                    sa.get("substitute_faculty_id") == faculty_id
                    and str(sa.get("assignment_date", ""))[:7] == month_year
                    and sa.get("status") in ["ASSIGNED", "ACCEPTED", "COMPLETED"]
                ):
                    cnt += 1
            return cnt

    def has_schedule_conflict(
        self, faculty_id: int, assignment_date: str, start_time: str, end_time: str
    ) -> bool:
        """
        Checks if the candidate substitute has a conflicting assignment on the date & time.
        """
        query = """
            SELECT id FROM substitute_assignments
            WHERE substitute_faculty_id = %s
              AND assignment_date = %s
              AND status IN ('ASSIGNED', 'ACCEPTED')
              AND (
                  (start_time <= %s AND end_time > %s) OR
                  (start_time < %s AND end_time >= %s) OR
                  (start_time >= %s AND end_time <= %s)
              );
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    faculty_id,
                    assignment_date,
                    start_time,
                    start_time,
                    end_time,
                    end_time,
                    start_time,
                    end_time,
                ),
            )
            conflict = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return conflict
        except Exception as exc:
            logger.debug(f"DB schedule conflict query fallback: {exc}")
            for sa in DEMO_SUBSTITUTE_ASSIGNMENTS:
                if (
                    sa.get("substitute_faculty_id") == faculty_id
                    and sa.get("assignment_date") == assignment_date
                    and sa.get("status") in ["ASSIGNED", "ACCEPTED"]
                ):
                    if sa.get("start_time") == start_time:
                        return True
            return False

    def update_assignment_status(
        self, assignment_id: int, status: str, remarks: Optional[str] = None
    ) -> bool:
        """Updates assignment status and remarks."""
        update_sql = """
            UPDATE substitute_assignments
            SET status = %s, remarks = %s
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(update_sql, (status.upper(), remarks, assignment_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.warning(f"DB update assignment status error, updating fallback: {exc}")
            for sa in DEMO_SUBSTITUTE_ASSIGNMENTS:
                if sa["id"] == assignment_id:
                    sa["status"] = status.upper()
                    if remarks:
                        sa["remarks"] = remarks
                    return True
            return True


substitute_repository = SubstituteRepository()
