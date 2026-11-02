"""
Leave Repository
Handles SQL database queries and memory fallbacks for leave_types and leave_balance tables.
"""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.leave_repository")

# Fallback datasets for offline/prototype execution
DEMO_LEAVE_TYPES = [
    {
        "id": 1,
        "code": "CL",
        "name": "Casual Leave",
        "max_days_per_year": 12,
        "carry_forward_allowed": 0,
        "requires_document": 0,
        "ai_classification_enabled": 1,
        "is_active": 1,
        "description": "Short period leave for personal matters",
    },
    {
        "id": 2,
        "code": "EL",
        "name": "Earned Leave",
        "max_days_per_year": 15,
        "carry_forward_allowed": 1,
        "requires_document": 0,
        "ai_classification_enabled": 1,
        "is_active": 1,
        "description": "Leave earned by performing duty",
    },
    {
        "id": 3,
        "code": "AVL",
        "name": "Academic Vacation Leave",
        "max_days_per_year": 30,
        "carry_forward_allowed": 0,
        "requires_document": 0,
        "ai_classification_enabled": 1,
        "is_active": 1,
        "description": "Vacation leave granted during semester breaks",
    },
    {
        "id": 4,
        "code": "SCL",
        "name": "Special Casual Leave",
        "max_days_per_year": 6,
        "carry_forward_allowed": 0,
        "requires_document": 1,
        "ai_classification_enabled": 1,
        "is_active": 1,
        "description": "Leave for attending conferences, workshops, or exam duties",
    },
    {
        "id": 5,
        "code": "ML",
        "name": "Medical Leave",
        "max_days_per_year": 10,
        "carry_forward_allowed": 1,
        "requires_document": 1,
        "ai_classification_enabled": 1,
        "is_active": 1,
        "description": "Leave granted on medical grounds or illness",
    },
    {
        "id": 6,
        "code": "OD",
        "name": "On Duty Leave",
        "max_days_per_year": 15,
        "carry_forward_allowed": 0,
        "requires_document": 1,
        "ai_classification_enabled": 1,
        "is_active": 1,
        "description": "Official institutional external duty or university work",
    },
]

DEMO_LEAVE_BALANCES = [
    # Dr. Suresh Kumar (Faculty ID 1, MCA)
    {"id": 1, "faculty_id": 1, "employee_code": "F001", "faculty_name": "Dr. Suresh Kumar", "department_id": 1, "department_code": "MCA", "leave_type_id": 1, "leave_type_code": "CL", "leave_type_name": "Casual Leave", "year": 2026, "allocated_days": 12.0, "used_days": 2.0, "pending_days": 0.0, "remaining_days": 10.0},
    {"id": 2, "faculty_id": 1, "employee_code": "F001", "faculty_name": "Dr. Suresh Kumar", "department_id": 1, "department_code": "MCA", "leave_type_id": 5, "leave_type_code": "ML", "leave_type_name": "Medical Leave", "year": 2026, "allocated_days": 10.0, "used_days": 0.0, "pending_days": 0.0, "remaining_days": 10.0},
    {"id": 3, "faculty_id": 1, "employee_code": "F001", "faculty_name": "Dr. Suresh Kumar", "department_id": 1, "department_code": "MCA", "leave_type_id": 2, "leave_type_code": "EL", "leave_type_name": "Earned Leave", "year": 2026, "allocated_days": 15.0, "used_days": 3.0, "pending_days": 0.0, "remaining_days": 12.0},

    # Rahul Sharma (Faculty ID 2, MCA)
    {"id": 4, "faculty_id": 2, "employee_code": "F002", "faculty_name": "Rahul Sharma", "department_id": 1, "department_code": "MCA", "leave_type_id": 1, "leave_type_code": "CL", "leave_type_name": "Casual Leave", "year": 2026, "allocated_days": 12.0, "used_days": 4.0, "pending_days": 1.0, "remaining_days": 7.0},
    {"id": 5, "faculty_id": 2, "employee_code": "F002", "faculty_name": "Rahul Sharma", "department_id": 1, "department_code": "MCA", "leave_type_id": 5, "leave_type_code": "ML", "leave_type_name": "Medical Leave", "year": 2026, "allocated_days": 10.0, "used_days": 2.0, "pending_days": 0.0, "remaining_days": 8.0},
    {"id": 6, "faculty_id": 2, "employee_code": "F002", "faculty_name": "Rahul Sharma", "department_id": 1, "department_code": "MCA", "leave_type_id": 2, "leave_type_code": "EL", "leave_type_name": "Earned Leave", "year": 2026, "allocated_days": 15.0, "used_days": 0.0, "pending_days": 0.0, "remaining_days": 15.0},

    # Priya Verma (Faculty ID 3, MCA)
    {"id": 7, "faculty_id": 3, "employee_code": "F003", "faculty_name": "Priya Verma", "department_id": 1, "department_code": "MCA", "leave_type_id": 1, "leave_type_code": "CL", "leave_type_name": "Casual Leave", "year": 2026, "allocated_days": 12.0, "used_days": 1.0, "pending_days": 0.0, "remaining_days": 11.0},
    {"id": 8, "faculty_id": 3, "employee_code": "F003", "faculty_name": "Priya Verma", "department_id": 1, "department_code": "MCA", "leave_type_id": 5, "leave_type_code": "ML", "leave_type_name": "Medical Leave", "year": 2026, "allocated_days": 10.0, "used_days": 0.0, "pending_days": 0.0, "remaining_days": 10.0},

    # Amit Patel (Faculty ID 4, CSE)
    {"id": 9, "faculty_id": 4, "employee_code": "F004", "faculty_name": "Dr. Amit Patel", "department_id": 2, "department_code": "CSE", "leave_type_id": 1, "leave_type_code": "CL", "leave_type_name": "Casual Leave", "year": 2026, "allocated_days": 12.0, "used_days": 11.0, "pending_days": 1.0, "remaining_days": 0.0},
    {"id": 10, "faculty_id": 4, "employee_code": "F004", "faculty_name": "Dr. Amit Patel", "department_id": 2, "department_code": "CSE", "leave_type_id": 5, "leave_type_code": "ML", "leave_type_name": "Medical Leave", "year": 2026, "allocated_days": 10.0, "used_days": 5.0, "pending_days": 0.0, "remaining_days": 5.0},
]


class LeaveRepository:
    """Repository managing SQL queries for leave_types and leave_balance tables."""

    def get_leave_types(self) -> List[Dict[str, Any]]:
        """Retrieves active leave type catalog."""
        query = """
            SELECT id, code, name, max_days_per_year, carry_forward_allowed, 
                   requires_document, ai_classification_enabled, is_active, description
            FROM leave_types
            WHERE is_active = 1
            ORDER BY code ASC;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB leave_types query unavailable, using fallback: {exc}")
            return [t.copy() for t in DEMO_LEAVE_TYPES]

    def get_leave_type_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Finds a leave type record by its unique code string (e.g. 'CL', 'ML')."""
        query = """
            SELECT id, code, name, max_days_per_year, carry_forward_allowed, 
                   requires_document, ai_classification_enabled, is_active, description
            FROM leave_types
            WHERE code = %s AND is_active = 1;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (code.strip().upper(),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row
        except Exception as exc:
            logger.debug(f"DB leave type by code lookup fallback: {exc}")
            for t in DEMO_LEAVE_TYPES:
                if t["code"].upper() == code.strip().upper():
                    return t.copy()
            return None

    def get_faculty_balances(self, faculty_id: int, year: int = 2026) -> List[Dict[str, Any]]:
        """Retrieves leave balance records for a single faculty member for a given year."""
        query = """
            SELECT 
                lb.id,
                lb.faculty_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS faculty_name,
                f.department_id,
                d.code AS department_code,
                lb.leave_type_id,
                lt.code AS leave_type_code,
                lt.name AS leave_type_name,
                lb.year,
                lb.allocated_days,
                lb.used_days,
                lb.pending_days,
                (lb.allocated_days - lb.used_days - lb.pending_days) AS remaining_days
            FROM leave_balance lb
            INNER JOIN faculty f ON f.id = lb.faculty_id
            INNER JOIN departments d ON d.id = f.department_id
            INNER JOIN leave_types lt ON lt.id = lb.leave_type_id
            WHERE lb.faculty_id = %s AND lb.year = %s
            ORDER BY lt.code ASC;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (faculty_id, year))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB faculty balance query fallback: {exc}")
            return [
                b.copy()
                for b in DEMO_LEAVE_BALANCES
                if b["faculty_id"] == faculty_id and b["year"] == year
            ]

    def get_department_balances(
        self, department_id: Optional[int] = None, year: int = 2026
    ) -> List[Dict[str, Any]]:
        """Retrieves leave balance records across department or whole institution."""
        query = """
            SELECT 
                lb.id,
                lb.faculty_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS faculty_name,
                f.department_id,
                d.code AS department_code,
                lb.leave_type_id,
                lt.code AS leave_type_code,
                lt.name AS leave_type_name,
                lb.year,
                lb.allocated_days,
                lb.used_days,
                lb.pending_days,
                (lb.allocated_days - lb.used_days - lb.pending_days) AS remaining_days
            FROM leave_balance lb
            INNER JOIN faculty f ON f.id = lb.faculty_id
            INNER JOIN departments d ON d.id = f.department_id
            INNER JOIN leave_types lt ON lt.id = lb.leave_type_id
            WHERE lb.year = %s
        """
        params = [year]
        if department_id is not None:
            query += " AND f.department_id = %s"
            params.append(department_id)

        query += " ORDER BY d.code ASC, f.employee_code ASC, lt.code ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB department balance query fallback: {exc}")
            results = []
            for b in DEMO_LEAVE_BALANCES:
                if b["year"] != year:
                    continue
                if department_id is not None and b.get("department_id") != department_id:
                    continue
                c = b.copy()
                c["remaining_days"] = c["allocated_days"] - c["used_days"] - c["pending_days"]
                results.append(c)
            return results

    def update_balance_allocation(
        self, faculty_id: int, leave_type_id: int, year: int, new_allocated: float
    ) -> bool:
        """Updates allocated days quota for a faculty member and leave type."""
        upsert_sql = """
            INSERT INTO leave_balance (faculty_id, leave_type_id, year, allocated_days, used_days, pending_days)
            VALUES (%s, %s, %s, %s, 0.00, 0.00)
            ON CONFLICT (faculty_id, leave_type_id, year) DO UPDATE SET allocated_days = EXCLUDED.allocated_days;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(upsert_sql, (faculty_id, leave_type_id, year, new_allocated))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as exc:
            logger.warning(f"DB update leave balance allocation error, updating fallback: {exc}")
            for b in DEMO_LEAVE_BALANCES:
                if (
                    b["faculty_id"] == faculty_id
                    and b["leave_type_id"] == leave_type_id
                    and b["year"] == year
                ):
                    b["allocated_days"] = new_allocated
                    b["remaining_days"] = b["allocated_days"] - b["used_days"] - b["pending_days"]
                    return True
            return True

    def init_faculty_annual_balances(self, faculty_id: int, year: int = 2026) -> int:
        """Initializes default annual leave balance entries for a faculty member."""
        insert_sql = """
            INSERT INTO leave_balance (faculty_id, leave_type_id, year, allocated_days, used_days, pending_days)
            SELECT %s, lt.id, %s, lt.max_days_per_year, 0.00, 0.00
            FROM leave_types lt
            WHERE lt.is_active = 1
            ON CONFLICT (faculty_id, leave_type_id, year) DO NOTHING;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(insert_sql, (faculty_id, year))
            count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return count
        except Exception as exc:
            logger.warning(f"DB init faculty balances error, fallback executed: {exc}")
            return len(DEMO_LEAVE_TYPES)


leave_repository = LeaveRepository()
