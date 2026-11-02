"""
Student Marks Service
Orchestrates marks validation, grade computation (VTU 10-point scale),
bulk persistence, and ReportLab PDF Mark Sheet compilation.
"""
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

from repositories.student_marks_repository import (
    student_marks_repository,
    StudentMarksRepository,
    DEFAULT_SUBJECTS,
)
from utils.logger import get_logger
from utils.exceptions import ValidationError

logger = get_logger("services.student_marks_service")

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas


class MarksNumberedCanvas(canvas.Canvas):
    """Adds running headers and two-pass 'Page X of Y' footers to Mark Sheets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#546E7A"))

        # Running header rule
        self.setStrokeColor(colors.HexColor("#CFD8DC"))
        self.setLineWidth(0.5)
        self.line(40, 755, 572, 755)
        self.drawString(40, 760, "A.J. INSTITUTE OF ENGINEERING & TECHNOLOGY — OFFICIAL STUDENT MARKSHEET")
        self.drawRightString(572, 760, "ACADEMIC TRANSCRIPT RECORD")

        # Running footer rule
        self.line(40, 42, 572, 42)
        ts = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        self.drawString(40, 30, f"Generated: {ts} | Confidential Institutional Evaluation Document")
        self.drawRightString(572, 30, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class StudentMarksService:
    """Service managing business rules and PDF exports for student marks."""

    def __init__(self):
        self.repo = student_marks_repository

    def get_subjects(self, department_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns registered subjects."""
        return self.repo.get_subjects(department_code)

    def calculate_grade_and_status(
        self,
        internal_1: float,
        internal_2: float,
        assignment: float,
        semester_exam: float,
    ) -> Tuple[float, str, str]:
        """
        Computes total marks (out of 100), letter grade, and PASS/FAIL status.
        Scale:
          Total >= 90: 'O'  (Outstanding)
          Total >= 80: 'A+' (Excellent)
          Total >= 70: 'A'  (Very Good)
          Total >= 60: 'B+' (Good)
          Total >= 50: 'B'  (Above Average)
          Total >= 40: 'C'  (Pass)
          Total <  40: 'F'  (Fail)
        """
        # Clamp inputs
        i1 = max(0.0, min(25.0, float(internal_1)))
        i2 = max(0.0, min(25.0, float(internal_2)))
        asgn = max(0.0, min(10.0, float(assignment)))
        exam = max(0.0, min(40.0, float(semester_exam)))

        total = round(i1 + i2 + asgn + exam, 2)

        if total >= 90.0:
            grade = "O"
            status = "PASS"
        elif total >= 80.0:
            grade = "A+"
            status = "PASS"
        elif total >= 70.0:
            grade = "A"
            status = "PASS"
        elif total >= 60.0:
            grade = "B+"
            status = "PASS"
        elif total >= 50.0:
            grade = "B"
            status = "PASS"
        elif total >= 40.0:
            grade = "C"
            status = "PASS"
        else:
            grade = "F"
            status = "FAIL"

        return total, grade, status

    def get_marks_for_subject(
        self,
        subject_code: str,
        semester: int = 1,
        department_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetches marks for subject."""
        return self.repo.get_marks_for_subject(subject_code, semester, department_id)

    def save_marks(self, marks_list: List[Dict[str, Any]], recorded_by_user_id: int = 1) -> int:
        """Validates and saves a list of marks."""
        saved_count = 0
        for item in marks_list:
            i1 = float(item.get("internal_1", 0.0))
            i2 = float(item.get("internal_2", 0.0))
            asgn = float(item.get("assignment", 0.0))
            exam = float(item.get("semester_exam", 0.0))

            total, grade, status = self.calculate_grade_and_status(i1, i2, asgn, exam)
            payload = {
                "student_id": item["student_id"],
                "subject_code": item["subject_code"],
                "subject_name": item.get("subject_name", item["subject_code"]),
                "semester": item.get("semester", 1),
                "internal_1": i1,
                "internal_2": i2,
                "assignment": asgn,
                "semester_exam": exam,
                "total_marks": total,
                "grade": grade,
                "status": status,
                "recorded_by_user_id": recorded_by_user_id,
            }
            self.repo.save_mark(payload)
            saved_count += 1

        logger.info(f"Successfully processed and saved {saved_count} student mark records.")
        return saved_count

    def generate_marksheet_pdf(
        self,
        subject_code: str,
        semester: int = 1,
        department_id: Optional[int] = None,
        output_dir: str = "reports_output",
    ) -> str:
        """
        Generates a comprehensive publication-grade PDF Mark Sheet report using ReportLab.
        Returns the absolute path to the generated PDF.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        filename = f"marksheet_{subject_code}_sem{semester}.pdf"
        file_path = out_path / filename

        # Fetch records
        records = self.get_marks_for_subject(subject_code, semester, department_id)
        subj_meta = next((s for s in DEFAULT_SUBJECTS if s["code"] == subject_code), None)
        subj_name = subj_meta["name"] if subj_meta else subject_code
        dept_code = subj_meta["department_code"] if subj_meta else "GENERAL"

        # Calculate summary metrics
        total_students = len(records)
        passed_students = sum(1 for r in records if r.get("status") == "PASS" and float(r.get("total_marks", 0)) > 0)
        failed_students = sum(1 for r in records if r.get("status") == "FAIL" and float(r.get("total_marks", 0)) > 0)
        graded_students = passed_students + failed_students
        avg_marks = (
            round(sum(float(r.get("total_marks", 0)) for r in records) / total_students, 2)
            if total_students > 0 else 0.0
        )
        highest_marks = (
            max([float(r.get("total_marks", 0)) for r in records], default=0.0)
            if total_students > 0 else 0.0
        )
        pass_pct = (
            round((passed_students / graded_students) * 100, 1)
            if graded_students > 0 else 0.0
        )

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()
        st_title = ParagraphStyle(
            "Title", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=13, leading=16,
            textColor=colors.HexColor("#1B365D"), alignment=1, spaceAfter=2
        )
        st_sub = ParagraphStyle(
            "Sub", parent=styles["Normal"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=colors.HexColor("#455A64"), alignment=1, spaceAfter=10
        )
        st_sec = ParagraphStyle(
            "Sec", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=10, leading=13,
            textColor=colors.HexColor("#1B365D"), spaceBefore=8, spaceAfter=4
        )
        st_cell = ParagraphStyle(
            "Cell", parent=styles["Normal"],
            fontName="Helvetica", fontSize=7.5, leading=10, textColor=colors.HexColor("#263238")
        )
        st_cell_b = ParagraphStyle(
            "CellB", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=colors.HexColor("#263238")
        )
        st_cell_hdr = ParagraphStyle(
            "CellHdr", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=1
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("A.J. INSTITUTE OF ENGINEERING & TECHNOLOGY, MANGALURU", st_title))
        story.append(Paragraph(f"DEPARTMENT OF {dept_code} | TABULATION REGISTER & GRADE SHEET", st_sub))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0288D1"), spaceAfter=10))

        # 2. Metadata & KPI Table
        meta_data = [
            [
                Paragraph("<b>Subject Code:</b>", st_cell), Paragraph(subject_code, st_cell_b),
                Paragraph("<b>Semester:</b>", st_cell), Paragraph(f"Semester {semester}", st_cell_b),
                Paragraph("<b>Enrolled Students:</b>", st_cell), Paragraph(str(total_students), st_cell_b),
            ],
            [
                Paragraph("<b>Subject Name:</b>", st_cell), Paragraph(subj_name, st_cell_b),
                Paragraph("<b>Class Average:</b>", st_cell), Paragraph(f"{avg_marks:.2f} / 100", st_cell_b),
                Paragraph("<b>Pass Percentage:</b>", st_cell), Paragraph(f"{pass_pct}%", st_cell_b),
            ],
            [
                Paragraph("<b>Evaluation Date:</b>", st_cell), Paragraph(datetime.now().strftime("%d-%b-%Y"), st_cell_b),
                Paragraph("<b>Highest Score:</b>", st_cell), Paragraph(f"{highest_marks:.2f} / 100", st_cell_b),
                Paragraph("<b>Pass / Fail Ratio:</b>", st_cell), Paragraph(f"{passed_students} Pass / {failed_students} Fail", st_cell_b),
            ],
        ]
        t_meta = Table(meta_data, colWidths=[80, 150, 75, 110, 85, 40])
        t_meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8DC")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ECEFF1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 10))

        # 3. Marks Tabulation Table
        story.append(Paragraph("Consolidated Student Grade Matrix", st_sec))

        table_data = [[
            Paragraph("S.No", st_cell_hdr),
            Paragraph("USN", st_cell_hdr),
            Paragraph("Student Name", st_cell_hdr),
            Paragraph("IA-1 (25)", st_cell_hdr),
            Paragraph("IA-2 (25)", st_cell_hdr),
            Paragraph("Asgn (10)", st_cell_hdr),
            Paragraph("Exam (40)", st_cell_hdr),
            Paragraph("Total (100)", st_cell_hdr),
            Paragraph("Grade", st_cell_hdr),
            Paragraph("Result", st_cell_hdr),
        ]]

        for idx, r in enumerate(records, start=1):
            tot = float(r.get("total_marks", 0))
            grd = r.get("grade", "F")
            res = r.get("status", "PASS")
            res_color = "#2E7D32" if res == "PASS" and tot > 0 else ("#C62828" if tot > 0 else "#546E7A")

            st_res = ParagraphStyle(
                f"Res_{idx}", parent=st_cell_b,
                textColor=colors.HexColor(res_color), alignment=1
            )
            st_grd = ParagraphStyle(
                f"Grd_{idx}", parent=st_cell_b,
                textColor=colors.HexColor("#1B365D"), alignment=1
            )

            table_data.append([
                Paragraph(str(idx), st_cell),
                Paragraph(r.get("usn", ""), st_cell_b),
                Paragraph(r.get("student_name", ""), st_cell),
                Paragraph(f"{float(r.get('internal_1', 0)):.1f}", st_cell),
                Paragraph(f"{float(r.get('internal_2', 0)):.1f}", st_cell),
                Paragraph(f"{float(r.get('assignment', 0)):.1f}", st_cell),
                Paragraph(f"{float(r.get('semester_exam', 0)):.1f}", st_cell),
                Paragraph(f"<b>{tot:.2f}</b>", st_cell),
                Paragraph(grd, st_grd),
                Paragraph(res if tot > 0 else "ABSENT", st_res),
            ])

        t_marks = Table(table_data, colWidths=[28, 75, 155, 45, 45, 45, 45, 50, 32, 40])
        t_marks_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B365D")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B0BEC5")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ECEFF1")),
        ]
        for row_i in range(1, len(table_data)):
            bg = "#F8F9FA" if row_i % 2 == 0 else "#FFFFFF"
            t_marks_style.append(("BACKGROUND", (0, row_i), (-1, row_i), colors.HexColor(bg)))

        t_marks.setStyle(TableStyle(t_marks_style))
        story.append(t_marks)

        # 4. Signature Block
        story.append(Spacer(1, 24))
        sig_data = [
            [
                Paragraph("<b>Course Instructor Signature</b><br/>Name: ______________________", st_cell),
                Paragraph("<b>Head of Department (HOD)</b><br/>Seal & Signature", st_cell),
                Paragraph("<b>Controller of Examinations</b><br/>Official Endorsement", st_cell),
            ]
        ]
        t_sig = Table(sig_data, colWidths=[180, 180, 180])
        t_sig.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, -1), 0.5, colors.HexColor("#90A4AE")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_sig)

        doc.build(story, canvasmaker=MarksNumberedCanvas)
        logger.info(f"Mark Sheet PDF generated successfully at: {file_path}")
        return str(file_path.resolve())


student_marks_service = StudentMarksService()
