"""
Student Marks Repository
Handles data access and persistence for student grades, internals, and semester exam marks.
Provides MySQL integration with in-memory mock fallback for offline environments.
"""
from typing import List, Dict, Any, Optional
from database.connection import get_connection
from utils.logger import get_logger
from repositories.student_repository import DEMO_STUDENTS

logger = get_logger("repositories.student_marks_repository")

# Predefined Course / Subject Catalog
DEFAULT_SUBJECTS = [
    {"code": "MCA101", "name": "Advanced Data Structures & Algorithms", "semester": 1, "department_code": "MCA"},
    {"code": "MCA102", "name": "Web Technologies & Cloud Computing", "semester": 1, "department_code": "MCA"},
    {"code": "MCA103", "name": "Database Management Systems", "semester": 1, "department_code": "MCA"},
    {"code": "MCA201", "name": "Machine Learning & AI", "semester": 2, "department_code": "MCA"},
    {"code": "MCA202", "name": "Mobile Application Development", "semester": 2, "department_code": "MCA"},
    {"code": "CSE301", "name": "Operating Systems & Kernels", "semester": 3, "department_code": "CSE"},
    {"code": "CSE302", "name": "Computer Networks & Protocols", "semester": 3, "department_code": "CSE"},
    {"code": "CSD201", "name": "UI/UX Interaction Design & Figma", "semester": 2, "department_code": "CSD"},
    {"code": "CSD202", "name": "Computer Graphics & Multimedia", "semester": 2, "department_code": "CSD"},
    {"code": "ME201", "name": "Thermodynamics & Fluid Dynamics", "semester": 2, "department_code": "MECH"},
    {"code": "CV201", "name": "Structural Analysis & Materials", "semester": 2, "department_code": "CIVIL"},
    {"code": "EC301", "name": "Digital Signal Processing", "semester": 3, "department_code": "ECE"},
    {"code": "IS301", "name": "Big Data Analytics & Hadoop", "semester": 3, "department_code": "ISE"},
]

# Fallback in-memory dataset
DEMO_STUDENT_MARKS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "student_id": 1,
        "usn": "4JK23MC001",
        "student_name": "Aarav Sharma",
        "subject_code": "MCA101",
        "subject_name": "Advanced Data Structures & Algorithms",
        "semester": 1,
        "internal_1": 23.50,
        "internal_2": 22.00,
        "assignment": 9.50,
        "semester_exam": 36.00,
        "total_marks": 91.00,
        "grade": "O",
        "status": "PASS",
        "recorded_by_user_id": 2,
    },
    {
        "id": 2,
        "student_id": 2,
        "usn": "4JK23MC002",
        "student_name": "Aditi Rao",
        "subject_code": "MCA101",
        "subject_name": "Advanced Data Structures & Algorithms",
        "semester": 1,
        "internal_1": 21.00,
        "internal_2": 19.50,
        "assignment": 8.50,
        "semester_exam": 33.00,
        "total_marks": 82.00,
        "grade": "A+",
        "status": "PASS",
        "recorded_by_user_id": 2,
    },
    {
        "id": 3,
        "student_id": 3,
        "usn": "4JK23MC003",
        "student_name": "Ananya Hegde",
        "subject_code": "MCA101",
        "subject_name": "Advanced Data Structures & Algorithms",
        "semester": 1,
        "internal_1": 18.00,
        "internal_2": 20.00,
        "assignment": 8.00,
        "semester_exam": 30.00,
        "total_marks": 76.00,
        "grade": "A",
        "status": "PASS",
        "recorded_by_user_id": 2,
    },
    {
        "id": 4,
        "student_id": 4,
        "usn": "4JK23MC004",
        "student_name": "Chirag Poojary",
        "subject_code": "MCA101",
        "subject_name": "Advanced Data Structures & Algorithms",
        "semester": 1,
        "internal_1": 15.00,
        "internal_2": 16.00,
        "assignment": 7.00,
        "semester_exam": 26.00,
        "total_marks": 64.00,
        "grade": "B+",
        "status": "PASS",
        "recorded_by_user_id": 2,
    },
    {
        "id": 5,
        "student_id": 5,
        "usn": "4JK23MC005",
        "student_name": "Deepak Shenoy",
        "subject_code": "MCA101",
        "subject_name": "Advanced Data Structures & Algorithms",
        "semester": 1,
        "internal_1": 12.00,
        "internal_2": 14.00,
        "assignment": 6.00,
        "semester_exam": 20.00,
        "total_marks": 52.00,
        "grade": "B",
        "status": "PASS",
        "recorded_by_user_id": 2,
    },
]


class StudentMarksRepository:
    """Repository managing student marks data access and transactions."""

    def get_subjects(self, department_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of registered subjects, optionally filtered by department."""
        if not department_code:
            return DEFAULT_SUBJECTS.copy()
        code_upper = department_code.strip().upper()
        return [s for s in DEFAULT_SUBJECTS if s["department_code"] == code_upper]

    def get_marks_for_subject(
        self,
        subject_code: str,
        semester: int = 1,
        department_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves mark records for a specific subject and semester.
        Includes all enrolled students for the department/semester with default 0s if not yet entered.
        """
        query = """
            SELECT 
                s.id AS student_id,
                s.usn,
                s.full_name AS student_name,
                d.code AS department_code,
                s.current_semester,
                COALESCE(sm.id, 0) AS mark_id,
                COALESCE(sm.subject_code, %s) AS subject_code,
                COALESCE(sm.subject_name, %s) AS subject_name,
                COALESCE(sm.internal_1, 0.00) AS internal_1,
                COALESCE(sm.internal_2, 0.00) AS internal_2,
                COALESCE(sm.assignment, 0.00) AS assignment,
                COALESCE(sm.semester_exam, 0.00) AS semester_exam,
                COALESCE(sm.total_marks, 0.00) AS total_marks,
                COALESCE(sm.grade, 'F') AS grade,
                COALESCE(sm.status, 'PASS') AS status
            FROM students s
            JOIN departments d ON d.id = s.department_id
            LEFT JOIN student_marks sm ON sm.student_id = s.id 
                AND sm.subject_code = %s 
                AND sm.semester = %s
            WHERE s.status = 'ACTIVE'
        """
        params = [subject_code, subject_code, subject_code, semester]
        if department_id is not None:
            query += " AND s.department_id = %s"
            params.append(department_id)

        query += " ORDER BY s.usn ASC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB marks query unavailable, using fallback: {exc}")
            # Find subject metadata
            subj_meta = next((s for s in DEFAULT_SUBJECTS if s["code"] == subject_code), None)
            subj_name = subj_meta["name"] if subj_meta else subject_code
            dept_code = subj_meta["department_code"] if subj_meta else None

            results = []
            for st in DEMO_STUDENTS:
                if st.get("status", "ACTIVE") != "ACTIVE":
                    continue
                if dept_code and st.get("department_code") != dept_code:
                    continue
                if department_id is not None and st.get("department_id") != department_id:
                    continue

                st_name = st.get("full_name") or st.get("name", "")
                st_usn = st.get("usn", "")
                st_sem = st.get("current_semester") or st.get("year", 1)

                # Match existing mark record
                existing = next(
                    (m for m in DEMO_STUDENT_MARKS 
                     if m["student_id"] == st["id"] and m["subject_code"] == subject_code),
                    None
                )

                if existing:
                    row = existing.copy()
                    row["usn"] = st_usn
                    row["student_name"] = st_name
                    row["department_code"] = st.get("department_code", "")
                    row["current_semester"] = st_sem
                    results.append(row)
                else:
                    results.append({
                        "student_id": st["id"],
                        "usn": st_usn,
                        "student_name": st_name,
                        "department_code": st.get("department_code", ""),
                        "current_semester": st_sem,
                        "mark_id": 0,
                        "subject_code": subject_code,
                        "subject_name": subj_name,
                        "internal_1": 0.00,
                        "internal_2": 0.00,
                        "assignment": 0.00,
                        "semester_exam": 0.00,
                        "total_marks": 0.00,
                        "grade": "F",
                        "status": "PASS",
                    })

            return results

    def save_mark(self, mark_data: Dict[str, Any]) -> int:
        """Saves or updates a student's marks."""
        student_id = mark_data["student_id"]
        subj_code = mark_data["subject_code"]
        subj_name = mark_data.get("subject_name", subj_code)
        sem = mark_data.get("semester", 1)
        i1 = float(mark_data.get("internal_1", 0.0))
        i2 = float(mark_data.get("internal_2", 0.0))
        asgn = float(mark_data.get("assignment", 0.0))
        exam = float(mark_data.get("semester_exam", 0.0))
        total = float(mark_data.get("total_marks", 0.0))
        grade = mark_data.get("grade", "F")
        status = mark_data.get("status", "PASS")
        rec_user_id = mark_data.get("recorded_by_user_id", 1)

        sql = """
            INSERT INTO student_marks 
                (student_id, subject_code, subject_name, semester, internal_1, internal_2, assignment, semester_exam, total_marks, grade, status, recorded_by_user_id)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (student_id, subject_code, semester) DO UPDATE SET
                subject_name = EXCLUDED.subject_name,
                internal_1 = EXCLUDED.internal_1,
                internal_2 = EXCLUDED.internal_2,
                assignment = EXCLUDED.assignment,
                semester_exam = EXCLUDED.semester_exam,
                total_marks = EXCLUDED.total_marks,
                grade = EXCLUDED.grade,
                status = EXCLUDED.status,
                recorded_by_user_id = EXCLUDED.recorded_by_user_id,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id;
        """

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (student_id, subj_code, subj_name, sem, i1, i2, asgn, exam, total, grade, status, rec_user_id))
            row = cursor.fetchone()
            last_id = row[0] if row else getattr(cursor, "lastrowid", 1)
            conn.commit()
            cursor.close()
            conn.close()
            return last_id
        except Exception as exc:
            logger.debug(f"DB save_mark unavailable, using fallback: {exc}")
            # Update in-memory
            for m in DEMO_STUDENT_MARKS:
                if m["student_id"] == student_id and m["subject_code"] == subj_code:
                    m.update({
                        "internal_1": i1,
                        "internal_2": i2,
                        "assignment": asgn,
                        "semester_exam": exam,
                        "total_marks": total,
                        "grade": grade,
                        "status": status,
                        "recorded_by_user_id": rec_user_id,
                    })
                    return m.get("id", 1)

            new_id = max([m.get("id", 0) for m in DEMO_STUDENT_MARKS], default=0) + 1
            st_info = next((s for s in DEMO_STUDENTS if s["id"] == student_id), {})
            DEMO_STUDENT_MARKS.append({
                "id": new_id,
                "student_id": student_id,
                "usn": st_info.get("usn", ""),
                "student_name": st_info.get("full_name", ""),
                "subject_code": subj_code,
                "subject_name": subj_name,
                "semester": sem,
                "internal_1": i1,
                "internal_2": i2,
                "assignment": asgn,
                "semester_exam": exam,
                "total_marks": total,
                "grade": grade,
                "status": status,
                "recorded_by_user_id": rec_user_id,
            })
            return new_id


student_marks_repository = StudentMarksRepository()
