"""
Stationery Repository
Manages database operations and memory fallbacks for departmental stationery
and consumable resource requisition workflows.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.stationery_repository")

# Predefined consumable stationery items catalog
PREDEFINED_STATIONERY_ITEMS = [
    "Whiteboard Markers (Pack of 4 - Black/Blue/Red/Green)",
    "A4 Paper Ream (75 GSM, 500 Sheets)",
    "Box Files / Document Folders (Pack of 5)",
    "Printer Toner Cartridge (Black)",
    "Sticky Notes / Post-it Pads (Pack of 3)",
    "Stapler & Staple Pins Box",
    "Whiteboard Duster & Cleaning Spray",
    "Attendance Register Notebook (Hardbound)",
    "Ballpoint Pens (Pack of 10 - Blue/Black)",
    "Permanent Marker & Highlighter Set",
]

# In-memory mock fallback dataset
DEMO_STATIONERY_REQUESTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "requester_user_id": 3,
        "requester_name": "Rahul Sharma",
        "requester_role": "FACULTY",
        "department_id": 1,
        "department_code": "MCA",
        "item_name": "Whiteboard Markers (Pack of 4 - Black/Blue/Red/Green)",
        "quantity": 2,
        "urgency": "NORMAL",
        "purpose": "Required for Semester 1 Data Structures lecture hall",
        "status": "PENDING",
        "hod_remarks": "",
        "reviewed_by_user_id": None,
        "created_at": "2026-10-28 09:30:00",
        "reviewed_at": None,
    },
    {
        "id": 2,
        "requester_user_id": 4,
        "requester_name": "Priya Verma",
        "requester_role": "FACULTY",
        "department_id": 1,
        "department_code": "MCA",
        "item_name": "A4 Paper Ream (75 GSM, 500 Sheets)",
        "quantity": 1,
        "urgency": "HIGH",
        "purpose": "Printing question papers for Internal Assessment 1",
        "status": "APPROVED",
        "hod_remarks": "Approved for exam cell preparation",
        "reviewed_by_user_id": 2,
        "created_at": "2026-10-25 11:15:00",
        "reviewed_at": "2026-10-25 14:00:00",
    },
    {
        "id": 3,
        "requester_user_id": 5,
        "requester_name": "Amit Patel",
        "requester_role": "FACULTY",
        "department_id": 2,
        "department_code": "CSE",
        "item_name": "Box Files / Document Folders (Pack of 5)",
        "quantity": 2,
        "urgency": "NORMAL",
        "purpose": "Accreditation and NBA course file documentation",
        "status": "PENDING",
        "hod_remarks": "",
        "reviewed_by_user_id": None,
        "created_at": "2026-10-29 14:20:00",
        "reviewed_at": None,
    },
]


class StationeryRepository:
    """Repository handling SQL persistence and fallback states for stationery requests."""

    def get_predefined_items(self) -> List[str]:
        """Returns the list of institutional consumable stationery items."""
        return PREDEFINED_STATIONERY_ITEMS.copy()

    def get_requests(
        self,
        department_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves stationery requests filtered by department or requester user ID.
        """
        query = """
            SELECT 
                sr.id,
                sr.requester_user_id,
                sr.requester_name,
                sr.requester_role,
                sr.department_id,
                d.code AS department_code,
                sr.item_name,
                sr.quantity,
                sr.urgency,
                sr.purpose,
                sr.status,
                sr.hod_remarks,
                sr.reviewed_by_user_id,
                TO_CHAR(sr.created_at, 'YYYY-MM-DD HH24:MI') AS created_at,
                TO_CHAR(sr.reviewed_at, 'YYYY-MM-DD HH24:MI') AS reviewed_at
            FROM stationery_requests sr
            LEFT JOIN departments d ON d.id = sr.department_id
            WHERE 1=1
        """
        params = []
        if department_id is not None:
            query += " AND sr.department_id = %s"
            params.append(department_id)
        if user_id is not None:
            query += " AND sr.requester_user_id = %s"
            params.append(user_id)

        query += " ORDER BY sr.id DESC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB stationery query unavailable, using fallback: {exc}")
            results = []
            for r in DEMO_STATIONERY_REQUESTS:
                if department_id is not None and r.get("department_id") != department_id:
                    continue
                if user_id is not None and r.get("requester_user_id") != user_id:
                    continue
                results.append(r.copy())
            return sorted(results, key=lambda x: x["id"], reverse=True)

    def create_request(self, data: Dict[str, Any]) -> int:
        """Submits a new stationery request."""
        sql = """
            INSERT INTO stationery_requests 
                (requester_user_id, requester_name, requester_role, department_id, item_name, quantity, urgency, purpose, status)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """
        params = (
            data["requester_user_id"],
            data["requester_name"],
            data.get("requester_role", "FACULTY"),
            data.get("department_id"),
            data["item_name"],
            data.get("quantity", 1),
            data.get("urgency", "NORMAL"),
            data.get("purpose", ""),
        )

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            last_id = row[0] if row else getattr(cursor, "lastrowid", None)
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Stationery request #{last_id} created in PostgreSQL.")
            return last_id
        except Exception as exc:
            logger.debug(f"DB create stationery request unavailable, using fallback: {exc}")
            new_id = max([r["id"] for r in DEMO_STATIONERY_REQUESTS], default=0) + 1
            dept_id = data.get("department_id", 1)
            dept_code = "MCA" if dept_id == 1 else ("CSE" if dept_id == 2 else "GEN")

            new_record = {
                "id": new_id,
                "requester_user_id": data["requester_user_id"],
                "requester_name": data["requester_name"],
                "requester_role": data.get("requester_role", "FACULTY"),
                "department_id": dept_id,
                "department_code": dept_code,
                "item_name": data["item_name"],
                "quantity": data.get("quantity", 1),
                "urgency": data.get("urgency", "NORMAL"),
                "purpose": data.get("purpose", ""),
                "status": "PENDING",
                "hod_remarks": "",
                "reviewed_by_user_id": None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "reviewed_at": None,
            }
            DEMO_STATIONERY_REQUESTS.append(new_record)
            return new_id

    def update_status(
        self,
        request_id: int,
        status: str,
        hod_remarks: str = "",
        reviewed_by_user_id: int = 1,
    ) -> bool:
        """Updates approval or rejection status with HOD remarks."""
        sql = """
            UPDATE stationery_requests 
            SET status = %s, hod_remarks = %s, reviewed_by_user_id = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (status, hod_remarks, reviewed_by_user_id, request_id))
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Stationery request #{request_id} updated to {status} in MySQL.")
            return True
        except Exception as exc:
            logger.debug(f"DB update stationery status unavailable, using fallback: {exc}")
            for r in DEMO_STATIONERY_REQUESTS:
                if r["id"] == request_id:
                    r["status"] = status
                    r["hod_remarks"] = hod_remarks
                    r["reviewed_by_user_id"] = reviewed_by_user_id
                    r["reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    return True
            return False


stationery_repository = StationeryRepository()
