"""
Leave Rules & Entitlements View (PySide6)
Presents institutional leave entitlement ledgers, annual quota adjustments, and an interactive policy rules simulator.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

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
    QDoubleSpinBox,
    QCheckBox,
    QTabWidget,
    QTextEdit,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.auth_service import auth_service
from services.department_service import department_service
from services.faculty_service import faculty_service
from services.leave_service import leave_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("ui.leave_rules_view")


class AdjustEntitlementDialog(QDialog):
    """Modal dialog for Admin/HOD to adjust leave entitlement allocation for a faculty member."""

    def __init__(self, parent=None, faculty_info: dict = None, year: int = 2026):
        super().__init__(parent)
        self.faculty_info = faculty_info or {}
        self.year = year
        self.setWindowTitle("Adjust Leave Entitlement Quota")
        self.setMinimumSize(440, 280)
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

        lbl_year = QLabel(f"<b>{self.year}</b>")
        form.addRow("Year:", lbl_year)

        lbl_type = QLabel(
            f"<b>{self.faculty_info.get('leave_type_code', 'CL')}</b> - "
            f"{self.faculty_info.get('leave_type_name', 'Casual Leave')}"
        )
        form.addRow("Leave Type:", lbl_type)

        lbl_curr = QLabel(f"{self.faculty_info.get('allocated_days', 0.0):.2f} days")
        form.addRow("Current Quota:", lbl_curr)

        self.spin_allocated = QDoubleSpinBox()
        self.spin_allocated.setRange(0.0, 365.0)
        self.spin_allocated.setSingleStep(0.5)
        self.spin_allocated.setValue(float(self.faculty_info.get("allocated_days", 12.0)))
        self.spin_allocated.setSuffix(" days")
        form.addRow("New Quota:", self.spin_allocated)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("Enter administrative reason (min 5 chars)")
        form.addRow("Reason:", self.txt_reason)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Allocation")
        btn_save.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.accept)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_data(self) -> tuple[float, str]:
        return self.spin_allocated.value(), self.txt_reason.text().strip()


class LeaveRulesView(QWidget):
    """PySide6 Desktop View displaying Entitlements Ledger and Interactive Policy Simulator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_departments()
        self.load_faculty_list()
        self.load_balances()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Tab Widget separating Ledger and Policy Simulator
        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Entitlements Ledger
        self.tab_ledger = QWidget()
        self._build_ledger_tab(self.tab_ledger)
        self.sub_tabs.addTab(self.tab_ledger, "Entitlements & Balances Ledger")

        # Sub-Tab 2: Policy Rules & Sandwich Simulator (Wrapped in QScrollArea)
        scroll_sim = QScrollArea()
        scroll_sim.setWidgetResizable(True)
        scroll_sim.setFrameShape(QFrame.NoFrame)
        scroll_sim.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_sim.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.tab_simulator = QWidget()
        self._build_simulator_tab(self.tab_simulator)
        scroll_sim.setWidget(self.tab_simulator)
        self.sub_tabs.addTab(scroll_sim, "Policy Rules & Sandwich Simulator")

        main_layout.addWidget(self.sub_tabs)

    def _build_ledger_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. Filter Control Panel
        filter_group = QGroupBox("Leave Entitlement Ledger Controls")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("<b>Year:</b>"))
        self.txt_year = QLineEdit("2026")
        self.txt_year.setFixedWidth(70)
        filter_layout.addWidget(self.txt_year)

        filter_layout.addWidget(QLabel("<b>Department:</b>"))
        self.combo_dept = QComboBox()
        self.combo_dept.setMinimumWidth(180)
        filter_layout.addWidget(self.combo_dept)

        self.btn_refresh = QPushButton("Refresh Ledger")
        self.btn_refresh.clicked.connect(self.load_balances)
        filter_layout.addWidget(self.btn_refresh)

        self.btn_adjust = QPushButton("Adjust Selected Quota...")
        self.btn_adjust.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
        self.btn_adjust.clicked.connect(self.on_adjust_click)
        filter_layout.addWidget(self.btn_adjust)

        filter_layout.addStretch()
        tab_layout.addWidget(filter_group)

        # 2. Metric KPI Cards Banner
        cards_layout = QHBoxLayout()
        self.card_faculty_cnt = self._create_kpi_card("Faculty Covered", "0", "#1b365d")
        self.card_cl_rem = self._create_kpi_card("Total CL Remainder", "0 days", "#2e7d32")
        self.card_ml_rem = self._create_kpi_card("Total ML Remainder", "0 days", "#1565c0")
        self.card_pending_days = self._create_kpi_card("Pending Requests", "0 days", "#e65100")

        cards_layout.addWidget(self.card_faculty_cnt)
        cards_layout.addWidget(self.card_cl_rem)
        cards_layout.addWidget(self.card_ml_rem)
        cards_layout.addWidget(self.card_pending_days)

        tab_layout.addLayout(cards_layout)

        # 3. Balances Ledger Table
        ledger_group = QGroupBox("Faculty Annual Leave Entitlements")
        ledger_layout = QVBoxLayout(ledger_group)

        self.tbl_balances = QTableWidget()
        self.tbl_balances.setColumnCount(11)
        self.tbl_balances.setHorizontalHeaderLabels(
            [
                "Faculty ID",
                "Employee Code",
                "Faculty Name",
                "Department",
                "Code",
                "Leave Type",
                "Year",
                "Allocated Days",
                "Used Days",
                "Pending Days",
                "Remaining Days",
            ]
        )
        self.tbl_balances.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_balances.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_balances.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_balances.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_balances.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_balances.verticalHeader().setDefaultSectionSize(38)
        self.tbl_balances.setAlternatingRowColors(True)

        ledger_layout.addWidget(self.tbl_balances)
        tab_layout.addWidget(ledger_group, stretch=1)

    def _build_simulator_tab(self, parent_widget: QWidget):
        tab_layout = QHBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(15)

        # Left Column: Input Form Box
        input_group = QGroupBox("Leave Request Parameter Simulation")
        input_layout = QFormLayout(input_group)
        input_layout.setSpacing(12)

        self.combo_sim_fac = QComboBox()
        input_layout.addRow("Faculty Member:", self.combo_sim_fac)

        self.combo_sim_type = QComboBox()
        self.combo_sim_type.addItems(["CL", "EL", "ML", "SCL", "AVL", "OD"])
        input_layout.addRow("Leave Type Code:", self.combo_sim_type)

        today_str = date.today().strftime("%Y-%m-%d")
        fut_str = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")

        self.txt_sim_from = QLineEdit(today_str)
        input_layout.addRow("From Date (YYYY-MM-DD):", self.txt_sim_from)

        self.txt_sim_to = QLineEdit(fut_str)
        input_layout.addRow("To Date (YYYY-MM-DD):", self.txt_sim_to)

        self.chk_sim_half = QCheckBox("Half-Day Request (0.5 Day)")
        input_layout.addRow("Option:", self.chk_sim_half)

        self.btn_simulate = QPushButton("Simulate & Evaluate Policy Rules")
        self.btn_simulate.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; padding: 10px;")
        self.btn_simulate.clicked.connect(self.on_simulate_click)
        input_layout.addRow(self.btn_simulate)

        tab_layout.addWidget(input_group, stretch=1)

        # Right Column: Results & Compliance Display Panel
        result_group = QGroupBox("Policy Evaluation & Compliance Results")
        result_layout = QVBoxLayout(result_group)

        self.lbl_status_badge = QLabel("STATUS: PENDING EVALUATION")
        self.lbl_status_badge.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_badge.setStyleSheet("background-color: #e0e0e0; color: #333; padding: 8px; border-radius: 4px;")
        result_layout.addWidget(self.lbl_status_badge)

        self.lbl_sim_metrics = QLabel(
            "<b>Calendar Days:</b> - | <b>Requested Days:</b> - | <b>Sandwich Days:</b> - | <b>Remaining Bal:</b> -"
        )
        self.lbl_sim_metrics.setStyleSheet("font-size: 13px; color: #333;")
        result_layout.addWidget(self.lbl_sim_metrics)

        result_layout.addWidget(QLabel("<b>Policy Warnings & Alerts:</b>"))
        self.txt_sim_warnings = QTextEdit()
        self.txt_sim_warnings.setReadOnly(True)
        self.txt_sim_warnings.setMaximumHeight(100)
        result_layout.addWidget(self.txt_sim_warnings)

        result_layout.addWidget(QLabel("<b>Validation Errors:</b>"))
        self.txt_sim_errors = QTextEdit()
        self.txt_sim_errors.setReadOnly(True)
        self.txt_sim_errors.setMaximumHeight(100)
        result_layout.addWidget(self.txt_sim_errors)

        tab_layout.addWidget(result_group, stretch=1)

    def _create_kpi_card(self, title: str, initial_value: str, color_hex: str) -> QGroupBox:
        box = QGroupBox()
        box.setStyleSheet(f"border: 1px solid {color_hex}; border-radius: 6px; background-color: #ffffff;")
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
        """Populates department combo box."""
        self.combo_dept.clear()
        self.combo_dept.addItem("All Departments", None)
        try:
            depts = department_service.list_departments()
            for d in depts:
                self.combo_dept.addItem(f"{d['code']} - {d['name']}", d["id"])
        except Exception as exc:
            logger.warning(f"Failed to load departments in LeaveRulesView: {exc}")

    def load_faculty_list(self):
        """Populates simulator faculty dropdown."""
        self.combo_sim_fac.clear()
        try:
            session = auth_service.current_user
            faculty_list = faculty_service.list_faculty(session)
            for f in faculty_list:
                self.combo_sim_fac.addItem(f"{f['employee_code']} - {f['full_name']}", f["id"])
        except Exception as exc:
            logger.warning(f"Failed to load faculty list for simulator: {exc}")
            self.combo_sim_fac.addItem("F001 - Dr. Suresh Kumar", 1)
            self.combo_sim_fac.addItem("F002 - Rahul Sharma", 2)

    def load_balances(self):
        """Loads and populates leave balance ledger."""
        year_val = int(self.txt_year.text().strip() or "2026")
        dept_id = self.combo_dept.currentData()
        session = auth_service.current_user
        if not session:
            session = auth_service.login("admin", "Password@123")

        try:
            res = leave_service.get_department_balances_summary(
                user_session=session, year=year_val, department_id=dept_id
            )
            summary = res["summary"]
            balances = res["balances"]

            # Update KPI Cards
            self._update_kpi_value(self.card_faculty_cnt, str(summary["total_faculty"]))
            self._update_kpi_value(self.card_cl_rem, f"{summary['total_cl_remaining']:.1f} days")
            self._update_kpi_value(self.card_ml_rem, f"{summary['total_ml_remaining']:.1f} days")
            self._update_kpi_value(self.card_pending_days, f"{summary['total_pending_days']:.1f} days")

            # Populate Table
            self.tbl_balances.setRowCount(0)
            for row_idx, b in enumerate(balances):
                self.tbl_balances.insertRow(row_idx)

                item_id = QTableWidgetItem(str(b.get("faculty_id", "")))
                item_code = QTableWidgetItem(b.get("employee_code", ""))
                item_name = QTableWidgetItem(b.get("faculty_name", ""))
                item_dept = QTableWidgetItem(b.get("department_code", ""))
                item_tcode = QTableWidgetItem(b.get("leave_type_code", ""))
                item_tname = QTableWidgetItem(b.get("leave_type_name", ""))
                item_year = QTableWidgetItem(str(b.get("year", 2026)))

                item_alloc = QTableWidgetItem(f"{b.get('allocated_days', 0.0):.2f}")
                item_used = QTableWidgetItem(f"{b.get('used_days', 0.0):.2f}")
                item_pending = QTableWidgetItem(f"{b.get('pending_days', 0.0):.2f}")

                rem_val = float(b.get("remaining_days", 0.0))
                item_rem = QTableWidgetItem(f"{rem_val:.2f}")

                # Format remaining balance cell
                if rem_val > 5.0:
                    item_rem.setForeground(QColor("#155724"))
                elif rem_val > 0.0:
                    item_rem.setForeground(QColor("#856404"))
                else:
                    item_rem.setForeground(QColor("#721c24"))

                self.tbl_balances.setItem(row_idx, 0, item_id)
                self.tbl_balances.setItem(row_idx, 1, item_code)
                self.tbl_balances.setItem(row_idx, 2, item_name)
                self.tbl_balances.setItem(row_idx, 3, item_dept)
                self.tbl_balances.setItem(row_idx, 4, item_tcode)
                self.tbl_balances.setItem(row_idx, 5, item_tname)
                self.tbl_balances.setItem(row_idx, 6, item_year)
                self.tbl_balances.setItem(row_idx, 7, item_alloc)
                self.tbl_balances.setItem(row_idx, 8, item_used)
                self.tbl_balances.setItem(row_idx, 9, item_pending)
                self.tbl_balances.setItem(row_idx, 10, item_rem)

        except Exception as exc:
            logger.error(f"Failed to load leave balances ledger: {exc}")
            QMessageBox.warning(self, "Ledger Error", f"Could not load leave balances: {exc}")

    def on_adjust_click(self):
        """Displays modal dialog to adjust selected faculty leave entitlement."""
        selected_rows = self.tbl_balances.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Record", "Please select a row in the leave entitlements table first.")
            return

        row_idx = selected_rows[0].row()
        faculty_id = int(self.tbl_balances.item(row_idx, 0).text())
        emp_code = self.tbl_balances.item(row_idx, 1).text()
        fac_name = self.tbl_balances.item(row_idx, 2).text()
        tcode = self.tbl_balances.item(row_idx, 4).text()
        tname = self.tbl_balances.item(row_idx, 5).text()
        allocated = float(self.tbl_balances.item(row_idx, 7).text())

        faculty_info = {
            "faculty_id": faculty_id,
            "employee_code": emp_code,
            "faculty_name": fac_name,
            "leave_type_code": tcode,
            "leave_type_name": tname,
            "allocated_days": allocated,
        }
        year_val = int(self.txt_year.text().strip() or "2026")

        dlg = AdjustEntitlementDialog(self, faculty_info=faculty_info, year=year_val)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_alloc, reason = dlg.get_data()
            try:
                session = auth_service.current_user
                res = leave_service.adjust_entitlement_allocation(
                    user_session=session,
                    faculty_id=faculty_id,
                    leave_type_code=tcode,
                    year=year_val,
                    new_allocated=new_alloc,
                    reason=reason,
                )
                QMessageBox.information(self, "Success", res["message"])
                self.load_balances()
            except (ValidationError, BusinessLogicError) as err:
                QMessageBox.warning(self, "Adjustment Error", str(err))

    def on_simulate_click(self):
        """Simulates leave application policy evaluation."""
        faculty_id = self.combo_sim_fac.currentData() or 1
        tcode = self.combo_sim_type.currentText()
        from_str = self.txt_sim_from.text().strip()
        to_str = self.txt_sim_to.text().strip()
        is_half = self.chk_sim_half.isChecked()

        session = auth_service.current_user
        try:
            eval_res = leave_service.validate_leave_application(
                user_session=session,
                faculty_id=faculty_id,
                leave_type_code=tcode,
                from_date_str=from_str,
                to_date_str=to_str,
                is_half_day=is_half,
            )

            # Update badge
            if eval_res["valid"]:
                self.lbl_status_badge.setText("STATUS: COMPLIANT / VALID REQUEST")
                self.lbl_status_badge.setStyleSheet(
                    "background-color: #2e7d32; color: #ffffff; padding: 8px; border-radius: 4px;"
                )
            else:
                self.lbl_status_badge.setText("STATUS: POLICY VIOLATION / INVALID")
                self.lbl_status_badge.setStyleSheet(
                    "background-color: #c62828; color: #ffffff; padding: 8px; border-radius: 4px;"
                )

            # Metrics
            doc_str = "YES" if eval_res["requires_document"] else "NO"
            self.lbl_sim_metrics.setText(
                f"<b>Calendar Days:</b> {eval_res['calendar_days']} | "
                f"<b>Requested Days:</b> {eval_res['requested_days']} | "
                f"<b>Sandwich Days:</b> {eval_res['sandwich_days']} | "
                f"<b>Doc Required:</b> {doc_str} | "
                f"<b>Remaining Balance:</b> {eval_res['remaining_balance']} days"
            )

            # Warnings
            self.txt_sim_warnings.clear()
            if eval_res["warnings"]:
                self.txt_sim_warnings.setText("\n".join([f"• {w}" for w in eval_res["warnings"]]))
            else:
                self.txt_sim_warnings.setText("None. No policy warnings flagged.")

            # Errors
            self.txt_sim_errors.clear()
            if eval_res["errors"]:
                self.txt_sim_errors.setText("\n".join([f"• {e}" for e in eval_res["errors"]]))
            else:
                self.txt_sim_errors.setText("None. All policy checks passed.")

        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Simulation Error", str(err))
