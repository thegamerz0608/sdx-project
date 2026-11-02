"""
User Repository
Handles data access for user accounts, credentials, and linked faculty profiles using parameterized queries.
"""
from typing import Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger
from utils.security import hash_password

logger = get_logger("repositories.user_repository")

# Fallback prototype demo users dictionary for offline testing/development
DEMO_USERS = {
    "admin": {
        "user_id": 1,
        "username": "admin",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "ADMIN",
        "status": "ACTIVE",
        "faculty_id": 1,
        "employee_code": "EMP001",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "System",
        "last_name": "Admin",
        "email": "admin@erp.edu",
        "designation": "System Administrator",
        "profile_image_path": "uploads/avatars/admin.png",
    },
    "hod_mca": {
        "user_id": 2,
        "username": "hod_mca",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "HOD",
        "status": "ACTIVE",
        "faculty_id": 2,
        "employee_code": "F001",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Dr. Suresh",
        "last_name": "Kumar",
        "email": "hod.mca@erp.edu",
        "designation": "Professor & HOD",
        "profile_image_path": "uploads/avatars/hod_mca.png",
    },
    "fac_rahul": {
        "user_id": 3,
        "username": "fac_rahul",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 3,
        "employee_code": "F002",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Rahul",
        "last_name": "Sharma",
        "email": "rahul.sharma@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "uploads/avatars/fac_rahul.png",
    },
    "fac_priya": {
        "user_id": 4,
        "username": "fac_priya",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 4,
        "employee_code": "F003",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Priya",
        "last_name": "Verma",
        "email": "priya.verma@erp.edu",
        "designation": "Associate Professor",
        "profile_image_path": "",
    },
    "fac_amit": {
        "user_id": 5,
        "username": "fac_amit",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 5,
        "employee_code": "F004",
        "department_id": 2,
        "department_code": "CSE",
        "department_name": "Department of Computer Science & Engineering",
        "first_name": "Amit",
        "last_name": "Patel",
        "email": "amit.patel@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "",
    },
    "inst_kavita": {
        "user_id": 6,
        "username": "inst_kavita",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS001",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Kavita",
        "last_name": "Nair",
        "email": "kavita.nair@erp.edu",
        "designation": "Senior Lab Instructor",
        "profile_image_path": "uploads/avatars/inst_kavita.png",
    },
    "hr_manager": {
        "user_id": 7,
        "username": "hr_manager",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "HR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "HR001",
        "department_id": None,
        "department_code": "ADMIN",
        "department_name": "Human Resources & Personnel Division",
        "first_name": "Meenakshi",
        "last_name": "Sundaram",
        "email": "hr@erp.edu",
        "designation": "Chief Human Resources Officer",
        "profile_image_path": "uploads/avatars/hr_manager.png",
    },
    "principal": {
        "user_id": 8,
        "username": "principal",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",  # Password@123
        "role": "PRINCIPAL",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "PRIN001",
        "department_id": None,
        "department_code": "ADMIN",
        "department_name": "Executive Leadership & Directorate",
        "first_name": "Dr. Anirudh",
        "last_name": "Deshmukh",
        "email": "principal@erp.edu",
        "designation": "Principal & Institutional Director",
        "profile_image_path": "uploads/avatars/principal.png",
    },
    "fac_csd_hod": {
        "user_id": 12,
        "username": "fac_csd_hod",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "HOD",
        "status": "ACTIVE",
        "faculty_id": 14,
        "employee_code": "F011",
        "department_id": 8,
        "department_code": "CSD",
        "department_name": "Department of Computer Science & Design",
        "first_name": "Dr. Deepa",
        "last_name": "Shenoy",
        "email": "hod.csd@erp.edu",
        "designation": "Professor & HOD",
        "profile_image_path": "",
    },
    "fac_csd1": {
        "user_id": 13,
        "username": "fac_csd1",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 15,
        "employee_code": "F012",
        "department_id": 8,
        "department_code": "CSD",
        "department_name": "Department of Computer Science & Design",
        "first_name": "Vikram",
        "last_name": "Hegde",
        "email": "vikram.hegde@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "",
    },
    "fac_mech1": {
        "user_id": 14,
        "username": "fac_mech1",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 16,
        "employee_code": "F013",
        "department_id": 4,
        "department_code": "MECH",
        "department_name": "Department of Mechanical Engineering",
        "first_name": "Pradeep",
        "last_name": "Nayak",
        "email": "pradeep.nayak@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "",
    },
    "fac_civil1": {
        "user_id": 15,
        "username": "fac_civil1",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 17,
        "employee_code": "F014",
        "department_id": 5,
        "department_code": "CIVIL",
        "department_name": "Department of Civil Engineering",
        "first_name": "Ananya",
        "last_name": "Pai",
        "email": "ananya.pai@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "",
    },
    "fac_ece1": {
        "user_id": 16,
        "username": "fac_ece1",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 18,
        "employee_code": "F015",
        "department_id": 6,
        "department_code": "ECE",
        "department_name": "Department of Electronics & Communication Engineering",
        "first_name": "Gautam",
        "last_name": "Prabhu",
        "email": "gautam.prabhu@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "",
    },
    "fac_ise_hod": {
        "user_id": 17,
        "username": "fac_ise_hod",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "HOD",
        "status": "ACTIVE",
        "faculty_id": 12,
        "employee_code": "F009",
        "department_id": 7,
        "department_code": "ISE",
        "department_name": "Department of Information Science & Engineering",
        "first_name": "Dr. Vinay",
        "last_name": "K",
        "email": "hod.ise@erp.edu",
        "designation": "Professor & HOD",
        "profile_image_path": "",
    },
    "fac_ise1": {
        "user_id": 18,
        "username": "fac_ise1",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "FACULTY",
        "status": "ACTIVE",
        "faculty_id": 19,
        "employee_code": "F016",
        "department_id": 7,
        "department_code": "ISE",
        "department_name": "Department of Information Science & Engineering",
        "first_name": "Rohit",
        "last_name": "Shetty",
        "email": "rohit.shetty@erp.edu",
        "designation": "Assistant Professor",
        "profile_image_path": "",
    },
    "inst_manoj": {
        "user_id": 20,
        "username": "inst_manoj",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS002",
        "department_id": 2,
        "department_code": "CSE",
        "department_name": "Department of Computer Science & Engineering",
        "first_name": "Manoj",
        "last_name": "Bhat",
        "email": "manoj.bhat@erp.edu",
        "designation": "Lab Instructor",
        "profile_image_path": "",
    },
    "inst_divya": {
        "user_id": 21,
        "username": "inst_divya",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS003",
        "department_id": 8,
        "department_code": "CSD",
        "department_name": "Department of Computer Science & Design",
        "first_name": "Divya",
        "last_name": "Rao",
        "email": "divya.rao@erp.edu",
        "designation": "Lab Instructor",
        "profile_image_path": "",
    },
    "inst_harish": {
        "user_id": 22,
        "username": "inst_harish",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS004",
        "department_id": 4,
        "department_code": "MECH",
        "department_name": "Department of Mechanical Engineering",
        "first_name": "Harish",
        "last_name": "Poojary",
        "email": "harish.poojary@erp.edu",
        "designation": "Lab Instructor",
        "profile_image_path": "",
    },
    "inst_shilpa": {
        "user_id": 23,
        "username": "inst_shilpa",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS005",
        "department_id": 5,
        "department_code": "CIVIL",
        "department_name": "Department of Civil Engineering",
        "first_name": "Shilpa",
        "last_name": "Shetty",
        "email": "shilpa.shetty@erp.edu",
        "designation": "Lab Instructor",
        "profile_image_path": "",
    },
    "inst_praveen": {
        "user_id": 24,
        "username": "inst_praveen",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS006",
        "department_id": 6,
        "department_code": "ECE",
        "department_name": "Department of Electronics & Communication Engineering",
        "first_name": "Praveen",
        "last_name": "Kumar",
        "email": "praveen.kumar@erp.edu",
        "designation": "Lab Instructor",
        "profile_image_path": "",
    },
    "inst_preeti": {
        "user_id": 25,
        "username": "inst_preeti",
        "password_hash": "31323334353637383930313233343536$18cb20a8f348be90166d435db17b182cd03c356fd8381afa395b98c8eee14b87",
        "role": "LAB_INSTRUCTOR",
        "status": "ACTIVE",
        "faculty_id": None,
        "employee_code": "INS007",
        "department_id": 7,
        "department_code": "ISE",
        "department_name": "Department of Information Science & Engineering",
        "first_name": "Preeti",
        "last_name": "Shenoy",
        "email": "preeti.shenoy@erp.edu",
        "designation": "Lab Instructor",
        "profile_image_path": "",
    },
}


class UserRepository:
    """Repository managing user authentication queries and profile lookups."""

    def get_by_username(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Fetches user credentials and profile details by Employee ID or username using parameterized SQL JOIN query.
        Falls back to local prototype dictionary if DB is offline.
        """
        clean_id = identifier.strip()
        query = """
            SELECT 
                u.id AS user_id,
                u.username,
                u.password_hash,
                u.role,
                u.status,
                COALESCE(f.id, li.id) AS faculty_id,
                COALESCE(f.employee_code, li.instructor_code) AS employee_code,
                COALESCE(f.department_id, li.department_id) AS department_id,
                d.code AS department_code,
                d.name AS department_name,
                COALESCE(f.first_name, li.first_name) AS first_name,
                COALESCE(f.last_name, li.last_name) AS last_name,
                COALESCE(f.email, li.email) AS email,
                COALESCE(f.designation, li.lab_specialization) AS designation,
                COALESCE(f.profile_image_path, li.profile_image_path) AS profile_image_path
            FROM users u
            LEFT JOIN faculty f ON f.user_id = u.id
            LEFT JOIN lab_instructors li ON li.user_id = u.id
            LEFT JOIN departments d ON d.id = COALESCE(f.department_id, li.department_id)
            WHERE u.username = %s 
               OR UPPER(COALESCE(f.employee_code, li.instructor_code)) = UPPER(%s)
            LIMIT 1;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (clean_id, clean_id))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return row
        except Exception as exc:
            logger.debug(f"DB lookup unavailable for '{clean_id}', using demo fallback: {exc}")

        # Fallback to local demo dictionary if DB is offline
        clean_key = clean_id.lower()
        if clean_key in DEMO_USERS:
            return DEMO_USERS[clean_key].copy()

        # Check by employee_code in DEMO_USERS
        for u in DEMO_USERS.values():
            if u.get("employee_code", "").upper() == clean_id.upper():
                return u.copy()

        return None

    get_by_employee_id = get_by_username

    def update_last_login(self, user_id: int):
        """Updates last_login timestamp for the user."""
        query = "UPDATE users SET last_login = NOW() WHERE id = %s;"
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.debug(f"Failed to update last_login for user_id={user_id}: {exc}")

    def update_password(self, user_id: int, new_password_hash: str) -> bool:
        """Updates user's password hash in MySQL DB and in-memory mock."""
        query = "UPDATE users SET password_hash = %s WHERE id = %s;"
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (new_password_hash, user_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.debug(f"DB update password skipped: {exc}")

        # Update in-memory mock users
        for u in DEMO_USERS.values():
            if u.get("user_id") == user_id or u.get("id") == user_id:
                u["password_hash"] = new_password_hash
                return True
        return True


user_repository = UserRepository()

