"""
Grace Minutes Repository
Handles SQL database operations and memory fallbacks for monthly faculty grace minute allocations, deductions, ledgers, and allowance updates.
"""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.grace_repository")

# In-memory fallback dataset for offline/prototype execution
DEMO_GRACE_LEDGER = [
    {
        "id": 1,
        "faculty_id": 1,
        "employee_code": "F001",
        "faculty_name": "Dr. Suresh Kumar",
        "department_id": 1,
        "department_code": "MCA",
        "month_year": "2026-09",
        "allowed_minutes": 45,
        "used_minutes": 0,
        "remaining_minutes": 45,
        "status": "NORMAL",
    },
    {
        "id": 2,
        "faculty_id": 2,
        "employee_code": "F002",
        "faculty_name": "Rahul Sharma",
        "department_id": 1,
        "department_code": "MCA",
        "month_year": "2026-09",
        "allowed_minutes": 45,
        "used_minutes": 17,
        "remaining_minutes": 28,
        "status": "NORMAL",
    },
    {
        "id": 3,
        "faculty_id": 3,
        "employee_code": "F003",
        "faculty_name": "Priya Verma",
        "department_id": 1,
        "department_code": "MCA",
        "month_year": "2026-09",
        "allowed_minutes": 45,
        "used_minutes": 38,
        "remaining_minutes": 7,
        "status": "WARNING",
    },
    {
        "id": 4,
        "faculty_id": 4,
        "employee_code": "F004",
        "faculty_name": "Dr. Amit Patel",
        "department_id": 2,
        "department_code": "MBA",
        "month_year": "2026-09",
        "allowed_minutes": 45,
        "used_minutes": 50,
        "remaining_minutes": -5,
        "status": "EXHAUSTED",
    },
]


class GraceRepository:
    """Repository managing MySQL operations for faculty grace minute allocations & ledgers."""

    def _compute_status(self, remaining: int) -> str:
        """Determines exhaustion status tag based on remaining grace minutes."""
        if remaining > 15:
            return "NORMAL"
        elif remaining >= 0:
            return "WARNING"
        else:
            return "EXHAUSTED"

    def get_ledger(
        self, department_id: Optional[int] = None, month_year: str = "2026-09"
    ) -> List[Dict[str, Any]]:
        """
        Retrieves monthly grace ledger records joined with faculty & department details.
        """
        query = """
            SELECT 
                g.id,
                g.faculty_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS faculty_name,
                f.department_id,
                d.code AS department_code,
                g.month_year,
                g.allowed_minutes,
                g.used_minutes,
                (g.allowed_minutes - g.used_minutes) AS remaining_minutes
            FROM grace_minutes g
            INNER JOIN faculty f ON f.id = g.faculty_id
            INNER JOIN departments d ON d.id = f.department_id
            WHERE g.month_year = %s
        """
        params = [month_year]
        if department_id is not None:
            query += " AND f.department_id = %s"
            params.append(department_id)

        query += " ORDER BY d.code ASC, f.employee_code ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            for r in rows:
                r["status"] = self._compute_status(r["remaining_minutes"])
            return rows

        except Exception as exc:
            logger.debug(f"DB grace ledger query unavailable, using fallback: {exc}")
            results = []
            for item in DEMO_GRACE_LEDGER:
                if item["month_year"] != month_year:
                    continue
                if department_id is not None and item.get("department_id") != department_id:
                    continue
                c = item.copy()
                c["remaining_minutes"] = c["allowed_minutes"] - c["used_minutes"]
                c["status"] = self._compute_status(c["remaining_minutes"])
                results.append(c)
            return results

    def get_faculty_grace(self, faculty_id: int, month_year: str) -> Optional[Dict[str, Any]]:
        """Retrieves grace record for a specific faculty member and month."""
        query = """
            SELECT 
                g.id,
                g.faculty_id,
                g.month_year,
                g.allowed_minutes,
                g.used_minutes,
                (g.allowed_minutes - g.used_minutes) AS remaining_minutes
            FROM grace_minutes g
            WHERE g.faculty_id = %s AND g.month_year = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (faculty_id, month_year))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                row["status"] = self._compute_status(row["remaining_minutes"])
                return row
            return None
        except Exception as exc:
            logger.debug(f"DB faculty grace query unavailable, fallback lookup: {exc}")
            for item in DEMO_GRACE_LEDGER:
                if item["faculty_id"] == faculty_id and item["month_year"] == month_year:
                    c = item.copy()
                    c["remaining_minutes"] = c["allowed_minutes"] - c["used_minutes"]
                    c["status"] = self._compute_status(c["remaining_minutes"])
                    return c
            return None

    def deduct_grace_minutes(self, faculty_id: int, month_year: str, minutes: int) -> Dict[str, Any]:
        """
        Adds minutes to used_minutes for the specified faculty and month.
        Creates record if it does not exist.
        """
        upsert_sql = """
            INSERT INTO grace_minutes (faculty_id, month_year, allowed_minutes, used_minutes)
            VALUES (%s, %s, 45, %s)
            ON CONFLICT (faculty_id, month_year) DO UPDATE SET used_minutes = grace_minutes.used_minutes + EXCLUDED.used_minutes;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(upsert_sql, (faculty_id, month_year, minutes))
            conn.commit()
            cursor.close()
            conn.close()
            return self.get_faculty_grace(faculty_id, month_year) or {}

        except Exception as exc:
            logger.warning(f"DB deduct grace error, updating fallback: {exc}")
            found = False
            for item in DEMO_GRACE_LEDGER:
                if item["faculty_id"] == faculty_id and item["month_year"] == month_year:
                    item["used_minutes"] += minutes
                    item["remaining_minutes"] = item["allowed_minutes"] - item["used_minutes"]
                    item["status"] = self._compute_status(item["remaining_minutes"])
                    return item.copy()
            if not found:
                new_item = {
                    "id": max([r["id"] for r in DEMO_GRACE_LEDGER], default=0) + 1,
                    "faculty_id": faculty_id,
                    "employee_code": f"F00{faculty_id}",
                    "faculty_name": f"Faculty #{faculty_id}",
                    "department_id": 1,
                    "department_code": "MCA",
                    "month_year": month_year,
                    "allowed_minutes": 45,
                    "used_minutes": minutes,
                    "remaining_minutes": 45 - minutes,
                    "status": self._compute_status(45 - minutes),
                }
                DEMO_GRACE_LEDGER.append(new_item)
                return new_item.copy()
            return {}

    def update_allowed_minutes(self, faculty_id: int, month_year: str, new_allowed: int) -> bool:
        """Updates the allowed grace minutes quota for a faculty member."""
        upsert_sql = """
            INSERT INTO grace_minutes (faculty_id, month_year, allowed_minutes, used_minutes)
            VALUES (%s, %s, %s, 0)
            ON CONFLICT (faculty_id, month_year) DO UPDATE SET allowed_minutes = EXCLUDED.allowed_minutes;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(upsert_sql, (faculty_id, month_year, new_allowed))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.warning(f"DB update allowed grace error, updating fallback: {exc}")
            for item in DEMO_GRACE_LEDGER:
                if item["faculty_id"] == faculty_id and item["month_year"] == month_year:
                    item["allowed_minutes"] = new_allowed
                    item["remaining_minutes"] = item["allowed_minutes"] - item["used_minutes"]
                    item["status"] = self._compute_status(item["remaining_minutes"])
                    return True
            return True

    def allocate_monthly_grace(self, month_year: str, default_minutes: int = 45) -> int:
        """Ensures all active faculty members have a grace record for the month."""
        insert_sql = """
            INSERT INTO grace_minutes (faculty_id, month_year, allowed_minutes, used_minutes)
            SELECT f.id, %s, %s, 0
            FROM faculty f
            WHERE f.status = 'ACTIVE'
            ON CONFLICT (faculty_id, month_year) DO NOTHING;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(insert_sql, (month_year, default_minutes))
            count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return count
        except Exception as exc:
            logger.warning(f"DB allocate grace error, fallback executed: {exc}")
            return len(DEMO_GRACE_LEDGER)


grace_repository = GraceRepository()
