"""
Lab Instructor Repository
Handles data access and transactions for lab instructors, user account provisioning,
and profile images with dual-mode SQL and in-memory mock resilience.
"""
from typing import List, Dict, Any, Optional
from datetime import date
from database.connection import get_connection
from utils.logger import get_logger
from utils.security import hash_password

logger = get_logger("repositories.instructor_repository")

# Fallback prototype demo list when MySQL is offline
DEMO_INSTRUCTORS_LIST = [
    {
        "id": 1,
        "instructor_code": "INS001",
        "user_id": 6,
        "username": "inst_kavita",
        "role": "LAB_INSTRUCTOR",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Kavita",
        "last_name": "Nair",
        "full_name": "Kavita Nair",
        "email": "kavita.nair@erp.edu",
        "phone": "9876543220",
        "lab_specialization": "Data Structures & AI Lab",
        "profile_image_path": "uploads/avatars/inst_kavita.png",
        "joining_date": "2023-02-01",
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "instructor_code": "INS002",
        "user_id": 20,
        "username": "inst_manoj",
        "role": "LAB_INSTRUCTOR",
        "department_id": 2,
        "department_code": "CSE",
        "department_name": "Department of Computer Science & Engineering",
        "first_name": "Manoj",
        "last_name": "Bhat",
        "full_name": "Manoj Bhat",
        "email": "manoj.bhat@erp.edu",
        "phone": "9876543221",
        "lab_specialization": "Networks & Systems Lab",
        "profile_image_path": "",
        "joining_date": "2023-03-01",
        "status": "ACTIVE",
    },
    {
        "id": 3,
        "instructor_code": "INS003",
        "user_id": 21,
        "username": "inst_divya",
        "role": "LAB_INSTRUCTOR",
        "department_id": 8,
        "department_code": "CSD",
        "department_name": "Department of Computer Science & Design",
        "first_name": "Divya",
        "last_name": "Rao",
        "full_name": "Divya Rao",
        "email": "divya.rao@erp.edu",
        "phone": "9876543222",
        "lab_specialization": "Graphics & UI/UX Design Lab",
        "profile_image_path": "",
        "joining_date": "2023-04-10",
        "status": "ACTIVE",
    },
    {
        "id": 4,
        "instructor_code": "INS004",
        "user_id": 22,
        "username": "inst_harish",
        "role": "LAB_INSTRUCTOR",
        "department_id": 4,
        "department_code": "MECH",
        "department_name": "Department of Mechanical Engineering",
        "first_name": "Harish",
        "last_name": "Poojary",
        "full_name": "Harish Poojary",
        "email": "harish.poojary@erp.edu",
        "phone": "9876543223",
        "lab_specialization": "CAD/CAM & Thermodynamics Lab",
        "profile_image_path": "",
        "joining_date": "2022-08-15",
        "status": "ACTIVE",
    },
    {
        "id": 5,
        "instructor_code": "INS005",
        "user_id": 23,
        "username": "inst_shilpa",
        "role": "LAB_INSTRUCTOR",
        "department_id": 5,
        "department_code": "CIVIL",
        "department_name": "Department of Civil Engineering",
        "first_name": "Shilpa",
        "last_name": "Shetty",
        "full_name": "Shilpa Shetty",
        "email": "shilpa.shetty@erp.edu",
        "phone": "9876543224",
        "lab_specialization": "Geotechnical & Surveying Lab",
        "profile_image_path": "",
        "joining_date": "2023-01-20",
        "status": "ACTIVE",
    },
    {
        "id": 6,
        "instructor_code": "INS006",
        "user_id": 24,
        "username": "inst_praveen",
        "role": "LAB_INSTRUCTOR",
        "department_id": 6,
        "department_code": "ECE",
        "department_name": "Department of Electronics & Communication Engineering",
        "first_name": "Praveen",
        "last_name": "Kumar",
        "full_name": "Praveen Kumar",
        "email": "praveen.kumar@erp.edu",
        "phone": "9876543225",
        "lab_specialization": "VLSI & Embedded Systems Lab",
        "profile_image_path": "",
        "joining_date": "2022-11-05",
        "status": "ACTIVE",
    },
    {
        "id": 7,
        "instructor_code": "INS007",
        "user_id": 25,
        "username": "inst_preeti",
        "role": "LAB_INSTRUCTOR",
        "department_id": 7,
        "department_code": "ISE",
        "department_name": "Department of Information Science & Engineering",
        "first_name": "Preeti",
        "last_name": "Shenoy",
        "full_name": "Preeti Shenoy",
        "email": "preeti.shenoy@erp.edu",
        "phone": "9876543226",
        "lab_specialization": "Cloud & Data Engineering Lab",
        "profile_image_path": "",
        "joining_date": "2023-05-12",
        "status": "ACTIVE",
    },
]


class InstructorRepository:
    """Repository managing SQL and memory fallback operations for lab instructors."""

    def get_all(
        self,
        department_id: Optional[int] = None,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves lab instructors filtered by department_id and optional search term.
        """
        query = """
            SELECT 
                li.id,
                li.instructor_code,
                li.user_id,
                u.username,
                u.role,
                li.department_id,
                d.code AS department_code,
                d.name AS department_name,
                li.first_name,
                li.last_name,
                CONCAT(li.first_name, ' ', li.last_name) AS full_name,
                li.email,
                li.phone,
                li.lab_specialization,
                li.profile_image_path,
                li.joining_date,
                li.status
            FROM lab_instructors li
            INNER JOIN users u ON u.id = li.user_id
            INNER JOIN departments d ON d.id = li.department_id
            WHERE 1=1
        """
        params = []
        if department_id is not None:
            query += " AND li.department_id = %s"
            params.append(department_id)

        if search_term and search_term.strip():
            term = f"%{search_term.strip()}%"
            query += " AND (li.instructor_code LIKE %s OR li.first_name LIKE %s OR li.last_name LIKE %s OR li.email LIKE %s)"
            params.extend([term, term, term, term])

        query += " ORDER BY li.instructor_code ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB instructor query unavailable, using fallback: {exc}")
            results = []
            for item in DEMO_INSTRUCTORS_LIST:
                if department_id is not None and item["department_id"] != department_id:
                    continue
                if search_term and search_term.strip():
                    st = search_term.strip().lower()
                    match_code = st in item["instructor_code"].lower()
                    match_name = st in item["full_name"].lower()
                    match_email = st in item["email"].lower()
                    if not (match_code or match_name or match_email):
                        continue
                results.append(item.copy())
            return results

    def get_by_id(self, instructor_id: int) -> Optional[Dict[str, Any]]:
        """Fetches lab instructor by primary key ID."""
        instructors = self.get_all()
        for inst in instructors:
            if inst["id"] == instructor_id:
                return inst
        return None

    def get_by_code(self, instructor_code: str) -> Optional[Dict[str, Any]]:
        """Fetches lab instructor by unique employee/instructor code."""
        code_clean = instructor_code.strip().upper()
        instructors = self.get_all()
        for inst in instructors:
            if inst["instructor_code"].upper() == code_clean:
                return inst
        return None

    def create(self, instructor_data: Dict[str, Any]) -> int:
        """
        Creates user account with role LAB_INSTRUCTOR and linked lab instructor profile.
        """
        code = instructor_data["instructor_code"].strip().upper()
        username = instructor_data["username"].strip().lower()
        pass_hash = hash_password(instructor_data["password"])
        dept_id = int(instructor_data["department_id"])
        image_path = instructor_data.get("profile_image_path", "")

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # 1. Insert into users table
            user_sql = "INSERT INTO users (username, password_hash, role, status) VALUES (%s, %s, 'LAB_INSTRUCTOR', 'ACTIVE') RETURNING id;"
            cursor.execute(user_sql, (username, pass_hash))
            u_row = cursor.fetchone()
            user_id = u_row[0] if u_row else getattr(cursor, "lastrowid", None)

            # 2. Insert into lab_instructors table
            inst_sql = """
                INSERT INTO lab_instructors (instructor_code, user_id, department_id, first_name, last_name, email, phone, lab_specialization, profile_image_path, joining_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                RETURNING id;
            """
            joining = instructor_data.get("joining_date", str(date.today()))
            cursor.execute(
                inst_sql,
                (
                    code,
                    user_id,
                    dept_id,
                    instructor_data["first_name"].strip(),
                    instructor_data["last_name"].strip(),
                    instructor_data["email"].strip(),
                    instructor_data.get("phone", "").strip(),
                    instructor_data.get("lab_specialization", "Computer Laboratory").strip(),
                    image_path,
                    joining,
                ),
            )
            i_row = cursor.fetchone()
            inst_id = i_row[0] if i_row else getattr(cursor, "lastrowid", None)
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Created lab instructor '{code}' (ID={inst_id}, User ID={user_id}).")
            return inst_id

        except Exception as exc:
            logger.warning(f"DB create instructor error, using fallback: {exc}")
            new_id = max([i["id"] for i in DEMO_INSTRUCTORS_LIST], default=0) + 1
            new_uid = max([i["user_id"] for i in DEMO_INSTRUCTORS_LIST], default=0) + 1
            dept_code = "MCA" if dept_id == 1 else ("CSE" if dept_id == 2 else "IT")

            DEMO_INSTRUCTORS_LIST.append(
                {
                    "id": new_id,
                    "instructor_code": code,
                    "user_id": new_uid,
                    "username": username,
                    "role": "LAB_INSTRUCTOR",
                    "department_id": dept_id,
                    "department_code": dept_code,
                    "department_name": f"Department of {dept_code}",
                    "first_name": instructor_data["first_name"].strip(),
                    "last_name": instructor_data["last_name"].strip(),
                    "full_name": f"{instructor_data['first_name'].strip()} {instructor_data['last_name'].strip()}",
                    "email": instructor_data["email"].strip(),
                    "phone": instructor_data.get("phone", "").strip(),
                    "lab_specialization": instructor_data.get("lab_specialization", "Computer Laboratory").strip(),
                    "profile_image_path": image_path,
                    "joining_date": str(date.today()),
                    "status": "ACTIVE",
                }
            )
            return new_id

    def update(self, instructor_id: int, instructor_data: Dict[str, Any]):
        """Updates lab instructor profile record."""
        dept_id = int(instructor_data["department_id"])
        image_path = instructor_data.get("profile_image_path", "")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            sql = """
                UPDATE lab_instructors
                SET department_id = %s,
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    phone = %s,
                    lab_specialization = %s,
                    profile_image_path = %s,
                    status = %s
                WHERE id = %s;
            """
            cursor.execute(
                sql,
                (
                    dept_id,
                    instructor_data["first_name"].strip(),
                    instructor_data["last_name"].strip(),
                    instructor_data["email"].strip(),
                    instructor_data.get("phone", "").strip(),
                    instructor_data.get("lab_specialization", "Computer Laboratory").strip(),
                    image_path,
                    instructor_data.get("status", "ACTIVE"),
                    instructor_id,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.warning(f"DB update instructor error, using fallback: {exc}")
            for item in DEMO_INSTRUCTORS_LIST:
                if item["id"] == instructor_id:
                    item["department_id"] = dept_id
                    item["first_name"] = instructor_data["first_name"].strip()
                    item["last_name"] = instructor_data["last_name"].strip()
                    item["full_name"] = f"{item['first_name']} {item['last_name']}"
                    item["email"] = instructor_data["email"].strip()
                    item["phone"] = instructor_data.get("phone", "").strip()
                    item["lab_specialization"] = instructor_data.get("lab_specialization", "Computer Laboratory").strip()
                    if image_path:
                        item["profile_image_path"] = image_path
                    item["status"] = instructor_data.get("status", "ACTIVE")
                    break

    def delete(self, instructor_id: int):
        """Removes or deactivates a lab instructor record."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            sql = "UPDATE lab_instructors SET status = 'INACTIVE' WHERE id = %s;"
            cursor.execute(sql, (instructor_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.warning(f"DB delete instructor error, using fallback: {exc}")
            for item in DEMO_INSTRUCTORS_LIST:
                if item["id"] == instructor_id:
                    item["status"] = "INACTIVE"
                    break


instructor_repository = InstructorRepository()

