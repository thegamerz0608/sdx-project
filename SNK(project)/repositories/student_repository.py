"""
Student Repository
Handles database persistence and queries for Student records, with parameterized queries
and offline fallback prototype support.
"""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.student_repository")

# Fallback prototype students for offline development and test verification across varying department sizes
DEMO_STUDENTS = [
    # Department of Computer Applications (MCA) - 10 students
    {"id": 1, "usn": "1MS23MCA001", "name": "Aarav Sharma", "year": 1, "phone_number": "9876543210", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": "uploads/avatars/student1.png"},
    {"id": 2, "usn": "1MS23MCA002", "name": "Bhavna Patel", "year": 1, "phone_number": "9876543211", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 3, "usn": "1MS22MCA045", "name": "Chetan Kumar", "year": 2, "phone_number": "9876543212", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 4, "usn": "1MS22MCA048", "name": "Divya Acharya", "year": 2, "phone_number": "9876543215", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 5, "usn": "1MS23MCA015", "name": "Gaurav Shenoy", "year": 1, "phone_number": "9876543216", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 6, "usn": "1MS22MCA022", "name": "Harini Bhat", "year": 2, "phone_number": "9876543217", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 7, "usn": "1MS23MCA030", "name": "Irfan Khan", "year": 1, "phone_number": "9876543218", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 8, "usn": "1MS22MCA035", "name": "Jyothi M", "year": 2, "phone_number": "9876543219", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 9, "usn": "1MS23MCA040", "name": "Kiran Pai", "year": 1, "phone_number": "9876543220", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},
    {"id": 10, "usn": "1MS22MCA050", "name": "Latha Poojary", "year": 2, "phone_number": "9876543221", "department_id": 1, "department_code": "MCA", "department_name": "Department of Computer Applications", "profile_image_path": ""},

    # Department of Computer Science & Engineering (CSE) - 12 students (Large population)
    {"id": 11, "usn": "1MS21CS089", "name": "Deepika Rao", "year": 4, "phone_number": "9876543213", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 12, "usn": "1MS22CS110", "name": "Eshwar Gowda", "year": 3, "phone_number": "9876543214", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 13, "usn": "1MS21CS012", "name": "Abhishek Hegde", "year": 4, "phone_number": "9876543222", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 14, "usn": "1MS22CS045", "name": "Ananya Kulkarni", "year": 3, "phone_number": "9876543223", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 15, "usn": "1MS23CS010", "name": "Bharat Deshpande", "year": 2, "phone_number": "9876543224", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 16, "usn": "1MS23CS088", "name": "Chaitra Nayak", "year": 2, "phone_number": "9876543225", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 17, "usn": "1MS24CS005", "name": "Dhanush Shetty", "year": 1, "phone_number": "9876543226", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 18, "usn": "1MS24CS032", "name": "Geetha Karanth", "year": 1, "phone_number": "9876543227", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 19, "usn": "1MS21CS105", "name": "Manoj Kulal", "year": 4, "phone_number": "9876543228", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 20, "usn": "1MS22CS099", "name": "Nandini R", "year": 3, "phone_number": "9876543229", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 21, "usn": "1MS23CS072", "name": "Pawan Kumar V", "year": 2, "phone_number": "9876543230", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},
    {"id": 22, "usn": "1MS24CS061", "name": "Ruchita Sen", "year": 1, "phone_number": "9876543231", "department_id": 2, "department_code": "CSE", "department_name": "Department of Computer Science & Engineering", "profile_image_path": ""},

    # Department of Mechanical Engineering (MECH) - 6 students (Medium-small population)
    {"id": 23, "usn": "1MS21ME001", "name": "Aditya Shinde", "year": 4, "phone_number": "9876543232", "department_id": 4, "department_code": "MECH", "department_name": "Department of Mechanical Engineering", "profile_image_path": ""},
    {"id": 24, "usn": "1MS21ME025", "name": "Chinmay Gokhale", "year": 4, "phone_number": "9876543233", "department_id": 4, "department_code": "MECH", "department_name": "Department of Mechanical Engineering", "profile_image_path": ""},
    {"id": 25, "usn": "1MS22ME014", "name": "Darshan B", "year": 3, "phone_number": "9876543234", "department_id": 4, "department_code": "MECH", "department_name": "Department of Mechanical Engineering", "profile_image_path": ""},
    {"id": 26, "usn": "1MS22ME033", "name": "Karthik Hebbar", "year": 3, "phone_number": "9876543235", "department_id": 4, "department_code": "MECH", "department_name": "Department of Mechanical Engineering", "profile_image_path": ""},
    {"id": 27, "usn": "1MS23ME008", "name": "Prashant Patil", "year": 2, "phone_number": "9876543236", "department_id": 4, "department_code": "MECH", "department_name": "Department of Mechanical Engineering", "profile_image_path": ""},
    {"id": 28, "usn": "1MS24ME015", "name": "Sagar Malnad", "year": 1, "phone_number": "9876543237", "department_id": 4, "department_code": "MECH", "department_name": "Department of Mechanical Engineering", "profile_image_path": ""},

    # Department of Civil Engineering (CIVIL) - 6 students (Medium-small population)
    {"id": 29, "usn": "1MS21CV002", "name": "Archana Naik", "year": 4, "phone_number": "9876543238", "department_id": 5, "department_code": "CIVIL", "department_name": "Department of Civil Engineering", "profile_image_path": ""},
    {"id": 30, "usn": "1MS21CV019", "name": "Deepak Kamat", "year": 4, "phone_number": "9876543239", "department_id": 5, "department_code": "CIVIL", "department_name": "Department of Civil Engineering", "profile_image_path": ""},
    {"id": 31, "usn": "1MS22CV011", "name": "Hemanth G", "year": 3, "phone_number": "9876543240", "department_id": 5, "department_code": "CIVIL", "department_name": "Department of Civil Engineering", "profile_image_path": ""},
    {"id": 32, "usn": "1MS22CV028", "name": "Meghana Salian", "year": 3, "phone_number": "9876543241", "department_id": 5, "department_code": "CIVIL", "department_name": "Department of Civil Engineering", "profile_image_path": ""},
    {"id": 33, "usn": "1MS23CV007", "name": "Naveen Suvarna", "year": 2, "phone_number": "9876543242", "department_id": 5, "department_code": "CIVIL", "department_name": "Department of Civil Engineering", "profile_image_path": ""},
    {"id": 34, "usn": "1MS24CV012", "name": "Rohit Vernekar", "year": 1, "phone_number": "9876543243", "department_id": 5, "department_code": "CIVIL", "department_name": "Department of Civil Engineering", "profile_image_path": ""},

    # Department of Electronics & Communication Engineering (ECE) - 8 students
    {"id": 35, "usn": "1MS21EC005", "name": "Ashwin Prabhu", "year": 4, "phone_number": "9876543244", "department_id": 6, "department_code": "ECE", "department_name": "Department of Electronics & Communication", "profile_image_path": ""},
    {"id": 36, "usn": "1MS21EC044", "name": "Bhavya Kundar", "year": 4, "phone_number": "9876543245", "department_id": 6, "department_code": "ECE", "department_name": "Department of Electronics & Communication", "profile_image_path": ""},
    {"id": 37, "usn": "1MS22EC018", "name": "Charan Teja", "year": 3, "phone_number": "9876543246", "department_id": 6, "department_code": "ECE", "department_name": "Department of Electronics & Communication", "profile_image_path": ""},
    {"id": 38, "usn": "1MS22EC052", "name": "Keerthana S", "year": 3, "phone_number": "9876543247", "department_id": 6, "department_code": "ECE", "department_name": "Department of Electronics & Communication", "profile_image_path": ""},
    {"id": 39, "usn": "1MS23EC021", "name": "Prajwal Kotian", "year": 2, "phone_number": "9876543248", "department_id": 6, "department_code": "ECE", "department_name": "Department of Electronics & Communication", "profile_image_path": ""},
    {"id": 40, "usn": "1MS24EC009", "name": "Siddharth Alva", "year": 1, "phone_number": "9876543249", "department_id": 6, "department_code": "ECE", "department_name": "Department of Electronics & Communication", "profile_image_path": ""},
]


class StudentRepository:
    """Repository handling CRUD and multi-field search queries for Students."""

    def search_students(
        self,
        search_term: Optional[str] = None,
        department_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Searches students across USN, Name, Phone, and Year.
        """
        query = """
            SELECT 
                s.id,
                s.usn,
                s.name,
                s.year,
                s.phone_number,
                s.department_id,
                d.code AS department_code,
                d.name AS department_name,
                s.profile_image_path,
                s.created_at
            FROM students s
            INNER JOIN departments d ON d.id = s.department_id
            WHERE 1=1
        """
        params = []
        if department_id:
            query += " AND s.department_id = %s"
            params.append(department_id)
        if year:
            query += " AND s.year = %s"
            params.append(year)
        if search_term:
            term = f"%{search_term.strip()}%"
            query += " AND (s.name LIKE %s OR s.usn LIKE %s OR s.phone_number LIKE %s)"
            params.extend([term, term, term])

        query += " ORDER BY s.year ASC, s.usn ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            if rows:
                return rows
        except Exception as exc:
            logger.debug(f"Database search failed for students, using demo fallback: {exc}")

        # In-memory search fallback
        results = []
        term_clean = (search_term or "").strip().lower()
        for s in DEMO_STUDENTS:
            if department_id and s.get("department_id") != department_id:
                continue
            if year and s.get("year") != year:
                continue
            if term_clean:
                matches = (
                    term_clean in s.get("name", "").lower()
                    or term_clean in s.get("usn", "").lower()
                    or term_clean in s.get("phone_number", "").lower()
                    or term_clean == str(s.get("year", ""))
                )
                if not matches:
                    continue
            results.append(s.copy())
        return results

    def get_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Finds a student by primary key ID."""
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT s.id, s.usn, s.name, s.year, s.phone_number, s.department_id,
                       d.code AS department_code, d.name AS department_name, s.profile_image_path
                FROM students s
                INNER JOIN departments d ON d.id = s.department_id
                WHERE s.id = %s LIMIT 1;
                """,
                (student_id,),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                return row
        except Exception:
            pass

        for s in DEMO_STUDENTS:
            if s["id"] == student_id:
                return s.copy()
        return None

    def get_by_usn(self, usn: str) -> Optional[Dict[str, Any]]:
        """Finds a student by USN."""
        usn_clean = usn.strip().upper()
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT s.id, s.usn, s.name, s.year, s.phone_number, s.department_id,
                       d.code AS department_code, d.name AS department_name, s.profile_image_path
                FROM students s
                INNER JOIN departments d ON d.id = s.department_id
                WHERE UPPER(s.usn) = %s LIMIT 1;
                """,
                (usn_clean,),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                return row
        except Exception:
            pass

        for s in DEMO_STUDENTS:
            if s["usn"].upper() == usn_clean:
                return s.copy()
        return None

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new student record."""
        query = """
            INSERT INTO students (usn, name, year, phone_number, department_id, profile_image_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            data["usn"].strip().upper(),
            data["name"].strip(),
            int(data["year"]),
            data.get("phone_number", "").strip(),
            int(data["department_id"]),
            data.get("profile_image_path"),
        )
        new_id = len(DEMO_STUDENTS) + 1
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                new_id = row[0]
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.debug(f"Could not insert student to DB, persisting to demo store: {exc}")

        record = {
            "id": new_id,
            "usn": data["usn"].strip().upper(),
            "name": data["name"].strip(),
            "year": int(data["year"]),
            "phone_number": data.get("phone_number", "").strip(),
            "department_id": int(data["department_id"]),
            "department_code": data.get("department_code", "MCA"),
            "department_name": data.get("department_name", "Department of Computer Applications"),
            "profile_image_path": data.get("profile_image_path", ""),
        }
        DEMO_STUDENTS.append(record)
        return record


student_repository = StudentRepository()
