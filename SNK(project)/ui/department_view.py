"""
PySide6 Department Management View Component
Presents department listing table, search filter, and Add/Edit Department modal forms.
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
    QDialog,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QMessageBox,
    QGroupBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from services.department_service import department_service
from services.faculty_service import faculty_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger

logger = get_logger("ui.department_view")


class DepartmentDialog(QDialog):
    """Modal Form Dialog for Adding/Editing Department."""

    def __init__(self, parent=None, dept_data=None):
        super().__init__(parent)
        self.dept_data = dept_data
        self.setWindowTitle("Edit Department" if dept_data else "Add New Department")
        self.setMinimumSize(420, 320)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("e.g. MCA, CSE, IT")

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Department of Computer Applications")

        # HOD Dropdown
        self.cmb_hod = QComboBox()
        self.cmb_hod.addItem("-- Unassigned --", None)
        all_fac = faculty_service.list_faculty(auth_service.current_user)
        for f in all_fac:
            self.cmb_hod.addItem(f"{f['full_name']} ({f['employee_code']})", f["id"])

        # Status Dropdown
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["ACTIVE", "INACTIVE"])

        if self.dept_data:
            self.txt_code.setText(self.dept_data.get("code", ""))
            self.txt_name.setText(self.dept_data.get("name", ""))
            current_hod = self.dept_data.get("hod_faculty_id")
            if current_hod:
                idx = self.cmb_hod.findData(current_hod)
                if idx >= 0:
                    self.cmb_hod.setCurrentIndex(idx)
            self.cmb_status.setCurrentText(self.dept_data.get("status", "ACTIVE"))

        form_layout.addRow(QLabel("<b>Department Code:</b>"), self.txt_code)
        form_layout.addRow(QLabel("<b>Department Name:</b>"), self.txt_name)
        form_layout.addRow(QLabel("<b>Head of Department (HOD):</b>"), self.cmb_hod)
        form_layout.addRow(QLabel("<b>Status:</b>"), self.cmb_status)

        layout.addLayout(form_layout)

        # Buttons
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #6c757d; color: white;")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Department")
        btn_save.clicked.connect(self._handle_save)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _handle_save(self):
        code = self.txt_code.text().strip().upper()
        name = self.txt_name.text().strip()
        hod_id = self.cmb_hod.currentData()
        status = self.cmb_status.currentText()

        try:
            user = auth_service.current_user
            dept_payload = {
                "code": code,
                "name": name,
                "hod_faculty_id": hod_id,
                "status": status,
            }
            if self.dept_data:
                department_service.update_department(user, self.dept_data["id"], dept_payload)
                QMessageBox.information(self, "Success", f"Department '{code}' updated successfully.")
            else:
                department_service.create_department(user, dept_payload)
                QMessageBox.information(self, "Success", f"Department '{code}' created successfully.")

            self.accept()
        except (ValidationError, BusinessLogicError) as exc:
            QMessageBox.warning(self, "Validation Error", exc.message)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save department: {exc}")


class DepartmentView(QWidget):
    """Primary PySide6 Department Management View Panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_departments()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Top Control Bar
        control_card = QGroupBox("Department Management Controls")
        control_layout = QHBoxLayout(control_card)

        self.btn_add_dept = QPushButton("+ Add Department")
        self.btn_add_dept.clicked.connect(self._show_add_dialog)

        self.btn_edit_dept = QPushButton("Edit Selected")
        self.btn_edit_dept.setStyleSheet("background-color: #6c757d; color: white;")
        self.btn_edit_dept.clicked.connect(self._show_edit_dialog)

        self.btn_refresh = QPushButton("Refresh Table")
        self.btn_refresh.setStyleSheet("background-color: #17a2b8; color: white;")
        self.btn_refresh.clicked.connect(self.load_departments)

        control_layout.addWidget(self.btn_add_dept)
        control_layout.addWidget(self.btn_edit_dept)
        control_layout.addStretch(1)
        control_layout.addWidget(self.btn_refresh)

        layout.addWidget(control_card)

        # Data Table
        self.tbl_departments = QTableWidget()
        self.tbl_departments.setColumnCount(6)
        self.tbl_departments.setHorizontalHeaderLabels(
            ["ID", "Code", "Department Name", "Head of Department (HOD)", "Faculty Count", "Status"]
        )
        self.tbl_departments.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_departments.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_departments.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_departments.setAlternatingRowColors(True)
        self.tbl_departments.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_departments.verticalHeader().setDefaultSectionSize(38)

        layout.addWidget(self.tbl_departments, stretch=1)

    def load_departments(self):
        """Fetches and displays department list."""
        depts = department_service.list_departments()
        self.tbl_departments.setRowCount(len(depts))

        for row_idx, d in enumerate(depts):
            self.tbl_departments.setItem(row_idx, 0, QTableWidgetItem(str(d["id"])))
            self.tbl_departments.setItem(row_idx, 1, QTableWidgetItem(d["code"]))
            self.tbl_departments.setItem(row_idx, 2, QTableWidgetItem(d["name"]))
            self.tbl_departments.setItem(row_idx, 3, QTableWidgetItem(d.get("hod_name", "Unassigned")))
            self.tbl_departments.setItem(row_idx, 4, QTableWidgetItem(str(d.get("faculty_count", 0))))

            status_item = QTableWidgetItem(d.get("status", "ACTIVE"))
            if d.get("status") == "ACTIVE":
                status_item.setForeground(QColor("#2e7d32"))
            else:
                status_item.setForeground(QColor("#c62828"))
            self.tbl_departments.setItem(row_idx, 5, status_item)

    def _show_add_dialog(self):
        """Opens dialog to add a department."""
        dlg = DepartmentDialog(self)
        if dlg.exec():
            self.load_departments()

    def _show_edit_dialog(self):
        """Opens dialog to edit selected department."""
        selected_rows = self.tbl_departments.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please select a department from the table to edit.")
            return

        dept_id = int(self.tbl_departments.item(selected_rows[0].row(), 0).text())
        dept_data = department_service.get_department(dept_id)

        if dept_data:
            dlg = DepartmentDialog(self, dept_data=dept_data)
            if dlg.exec():
                self.load_departments()
