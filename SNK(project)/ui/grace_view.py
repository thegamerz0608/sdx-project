"""
Grace & Policy Engine View (PySide6)
Displays monthly grace minute ledgers, summary metric cards, exhaustion warnings, and administrative allowance override tools.
"""
import sys
from pathlib import Path

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
    QSpinBox,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.auth_service import auth_service
from services.department_service import department_service
from services.grace_service import grace_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger
from ui.styles import style_table_cell_badge

logger = get_logger("ui.grace_view")


class AdjustAllowanceDialog(QDialog):
    """Modal dialog for Admin/HOD to adjust monthly grace allowance for a faculty member."""

    def __init__(self, parent=None, faculty_info: dict = None, month_year: str = "2026-09"):
        super().__init__(parent)
        self.faculty_info = faculty_info or {}
        self.month_year = month_year
        self.setWindowTitle("Adjust Grace Allowance Quota")
        self.setMinimumSize(420, 260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        form = QFormLayout()

        lbl_faculty = QLabel(
            f"<b>{self.faculty_info.get('faculty_name', 'N/A')}</b> "
            f"({self.faculty_info.get('employee_code', 'N/A')})"
        )
        form.addRow("Faculty:", lbl_faculty)

        lbl_month = QLabel(f"<b>{self.month_year}</b>")
        form.addRow("Month:", lbl_month)

        lbl_current = QLabel(f"{self.faculty_info.get('allowed_minutes', 45)} minutes")
        form.addRow("Current Allowed:", lbl_current)

        self.spin_allowed = QSpinBox()
        self.spin_allowed.setRange(0, 300)
        self.spin_allowed.setValue(int(self.faculty_info.get("allowed_minutes", 45)))
        self.spin_allowed.setSuffix(" mins")
        form.addRow("New Allowed Quota:", self.spin_allowed)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("Enter administrative reason (min 5 chars)")
        form.addRow("Reason:", self.txt_reason)

        layout.addLayout(form)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Adjustment")
        btn_save.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.accept)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_data(self) -> tuple[int, str]:
        return self.spin_allowed.value(), self.txt_reason.text().strip()


class GraceView(QWidget):
    """PySide6 Desktop Tab View presenting Grace Minute Ledger and Policy Dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_departments()
        self.load_ledger()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. Filter Control Panel Bar
        filter_group = QGroupBox("Grace Ledger & Month Controls")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("<b>Month-Year:</b>"))
        self.txt_month = QLineEdit("2026-09")
        self.txt_month.setFixedWidth(80)
        filter_layout.addWidget(self.txt_month)

        filter_layout.addWidget(QLabel("<b>Department:</b>"))
        self.combo_dept = QComboBox()
        self.combo_dept.setMinimumWidth(180)
        filter_layout.addWidget(self.combo_dept)

        self.btn_refresh = QPushButton("Refresh Ledger")
        self.btn_refresh.clicked.connect(self.load_ledger)
        filter_layout.addWidget(self.btn_refresh)

        self.btn_allocate = QPushButton("Allocate Monthly Grace")
        self.btn_allocate.setStyleSheet("background-color: #2b579a; color: white;")
        self.btn_allocate.clicked.connect(self.on_allocate_click)
        filter_layout.addWidget(self.btn_allocate)

        self.btn_adjust = QPushButton("Adjust Allowance...")
        self.btn_adjust.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
        self.btn_adjust.clicked.connect(self.on_adjust_click)
        filter_layout.addWidget(self.btn_adjust)

        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        # 2. Metric KPI Cards Banner
        cards_layout = QHBoxLayout()

        self.card_total_fac = self._create_kpi_card("Faculty Covered", "0", "#1b365d")
        self.card_total_allowed = self._create_kpi_card("Total Allowed", "0 mins", "#2e7d32")
        self.card_total_used = self._create_kpi_card("Total Used", "0 mins", "#e65100")
        self.card_violations = self._create_kpi_card("Exhausted / Warnings", "0", "#c62828")

        cards_layout.addWidget(self.card_total_fac)
        cards_layout.addWidget(self.card_total_allowed)
        cards_layout.addWidget(self.card_total_used)
        cards_layout.addWidget(self.card_violations)

        main_layout.addLayout(cards_layout)

        # 3. Monthly Grace Ledger Table Group
        ledger_group = QGroupBox("Faculty Monthly Grace Ledger")
        ledger_layout = QVBoxLayout(ledger_group)

        self.tbl_ledger = QTableWidget()
        self.tbl_ledger.setColumnCount(9)
        self.tbl_ledger.setHorizontalHeaderLabels(
            [
                "Faculty ID",
                "Employee Code",
                "Faculty Name",
                "Department",
                "Month-Year",
                "Allowed Mins",
                "Used Mins",
                "Remaining Mins",
                "Exhaustion Status",
            ]
        )
        self.tbl_ledger.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_ledger.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_ledger.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_ledger.setAlternatingRowColors(True)
        self.tbl_ledger.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_ledger.verticalHeader().setDefaultSectionSize(38)

        ledger_layout.addWidget(self.tbl_ledger)
        main_layout.addWidget(ledger_group, stretch=1)

    def _create_kpi_card(self, title: str, initial_value: str, color_hex: str) -> QGroupBox:
        box = QGroupBox()
        box.setStyleSheet(
            f"border: 1px solid {color_hex}; border-radius: 6px; background-color: #ffffff;"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 9))
        lbl_t.setStyleSheet("color: #666666;")

        lbl_v = QLabel(initial_value)
        lbl_v.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {color_hex};")
        lbl_v.setObjectName("value_label")

        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return box

    def _update_kpi_value(self, card_box: QGroupBox, new_text: str):
        lbl = card_box.findChild(QLabel, "value_label")
        if lbl:
            lbl.setText(new_text)

    def load_departments(self):
        """Populates department filter combo box."""
        self.combo_dept.clear()
        self.combo_dept.addItem("All Departments", None)
        try:
            depts = department_service.list_departments()
            for d in depts:
                self.combo_dept.addItem(f"{d['code']} - {d['name']}", d["id"])
        except Exception as exc:
            logger.warning(f"Failed to load departments in GraceView: {exc}")

    def load_ledger(self):
        """Loads and populates monthly grace ledger data."""
        month_yr = self.txt_month.text().strip() or "2026-09"
        dept_id = self.combo_dept.currentData()
        session = auth_service.current_user
        if not session:
            session = auth_service.login("admin", "Password@123")

        try:
            res = grace_service.get_department_grace_summary(
                user_session=session, month_year=month_yr, department_id=dept_id
            )
            summary = res["summary"]
            ledger = res["ledger"]

            # Update KPI cards
            self._update_kpi_value(self.card_total_fac, str(summary["total_faculty"]))
            self._update_kpi_value(self.card_total_allowed, f"{summary['total_allowed']} mins")
            self._update_kpi_value(self.card_total_used, f"{summary['total_used']} mins")
            self._update_kpi_value(
                self.card_violations,
                f"{summary['exhausted_count']} Exh / {summary['warning_count']} Warn",
            )

            # Populate Table
            self.tbl_ledger.setRowCount(0)
            for row_idx, r in enumerate(ledger):
                self.tbl_ledger.insertRow(row_idx)

                item_id = QTableWidgetItem(str(r.get("faculty_id", "")))
                item_code = QTableWidgetItem(r.get("employee_code", ""))
                item_name = QTableWidgetItem(r.get("faculty_name", ""))
                item_dept = QTableWidgetItem(r.get("department_code", ""))
                item_month = QTableWidgetItem(r.get("month_year", ""))
                item_allowed = QTableWidgetItem(str(r.get("allowed_minutes", 45)))
                item_used = QTableWidgetItem(str(r.get("used_minutes", 0)))

                rem_val = r.get("remaining_minutes", 0)
                item_rem = QTableWidgetItem(str(rem_val))

                status_str = r.get("status", "NORMAL")
                item_status = QTableWidgetItem(status_str)
                style_table_cell_badge(item_status, status_str)

                self.tbl_ledger.setItem(row_idx, 0, item_id)
                self.tbl_ledger.setItem(row_idx, 1, item_code)
                self.tbl_ledger.setItem(row_idx, 2, item_name)
                self.tbl_ledger.setItem(row_idx, 3, item_dept)
                self.tbl_ledger.setItem(row_idx, 4, item_month)
                self.tbl_ledger.setItem(row_idx, 5, item_allowed)
                self.tbl_ledger.setItem(row_idx, 6, item_used)
                self.tbl_ledger.setItem(row_idx, 7, item_rem)
                self.tbl_ledger.setItem(row_idx, 8, item_status)

        except Exception as exc:
            logger.error(f"Failed to load grace ledger: {exc}")
            QMessageBox.warning(self, "Ledger Error", f"Could not load grace ledger: {exc}")

    def on_allocate_click(self):
        """Triggers monthly grace allocation for all active faculty."""
        month_yr = self.txt_month.text().strip() or "2026-09"
        session = auth_service.current_user
        try:
            count = grace_service.ensure_monthly_allocations(session, month_yr)
            QMessageBox.information(
                self, "Allocation Success", f"Allocated 45-minute monthly grace for {count} faculty members."
            )
            self.load_ledger()
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Allocation Error", str(err))

    def on_adjust_click(self):
        """Displays modal dialog to adjust selected faculty member's grace quota."""
        selected_rows = self.tbl_ledger.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Record", "Please select a faculty row in the ledger table first.")
            return

        row_idx = selected_rows[0].row()
        faculty_id = int(self.tbl_ledger.item(row_idx, 0).text())
        emp_code = self.tbl_ledger.item(row_idx, 1).text()
        fac_name = self.tbl_ledger.item(row_idx, 2).text()
        allowed_mins = int(self.tbl_ledger.item(row_idx, 5).text())

        faculty_info = {
            "faculty_id": faculty_id,
            "employee_code": emp_code,
            "faculty_name": fac_name,
            "allowed_minutes": allowed_mins,
        }
        month_yr = self.txt_month.text().strip() or "2026-09"

        dlg = AdjustAllowanceDialog(self, faculty_info=faculty_info, month_year=month_yr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_allowed, reason = dlg.get_data()
            try:
                session = auth_service.current_user
                res = grace_service.adjust_faculty_allowance(
                    user_session=session,
                    faculty_id=faculty_id,
                    month_year=month_yr,
                    new_allowed=new_allowed,
                    reason=reason,
                )
                QMessageBox.information(self, "Success", res["message"])
                self.load_ledger()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Adjustment Error", str(err))
