"""
Faculty Repository
Handles database operations for faculty profiles, linked user accounts, leave balances, and grace allocations.
"""
from typing import List, Dict, Any, Optional
from datetime import date
from database.connection import get_connection
from utils.logger import get_logger
from utils.security import hash_password

logger = get_logger("repositories.faculty_repository")

# Fallback prototype demo faculty list when DB is offline
DEMO_FACULTY_LIST = [
    {
        "id": 1,
        "employee_code": "EMP001",
        "user_id": 1,
        "username": "admin",
        "role": "ADMIN",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "System",
        "last_name": "Admin",
        "full_name": "System Admin",
        "email": "admin@erp.edu",
        "phone": "9876543210",
        "designation": "System Administrator",
        "profile_image_path": "uploads/avatars/admin.png",
        "joining_date": "2020-01-01",
        "status": "ACTIVE",
    },
    {
        "id": 2,
        "employee_code": "F001",
        "user_id": 2,
        "username": "hod_mca",
        "role": "HOD",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Dr. Suresh",
        "last_name": "Kumar",
        "full_name": "Dr. Suresh Kumar",
        "email": "hod.mca@erp.edu",
        "personal_email": "suresh.kumar.prof@gmail.com",
        "phone": "9876543211",
        "designation": "Professor & HOD",
        "profile_image_path": "uploads/avatars/hod_mca.png",
        "joining_date": "2015-06-15",
        "dob": "1975-09-20",
        "employment_type": "PERMANENT",
        "pan_number": "BKZPK9876Q",
        "aadhaar_number": "876543210987",
        "pf_number": "KN/BNG/0045612/000/0000045",
        "uan_number": "100876543210",
        "vtu_id": "VTU10124",
        "salary_account_no": "50100987654321",
        "experience_years": 15.0,
        "status": "ACTIVE",
    },
    {
        "id": 3,
        "employee_code": "F002",
        "user_id": 3,
        "username": "fac_rahul",
        "role": "FACULTY",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Rahul",
        "last_name": "Sharma",
        "full_name": "Rahul Sharma",
        "email": "rahul.sharma@erp.edu",
        "personal_email": "rahul.sharma.personal@gmail.com",
        "phone": "9876543212",
        "designation": "Assistant Professor",
        "profile_image_path": "uploads/avatars/fac_rahul.png",
        "joining_date": "2021-08-10",
        "dob": "1988-04-12",
        "employment_type": "PERMANENT",
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "987654321012",
        "pf_number": "KN/BNG/0045612/000/0000123",
        "uan_number": "100987654321",
        "vtu_id": "VTU14589",
        "salary_account_no": "50100234567890",
        "experience_years": 6.5,
        "status": "ACTIVE",
    },
    {
        "id": 4,
        "employee_code": "F003",
        "user_id": 4,
        "username": "fac_priya",
        "role": "FACULTY",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Priya",
        "last_name": "Verma",
        "full_name": "Priya Verma",
        "email": "priya.verma@erp.edu",
        "personal_email": "priya.verma.res@gmail.com",
        "phone": "9876543213",
        "designation": "Associate Professor",
        "profile_image_path": "",
        "joining_date": "2019-03-01",
        "dob": "1990-11-05",
        "employment_type": "PERMANENT",
        "pan_number": "CPRPV5432A",
        "aadhaar_number": "765432109876",
        "pf_number": "KN/BNG/0045612/000/0000210",
        "uan_number": "100765432109",
        "vtu_id": "VTU16782",
        "salary_account_no": "50100456123789",
        "experience_years": 5.0,
        "status": "ACTIVE",
    },
    {
        "id": 5,
        "employee_code": "F004",
        "user_id": 5,
        "username": "fac_amit",
        "role": "FACULTY",
        "department_id": 2,
        "department_code": "CSE",
        "department_name": "Department of Computer Science & Engineering",
        "first_name": "Amit",
        "last_name": "Patel",
        "full_name": "Amit Patel",
        "email": "amit.patel@erp.edu",
        "phone": "9876543214",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2022-01-15",
        "status": "ACTIVE",
    },
    {
        "id": 6,
        "employee_code": "F005",
        "user_id": 6,
        "username": "fac_arvind",
        "role": "HOD",
        "department_id": 2,
        "department_code": "CSE",
        "department_name": "Department of Computer Science & Engineering",
        "first_name": "Dr. Arvind",
        "last_name": "Sharma",
        "full_name": "Dr. Arvind Sharma",
        "email": "hod.cse@erp.edu",
        "phone": "9876543215",
        "designation": "Professor & HOD",
        "profile_image_path": "",
        "joining_date": "2016-07-01",
        "status": "ACTIVE",
    },
    {
        "id": 7,
        "employee_code": "F006",
        "user_id": 7,
        "username": "fac_ramesh",
        "role": "HOD",
        "department_id": 4,
        "department_code": "MECH",
        "department_name": "Department of Mechanical Engineering",
        "first_name": "Dr. Ramesh",
        "last_name": "Rao",
        "full_name": "Dr. Ramesh Rao",
        "email": "hod.mech@erp.edu",
        "phone": "9876543216",
        "designation": "Professor & HOD",
        "profile_image_path": "",
        "joining_date": "2014-04-12",
        "status": "ACTIVE",
    },
    {
        "id": 8,
        "employee_code": "F007",
        "user_id": 8,
        "username": "fac_sunita",
        "role": "HOD",
        "department_id": 5,
        "department_code": "CIVIL",
        "department_name": "Department of Civil Engineering",
        "first_name": "Dr. Sunita",
        "last_name": "Deshmukh",
        "full_name": "Dr. Sunita Deshmukh",
        "email": "hod.civil@erp.edu",
        "phone": "9876543217",
        "designation": "Professor & HOD",
        "profile_image_path": "",
        "joining_date": "2017-09-20",
        "status": "ACTIVE",
    },
    {
        "id": 9,
        "employee_code": "F008",
        "user_id": 9,
        "username": "fac_rajesh",
        "role": "HOD",
        "department_id": 6,
        "department_code": "ECE",
        "department_name": "Department of Electronics & Communication",
        "first_name": "Dr. Rajesh",
        "last_name": "Bhat",
        "full_name": "Dr. Rajesh Bhat",
        "email": "hod.ece@erp.edu",
        "phone": "9876543218",
        "designation": "Professor & HOD",
        "profile_image_path": "",
        "joining_date": "2018-01-10",
        "status": "ACTIVE",
    },
    {
        "id": 10,
        "employee_code": "HR001",
        "user_id": 10,
        "username": "hr_manager",
        "role": "HR",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Karthik",
        "last_name": "Shenoy",
        "full_name": "Karthik Shenoy",
        "email": "hr@erp.edu",
        "phone": "9876543219",
        "designation": "HR Manager",
        "profile_image_path": "",
        "joining_date": "2019-11-01",
        "status": "ACTIVE",
    },
    {
        "id": 11,
        "employee_code": "PRIN001",
        "user_id": 11,
        "username": "principal",
        "role": "PRINCIPAL",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "first_name": "Dr. Shreedhar",
        "last_name": "K",
        "full_name": "Dr. Shreedhar K",
        "email": "principal@erp.edu",
        "phone": "9876543200",
        "designation": "Principal",
        "profile_image_path": "",
        "joining_date": "2012-05-01",
        "status": "ACTIVE",
    },
    {
        "id": 12,
        "employee_code": "F009",
        "user_id": 17,
        "username": "fac_ise_hod",
        "role": "HOD",
        "department_id": 7,
        "department_code": "ISE",
        "department_name": "Department of Information Science & Engineering",
        "first_name": "Dr. Vinay",
        "last_name": "K",
        "full_name": "Dr. Vinay K",
        "email": "hod.ise@erp.edu",
        "phone": "9876543227",
        "designation": "Professor & HOD",
        "profile_image_path": "",
        "joining_date": "2016-08-01",
        "status": "ACTIVE",
    },
    {
        "id": 13,
        "employee_code": "F010",
        "user_id": 19,
        "username": "fac_cse2",
        "role": "FACULTY",
        "department_id": 2,
        "department_code": "CSE",
        "department_name": "Department of Computer Science & Engineering",
        "first_name": "Sneha",
        "last_name": "Reddy",
        "full_name": "Sneha Reddy",
        "email": "sneha.reddy@erp.edu",
        "phone": "9876543228",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2021-02-15",
        "status": "ACTIVE",
    },
    {
        "id": 14,
        "employee_code": "F011",
        "user_id": 12,
        "username": "fac_csd_hod",
        "role": "HOD",
        "department_id": 8,
        "department_code": "CSD",
        "department_name": "Department of Computer Science & Design",
        "first_name": "Dr. Deepa",
        "last_name": "Shenoy",
        "full_name": "Dr. Deepa Shenoy",
        "email": "hod.csd@erp.edu",
        "phone": "9876543229",
        "designation": "Professor & HOD",
        "profile_image_path": "",
        "joining_date": "2018-06-20",
        "status": "ACTIVE",
    },
    {
        "id": 15,
        "employee_code": "F012",
        "user_id": 13,
        "username": "fac_csd1",
        "role": "FACULTY",
        "department_id": 8,
        "department_code": "CSD",
        "department_name": "Department of Computer Science & Design",
        "first_name": "Vikram",
        "last_name": "Hegde",
        "full_name": "Vikram Hegde",
        "email": "vikram.hegde@erp.edu",
        "phone": "9876543230",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2022-03-01",
        "status": "ACTIVE",
    },
    {
        "id": 16,
        "employee_code": "F013",
        "user_id": 14,
        "username": "fac_mech1",
        "role": "FACULTY",
        "department_id": 4,
        "department_code": "MECH",
        "department_name": "Department of Mechanical Engineering",
        "first_name": "Pradeep",
        "last_name": "Nayak",
        "full_name": "Pradeep Nayak",
        "email": "pradeep.nayak@erp.edu",
        "phone": "9876543231",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2020-07-15",
        "status": "ACTIVE",
    },
    {
        "id": 17,
        "employee_code": "F014",
        "user_id": 15,
        "username": "fac_civil1",
        "role": "FACULTY",
        "department_id": 5,
        "department_code": "CIVIL",
        "department_name": "Department of Civil Engineering",
        "first_name": "Ananya",
        "last_name": "Pai",
        "full_name": "Ananya Pai",
        "email": "ananya.pai@erp.edu",
        "phone": "9876543232",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2021-09-10",
        "status": "ACTIVE",
    },
    {
        "id": 18,
        "employee_code": "F015",
        "user_id": 16,
        "username": "fac_ece1",
        "role": "FACULTY",
        "department_id": 6,
        "department_code": "ECE",
        "department_name": "Department of Electronics & Communication Engineering",
        "first_name": "Gautam",
        "last_name": "Prabhu",
        "full_name": "Gautam Prabhu",
        "email": "gautam.prabhu@erp.edu",
        "phone": "9876543233",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2020-01-20",
        "status": "ACTIVE",
    },
    {
        "id": 19,
        "employee_code": "F016",
        "user_id": 18,
        "username": "fac_ise1",
        "role": "FACULTY",
        "department_id": 7,
        "department_code": "ISE",
        "department_name": "Department of Information Science & Engineering",
        "first_name": "Rohit",
        "last_name": "Shetty",
        "full_name": "Rohit Shetty",
        "email": "rohit.shetty@erp.edu",
        "phone": "9876543234",
        "designation": "Assistant Professor",
        "profile_image_path": "",
        "joining_date": "2022-08-01",
        "status": "ACTIVE",
    },
]

DEMO_SUBJECTS_HANDLED = [
    {
        "id": 1,
        "faculty_id": 3,
        "employee_code": "F002",
        "admission_year": "2024",
        "subject_code": "22MCA11",
        "subject_name": "Data Structures & Algorithms",
        "semester": 1,
        "section": "A",
        "branch": "MCA",
    },
    {
        "id": 2,
        "faculty_id": 3,
        "employee_code": "F002",
        "admission_year": "2023",
        "subject_code": "22MCA32",
        "subject_name": "Machine Learning Applications",
        "semester": 3,
        "section": "A",
        "branch": "MCA",
    },
    {
        "id": 3,
        "faculty_id": 3,
        "employee_code": "F002",
        "admission_year": "2024",
        "subject_code": "22MCA16",
        "subject_name": "Data Structures Laboratory",
        "semester": 1,
        "section": "B",
        "branch": "MCA",
    },
    {
        "id": 4,
        "faculty_id": 2,
        "employee_code": "F001",
        "admission_year": "2023",
        "subject_code": "22MCA31",
        "subject_name": "Advanced Database Management Systems",
        "semester": 3,
        "section": "A",
        "branch": "MCA",
    },
]


class FacultyRepository:
    """Repository managing SQL operations for the faculty table."""

    def get_all(
        self,
        department_id: Optional[int] = None,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves faculty records with department details, role, and email.
        Supports filtering by department_id and searching by employee_code or full_name.
        """
        query = """
            SELECT 
                f.id,
                f.employee_code,
                f.user_id,
                u.username,
                u.role,
                f.department_id,
                d.code AS department_code,
                d.name AS department_name,
                f.first_name,
                f.last_name,
                CONCAT(f.first_name, ' ', f.last_name) AS full_name,
                f.email,
                f.personal_email,
                f.phone,
                f.designation,
                f.profile_image_path,
                f.joining_date,
                f.dob,
                f.employment_type,
                f.pan_number,
                f.aadhaar_number,
                f.pf_number,
                f.uan_number,
                f.vtu_id,
                f.salary_account_no,
                f.experience_years,
                f.status
            FROM faculty f
            INNER JOIN users u ON u.id = f.user_id
            INNER JOIN departments d ON d.id = f.department_id
            WHERE 1=1
        """
        params = []
        if department_id is not None:
            query += " AND f.department_id = %s"
            params.append(department_id)

        if search_term and search_term.strip():
            term = f"%{search_term.strip()}%"
            query += " AND (f.employee_code LIKE %s OR f.first_name LIKE %s OR f.last_name LIKE %s OR f.email LIKE %s)"
            params.extend([term, term, term, term])

        query += " ORDER BY f.employee_code ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB faculty query unavailable, using fallback: {exc}")
            results = []
            for f in DEMO_FACULTY_LIST:
                if department_id is not None and f["department_id"] != department_id:
                    continue
                if search_term and search_term.strip():
                    st = search_term.strip().lower()
                    match_code = st in f["employee_code"].lower()
                    match_name = st in f["full_name"].lower()
                    match_email = st in f["email"].lower()
                    if not (match_code or match_name or match_email):
                        continue
                item = f.copy()
                # Ensure all extended profile fields exist with clean defaults
                item.setdefault("personal_email", "")
                item.setdefault("dob", "")
                item.setdefault("employment_type", "PERMANENT")
                item.setdefault("pan_number", "")
                item.setdefault("aadhaar_number", "")
                item.setdefault("pf_number", "")
                item.setdefault("uan_number", "")
                item.setdefault("vtu_id", "")
                item.setdefault("salary_account_no", "")
                item.setdefault("experience_years", 0.0)
                results.append(item)
            return results

    def get_by_id(self, faculty_id: int) -> Optional[Dict[str, Any]]:
        """Fetches faculty record by ID."""
        facs = self.get_all()
        for f in facs:
            if f["id"] == faculty_id:
                return f
        return None

    def get_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetches faculty record by associated user ID."""
        facs = self.get_all()
        for f in facs:
            if f.get("user_id") == user_id:
                return f
        return None

    def get_by_employee_code(self, employee_code: str) -> Optional[Dict[str, Any]]:
        """Fetches faculty record by employee code."""
        facs = self.get_all()
        code_clean = employee_code.strip().upper()
        for f in facs:
            if f["employee_code"].upper() == code_clean:
                return f
        return None

    def get_subjects_handled(self, faculty_id: int) -> List[Dict[str, Any]]:
        """Retrieves list of academic subjects handled by the faculty member."""
        query = """
            SELECT 
                id,
                faculty_id,
                admission_year,
                subject_code,
                subject_name,
                semester,
                section,
                branch,
                created_at
            FROM faculty_subjects_handled
            WHERE faculty_id = %s
            ORDER BY admission_year DESC, semester ASC;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (faculty_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB subjects_handled query fallback: {exc}")
            return [s.copy() for s in DEMO_SUBJECTS_HANDLED if s.get("faculty_id") == faculty_id]


    def create(self, faculty_data: Dict[str, Any]) -> int:
        """
        Creates user authentication account, faculty profile, initial leave balances,
        and current month grace minutes in a single database transaction.
        """
        emp_code = faculty_data["employee_code"].strip().upper()
        username = faculty_data["username"].strip().lower()
        pass_hash = hash_password(faculty_data["password"])
        role = faculty_data.get("role", "FACULTY")
        dept_id = int(faculty_data["department_id"])

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # 1. Insert User Account
            user_sql = "INSERT INTO users (username, password_hash, role, status) VALUES (%s, %s, %s, 'ACTIVE') RETURNING id;"
            cursor.execute(user_sql, (username, pass_hash, role))
            u_row = cursor.fetchone()
            user_id = u_row[0] if u_row else getattr(cursor, "lastrowid", None)

            # 2. Insert Faculty Record
            fac_sql = """
                INSERT INTO faculty (employee_code, user_id, department_id, first_name, last_name, email, phone, designation, joining_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                RETURNING id;
            """
            joining = faculty_data.get("joining_date", str(date.today()))
            cursor.execute(
                fac_sql,
                (
                    emp_code,
                    user_id,
                    dept_id,
                    faculty_data["first_name"].strip(),
                    faculty_data["last_name"].strip(),
                    faculty_data["email"].strip(),
                    faculty_data.get("phone", "").strip(),
                    faculty_data.get("designation", "Assistant Professor").strip(),
                    joining,
                ),
            )
            f_row = cursor.fetchone()
            faculty_id = f_row[0] if f_row else getattr(cursor, "lastrowid", None)

            # 3. Initialize 2026 Leave Balances for all active leave types
            bal_sql = """
                INSERT INTO leave_balance (faculty_id, leave_type_id, year, allocated_days, used_days, pending_days)
                SELECT %s, id, 2026, max_days_per_year, 0.00, 0.00 FROM leave_types WHERE is_active = 1
                ON CONFLICT (faculty_id, leave_type_id, year) DO NOTHING;
            """
            cursor.execute(bal_sql, (faculty_id,))

            # 4. Initialize Grace Minutes Record for current month
            current_month = date.today().strftime("%Y-%m")
            grace_sql = """
                INSERT INTO grace_minutes (faculty_id, month_year, allowed_minutes, used_minutes)
                VALUES (%s, %s, 45, 0) ON CONFLICT (faculty_id, month_year) DO NOTHING;
            """
            cursor.execute(grace_sql, (faculty_id, current_month))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Created faculty '{emp_code}' (Faculty ID={faculty_id}, User ID={user_id}).")
            return faculty_id

        except Exception as exc:
            logger.warning(f"DB create faculty error, adding to memory fallback: {exc}")
            new_fac_id = max([f["id"] for f in DEMO_FACULTY_LIST], default=0) + 1
            new_user_id = max([f["user_id"] for f in DEMO_FACULTY_LIST], default=0) + 1
            dept_code = "MCA" if dept_id == 1 else ("CSE" if dept_id == 2 else "IT")

            DEMO_FACULTY_LIST.append(
                {
                    "id": new_fac_id,
                    "employee_code": emp_code,
                    "user_id": new_user_id,
                    "username": username,
                    "role": role,
                    "department_id": dept_id,
                    "department_code": dept_code,
                    "department_name": f"Department of {dept_code}",
                    "first_name": faculty_data["first_name"].strip(),
                    "last_name": faculty_data["last_name"].strip(),
                    "full_name": f"{faculty_data['first_name'].strip()} {faculty_data['last_name'].strip()}",
                    "email": faculty_data["email"].strip(),
                    "phone": faculty_data.get("phone", "").strip(),
                    "designation": faculty_data.get("designation", "Assistant Professor").strip(),
                    "joining_date": str(date.today()),
                    "status": "ACTIVE",
                }
            )
            return new_fac_id

    def update(self, faculty_id: int, faculty_data: Dict[str, Any]):
        """Updates faculty profile details using parameterized SQL."""
        existing = self.get_by_id(faculty_id) or {}
        merged = {**existing, **faculty_data}

        query = """
            UPDATE faculty 
            SET department_id = %s,
                first_name = %s,
                last_name = %s,
                email = %s,
                phone = %s,
                personal_email = %s,
                designation = %s,
                profile_image_path = COALESCE(%s, profile_image_path),
                joining_date = %s,
                dob = %s,
                employment_type = %s,
                pan_number = %s,
                aadhaar_number = %s,
                pf_number = %s,
                uan_number = %s,
                vtu_id = %s,
                salary_account_no = %s,
                experience_years = %s,
                status = %s
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    int(merged.get("department_id") or 1),
                    str(merged.get("first_name", "")).strip(),
                    str(merged.get("last_name", "")).strip(),
                    str(merged.get("email", "")).strip(),
                    str(merged.get("phone", "") or "").strip() or None,
                    str(merged.get("personal_email", "") or "").strip() or None,
                    str(merged.get("designation", "") or "").strip(),
                    merged.get("profile_image_path"),
                    str(merged.get("joining_date") or date.today()),
                    str(merged.get("dob") or "") or None,
                    str(merged.get("employment_type", "PERMANENT")),
                    str(merged.get("pan_number", "") or "").strip() or None,
                    str(merged.get("aadhaar_number", "") or "").strip() or None,
                    str(merged.get("pf_number", "") or "").strip() or None,
                    str(merged.get("uan_number", "") or "").strip() or None,
                    str(merged.get("vtu_id", "") or "").strip() or None,
                    str(merged.get("salary_account_no", "") or "").strip() or None,
                    float(merged.get("experience_years") or 0.0),
                    str(merged.get("status", "ACTIVE")),
                    faculty_id,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Updated faculty ID={faculty_id}.")
        except Exception as exc:
            logger.warning(f"DB update faculty error, updating memory fallback: {exc}")

        # Update in-memory fallback
        for f in DEMO_FACULTY_LIST:
            if f["id"] == faculty_id:
                for k, v in faculty_data.items():
                    f[k] = v
                f["full_name"] = f"{f.get('first_name', '')} {f.get('last_name', '')}".strip()
                break


faculty_repository = FacultyRepository()
