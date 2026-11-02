"""
PySide6 Attendance Management View Component
Presents CSV/Excel file selection, format validation, preview, invalid record reporting,
and attendance roster filtering.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Automatically ensure venv site-packages is in sys.path if present
VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QTabWidget,
    QComboBox,
    QDateEdit,
    QLineEdit,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from services.attendance_service import attendance_service
from services.department_service import department_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger
from ui.smartphone_punch_widget import SmartphonePunchWidget
from ui.empty_state import EmptyStateWidget
from ui.styles import style_table_cell_badge
from ui.worker import WorkerThread, LoadingOverlay

logger = get_logger("ui.attendance_view")


class AttendanceView(QWidget):
    """Primary PySide6 Attendance Management View Component."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_preview_report = None
        self._parse_worker = None
        self._commit_worker = None
        self._init_ui()
        self.overlay = LoadingOverlay(self)
        self.load_attendance_roster()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Tab Widget for Import vs Roster View
        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Import Attendance CSV/Excel
        self.tab_import = QWidget()
        self._build_import_tab(self.tab_import)
        self.sub_tabs.addTab(self.tab_import, "Import Attendance (CSV/Excel)")

        # Sub-Tab 2: Attendance Roster
        self.tab_roster = QWidget()
        self._build_roster_tab(self.tab_roster)
        self.sub_tabs.addTab(self.tab_roster, "Attendance Roster & History")

        # Decoupled: Biometric QR Bridge moved to standalone lobby BiometricKioskWindow
        self.tab_smartphone = None

        layout.addWidget(self.sub_tabs)

    def _build_import_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # File Picker Control Group
        file_card = QGroupBox("Select Attendance Import Source")
        file_layout = QHBoxLayout(file_card)

        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("Select CSV or Excel file (e.g. sample_attendance.csv)...")

        btn_browse = QPushButton("Browse File...")
        btn_browse.clicked.connect(self._browse_file)

        btn_sample = QPushButton("Generate Sample CSV")
        btn_sample.setStyleSheet("background-color: #17a2b8; color: white;")
        btn_sample.clicked.connect(self._generate_sample_csv)

        self.btn_parse = QPushButton("Parse & Preview")
        self.btn_parse.clicked.connect(self._parse_file)

        file_layout.addWidget(self.txt_file_path, stretch=1)
        file_layout.addWidget(btn_browse)
        file_layout.addWidget(btn_sample)
        file_layout.addWidget(self.btn_parse)

        layout.addWidget(file_card)

        # Import Summary Metrics Row
        metrics_layout = QHBoxLayout()
        self.card_found = self._create_metric_card("Records Found", "0", "#6c757d")
        self.card_valid = self._create_metric_card("Valid Records", "0", "#2e7d32")
        self.card_invalid = self._create_metric_card("Invalid Records", "0", "#c62828")
        self.card_duplicates = self._create_metric_card("Duplicates", "0", "#ff8f00")

        metrics_layout.addWidget(self.card_found)
        metrics_layout.addWidget(self.card_valid)
        metrics_layout.addWidget(self.card_invalid)
        metrics_layout.addWidget(self.card_duplicates)

        layout.addLayout(metrics_layout)

        # Sub-tabs for Valid Preview vs Invalid Error Log
        preview_tabs = QTabWidget()

        # Valid Preview Table
        self.tbl_valid = QTableWidget()
        self.tbl_valid.setColumnCount(8)
        self.tbl_valid.setHorizontalHeaderLabels(
            ["Emp Code", "Faculty Name", "Date", "Login", "Logout", "Late Mins", "Working Hours", "Status"]
        )
        self.tbl_valid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_valid.setAlternatingRowColors(True)
        self.tbl_valid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_valid.verticalHeader().setDefaultSectionSize(36)
        preview_tabs.addTab(self.tbl_valid, "Valid Records Preview")

        # Invalid Records Table
        self.tbl_invalid = QTableWidget()
        self.tbl_invalid.setColumnCount(3)
        self.tbl_invalid.setHorizontalHeaderLabels(["Row #", "Raw Line / Data", "Validation Error Reason"])
        self.tbl_invalid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_invalid.setAlternatingRowColors(True)
        self.tbl_invalid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_invalid.verticalHeader().setDefaultSectionSize(36)
        preview_tabs.addTab(self.tbl_invalid, "Invalid / Error Records Log")

        layout.addWidget(preview_tabs, stretch=1)

        # Bottom Commit Row
        commit_row = QHBoxLayout()
        self.lbl_import_status = QLabel("Select a file and click 'Parse & Preview' to validate.")
        self.lbl_import_status.setStyleSheet("color: #555; font-style: italic;")

        self.btn_commit = QPushButton("Commit Valid Records to Database")
        self.btn_commit.setEnabled(False)
        self.btn_commit.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 10px 20px;")
        self.btn_commit.clicked.connect(self._commit_import)

        commit_row.addWidget(self.lbl_import_status, stretch=1)
        commit_row.addWidget(self.btn_commit)

        layout.addLayout(commit_row)

    def _create_metric_card(self, title: str, value: str, bg_color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 6px; padding: 10px;")
        l = QVBoxLayout(frame)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_t.setStyleSheet("color: #ffffff;")

        lbl_v = QLabel(value)
        lbl_v.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_v.setStyleSheet("color: #ffffff;")

        l.addWidget(lbl_t)
        l.addWidget(lbl_v)

        frame.lbl_val = lbl_v
        return frame

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Attendance Source File", "", "Attendance Files (*.csv *.txt *.xlsx)"
        )
        if path:
            self.txt_file_path.setText(path)

    def _generate_sample_csv(self):
        try:
            path = attendance_service.generate_demo_sample()
            self.txt_file_path.setText(path)
            QMessageBox.information(
                self, "Sample Generated", f"Sample test attendance CSV generated at:\n{path}\nClick 'Parse & Preview' to test."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to generate sample CSV: {exc}")

    def _parse_file(self):
        file_path = self.txt_file_path.text().strip()
        if not file_path:
            QMessageBox.warning(self, "File Required", "Please select or enter an attendance CSV file path.")
            return

        user = auth_service.current_user
        if "pytest" in sys.modules:
            self._do_parse_sync(user, file_path)
        else:
            self._do_parse_async(user, file_path)

    def _do_parse_sync(self, user, file_path):
        try:
            report = attendance_service.parse_import_file(user, file_path)
            self._apply_parsed_report(report)
        except (ValidationError, BusinessLogicError) as exc:
            QMessageBox.warning(self, "Import Error", exc.message)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to parse attendance file: {exc}")

    def _do_parse_async(self, user, file_path):
        self.btn_parse.setEnabled(False)
        self.lbl_import_status.setText("Validating and parsing records in background...")
        self.lbl_import_status.setStyleSheet("color: #2563EB; font-style: italic;")
        self.overlay.show_message("Parsing Attendance File...", "Validating timestamps, shifts, and grace rules...")

        def _work():
            return attendance_service.parse_import_file(user, file_path)

        worker = WorkerThread(_work)

        def _on_done(report):
            self.overlay.hide()
            self.btn_parse.setEnabled(True)
            self._apply_parsed_report(report)

        def _on_err(err_str):
            self.overlay.hide()
            self.btn_parse.setEnabled(True)
            self.lbl_import_status.setText("Parsing failed.")
            self.overlay.show_error(
                "Parsing Error",
                f"Failed to parse attendance file:\n{err_str[:120]}",
                retry_callback=self._parse_file,
            )

        worker.result.connect(_on_done)
        worker.error.connect(_on_err)
        worker.start()
        self._parse_worker = worker

    def _apply_parsed_report(self, report):
        self.last_preview_report = report

        # Update Metric Cards
        self.card_found.lbl_val.setText(str(report["records_found"]))
        self.card_valid.lbl_val.setText(str(len(report["valid_records"])))
        self.card_invalid.lbl_val.setText(str(len(report["invalid_records"])))
        self.card_duplicates.lbl_val.setText(str(len(report["duplicate_records"])))

        # Populate Valid Table
        valids = report["valid_records"]
        self.tbl_valid.setRowCount(len(valids))
        for idx, r in enumerate(valids):
            self.tbl_valid.setItem(idx, 0, QTableWidgetItem(r["employee_code"]))
            self.tbl_valid.setItem(idx, 1, QTableWidgetItem(r["faculty_name"]))
            self.tbl_valid.setItem(idx, 2, QTableWidgetItem(r["attendance_date"]))
            self.tbl_valid.setItem(idx, 3, QTableWidgetItem(r["login_time"]))
            self.tbl_valid.setItem(idx, 4, QTableWidgetItem(r["logout_time"]))

            late_item = QTableWidgetItem(str(r["late_minutes"]))
            if r["late_minutes"] > 0:
                late_item.setForeground(QColor("#B45309"))
                late_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.tbl_valid.setItem(idx, 5, late_item)

            self.tbl_valid.setItem(idx, 6, QTableWidgetItem(str(r["working_hours"])))
            status_item = QTableWidgetItem(r["status"])
            style_table_cell_badge(status_item, r["status"])
            self.tbl_valid.setItem(idx, 7, status_item)

        # Populate Invalid Table
        invalids = report["invalid_records"]
        self.tbl_invalid.setRowCount(len(invalids))
        for idx, r in enumerate(invalids):
            self.tbl_invalid.setItem(idx, 0, QTableWidgetItem(str(r["row"])))
            self.tbl_invalid.setItem(idx, 1, QTableWidgetItem(r["raw"]))
            err_item = QTableWidgetItem(r["error"])
            err_item.setForeground(QColor("#DC2626"))
            self.tbl_invalid.setItem(idx, 2, err_item)

        self.lbl_import_status.setText(report["summary"])
        self.btn_commit.setEnabled(len(valids) > 0)

    def _commit_import(self):
        if not self.last_preview_report or not self.last_preview_report.get("valid_records"):
            return

        valids = self.last_preview_report["valid_records"]
        reply = QMessageBox.question(
            self,
            "Confirm Import Commitment",
            f"Are you sure you want to commit {len(valids)} valid attendance records to the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
        if reply == QMessageBox.StandardButton.Yes:
            user = auth_service.current_user
            if "pytest" in sys.modules:
                self._do_commit_sync(user, valids)
            else:
                self._do_commit_async(user, valids)

    def _do_commit_sync(self, user, valids):
        try:
            saved = attendance_service.commit_import(user, valids)
            QMessageBox.information(
                self, "Import Committed", f"Successfully saved {saved} attendance records to database."
            )
            self.btn_commit.setEnabled(False)
            self.load_attendance_roster()
            self.sub_tabs.setCurrentIndex(1)
        except Exception as exc:
            QMessageBox.critical(self, "Commit Error", f"Failed to commit attendance records: {exc}")

    def _do_commit_async(self, user, valids):
        self.btn_commit.setEnabled(False)
        self.btn_commit.setText("Committing...")
        self.overlay.show_message("Committing Records...", f"Saving {len(valids)} attendance entries to database...")

        def _work():
            return attendance_service.commit_import(user, valids)

        worker = WorkerThread(_work)

        def _on_done(saved):
            self.overlay.hide()
            self.btn_commit.setText("Commit Valid Records to Database")
            QMessageBox.information(
                self, "Import Committed", f"Successfully saved {saved} attendance records to database."
            )
            self.load_attendance_roster()
            self.sub_tabs.setCurrentIndex(1)

        def _on_err(err_str):
            self.overlay.hide()
            self.btn_commit.setEnabled(True)
            self.btn_commit.setText("Commit Valid Records to Database")
            self.overlay.show_error(
                "Commit Error",
                f"Failed to commit attendance records:\n{err_str[:120]}",
                retry_callback=lambda: self._do_commit_async(user, valids),
            )

        worker.result.connect(_on_done)
        worker.error.connect(_on_err)
        worker.start()
        self._commit_worker = worker

    def closeEvent(self, event):
        if hasattr(self, "_parse_worker") and self._parse_worker:
            self._parse_worker.stop()
        if hasattr(self, "_commit_worker") and self._commit_worker:
            self._commit_worker.stop()
        super().closeEvent(event)

    def _build_roster_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Filter Bar Card
        filter_card = QGroupBox("Filter Attendance Logs")
        filter_layout = QHBoxLayout(filter_card)

        self.cmb_dept_roster = QComboBox()
        self.cmb_dept_roster.addItem("-- All Departments --", None)
        depts = department_service.list_departments()
        for d in depts:
            self.cmb_dept_roster.addItem(f"{d['code']} - {d['name']}", d["id"])
        self.cmb_dept_roster.currentIndexChanged.connect(self.load_attendance_roster)

        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate.currentDate().addDays(-30))

        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate())

        btn_filter = QPushButton("Apply Filter")
        btn_filter.clicked.connect(self.load_attendance_roster)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("background-color: #17a2b8; color: white;")
        btn_refresh.clicked.connect(self.load_attendance_roster)

        filter_layout.addWidget(QLabel("<b>Department:</b>"))
        self.cmb_dept_roster.setMinimumWidth(160)
        self.cmb_dept_roster.setMaximumWidth(240)
        filter_layout.addWidget(self.cmb_dept_roster)

        filter_layout.addWidget(QLabel("<b>From:</b>"))
        self.dt_start.setMaximumWidth(130)
        filter_layout.addWidget(self.dt_start)

        filter_layout.addWidget(QLabel("<b>To:</b>"))
        self.dt_end.setMaximumWidth(130)
        filter_layout.addWidget(self.dt_end)
        filter_layout.addWidget(btn_filter)
        filter_layout.addStretch(1)
        filter_layout.addWidget(btn_refresh)

        layout.addWidget(filter_card)

        # Attendance Roster Table
        self.tbl_roster = QTableWidget()
        self.tbl_roster.setColumnCount(9)
        self.tbl_roster.setHorizontalHeaderLabels(
            ["Emp Code", "Faculty Name", "Dept", "Date", "Login", "Logout", "Status", "Late Mins", "Working Hrs"]
        )
        self.tbl_roster.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_roster.setAlternatingRowColors(True)
        self.tbl_roster.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_roster.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(self.tbl_roster, stretch=1)

        # Modern Empty State Container
        self.empty_state_roster = EmptyStateWidget(
            icon="📅",
            title="No Attendance Logs Found",
            message="No attendance logs found for the selected department and date range.",
            action_text="Refresh Roster",
            action_callback=self.load_attendance_roster,
        )
        layout.addWidget(self.empty_state_roster, stretch=1)
        self.empty_state_roster.hide()

    def load_attendance_roster(self):
        """Fetches and displays attendance logs in Roster tab."""
        user = auth_service.current_user
        if hasattr(self, "cmb_dept_roster"):
            dept_id = self.cmb_dept_roster.currentData()
            start_s = self.dt_start.date().toString("yyyy-MM-dd")
            end_s = self.dt_end.date().toString("yyyy-MM-dd")
        else:
            dept_id, start_s, end_s = None, None, None

        records = attendance_service.list_attendance(
            user_session=user,
            department_id=dept_id,
            start_date=start_s,
            end_date=end_s,
        )

        if hasattr(self, "tbl_roster"):
            self.tbl_roster.setRowCount(len(records))

            if len(records) == 0:
                self.tbl_roster.hide()
                if hasattr(self, "empty_state_roster"):
                    self.empty_state_roster.show()
            else:
                if hasattr(self, "empty_state_roster"):
                    self.empty_state_roster.hide()
                self.tbl_roster.show()

            for idx, r in enumerate(records):
                self.tbl_roster.setItem(idx, 0, QTableWidgetItem(r["employee_code"]))
                self.tbl_roster.setItem(idx, 1, QTableWidgetItem(r["faculty_name"]))
                self.tbl_roster.setItem(idx, 2, QTableWidgetItem(r.get("department_code", "")))
                self.tbl_roster.setItem(idx, 3, QTableWidgetItem(str(r["attendance_date"])))
                self.tbl_roster.setItem(idx, 4, QTableWidgetItem(str(r["login_time"])))
                self.tbl_roster.setItem(idx, 5, QTableWidgetItem(str(r["logout_time"])))

                status_item = QTableWidgetItem(r["status"])
                style_table_cell_badge(status_item, r["status"])
                self.tbl_roster.setItem(idx, 6, status_item)

                late_item = QTableWidgetItem(str(r["late_minutes"]))
                if r["late_minutes"] > 0:
                    late_item.setForeground(QColor("#B45309"))
                    late_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.tbl_roster.setItem(idx, 7, late_item)

                self.tbl_roster.setItem(idx, 8, QTableWidgetItem(str(r["working_hours"])))

    def _on_smartphone_punch_recorded(self, data: dict):
        """Auto-refreshes the roster when a biometric punch is registered."""
        logger.info(f"Biometric punch detected for {data.get('employee_code')}. Updating roster view.")
        self.load_attendance_roster()
