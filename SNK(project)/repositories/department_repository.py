"""
Department Repository
Handles database access and SQL queries for department records.
"""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.department_repository")

# Fallback prototype demo data when DB is offline
DEMO_DEPARTMENTS = [
    {
        "id": 1,
        "code": "MCA",
        "name": "Department of Computer Applications",
        "hod_faculty_id": 2,
        "hod_name": "Dr. Suresh Kumar",
        "faculty_count": 4,
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "code": "CSE",
        "name": "Department of Computer Science & Engineering",
        "hod_faculty_id": None,
        "hod_name": "Unassigned",
        "faculty_count": 1,
        "status": "ACTIVE",
    },
    {
        "id": 3,
        "code": "IT",
        "name": "Department of Information Technology",
        "hod_faculty_id": None,
        "hod_name": "Unassigned",
        "faculty_count": 0,
        "status": "ACTIVE",
    },
    {
        "id": 4,
        "code": "MECH",
        "name": "Department of Mechanical Engineering",
        "hod_faculty_id": 7,
        "hod_name": "Dr. Ramesh Rao",
        "faculty_count": 2,
        "status": "ACTIVE",
    },
    {
        "id": 5,
        "code": "CIVIL",
        "name": "Department of Civil Engineering",
        "hod_faculty_id": 8,
        "hod_name": "Dr. Sunita Deshmukh",
        "faculty_count": 2,
        "status": "ACTIVE",
    },
    {
        "id": 6,
        "code": "ECE",
        "name": "Department of Electronics & Communication Engineering",
        "hod_faculty_id": 9,
        "hod_name": "Dr. Rajesh Bhat",
        "faculty_count": 2,
        "status": "ACTIVE",
    },
    {
        "id": 7,
        "code": "ISE",
        "name": "Department of Information Science & Engineering",
        "hod_faculty_id": None,
        "hod_name": "Unassigned",
        "faculty_count": 1,
        "status": "ACTIVE",
    },
    {
        "id": 8,
        "code": "CSD",
        "name": "Department of Computer Science & Design",
        "hod_faculty_id": None,
        "hod_name": "Dr. Deepa Shenoy",
        "faculty_count": 2,
        "status": "ACTIVE",
    },
]


class DepartmentRepository:
    """Repository managing SQL operations for the departments table."""

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Retrieves all department records with HOD faculty name and total faculty count.
        """
        query = """
            SELECT 
                d.id,
                d.code,
                d.name,
                d.hod_faculty_id,
                d.status,
                CONCAT(COALESCE(h.first_name, ''), ' ', COALESCE(h.last_name, '')) AS hod_name,
                COUNT(f.id) AS faculty_count
            FROM departments d
            LEFT JOIN faculty h ON h.id = d.hod_faculty_id
            LEFT JOIN faculty f ON f.department_id = d.id
            GROUP BY d.id, d.code, d.name, d.hod_faculty_id, d.status, h.first_name, h.last_name
            ORDER BY d.code ASC;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            # Clean HOD name formatting
            for row in rows:
                if not row.get("hod_name") or row["hod_name"].strip() == "":
                    row["hod_name"] = "Unassigned"
                else:
                    row["hod_name"] = row["hod_name"].strip()

            return rows
        except Exception as exc:
            logger.debug(f"DB department query unavailable, using fallback: {exc}")
            return [d.copy() for d in DEMO_DEPARTMENTS]

    def get_by_id(self, dept_id: int) -> Optional[Dict[str, Any]]:
        """Fetches department by ID."""
        depts = self.get_all()
        for d in depts:
            if d["id"] == dept_id:
                return d
        return None

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Fetches department by code."""
        depts = self.get_all()
        clean_code = code.strip().upper()
        for d in depts:
            if d["code"].upper() == clean_code:
                return d
        return None

    def create(
        self,
        code: str,
        name: str,
        hod_faculty_id: Optional[int] = None,
        status: str = "ACTIVE",
    ) -> int:
        """Inserts a new department record."""
        query = """
            INSERT INTO departments (code, name, hod_faculty_id, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (code.strip().upper(), name.strip(), hod_faculty_id, status))
            row = cursor.fetchone()
            new_id = row[0] if row else getattr(cursor, "lastrowid", None)
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Created department '{code}' (ID={new_id}).")
            return new_id
        except Exception as exc:
            logger.warning(f"DB insert department error, writing to memory fallback: {exc}")
            new_id = max([d["id"] for d in DEMO_DEPARTMENTS], default=0) + 1
            DEMO_DEPARTMENTS.append(
                {
                    "id": new_id,
                    "code": code.strip().upper(),
                    "name": name.strip(),
                    "hod_faculty_id": hod_faculty_id,
                    "hod_name": "Unassigned",
                    "faculty_count": 0,
                    "status": status,
                }
            )
            return new_id

    def update(
        self,
        dept_id: int,
        code: str,
        name: str,
        hod_faculty_id: Optional[int] = None,
        status: str = "ACTIVE",
    ):
        """Updates an existing department record."""
        query = """
            UPDATE departments 
            SET code = %s, name = %s, hod_faculty_id = %s, status = %s
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (code.strip().upper(), name.strip(), hod_faculty_id, status, dept_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Updated department ID={dept_id} ('{code}').")
        except Exception as exc:
            logger.warning(f"DB update department error, updating memory fallback: {exc}")
            for d in DEMO_DEPARTMENTS:
                if d["id"] == dept_id:
                    d["code"] = code.strip().upper()
                    d["name"] = name.strip()
                    d["hod_faculty_id"] = hod_faculty_id
                    d["status"] = status
                    break


department_repository = DepartmentRepository()
