"""
Substitute Recommendation & Assignment View (PySide6)
Presents intelligent candidate ranking, timetable schedule collision detection, workload balancing metrics, and substitute response workflows.
"""
import sys
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QHeaderView,
    QDialog,
    QFormLayout,
    QTabWidget,
    QTextEdit,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.auth_service import auth_service
from services.department_service import department_service
from services.faculty_service import faculty_service
from services.substitute_service import substitute_service
from utils.exceptions import ValidationError, BusinessLogicError
from ui.worker import WorkerThread, LoadingOverlay
from utils.logger import get_logger

logger = get_logger("ui.substitute_view")


class SubstituteResponseDialog(QDialog):
    """Modal dialog for candidate to accept, decline, or complete substitute duty."""

    def __init__(self, parent=None, assignment_info: dict = None, action: str = "ACCEPT"):
        super().__init__(parent)
        self.assignment_info = assignment_info or {}
        self.action = action.upper()
        self.setWindowTitle(f"Substitute Duty - {self.action.capitalize()}")
        self.setMinimumSize(440, 240)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        form = QFormLayout()

        lbl_class = QLabel(f"<b>{self.assignment_info.get('class_details', 'N/A')}</b>")
        form.addRow("Class Details:", lbl_class)

        lbl_time = QLabel(
            f"<b>{self.assignment_info.get('assignment_date')}</b> "
            f"({self.assignment_info.get('start_time')} - {self.assignment_info.get('end_time')})"
        )
        form.addRow("Date & Time:", lbl_time)

        lbl_orig = QLabel(f"{self.assignment_info.get('original_faculty_name', 'N/A')}")
        form.addRow("Covering For:", lbl_orig)

        self.txt_remarks = QLineEdit()
        self.txt_reason_ph = "Enter decline reason..." if self.action == "REJECT" else "Optional remarks..."
        self.txt_remarks.setPlaceholderText(self.txt_reason_ph)
        form.addRow("Remarks:", self.txt_remarks)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        color_hex = "#2e7d32" if self.action in ["ACCEPT", "COMPLETE"] else "#c62828"
        btn_action = QPushButton(f"Confirm {self.action.capitalize()}")
        btn_action.setStyleSheet(f"background-color: {color_hex}; color: white; font-weight: bold;")
        btn_action.clicked.connect(self.accept)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_action)
        layout.addLayout(btn_layout)

    def get_remarks(self) -> str:
        return self.txt_remarks.text().strip()


class SubstituteView(QWidget):
    """PySide6 Desktop View displaying Intelligent Substitute Recommendation Engine and Duty Roster."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._find_worker = None
        self._init_ui()
        self.overlay = LoadingOverlay(self)
        self.load_departments()
        self.load_faculty_list()
        self.load_assignments()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Intelligent Substitute Recommendation Engine
        self.tab_recommend = QWidget()
        self._build_recommend_tab(self.tab_recommend)
        self.sub_tabs.addTab(self.tab_recommend, "Find & Recommend Substitutes")

        # Sub-Tab 2: Substitute Assignments Roster & Response Center
        self.tab_roster = QWidget()
        self._build_roster_tab(self.tab_roster)
        self.sub_tabs.addTab(self.tab_roster, "Assignments Roster & Response Center")

        main_layout.addWidget(self.sub_tabs)

    def _build_recommend_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. Parameter Input Box
        param_group = QGroupBox("Lecture Session Parameters for Substitute Matching")
        param_layout = QFormLayout(param_group)

        row1 = QHBoxLayout()
        self.combo_orig_fac = QComboBox()
        self.combo_orig_fac.setMinimumWidth(200)
        row1.addWidget(QLabel("<b>Original Faculty on Leave:</b>"))
        row1.addWidget(self.combo_orig_fac)

        self.txt_leave_app_id = QLineEdit("1")
        self.txt_leave_app_id.setFixedWidth(50)
        row1.addWidget(QLabel("<b>Leave App ID:</b>"))
        row1.addWidget(self.txt_leave_app_id)

        today_str = date.today().strftime("%Y-%m-%d")
        self.txt_date = QLineEdit(today_str)
        self.txt_date.setFixedWidth(90)
        row1.addWidget(QLabel("<b>Date:</b>"))
        row1.addWidget(self.txt_date)
        row1.addStretch()

        param_layout.addRow(row1)

        row2 = QHBoxLayout()
        self.txt_start_time = QLineEdit("09:00:00")
        self.txt_start_time.setFixedWidth(75)
        row2.addWidget(QLabel("<b>Start Time:</b>"))
        row2.addWidget(self.txt_start_time)

        self.txt_end_time = QLineEdit("10:00:00")
        self.txt_end_time.setFixedWidth(75)
        row2.addWidget(QLabel("<b>End Time:</b>"))
        row2.addWidget(self.txt_end_time)

        self.txt_class_details = QLineEdit("MCA 1st Sem - Data Structures Lecture")
        row2.addWidget(QLabel("<b>Class Details:</b>"))
        row2.addWidget(self.txt_class_details, stretch=1)

        self.btn_find = QPushButton("Find Eligible Substitutes")
        self.btn_find.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_find.clicked.connect(self.on_find_substitutes_click)
        row2.addWidget(self.btn_find)

        param_layout.addRow(row2)
        tab_layout.addWidget(param_group)

        # 2. Candidate Ranking Table
        candidates_group = QGroupBox("Ranked Substitute Candidates (Schedule Collision Checked & Workload Balanced)")
        candidates_layout = QVBoxLayout(candidates_group)

        self.tbl_candidates = QTableWidget()
        self.tbl_candidates.setColumnCount(8)
        self.tbl_candidates.setHorizontalHeaderLabels(
            [
                "Rank",
                "Faculty ID",
                "Employee Code",
                "Candidate Name",
                "Department",
                "Timetable Availability",
                "Monthly Substitute Count",
                "Workload Score",
            ]
        )
        self.tbl_candidates.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_candidates.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_candidates.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_candidates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_candidates.setAlternatingRowColors(True)
        self.tbl_candidates.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_candidates.verticalHeader().setDefaultSectionSize(38)

        candidates_layout.addWidget(self.tbl_candidates)

        # Assign Candidate Button
        btn_lay = QHBoxLayout()
        self.btn_assign_selected = QPushButton("Assign Selected Candidate as Substitute")
        self.btn_assign_selected.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold; padding: 8px 16px;")
        self.btn_assign_selected.clicked.connect(self.on_assign_candidate_click)
        btn_lay.addStretch()
        btn_lay.addWidget(self.btn_assign_selected)

        candidates_layout.addLayout(btn_lay)
        tab_layout.addWidget(candidates_group, stretch=1)

    def _build_roster_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # Filter Panel
        filter_group = QGroupBox("Filter Substitute Assignments")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("<b>Status:</b>"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["ALL", "ASSIGNED", "ACCEPTED", "REJECTED", "COMPLETED"])
        filter_layout.addWidget(self.combo_status)

        filter_layout.addWidget(QLabel("<b>Department:</b>"))
        self.combo_dept = QComboBox()
        self.combo_dept.setMinimumWidth(180)
        filter_layout.addWidget(self.combo_dept)

        self.btn_refresh_roster = QPushButton("Refresh List")
        self.btn_refresh_roster.clicked.connect(self.load_assignments)
        filter_layout.addWidget(self.btn_refresh_roster)

        # Action Response Controls
        self.btn_accept_duty = QPushButton("Accept Duty...")
        self.btn_accept_duty.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        self.btn_accept_duty.clicked.connect(self.on_accept_duty_click)
        filter_layout.addWidget(self.btn_accept_duty)

        self.btn_decline_duty = QPushButton("Decline Duty...")
        self.btn_decline_duty.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
        self.btn_decline_duty.clicked.connect(self.on_decline_duty_click)
        filter_layout.addWidget(self.btn_decline_duty)

        self.btn_complete_duty = QPushButton("Mark Completed")
        self.btn_complete_duty.clicked.connect(self.on_complete_duty_click)
        filter_layout.addWidget(self.btn_complete_duty)

        filter_layout.addStretch()
        tab_layout.addWidget(filter_group)

        # Table Group
        tbl_group = QGroupBox("Substitute Duty Assignments Roster")
        tbl_layout = QVBoxLayout(tbl_group)

        self.tbl_roster = QTableWidget()
        self.tbl_roster.setColumnCount(10)
        self.tbl_roster.setHorizontalHeaderLabels(
            [
                "ID",
                "Date",
                "Time Slot",
                "Class Details",
                "Original Faculty",
                "Substitute Faculty",
                "Department",
                "Status",
                "Remarks",
                "Created At",
            ]
        )
        self.tbl_roster.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_roster.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_roster.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_roster.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_roster.setAlternatingRowColors(True)
        self.tbl_roster.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_roster.verticalHeader().setDefaultSectionSize(38)

        tbl_layout.addWidget(self.tbl_roster)
        tab_layout.addWidget(tbl_group, stretch=1)

    def load_departments(self):
        self.combo_dept.clear()
        self.combo_dept.addItem("All Departments", None)
        try:
            depts = department_service.list_departments()
            for d in depts:
                self.combo_dept.addItem(f"{d['code']} - {d['name']}", d["id"])
        except Exception as exc:
            logger.warning(f"Failed to load departments in SubstituteView: {exc}")

    def load_faculty_list(self):
        self.combo_orig_fac.clear()
        try:
            session = auth_service.current_user
            faculty_list = faculty_service.list_faculty(session)
            for f in faculty_list:
                self.combo_orig_fac.addItem(f"{f['employee_code']} - {f['full_name']}", f["id"])
        except Exception as exc:
            logger.warning(f"Failed to load faculty list: {exc}")
            self.combo_orig_fac.addItem("F002 - Rahul Sharma", 2)
            self.combo_orig_fac.addItem("F003 - Priya Verma", 3)

    def load_assignments(self):
        status_flt = self.combo_status.currentText()
        dept_id = self.combo_dept.currentData()
        session = auth_service.current_user

        try:
            assignments = substitute_service.list_substitute_assignments(
                user_session=session, department_id=dept_id, status_filter=status_flt
            )

            self.tbl_roster.setRowCount(0)
            for row_idx, sa in enumerate(assignments):
                self.tbl_roster.insertRow(row_idx)

                item_id = QTableWidgetItem(str(sa.get("id", "")))
                item_date = QTableWidgetItem(str(sa.get("assignment_date", "")))
                time_slot = f"{sa.get('start_time', '')} - {sa.get('end_time', '')}"
                item_time = QTableWidgetItem(time_slot)
                item_class = QTableWidgetItem(sa.get("class_details", ""))
                item_orig = QTableWidgetItem(sa.get("original_faculty_name", ""))
                item_sub = QTableWidgetItem(sa.get("substitute_faculty_name", ""))
                item_dept = QTableWidgetItem(sa.get("department_code", ""))

                status_str = sa.get("status", "ASSIGNED")
                item_status = QTableWidgetItem(status_str)
                item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if status_str in ["ACCEPTED", "COMPLETED"]:
                    item_status.setBackground(QColor("#d4edda"))
                    item_status.setForeground(QColor("#155724"))
                elif status_str in ["ASSIGNED", "REQUESTED"]:
                    item_status.setBackground(QColor("#fff3cd"))
                    item_status.setForeground(QColor("#856404"))
                else:  # REJECTED / CANCELLED
                    item_status.setBackground(QColor("#f8d7da"))
                    item_status.setForeground(QColor("#721c24"))

                item_remarks = QTableWidgetItem(sa.get("remarks") or "-")
                item_created = QTableWidgetItem(str(sa.get("created_at", "")))

                self.tbl_roster.setItem(row_idx, 0, item_id)
                self.tbl_roster.setItem(row_idx, 1, item_date)
                self.tbl_roster.setItem(row_idx, 2, item_time)
                self.tbl_roster.setItem(row_idx, 3, item_class)
                self.tbl_roster.setItem(row_idx, 4, item_orig)
                self.tbl_roster.setItem(row_idx, 5, item_sub)
                self.tbl_roster.setItem(row_idx, 6, item_dept)
                self.tbl_roster.setItem(row_idx, 7, item_status)
                self.tbl_roster.setItem(row_idx, 8, item_remarks)
                self.tbl_roster.setItem(row_idx, 9, item_created)

        except Exception as exc:
            logger.error(f"Failed to load substitute assignments roster: {exc}")

    def on_find_substitutes_click(self):
        orig_fac_id = self.combo_orig_fac.currentData() or 2
        ass_date = self.txt_date.text().strip()
        start_t = self.txt_start_time.text().strip()
        end_t = self.txt_end_time.text().strip()
        session = auth_service.current_user

        self.btn_find.setEnabled(False)
        self.overlay.show_message(
            "Finding Eligible Substitutes...",
            "Checking timetable schedules, active duties, and balancing workloads...",
        )

        def _do_work():
            return substitute_service.recommend_substitutes(
                user_session=session,
                original_faculty_id=orig_fac_id,
                assignment_date=ass_date,
                start_time=start_t,
                end_time=end_t,
            )

        worker = WorkerThread(_do_work)

        def _on_success(candidates):
            self.overlay.hide()
            self.btn_find.setEnabled(True)
            self._render_candidates(candidates)

        def _on_failure(err_str):
            self.overlay.hide()
            self.btn_find.setEnabled(True)
            self.overlay.show_error(
                "Recommendation Failed",
                f"Could not load substitute recommendations:\n{err_str[:120]}",
                retry_callback=self.on_find_substitutes_click,
            )

        worker.result.connect(_on_success)
        worker.error.connect(_on_failure)
        worker.start()
        self._find_worker = worker

    def _render_candidates(self, candidates):
        self.tbl_candidates.setRowCount(0)
        for row_idx, c in enumerate(candidates):
            self.tbl_candidates.insertRow(row_idx)

            item_rank = QTableWidgetItem(f"#{c.get('rank', row_idx+1)}")
            item_id = QTableWidgetItem(str(c.get("faculty_id", "")))
            item_code = QTableWidgetItem(c.get("employee_code", ""))
            item_name = QTableWidgetItem(c.get("faculty_name", ""))
            item_dept = QTableWidgetItem(c.get("department_code", ""))

            avail_str = c.get("conflict_status", "AVAILABLE")
            item_avail = QTableWidgetItem(avail_str)
            item_avail.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if c.get("is_available"):
                item_avail.setBackground(QColor("#d4edda"))
                item_avail.setForeground(QColor("#155724"))
            else:
                item_avail.setBackground(QColor("#f8d7da"))
                item_avail.setForeground(QColor("#721c24"))

            item_count = QTableWidgetItem(str(c.get("monthly_substitute_count", 0)))
            item_score = QTableWidgetItem(f"{c.get('workload_score', 100)} / 100")

            self.tbl_candidates.setItem(row_idx, 0, item_rank)
            self.tbl_candidates.setItem(row_idx, 1, item_id)
            self.tbl_candidates.setItem(row_idx, 2, item_code)
            self.tbl_candidates.setItem(row_idx, 3, item_name)
            self.tbl_candidates.setItem(row_idx, 4, item_dept)
            self.tbl_candidates.setItem(row_idx, 5, item_avail)
            self.tbl_candidates.setItem(row_idx, 6, item_count)
            self.tbl_candidates.setItem(row_idx, 7, item_score)

    def closeEvent(self, event):
        if hasattr(self, "_find_worker") and self._find_worker:
            self._find_worker.stop()
        super().closeEvent(event)

    def on_assign_candidate_click(self):
        selected_rows = self.tbl_candidates.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Candidate", "Please run recommendation search and select a candidate row first.")
            return

        row_idx = selected_rows[0].row()
        sub_fac_id = int(self.tbl_candidates.item(row_idx, 1).text())
        sub_name = self.tbl_candidates.item(row_idx, 3).text()
        avail_str = self.tbl_candidates.item(row_idx, 5).text()

        if avail_str != "AVAILABLE":
            QMessageBox.warning(self, "Collision Warning", "Cannot assign candidate with a schedule collision.")
            return

        orig_fac_id = self.combo_orig_fac.currentData() or 2
        app_id = int(self.txt_leave_app_id.text().strip() or "1")
        ass_date = self.txt_date.text().strip()
        start_t = self.txt_start_time.text().strip()
        end_t = self.txt_end_time.text().strip()
        class_det = self.txt_class_details.text().strip()

        session = auth_service.current_user
        try:
            created = substitute_service.assign_substitute(
                user_session=session,
                leave_application_id=app_id,
                original_faculty_id=orig_fac_id,
                substitute_faculty_id=sub_fac_id,
                department_id=session.department_id if session.department_id else 1,
                assignment_date=ass_date,
                start_time=start_t,
                end_time=end_t,
                class_details=class_det,
            )
            QMessageBox.information(
                self, "Assignment Created", f"Successfully assigned {sub_name} as substitute for {class_det}!"
            )
            self.load_assignments()
            self.sub_tabs.setCurrentIndex(1)
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Assignment Error", str(err))

    def on_accept_duty_click(self):
        selected_rows = self.tbl_roster.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Assignment", "Please select an assignment row in the roster table first.")
            return

        row_idx = selected_rows[0].row()
        ass_id = int(self.tbl_roster.item(row_idx, 0).text())
        info = {
            "class_details": self.tbl_roster.item(row_idx, 3).text(),
            "original_faculty_name": self.tbl_roster.item(row_idx, 4).text(),
            "assignment_date": self.tbl_roster.item(row_idx, 1).text(),
            "start_time": self.tbl_roster.item(row_idx, 2).text().split(" - ")[0],
            "end_time": self.tbl_roster.item(row_idx, 2).text().split(" - ")[-1],
        }

        dlg = SubstituteResponseDialog(self, assignment_info=info, action="ACCEPT")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            remarks = dlg.get_remarks()
            try:
                session = auth_service.current_user
                substitute_service.respond_to_assignment(session, ass_id, "ACCEPT", remarks)
                QMessageBox.information(self, "Accepted", "Substitute duty accepted successfully!")
                self.load_assignments()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Error", str(err))

    def on_decline_duty_click(self):
        selected_rows = self.tbl_roster.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Assignment", "Please select an assignment row in the roster table first.")
            return

        row_idx = selected_rows[0].row()
        ass_id = int(self.tbl_roster.item(row_idx, 0).text())
        info = {
            "class_details": self.tbl_roster.item(row_idx, 3).text(),
            "original_faculty_name": self.tbl_roster.item(row_idx, 4).text(),
            "assignment_date": self.tbl_roster.item(row_idx, 1).text(),
            "start_time": self.tbl_roster.item(row_idx, 2).text().split(" - ")[0],
            "end_time": self.tbl_roster.item(row_idx, 2).text().split(" - ")[-1],
        }

        dlg = SubstituteResponseDialog(self, assignment_info=info, action="REJECT")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            remarks = dlg.get_remarks()
            try:
                session = auth_service.current_user
                substitute_service.respond_to_assignment(session, ass_id, "REJECT", remarks)
                QMessageBox.information(self, "Declined", "Substitute duty declined.")
                self.load_assignments()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Error", str(err))

    def on_complete_duty_click(self):
        selected_rows = self.tbl_roster.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Assignment", "Please select an assignment row in the roster table first.")
            return

        row_idx = selected_rows[0].row()
        ass_id = int(self.tbl_roster.item(row_idx, 0).text())
        try:
            session = auth_service.current_user
            substitute_service.respond_to_assignment(session, ass_id, "COMPLETE", "Lecture delivered successfully.")
            QMessageBox.information(self, "Completed", "Substitute assignment marked as COMPLETED.")
            self.load_assignments()
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Error", str(err))
