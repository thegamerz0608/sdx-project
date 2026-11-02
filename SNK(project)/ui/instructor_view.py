"""
Lab Instructor Management View Component
PySide6 UI for Admin CRUD operations on Lab Instructors, including profile images,
department assignments, and lab specialization.
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

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
    QHeaderView,
    QDialog,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QMessageBox,
    QGroupBox,
    QFileDialog,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.instructor_service import instructor_service
from services.department_service import department_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger
from ui.avatar_utils import create_circular_avatar
from ui.empty_state import EmptyStateWidget
from ui.styles import style_table_cell_badge

logger = get_logger("ui.instructor_view")


class InstructorDialog(QDialog):
    """Modal Form Dialog for Registering and Editing Lab Instructors."""

    def __init__(self, parent=None, instructor_data=None):
        super().__init__(parent)
        self.instructor_data = instructor_data
        self.selected_image_path = (
            instructor_data.get("profile_image_path", "") if instructor_data else ""
        )
        self.setWindowTitle(
            "Edit Lab Instructor" if instructor_data else "Register New Lab Instructor"
        )
        self.setMinimumSize(520, 560)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Avatar Preview and Selector Card
        avatar_box = QHBoxLayout()
        self.lbl_avatar_preview = QLabel()
        self.lbl_avatar_preview.setFixedSize(64, 64)
        self._update_avatar_preview()
        avatar_box.addWidget(self.lbl_avatar_preview)

        v_avatar_btns = QVBoxLayout()
        lbl_avatar_hint = QLabel("<b>Profile Picture</b><br><small style='color: #64748B;'>Select a PNG, JPG, or JPEG file</small>")
        btn_select_img = QPushButton("📁 Choose Photo...")
        btn_select_img.setStyleSheet("background-color: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; padding: 5px 12px;")
        btn_select_img.clicked.connect(self._browse_image)

        v_avatar_btns.addWidget(lbl_avatar_hint)
        v_avatar_btns.addWidget(btn_select_img)
        avatar_box.addLayout(v_avatar_btns)
        avatar_box.addStretch()
        layout.addLayout(avatar_box)

        # Form fields
        form = QFormLayout()
        form.setSpacing(10)

        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("e.g. INS002")

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. inst_suresh")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Enter login password (min 6 chars)")

        self.txt_first_name = QLineEdit()
        self.txt_first_name.setPlaceholderText("First Name")

        self.txt_last_name = QLineEdit()
        self.txt_last_name.setPlaceholderText("Last Name")

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("instructor@erp.edu")

        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("10-digit Phone Number")

        self.cmb_dept = QComboBox()
        depts = department_service.list_departments()
        for d in depts:
            self.cmb_dept.addItem(f"{d['name']} ({d['code']})", d["id"])

        self.txt_specialization = QLineEdit()
        self.txt_specialization.setPlaceholderText("e.g. Database & Cloud Lab")
        self.txt_specialization.setText("Computer Laboratory")

        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["ACTIVE", "INACTIVE"])

        if self.instructor_data:
            self.txt_code.setText(self.instructor_data.get("instructor_code", ""))
            self.txt_code.setEnabled(False)
            self.txt_username.setText(self.instructor_data.get("username", ""))
            self.txt_username.setEnabled(False)
            self.txt_password.setEnabled(False)
            self.txt_password.setPlaceholderText("(Unchanged)")

            self.txt_first_name.setText(self.instructor_data.get("first_name", ""))
            self.txt_last_name.setText(self.instructor_data.get("last_name", ""))
            self.txt_email.setText(self.instructor_data.get("email", ""))
            self.txt_phone.setText(self.instructor_data.get("phone", ""))
            self.txt_specialization.setText(
                self.instructor_data.get("lab_specialization", "Computer Laboratory")
            )

            idx = self.cmb_dept.findData(self.instructor_data.get("department_id"))
            if idx >= 0:
                self.cmb_dept.setCurrentIndex(idx)
            self.cmb_status.setCurrentText(self.instructor_data.get("status", "ACTIVE"))

        form.addRow(QLabel("<b>Instructor Code:</b>"), self.txt_code)
        form.addRow(QLabel("<b>Username:</b>"), self.txt_username)
        if not self.instructor_data:
            form.addRow(QLabel("<b>Password:</b>"), self.txt_password)
        form.addRow(QLabel("<b>First Name:</b>"), self.txt_first_name)
        form.addRow(QLabel("<b>Last Name:</b>"), self.txt_last_name)
        form.addRow(QLabel("<b>Email:</b>"), self.txt_email)
        form.addRow(QLabel("<b>Phone:</b>"), self.txt_phone)
        form.addRow(QLabel("<b>Department:</b>"), self.cmb_dept)
        form.addRow(QLabel("<b>Lab Specialization:</b>"), self.txt_specialization)
        if self.instructor_data:
            form.addRow(QLabel("<b>Status:</b>"), self.cmb_status)

        layout.addLayout(form)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #64748B; color: white; padding: 7px 16px;")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Instructor Profile")
        btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 7px 18px;")
        btn_save.clicked.connect(self._handle_save)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _update_avatar_preview(self):
        name = f"{self.txt_first_name.text() if hasattr(self, 'txt_first_name') else ''} {self.txt_last_name.text() if hasattr(self, 'txt_last_name') else ''}".strip() or "Lab Instructor"
        pix = create_circular_avatar(
            image_path=self.selected_image_path,
            size=64,
            name=name,
            role="LAB_INSTRUCTOR",
        )
        self.lbl_avatar_preview.setPixmap(pix)

    def _browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            # Copy file to uploads/avatars with timestamped name
            dest_dir = BASE_DIR / "uploads" / "avatars"
            dest_dir.mkdir(parents=True, exist_ok=True)
            code = self.txt_code.text().strip().lower() or "inst"
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
        dept_id = self.cmb_dept.currentData()

        payload = {
            "instructor_code": self.txt_code.text().strip().upper(),
            "username": self.txt_username.text().strip().lower(),
            "first_name": self.txt_first_name.text().strip(),
            "last_name": self.txt_last_name.text().strip(),
            "email": self.txt_email.text().strip().lower(),
            "phone": self.txt_phone.text().strip(),
            "department_id": dept_id,
            "lab_specialization": self.txt_specialization.text().strip(),
            "profile_image_path": self.selected_image_path,
            "status": self.cmb_status.currentText() if self.instructor_data else "ACTIVE",
        }

        try:
            if not self.instructor_data:
                payload["password"] = self.txt_password.text().strip()
                instructor_service.create_instructor(user, payload)
                QMessageBox.information(self, "Success", "Lab Instructor registered successfully.")
            else:
                instructor_service.update_instructor(user, self.instructor_data["id"], payload)
                QMessageBox.information(self, "Success", "Lab Instructor profile updated successfully.")
            self.accept()
        except (ValidationError, BusinessLogicError) as err:
            QMessageBox.warning(self, "Validation Warning", str(err))
        except Exception as exc:
            QMessageBox.critical(self, "System Error", f"Failed to save profile: {exc}")


class InstructorManagementWidget(QWidget):
    """
    Main View Component for Lab Instructor Management.
    Enables Administrators to Add, Update, and Remove Lab Instructors with avatar support.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Banner Card
        banner = QFrame()
        banner.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #334155); "
            "border-radius: 8px; padding: 14px;"
        )
        b_layout = QHBoxLayout(banner)
        v_title = QVBoxLayout()
        title = QLabel("🔬 Lab Instructor Administration")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        subtitle = QLabel("Manage laboratory personnel profiles, lab specializations, and profile avatars")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 11px;")
        v_title.addWidget(title)
        v_title.addWidget(subtitle)
        b_layout.addLayout(v_title)
        b_layout.addStretch()

        self.btn_add = QPushButton("➕ Add Lab Instructor")
        self.btn_add.setFixedHeight(34)
        self.btn_add.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 0 16px; border-radius: 6px;")
        self.btn_add.clicked.connect(self._on_add)
        b_layout.addWidget(self.btn_add)

        layout.addWidget(banner)

        # Filter & Search Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by instructor code, name, or email...")
        self.txt_search.setMinimumWidth(220)
        self.txt_search.setMaximumWidth(360)
        self.txt_search.textChanged.connect(self.load_instructors)
        toolbar.addWidget(self.txt_search)

        self.cmb_dept_filter = QComboBox()
        self.cmb_dept_filter.addItem("All Departments", None)
        self.cmb_dept_filter.setMinimumWidth(160)
        self.cmb_dept_filter.setMaximumWidth(240)
        depts = department_service.list_departments()
        for d in depts:
            self.cmb_dept_filter.addItem(f"{d['name']} ({d['code']})", d["id"])
        self.cmb_dept_filter.currentIndexChanged.connect(self.load_instructors)
        toolbar.addWidget(self.cmb_dept_filter)
        toolbar.addStretch(1)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.load_instructors)
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        # Instructors Table
        self.tbl_instructors = QTableWidget()
        self.tbl_instructors.setColumnCount(8)
        self.tbl_instructors.setHorizontalHeaderLabels([
            "Photo", "Code", "Full Name", "Department", "Lab Specialization", "Email", "Phone", "Status"
        ])
        header = self.tbl_instructors.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_instructors.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_instructors.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_instructors.setAlternatingRowColors(True)
        self.tbl_instructors.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_instructors.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.tbl_instructors, stretch=1)

        # Modern Empty State Placeholder
        self.empty_state = EmptyStateWidget(
            icon="🔬",
            title="No Lab Instructors Found",
            message="No lab instructor profiles match the active search filter. Click below to add an instructor.",
            action_text="+ Add Lab Instructor",
            action_callback=self._on_add,
        )
        layout.addWidget(self.empty_state, stretch=1)
        self.empty_state.hide()

        # Action bar at bottom
        action_bar = QHBoxLayout()
        self.lbl_count = QLabel("Total Instructors: 0")
        self.lbl_count.setStyleSheet("color: #64748B; font-weight: bold;")
        action_bar.addWidget(self.lbl_count)
        action_bar.addStretch()

        self.btn_edit = QPushButton("✏️ Edit Selected")
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete = QPushButton("🗑️ Deactivate / Remove")
        self.btn_delete.setStyleSheet("background-color: #DC2626; color: white;")
        self.btn_delete.clicked.connect(self._on_delete)

        action_bar.addWidget(self.btn_edit)
        action_bar.addWidget(self.btn_delete)
        layout.addLayout(action_bar)

        self.load_instructors()

    def load_instructors(self):
        """Loads and populates instructors table with circular photo avatars."""
        user = auth_service.current_user
        dept_id = self.cmb_dept_filter.currentData()
        search = self.txt_search.text().strip()

        instructors = instructor_service.list_instructors(
            user_session=user,
            department_id_filter=dept_id,
            search_term=search,
        )

        self.tbl_instructors.setRowCount(0)

        if len(instructors) == 0:
            self.tbl_instructors.hide()
            if hasattr(self, "empty_state"):
                self.empty_state.show()
        else:
            if hasattr(self, "empty_state"):
                self.empty_state.hide()
            self.tbl_instructors.show()

        for row, inst in enumerate(instructors):
            self.tbl_instructors.insertRow(row)

            # Avatar cell
            avatar_lbl = QLabel()
            avatar_lbl.setAlignment(Qt.AlignCenter)
            pix = create_circular_avatar(
                image_path=inst.get("profile_image_path"),
                size=36,
                name=inst.get("full_name", "Lab Instructor"),
                role="LAB_INSTRUCTOR",
            )
            avatar_lbl.setPixmap(pix)
            self.tbl_instructors.setCellWidget(row, 0, avatar_lbl)

            code_item = QTableWidgetItem(inst.get("instructor_code", ""))
            code_item.setData(Qt.UserRole, inst.get("id"))
            self.tbl_instructors.setItem(row, 1, code_item)

            name_item = QTableWidgetItem(inst.get("full_name", ""))
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.tbl_instructors.setItem(row, 2, name_item)

            dept_item = QTableWidgetItem(inst.get("department_code", ""))
            self.tbl_instructors.setItem(row, 3, dept_item)

            spec_item = QTableWidgetItem(inst.get("lab_specialization", "Computer Laboratory"))
            self.tbl_instructors.setItem(row, 4, spec_item)

            email_item = QTableWidgetItem(inst.get("email", ""))
            self.tbl_instructors.setItem(row, 5, email_item)

            phone_item = QTableWidgetItem(inst.get("phone", "") or "—")
            self.tbl_instructors.setItem(row, 6, phone_item)

            status_str = inst.get("status", "ACTIVE")
            status_item = QTableWidgetItem(status_str)
            style_table_cell_badge(status_item, status_str)
            self.tbl_instructors.setItem(row, 7, status_item)

        self.lbl_count.setText(f"Total Instructors: {len(instructors)}")

        # Enforce RBAC permissions
        is_admin = user and user.is_admin()
        self.btn_add.setEnabled(bool(is_admin))
        self.btn_edit.setEnabled(bool(is_admin))
        self.btn_delete.setEnabled(bool(is_admin))

    def _get_selected_instructor_id(self):
        selected_rows = self.tbl_instructors.selectedItems()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.tbl_instructors.item(row, 1)
        return item.data(Qt.UserRole) if item else None

    def _on_add(self):
        dlg = InstructorDialog(self)
        if dlg.exec():
            self.load_instructors()

    def _on_edit(self):
        inst_id = self._get_selected_instructor_id()
        if not inst_id:
            QMessageBox.warning(self, "Selection Required", "Please select a lab instructor from the table to edit.")
            return

        inst = instructor_service.get_instructor(auth_service.current_user, inst_id)
        if not inst:
            QMessageBox.warning(self, "Error", "Selected instructor not found.")
            return

        dlg = InstructorDialog(self, instructor_data=inst)
        if dlg.exec():
            self.load_instructors()

    def _on_delete(self):
        inst_id = self._get_selected_instructor_id()
        if not inst_id:
            QMessageBox.warning(self, "Selection Required", "Please select a lab instructor from the table to deactivate.")
            return

        inst = instructor_service.get_instructor(auth_service.current_user, inst_id)
        if not inst:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deactivation",
            f"Are you sure you want to deactivate lab instructor '{inst['instructor_code']}' ({inst['full_name']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            instructor_service.delete_instructor(auth_service.current_user, inst_id)
            self.load_instructors()
            QMessageBox.information(self, "Deactivated", f"Lab Instructor '{inst['instructor_code']}' deactivated.")
