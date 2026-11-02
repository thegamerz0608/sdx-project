"""
PySide6 Faculty Management View Component
Presents faculty member roster, search & department filter, RBAC department scoping, and Add/Edit Faculty forms.
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
    QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
import shutil
from datetime import datetime

from services.faculty_service import faculty_service
from services.department_service import department_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger
from ui.avatar_utils import create_circular_avatar
from ui.empty_state import EmptyStateWidget
from ui.styles import style_table_cell_badge

logger = get_logger("ui.faculty_view")


class FacultyDialog(QDialog):
    """Modal Form Dialog for Registering / Editing Faculty Profile."""

    def __init__(self, parent=None, faculty_data=None):
        super().__init__(parent)
        self.faculty_data = faculty_data
        self.selected_image_path = faculty_data.get("profile_image_path", "") if faculty_data else ""
        self.setWindowTitle("Edit Faculty Profile" if faculty_data else "Register New Faculty Member")
        self.setMinimumSize(500, 540)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Profile Picture Selection Row
        avatar_box = QHBoxLayout()
        self.lbl_avatar_preview = QLabel()
        self.lbl_avatar_preview.setFixedSize(54, 54)
        self._update_avatar_preview()
        avatar_box.addWidget(self.lbl_avatar_preview)

        v_avatar_btns = QVBoxLayout()
        lbl_hint = QLabel("<b>Profile Picture</b><br><small style='color: #64748B;'>Upload PNG, JPG, or JPEG</small>")
        btn_browse = QPushButton("📁 Choose Photo...")
        btn_browse.setStyleSheet("background-color: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; padding: 4px 10px;")
        btn_browse.clicked.connect(self._browse_image)
        v_avatar_btns.addWidget(lbl_hint)
        v_avatar_btns.addWidget(btn_browse)
        avatar_box.addLayout(v_avatar_btns)
        avatar_box.addStretch()
        layout.addLayout(avatar_box)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Employee Code & Username
        self.txt_emp_code = QLineEdit()
        self.txt_emp_code.setPlaceholderText("e.g. F005")

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. fac_samir")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Enter login password")

        # Name
        self.txt_first_name = QLineEdit()
        self.txt_first_name.setPlaceholderText("First Name")

        self.txt_last_name = QLineEdit()
        self.txt_last_name.setPlaceholderText("Last Name")

        # Email & Phone
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("email@erp.edu")

        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("Phone number")

        # Department Dropdown
        self.cmb_dept = QComboBox()
        depts = department_service.list_departments()
        for d in depts:
            self.cmb_dept.addItem(f"{d['name']} ({d['code']})", d["id"])

        # Designation & Role
        self.txt_designation = QLineEdit()
        self.txt_designation.setText("Assistant Professor")

        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["FACULTY", "HOD", "ADMIN", "LAB_INSTRUCTOR"])

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["ACTIVE", "INACTIVE", "ON_LEAVE"])

        # Lock department for HOD
        user = auth_service.current_user
        if user and user.is_hod():
            idx = self.cmb_dept.findData(user.department_id)
            if idx >= 0:
                self.cmb_dept.setCurrentIndex(idx)
            self.cmb_dept.setEnabled(False)

        if self.faculty_data:
            self.txt_emp_code.setText(self.faculty_data.get("employee_code", ""))
            self.txt_emp_code.setEnabled(False)
            self.txt_username.setText(self.faculty_data.get("username", ""))
            self.txt_username.setEnabled(False)
            self.txt_password.setEnabled(False)
            self.txt_password.setPlaceholderText("(Unchanged)")

            self.txt_first_name.setText(self.faculty_data.get("first_name", ""))
            self.txt_last_name.setText(self.faculty_data.get("last_name", ""))
            self.txt_email.setText(self.faculty_data.get("email", ""))
            self.txt_phone.setText(self.faculty_data.get("phone", ""))
            self.txt_designation.setText(self.faculty_data.get("designation", ""))

            idx = self.cmb_dept.findData(self.faculty_data.get("department_id"))
            if idx >= 0:
                self.cmb_dept.setCurrentIndex(idx)
            self.cmb_role.setCurrentText(self.faculty_data.get("role", "FACULTY"))
            self.cmb_status.setCurrentText(self.faculty_data.get("status", "ACTIVE"))

        form_layout.addRow(QLabel("<b>Employee Code:</b>"), self.txt_emp_code)
        form_layout.addRow(QLabel("<b>Username:</b>"), self.txt_username)
        if not self.faculty_data:
            form_layout.addRow(QLabel("<b>Password:</b>"), self.txt_password)
        form_layout.addRow(QLabel("<b>First Name:</b>"), self.txt_first_name)
        form_layout.addRow(QLabel("<b>Last Name:</b>"), self.txt_last_name)
        form_layout.addRow(QLabel("<b>Email:</b>"), self.txt_email)
        form_layout.addRow(QLabel("<b>Phone:</b>"), self.txt_phone)
        form_layout.addRow(QLabel("<b>Department:</b>"), self.cmb_dept)
        form_layout.addRow(QLabel("<b>Designation:</b>"), self.txt_designation)
        form_layout.addRow(QLabel("<b>System Role:</b>"), self.cmb_role)
        if self.faculty_data:
            form_layout.addRow(QLabel("<b>Status:</b>"), self.cmb_status)

        layout.addLayout(form_layout)

        # Buttons
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #6c757d; color: white;")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Profile")
        btn_save.clicked.connect(self._handle_save)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _update_avatar_preview(self):
        name = f"{self.txt_first_name.text() if hasattr(self, 'txt_first_name') else ''} {self.txt_last_name.text() if hasattr(self, 'txt_last_name') else ''}".strip() or "Faculty Member"
        role = self.cmb_role.currentText() if hasattr(self, "cmb_role") else "FACULTY"
        pix = create_circular_avatar(
            image_path=self.selected_image_path,
            size=54,
            name=name,
            role=role,
        )
        self.lbl_avatar_preview.setPixmap(pix)

    def _browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            dest_dir = BASE_DIR / "uploads" / "avatars"
            dest_dir.mkdir(parents=True, exist_ok=True)
            code = self.txt_emp_code.text().strip().lower() or "faculty"
            ext = Path(file_path).suffix or ".png"
            dest_file = dest_dir / f"{code}_{int(datetime.now().timestamp())}{ext}"
            try:
                shutil.copy2(file_path, dest_file)
                self.selected_image_path = str(dest_file.relative_to(BASE_DIR)).replace("\\", "/")
            except Exception as e:
                logger.warning(f"Could not copy avatar image, using direct path: {e}")
                self.selected_image_path = file_path

            self._update_avatar_preview()

    def _handle_save(self):
        user = auth_service.current_user
        payload = {
            "employee_code": self.txt_emp_code.text().strip().upper(),
            "username": self.txt_username.text().strip().lower(),
            "password": self.txt_password.text().strip(),
            "first_name": self.txt_first_name.text().strip(),
            "last_name": self.txt_last_name.text().strip(),
            "email": self.txt_email.text().strip().lower(),
            "phone": self.txt_phone.text().strip(),
            "department_id": self.cmb_dept.currentData(),
            "designation": self.txt_designation.text().strip(),
            "role": self.cmb_role.currentText(),
            "profile_image_path": self.selected_image_path,
            "status": self.cmb_status.currentText(),
        }

        try:
            if self.faculty_data:
                faculty_service.update_faculty(user, self.faculty_data["id"], payload)
                QMessageBox.information(self, "Success", "Faculty profile updated successfully.")
            else:
                faculty_service.create_faculty(user, payload)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Faculty member '{payload['employee_code']}' registered successfully with 2026 leave balances and grace minutes.",
                )
            self.accept()
        except (ValidationError, BusinessLogicError) as exc:
            QMessageBox.warning(self, "Validation Error", exc.message)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save faculty profile: {exc}")


class FacultyView(QWidget):
    """Primary PySide6 Faculty Management View Panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_faculty()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Control Bar
        control_card = QGroupBox("Faculty Search & Management Controls")
        control_layout = QHBoxLayout(control_card)

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by Name, Code, or Email...")
        self.txt_search.setMinimumWidth(200)
        self.txt_search.setMaximumWidth(320)
        self.txt_search.textChanged.connect(self.load_faculty)

        # Department Filter Dropdown
        self.cmb_dept_filter = QComboBox()
        self.cmb_dept_filter.setMinimumWidth(160)
        self.cmb_dept_filter.setMaximumWidth(240)
        self.cmb_dept_filter.addItem("-- All Departments --", None)
        depts = department_service.list_departments()
        for d in depts:
            self.cmb_dept_filter.addItem(f"{d['code']} - {d['name']}", d["id"])
        self.cmb_dept_filter.currentIndexChanged.connect(self.load_faculty)

        # Action Buttons
        self.btn_add_faculty = QPushButton("+ Register Faculty")
        self.btn_add_faculty.clicked.connect(self._show_add_dialog)

        self.btn_edit_faculty = QPushButton("Edit Profile")
        self.btn_edit_faculty.setStyleSheet("background-color: #6c757d; color: white;")
        self.btn_edit_faculty.clicked.connect(self._show_edit_dialog)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setStyleSheet("background-color: #17a2b8; color: white;")
        self.btn_refresh.clicked.connect(self.load_faculty)

        control_layout.addWidget(QLabel("<b>Filter Department:</b>"))
        control_layout.addWidget(self.cmb_dept_filter)
        control_layout.addWidget(QLabel("<b>Search:</b>"))
        control_layout.addWidget(self.txt_search)
        control_layout.addStretch(1)
        control_layout.addWidget(self.btn_add_faculty)
        control_layout.addWidget(self.btn_edit_faculty)
        control_layout.addWidget(self.btn_refresh)

        layout.addWidget(control_card)

        # Data Table
        self.tbl_faculty = QTableWidget()
        self.tbl_faculty.setColumnCount(9)
        self.tbl_faculty.setHorizontalHeaderLabels(
            ["ID", "Emp Code", "Full Name", "Designation", "Department", "Email", "Phone", "Role", "Status"]
        )
        self.tbl_faculty.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_faculty.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_faculty.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_faculty.setAlternatingRowColors(True)
        self.tbl_faculty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_faculty.verticalHeader().setDefaultSectionSize(38)

        layout.addWidget(self.tbl_faculty, stretch=1)

        # Modern Empty State Placeholder
        self.empty_state = EmptyStateWidget(
            icon="👨‍🏫",
            title="No Faculty Profiles Found",
            message="No faculty members match your search criteria. Click below to register a new faculty member.",
            action_text="+ Register Faculty",
            action_callback=self._show_add_dialog,
        )
        layout.addWidget(self.empty_state, stretch=1)
        self.empty_state.hide()

    def update_rbac_views(self):
        """Adjusts control availability and department filters based on current user role."""
        user = auth_service.current_user
        if user and user.is_hod():
            # Lock department filter dropdown to HOD's department
            idx = self.cmb_dept_filter.findData(user.department_id)
            if idx >= 0:
                self.cmb_dept_filter.setCurrentIndex(idx)
            self.cmb_dept_filter.setEnabled(False)
        else:
            self.cmb_dept_filter.setEnabled(True)

    def load_faculty(self):
        """Fetches and displays faculty member roster."""
        self.update_rbac_views()
        user = auth_service.current_user
        dept_id = self.cmb_dept_filter.currentData()
        search_txt = self.txt_search.text().strip()

        fac_list = faculty_service.list_faculty(user, department_id_filter=dept_id, search_term=search_txt)
        self.tbl_faculty.setRowCount(len(fac_list))

        if len(fac_list) == 0:
            self.tbl_faculty.hide()
            if hasattr(self, "empty_state"):
                self.empty_state.show()
        else:
            if hasattr(self, "empty_state"):
                self.empty_state.hide()
            self.tbl_faculty.show()

        for row_idx, f in enumerate(fac_list):
            self.tbl_faculty.setItem(row_idx, 0, QTableWidgetItem(str(f["id"])))
            self.tbl_faculty.setItem(row_idx, 1, QTableWidgetItem(f["employee_code"]))
            self.tbl_faculty.setItem(row_idx, 2, QTableWidgetItem(f["full_name"]))
            self.tbl_faculty.setItem(row_idx, 3, QTableWidgetItem(f.get("designation", "")))
            self.tbl_faculty.setItem(row_idx, 4, QTableWidgetItem(f.get("department_code", "")))
            self.tbl_faculty.setItem(row_idx, 5, QTableWidgetItem(f.get("email", "")))
            self.tbl_faculty.setItem(row_idx, 6, QTableWidgetItem(f.get("phone", "")))

            role_item = QTableWidgetItem(f.get("role", "FACULTY"))
            if f.get("role") == "ADMIN":
                role_item.setForeground(QColor("#1565c0"))
            elif f.get("role") == "HOD":
                role_item.setForeground(QColor("#6a1b9a"))
            self.tbl_faculty.setItem(row_idx, 7, role_item)

            status_str = f.get("status", "ACTIVE")
            status_item = QTableWidgetItem(status_str)
            style_table_cell_badge(status_item, status_str)
            self.tbl_faculty.setItem(row_idx, 8, status_item)

    def _show_add_dialog(self):
        """Opens dialog to register new faculty."""
        dlg = FacultyDialog(self)
        if dlg.exec():
            self.load_faculty()

    def _show_edit_dialog(self):
        """Opens dialog to edit selected faculty profile."""
        selected_rows = self.tbl_faculty.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please select a faculty member from the table to edit.")
            return

        fac_id = int(self.tbl_faculty.item(selected_rows[0].row(), 0).text())
        fac_data = faculty_service.get_faculty(auth_service.current_user, fac_id)

        if fac_data:
            dlg = FacultyDialog(self, faculty_data=fac_data)
            if dlg.exec():
                self.load_faculty()
