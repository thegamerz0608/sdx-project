"""
Student Marks Entry & Evaluation View
Modern PySide6 interface for course instructors, faculty, HODs, and administrators to
input student marks, calculate VTU grades in real-time, save mark ledgers, and export PDF mark sheets.
"""
import os
import subprocess
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QScrollArea, QSizePolicy
)

from services.student_marks_service import student_marks_service
from services.auth_service import auth_service
from utils.logger import get_logger

logger = get_logger("ui.student_marks_view")


class StudentMarksView(QWidget):
    """Modern, de-congested student marks entry and evaluation view."""

    marks_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("studentMarksView")
        self.service = student_marks_service
        self._current_records = []
        self._is_loading = False

        self._init_ui()
        self.load_subjects()
        self.load_marks()

    def _init_ui(self):
        # Outer scroll area wrapper to prevent monitor height clipping
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("marksScrollArea")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Header Banner
        header_card = QFrame()
        header_card.setObjectName("cardFrame")
        header_card.setStyleSheet(
            "#cardFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1B365D, stop:1 #0077B6); "
            "border-radius: 8px; padding: 12px; }"
        )
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.setSpacing(4)

        lbl_title = QLabel("🎓 Student Marks Evaluation & Grade Sheet Entry")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        lbl_subtitle = QLabel(
            "Global faculty marks register: evaluate internal assessments, assignments, semester exams, "
            "compute real-time VTU grades, and generate official PDF mark sheets."
        )
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #E0E1DD;")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_subtitle)
        layout.addWidget(header_card)

        # 2. Controls & Subject Selection Card
        control_card = QFrame()
        control_card.setObjectName("controlCard")
        control_card.setStyleSheet(
            "#controlCard { background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 14px; }"
        )
        c_layout = QGridLayout(control_card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setHorizontalSpacing(16)
        c_layout.setVerticalSpacing(10)

        # Subject Selector
        c_layout.addWidget(QLabel("Select Course / Subject:"), 0, 0)
        self.combo_subject = QComboBox()
        self.combo_subject.setMinimumWidth(260)
        self.combo_subject.setFixedHeight(34)
        c_layout.addWidget(self.combo_subject, 0, 1)

        # Semester Selector
        c_layout.addWidget(QLabel("Semester:"), 0, 2)
        self.combo_semester = QComboBox()
        self.combo_semester.setFixedHeight(34)
        for sem in range(1, 7):
            self.combo_semester.addItem(f"Semester {sem}", sem)
        c_layout.addWidget(self.combo_semester, 0, 3)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_load = QPushButton("🔄 Refresh Ledger")
        self.btn_load.setFixedHeight(34)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.setStyleSheet(
            "background-color: #ECEFF1; color: #263238; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        self.btn_load.clicked.connect(self.load_marks)
        btn_box.addWidget(self.btn_load)

        self.btn_save = QPushButton("💾 Save All Marks")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(
            "background-color: #2E7D32; color: #FFFFFF; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        self.btn_save.clicked.connect(self.save_all_marks)
        btn_box.addWidget(self.btn_save)

        self.btn_pdf = QPushButton("📄 Download Report (PDF)")
        self.btn_pdf.setFixedHeight(34)
        self.btn_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_pdf.setStyleSheet(
            "background-color: #0288D1; color: #FFFFFF; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        self.btn_pdf.clicked.connect(self.download_pdf_report)
        btn_box.addWidget(self.btn_pdf)

        c_layout.addLayout(btn_box, 0, 4)
        layout.addWidget(control_card)

        # 3. KPI Statistics Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.card_enrolled = self._create_kpi_card("Enrolled Students", "0", "#1B365D")
        self.card_avg = self._create_kpi_card("Class Average", "0.0 / 100", "#0077B6")
        self.card_pass_rate = self._create_kpi_card("Pass Rate", "0.0%", "#2E7D32")
        self.card_highest = self._create_kpi_card("Highest Marks", "0.0", "#D84315")

        kpi_row.addWidget(self.card_enrolled)
        kpi_row.addWidget(self.card_avg)
        kpi_row.addWidget(self.card_pass_rate)
        kpi_row.addWidget(self.card_highest)
        layout.addLayout(kpi_row)

        # 4. Student Marks Table
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_card.setStyleSheet(
            "#tableCard { background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 10px; }"
        )
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "USN", "Student Name", "IA-1 (25)", "IA-2 (25)", "Asgn (10)", "Exam (40)", "Total (100)", "Grade", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 9):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.table.setAlternatingRowColors(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setStyleSheet(
            "QTableWidget { gridline-color: #ECEFF1; font-size: 11.5px; } "
            "QHeaderView::section { background-color: #1B365D; color: #FFFFFF; font-weight: bold; padding: 6px; }"
        )
        self.table.itemChanged.connect(self._on_table_item_changed)
        t_layout.addWidget(self.table)
        layout.addWidget(table_card)

        # Connect Combo Change
        self.combo_subject.currentIndexChanged.connect(self.load_marks)
        self.combo_semester.currentIndexChanged.connect(self.load_marks)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def _create_kpi_card(self, title: str, value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(68)
        card.setStyleSheet(
            f"QFrame {{ background: #FFFFFF; border-left: 4px solid {color_hex}; "
            f"border-top: 1px solid #CFD8DC; border-right: 1px solid #CFD8DC; border-bottom: 1px solid #CFD8DC; "
            f"border-radius: 6px; padding: 6px 12px; }}"
        )
        l = QVBoxLayout(card)
        l.setContentsMargins(6, 4, 6, 4)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; color: #546E7A; font-weight: bold; text-transform: uppercase;")
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color_hex};")
        lbl_v.setObjectName("kpiVal")

        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return card

    def load_subjects(self):
        """Loads available subjects into the dropdown."""
        self.combo_subject.blockSignals(True)
        self.combo_subject.clear()
        subjects = self.service.get_subjects()
        for s in subjects:
            self.combo_subject.addItem(f"{s['code']} — {s['name']} ({s['department_code']})", s["code"])
        self.combo_subject.blockSignals(False)

    def load_marks(self):
        """Fetches and populates student marks for selected subject and semester."""
        if self.combo_subject.count() == 0:
            return

        subject_code = self.combo_subject.currentData()
        semester = self.combo_semester.currentData() or 1

        self._is_loading = True
        self._current_records = self.service.get_marks_for_subject(subject_code, semester=semester)

        self.table.setRowCount(len(self._current_records))
        total_students = len(self._current_records)
        sum_total = 0.0
        pass_count = 0
        max_score = 0.0

        for row_idx, r in enumerate(self._current_records):
            # USN (Read-Only)
            it_usn = QTableWidgetItem(r.get("usn", ""))
            it_usn.setFlags(it_usn.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 0, it_usn)

            # Name (Read-Only)
            it_name = QTableWidgetItem(r.get("student_name", ""))
            it_name.setFlags(it_name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 1, it_name)

            # Editable Marks: IA1, IA2, Assignment, Exam
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{float(r.get('internal_1', 0)):.1f}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{float(r.get('internal_2', 0)):.1f}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"{float(r.get('assignment', 0)):.1f}"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(f"{float(r.get('semester_exam', 0)):.1f}"))

            tot = float(r.get("total_marks", 0))
            sum_total += tot
            max_score = max(max_score, tot)
            if r.get("status") == "PASS" and tot > 0:
                pass_count += 1

            # Total (Calculated, Read-Only)
            it_tot = QTableWidgetItem(f"{tot:.1f}")
            it_tot.setFlags(it_tot.flags() & ~Qt.ItemIsEditable)
            it_tot.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 6, it_tot)

            # Grade Badge
            it_grd = QTableWidgetItem(r.get("grade", "F"))
            it_grd.setFlags(it_grd.flags() & ~Qt.ItemIsEditable)
            it_grd.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 7, it_grd)

            # Status Badge
            st_text = r.get("status", "PASS")
            it_st = QTableWidgetItem(st_text)
            it_st.setFlags(it_st.flags() & ~Qt.ItemIsEditable)
            it_st.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 8, it_st)

        self._is_loading = False

        # Update KPIs
        self._update_kpi_cards(total_students, sum_total, pass_count, max_score)

    def _update_kpi_cards(self, total: int, sum_tot: float, passed: int, highest: float):
        self.card_enrolled.findChild(QLabel, "kpiVal").setText(str(total))
        avg = round(sum_tot / total, 1) if total > 0 else 0.0
        self.card_avg.findChild(QLabel, "kpiVal").setText(f"{avg} / 100")
        pct = round((passed / total) * 100, 1) if total > 0 else 0.0
        self.card_pass_rate.findChild(QLabel, "kpiVal").setText(f"{pct}%")
        self.card_highest.findChild(QLabel, "kpiVal").setText(f"{highest:.1f}")

    def _on_table_item_changed(self, item: QTableWidgetItem):
        """Recalculates total, grade, and status dynamically upon keystroke editing."""
        if self._is_loading:
            return

        col = item.column()
        if col in (2, 3, 4, 5):  # IA1, IA2, Assignment, Exam
            row = item.row()
            try:
                i1 = float(self.table.item(row, 2).text().strip() or "0")
                i2 = float(self.table.item(row, 3).text().strip() or "0")
                asgn = float(self.table.item(row, 4).text().strip() or "0")
                exam = float(self.table.item(row, 5).text().strip() or "0")

                total, grade, status = self.service.calculate_grade_and_status(i1, i2, asgn, exam)

                self._is_loading = True
                self.table.item(row, 6).setText(f"{total:.1f}")
                self.table.item(row, 7).setText(grade)
                self.table.item(row, 8).setText(status)
                self._is_loading = False

                # Update in-memory record
                if row < len(self._current_records):
                    self._current_records[row].update({
                        "internal_1": i1,
                        "internal_2": i2,
                        "assignment": asgn,
                        "semester_exam": exam,
                        "total_marks": total,
                        "grade": grade,
                        "status": status,
                    })

            except ValueError:
                pass

    def save_all_marks(self):
        """Saves all marks for current subject into repository/database."""
        if not self._current_records:
            QMessageBox.information(self, "No Records", "No student mark records to save.")
            return

        subject_code = self.combo_subject.currentData()
        semester = self.combo_semester.currentData() or 1
        user_id = auth_service.current_user.user_id if auth_service.current_user else 1

        payload_list = []
        for row in range(self.table.rowCount()):
            try:
                st_id = self._current_records[row]["student_id"]
                i1 = float(self.table.item(row, 2).text().strip() or "0")
                i2 = float(self.table.item(row, 3).text().strip() or "0")
                asgn = float(self.table.item(row, 4).text().strip() or "0")
                exam = float(self.table.item(row, 5).text().strip() or "0")
                payload_list.append({
                    "student_id": st_id,
                    "subject_code": subject_code,
                    "semester": semester,
                    "internal_1": i1,
                    "internal_2": i2,
                    "assignment": asgn,
                    "semester_exam": exam,
                })
            except Exception as e:
                logger.warning(f"Error parsing row {row}: {e}")

        saved = self.service.save_marks(payload_list, recorded_by_user_id=user_id)
        QMessageBox.information(
            self,
            "Marks Saved",
            f"Successfully updated marks and grades for {saved} students in course {subject_code}."
        )
        self.marks_updated.emit()
        self.load_marks()

    def download_pdf_report(self):
        """Generates and opens the official PDF mark sheet report."""
        subject_code = self.combo_subject.currentData()
        semester = self.combo_semester.currentData() or 1

        try:
            pdf_path = self.service.generate_marksheet_pdf(subject_code=subject_code, semester=semester)
            reply = QMessageBox.information(
                self,
                "PDF Mark Sheet Generated",
                f"Official Mark Sheet successfully compiled:\n\n{pdf_path}\n\nWould you like to open it now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes and os.path.exists(pdf_path):
                os.startfile(pdf_path)
        except Exception as exc:
            logger.error(f"Failed to generate marksheet PDF: {exc}")
            QMessageBox.critical(self, "Generation Error", f"Could not generate mark sheet PDF: {exc}")
