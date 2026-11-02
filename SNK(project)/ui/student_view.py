"""
Student Management & Search View Component (PySide6)
Provides multi-field student search (USN, Name, Year, Phone), interactive student data grid,
detailed StudentProfileDialog modal, and student enrollment dialog.
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
    QFileDialog,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from services.student_service import student_service
from services.department_service import department_service
from services.auth_service import auth_service
from utils.exceptions import ValidationError, BusinessLogicError
from utils.logger import get_logger
from ui.avatar_utils import create_circular_avatar
from ui.empty_state import EmptyStateWidget
from ui.worker import WorkerThread

logger = get_logger("ui.student_view")


def _s(value, default: str = "") -> str:
    """Safely convert a possibly-None DB value to a string for Qt widgets."""
    if value is None or value == "":
        return default
    return str(value)


def _error_text(exc: Exception) -> str:
    return getattr(exc, "message", None) or str(exc)


class StudentProfileDialog(QDialog):
    """
    Modern Student Profile Card Modal Dialog.
    Features asynchronous background loading with skeleton placeholder,
    robust error handling with interactive retry, and thread lifecycle management.
    """

    def __init__(self, student_data: dict, parent=None, fetch_fn=None):
        super().__init__(parent)
        self.student = dict(student_data or {})
        self._fetch_fn = fetch_fn
        self._worker = None
        self.setWindowTitle(f"Student Profile - {_s(self.student.get('name'), 'Student')}")
        self.setMinimumSize(460, 480)
        self.setModal(True)
        self._init_ui()
        self.load_profile()

    def _init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(24, 24, 24, 24)
        self.root_layout.setSpacing(16)

        # 1. Loading Skeleton State Container
        self.skeleton_container = QFrame()
        self.skeleton_container.setObjectName("skeletonCard")
        self.skeleton_container.setStyleSheet(
            "QFrame#skeletonCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        skel_layout = QVBoxLayout(self.skeleton_container)
        skel_layout.setContentsMargins(18, 24, 18, 24)
        skel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        skel_layout.setSpacing(14)

        # Skeleton avatar placeholder
        sk_avatar = QFrame()
        sk_avatar.setFixedSize(88, 88)
        sk_avatar.setStyleSheet("background-color: #E2E8F0; border-radius: 44px;")
        skel_layout.addWidget(sk_avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Skeleton name placeholder
        sk_name = QFrame()
        sk_name.setFixedSize(220, 22)
        sk_name.setStyleSheet("background-color: #E2E8F0; border-radius: 6px;")
        skel_layout.addWidget(sk_name, alignment=Qt.AlignmentFlag.AlignCenter)

        # Skeleton USN badge
        sk_usn = QFrame()
        sk_usn.setFixedSize(140, 18)
        sk_usn.setStyleSheet("background-color: #E2E8F0; border-radius: 9px;")
        skel_layout.addWidget(sk_usn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Skeleton details frame
        sk_details = QFrame()
        sk_details.setFixedHeight(120)
        sk_details.setStyleSheet("background-color: #F8FAFC; border: 1px solid #F1F5F9; border-radius: 8px;")
        skel_layout.addWidget(sk_details)

        self.root_layout.addWidget(self.skeleton_container)

        # 2. Error Recovery State Container
        self.error_container = QFrame()
        self.error_container.setObjectName("errorCard")
        self.error_container.setStyleSheet(
            "QFrame#errorCard { background-color: #FEF2F2; border: 1px solid #FECACA; "
            "border-radius: 12px; }"
        )
        err_layout = QVBoxLayout(self.error_container)
        err_layout.setContentsMargins(20, 24, 20, 24)
        err_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_layout.setSpacing(14)

        lbl_err_icon = QLabel("⚠️")
        lbl_err_icon.setFont(QFont("Segoe UI", 32))
        lbl_err_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_layout.addWidget(lbl_err_icon)

        self.lbl_error_msg = QLabel("Failed to retrieve student profile record.")
        self.lbl_error_msg.setFont(QFont("Segoe UI", 10))
        self.lbl_error_msg.setStyleSheet("color: #991B1B; font-weight: 600; background: transparent;")
        self.lbl_error_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error_msg.setWordWrap(True)
        err_layout.addWidget(self.lbl_error_msg)

        self.btn_retry = QPushButton("🔄 Retry")
        self.btn_retry.setFixedHeight(34)
        self.btn_retry.setFixedWidth(120)
        self.btn_retry.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; border-radius: 6px; padding: 0 16px;"
        )
        self.btn_retry.clicked.connect(self.load_profile)
        err_layout.addWidget(self.btn_retry, alignment=Qt.AlignmentFlag.AlignCenter)

        self.root_layout.addWidget(self.error_container)
        self.error_container.hide()

        # 3. Content State Container
        self.content_container = QFrame()
        self.content_container.setObjectName("profileCard")
        self.content_container.setStyleSheet(
            "QFrame#profileCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        card_layout = QVBoxLayout(self.content_container)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(10)

        # Circular Avatar
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(88, 88)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Name & USN
        self.lbl_name = QLabel()
        self.lbl_name.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setWordWrap(True)
        card_layout.addWidget(self.lbl_name)

        self.lbl_usn = QLabel()
        self.lbl_usn.setStyleSheet(
            "background-color: #EFF6FF; color: #1E40AF; padding: 4px 12px; "
            "border-radius: 10px; font-weight: 700; font-size: 12px; border: none;"
        )
        card_layout.addWidget(self.lbl_usn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Details Grid
        details_box = QFrame()
        details_box.setObjectName("detailsBox")
        details_box.setStyleSheet(
            "QFrame#detailsBox { background-color: #F8FAFC; border-radius: 8px; }"
        )
        self.d_form = QFormLayout(details_box)
        self.d_form.setContentsMargins(12, 12, 12, 12)
        self.d_form.setSpacing(8)

        self.lbl_dept_val = QLabel()
        self.lbl_year_val = QLabel()
        self.lbl_phone_val = QLabel()
        self.lbl_status_val = QLabel("<span style='color: #10B981; font-weight: bold;'>ACTIVE</span>")

        self.d_form.addRow("<b>Department:</b>", self.lbl_dept_val)
        self.d_form.addRow("<b>Academic Year:</b>", self.lbl_year_val)
        self.d_form.addRow("<b>Contact Phone:</b>", self.lbl_phone_val)
        self.d_form.addRow("<b>Enrollment Status:</b>", self.lbl_status_val)

        card_layout.addWidget(details_box)
        self.root_layout.addWidget(self.content_container)
        self.content_container.hide()

        # Close button
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setFixedHeight(36)
        self.root_layout.addWidget(self.btn_close)

    def load_profile(self):
        """Asynchronously loads full student profile details with background WorkerThread."""
        self._cleanup_worker()
        self.skeleton_container.show()
        self.content_container.hide()
        self.error_container.hide()

        def _do_fetch():
            if self._fetch_fn:
                return self._fetch_fn()
            sid = self.student.get("id")
            if sid:
                user = auth_service.current_user
                return student_service.get_student_by_id(user, sid)
            return self.student

        self._worker = WorkerThread(_do_fetch)
        self._worker.result.connect(self._on_load_success)
        self._worker.error.connect(self._on_load_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_load_success(self, student_data: dict):
        if isinstance(student_data, dict):
            self.student.update(student_data)
        self._populate_data()
        self.skeleton_container.hide()
        self.error_container.hide()
        self.content_container.show()

    def _on_load_error(self, err_trace: str):
        self.skeleton_container.hide()
        self.content_container.hide()
        self.error_container.show()
        lines = [line.strip() for line in (err_trace or "").splitlines() if line.strip()]
        err_msg = lines[-1] if lines else "Failed to load student profile."
        self.lbl_error_msg.setText(f"Unable to load student record:\n{err_msg}")

    def _on_worker_finished(self):
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

    def _populate_data(self):
        name = _s(self.student.get("name"), "Student")
        self.setWindowTitle(f"Student Profile - {name}")
        pix = create_circular_avatar(
            image_path=self.student.get("profile_image_path"),
            size=88,
            name=name,
            role="STUDENT",
        )
        self.lbl_avatar.setPixmap(pix)
        self.lbl_name.setText(name)
        self.lbl_usn.setText(f"USN: {_s(self.student.get('usn'), 'N/A')}")

        dept_val = _s(self.student.get("department_name") or self.student.get("department_code"), "N/A")
        self.lbl_dept_val.setText(dept_val)
        self.lbl_year_val.setText(f"Year {_s(self.student.get('year'), '1')}")
        self.lbl_phone_val.setText(_s(self.student.get("phone_number"), "Not registered"))

    def _cleanup_worker(self):
        if self._worker:
            try:
                self._worker.result.disconnect()
                self._worker.error.disconnect()
                self._worker.finished.disconnect()
            except Exception:
                pass
            if self._worker.isRunning():
                self._worker.quit()
                self._worker.wait(300)
            self._worker.deleteLater()
            self._worker = None

    def closeEvent(self, event):
        self._cleanup_worker()
        super().closeEvent(event)

    def reject(self):
        self._cleanup_worker()
        super().reject()


class StudentFormDialog(QDialog):
    """Dialog for Enrolling / Registering a New Student."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enroll New Student")
        self.setMinimumSize(480, 500)
        self.setModal(True)
        self.selected_image_path = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Photo selection row
        photo_row = QHBoxLayout()
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(58, 58)
        self._update_preview()
        photo_row.addWidget(self.lbl_preview)

        v_btn = QVBoxLayout()
        v_btn.addWidget(
            QLabel("<b>Student Photograph</b><br><small style='color: #64748B;'>Upload PNG, JPG, or JPEG</small>")
        )
        btn_photo = QPushButton("📁 Select Picture...")
        btn_photo.setStyleSheet(
            "background-color: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; padding: 5px;"
        )
        btn_photo.clicked.connect(self._browse_photo)
        v_btn.addWidget(btn_photo)
        photo_row.addLayout(v_btn)
        photo_row.addStretch()
        layout.addLayout(photo_row)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_usn = QLineEdit()
        self.txt_usn.setPlaceholderText("e.g. 1MS23MCA099")
        form.addRow("<b>Student USN:</b>", self.txt_usn)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Full Name")
        form.addRow("<b>Full Name:</b>", self.txt_name)

        self.cmb_year = QComboBox()
        self.cmb_year.addItems(["Year 1", "Year 2", "Year 3", "Year 4"])
        form.addRow("<b>Academic Year:</b>", self.cmb_year)

        self.cmb_dept = QComboBox()
        try:
            depts = department_service.list_departments()
        except Exception as exc:
            logger.error(f"Failed to load departments: {exc}")
            depts = []
        for d in depts:
            self.cmb_dept.addItem(f"{d['name']} ({d['code']})", d["id"])
        form.addRow("<b>Department:</b>", self.cmb_dept)

        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("10-digit mobile number")
        form.addRow("<b>Phone Number:</b>", self.txt_phone)

        layout.addLayout(form)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Enroll Student")
        btn_save.clicked.connect(self._handle_save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #F1F5F9; color: #475569;")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _update_preview(self):
        pix = create_circular_avatar(
            image_path=self.selected_image_path,
            size=58,
            name="New Student",
            role="STUDENT",
        )
        self.lbl_preview.setPixmap(pix)

    def _browse_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Student Picture", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if not file_path:
            return

        dest_dir = BASE_DIR / "uploads" / "avatars"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            usn = self.txt_usn.text().strip().lower() or "student"
            ext = Path(file_path).suffix or ".png"
            dest_file = dest_dir / f"{usn}_{int(datetime.now().timestamp())}{ext}"
            shutil.copy2(file_path, dest_file)
            self.selected_image_path = str(dest_file.relative_to(BASE_DIR)).replace("\\", "/")
        except Exception as exc:
            logger.warning(f"Could not copy avatar, using original path: {exc}")
            self.selected_image_path = file_path
        self._update_preview()

    def _handle_save(self):
        user = auth_service.current_user
        if user is None:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to enroll a student.")
            return

        dept_id = self.cmb_dept.currentData()
        if dept_id is None:
            QMessageBox.warning(self, "Validation Error", "Please select a department.")
            return

        payload = {
            "usn": self.txt_usn.text().strip().upper(),
            "name": self.txt_name.text().strip(),
            "year": self.cmb_year.currentIndex() + 1,
            "department_id": dept_id,
            "phone_number": self.txt_phone.text().strip(),
            "profile_image_path": self.selected_image_path,
        }
        try:
            student_service.register_student(user, payload)
            QMessageBox.information(
                self, "Success",
                f"Student '{payload['name']}' ({payload['usn']}) registered successfully.",
            )
            self.accept()
        except (ValidationError, BusinessLogicError) as exc:
            QMessageBox.warning(self, "Validation Error", _error_text(exc))
        except Exception as exc:
            logger.error(f"Failed to enroll student: {exc}")
            QMessageBox.critical(self, "Error", f"Failed to enroll student: {exc}")


class StudentSearchWidget(QWidget):
    """
    Primary Student Academic Registry & Directory Component.
    Accessible to ADMIN, HOD, HR, and PRINCIPAL with instant multi-field search.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_students = []

        # Debounce timer so we don't hit the DB on every keystroke
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.load_students)

        self._init_ui()
        self.load_students()

    # ------------------------------------------------------------------ UI
    def _init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Banner (scoped stylesheet so gradient doesn't leak to child labels)
        banner = QFrame()
        banner.setObjectName("headerBanner")
        banner.setStyleSheet(
            "QFrame#headerBanner { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #1E3A8A, stop:1 #3B82F6); border-radius: 10px; }"
        )
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(14, 14, 14, 14)
        v_title = QVBoxLayout()
        title = QLabel("🎓 Student Academic Directory & Registry")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        subtitle = QLabel("Multi-Field Search & Student Profile Inspector across All Academic Departments")
        subtitle.setStyleSheet("color: #BFDBFE; font-size: 11px; background: transparent;")
        v_title.addWidget(title)
        v_title.addWidget(subtitle)
        b_layout.addLayout(v_title)
        b_layout.addStretch()

        self.btn_enroll = QPushButton("➕ Enroll Student")
        self.btn_enroll.setFixedHeight(34)
        self.btn_enroll.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 0 16px; border-radius: 6px;"
        )
        self.btn_enroll.clicked.connect(self._on_enroll)
        b_layout.addWidget(self.btn_enroll)

        layout.addWidget(banner)

        # Multi-Field Search & Filter Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by USN, Name, Phone, or Year...")
        self.txt_search.setMinimumWidth(240)
        self.txt_search.setMaximumWidth(380)
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(lambda _=None: self._search_timer.start())
        toolbar.addWidget(self.txt_search)

        self.cmb_dept = QComboBox()
        self.cmb_dept.addItem("-- All Departments --", None)
        try:
            depts = department_service.list_departments()
        except Exception as exc:
            logger.error(f"Failed to load departments: {exc}")
            depts = []
        for d in depts:
            self.cmb_dept.addItem(f"{d['name']} ({d['code']})", d["id"])
        self.cmb_dept.setMinimumWidth(160)
        self.cmb_dept.setMaximumWidth(240)
        self.cmb_dept.currentIndexChanged.connect(lambda _=None: self.load_students())
        toolbar.addWidget(self.cmb_dept)

        self.cmb_year = QComboBox()
        self.cmb_year.addItem("All Years", None)
        for y in range(1, 5):
            self.cmb_year.addItem(f"Year {y}", y)
        self.cmb_year.setFixedWidth(100)
        self.cmb_year.currentIndexChanged.connect(lambda _=None: self.load_students())
        toolbar.addWidget(self.cmb_year)
        toolbar.addStretch(1)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(lambda _=False: self.load_students())
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # Students Data Table
        self.tbl_students = QTableWidget()
        self.tbl_students.setColumnCount(7)
        self.tbl_students.setHorizontalHeaderLabels([
            "Photo", "USN", "Full Name", "Year", "Department", "Phone", "Action"
        ])
        header = self.tbl_students.horizontalHeader()
        for col in range(7):
            mode = QHeaderView.ResizeMode.Stretch if col == 2 else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(col, mode)
        self.tbl_students.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_students.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_students.setAlternatingRowColors(True)
        self.tbl_students.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tbl_students.verticalHeader().setDefaultSectionSize(46)
        self.tbl_students.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.tbl_students, stretch=1)

        # Modern Empty State Placeholder
        self.empty_state = EmptyStateWidget(
            icon="🎓",
            title="No Students Found",
            message="No student records match the active search criteria. Click below to enroll a new student.",
            action_text="+ Enroll Student",
            action_callback=self._on_enroll,
        )
        layout.addWidget(self.empty_state, stretch=1)
        self.empty_state.hide()

        # Status footer
        self.lbl_count = QLabel("Total Students: 0")
        self.lbl_count.setStyleSheet("color: #64748B; font-weight: bold;")
        layout.addWidget(self.lbl_count)

    # ---------------------------------------------------------------- Logic
    def _can_enroll(self) -> bool:
        user = auth_service.current_user
        return bool(user and (user.is_admin() or user.is_hod()))

    def load_students(self):
        """Executes search query and populates the students table."""
        user = auth_service.current_user
        search_term = self.txt_search.text().strip()
        dept_id = self.cmb_dept.currentData()
        year_val = self.cmb_year.currentData()

        # RBAC: Only Admin and HOD can enroll
        self.btn_enroll.setVisible(self._can_enroll())

        try:
            students = student_service.search_students(
                user_session=user,
                search_term=search_term,
                department_id=dept_id,
                year=year_val,
            )
        except Exception as exc:
            logger.error(f"Student search failed: {exc}")
            QMessageBox.critical(self, "Error", f"Failed to load students: {exc}")
            students = []

        students = students or []
        self.current_students = students

        self.tbl_students.setUpdatesEnabled(False)
        try:
            self.tbl_students.clearContents()
            self.tbl_students.setRowCount(len(students))

            if not students:
                self.tbl_students.hide()
                self.empty_state.show()
            else:
                self.empty_state.hide()
                self.tbl_students.show()

            for row, s in enumerate(students):
                # Avatar cell
                avatar_lbl = QLabel()
                avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pix = create_circular_avatar(
                    image_path=s.get("profile_image_path"),
                    size=36,
                    name=_s(s.get("name"), "Student"),
                    role="STUDENT",
                )
                avatar_lbl.setPixmap(pix)
                self.tbl_students.setCellWidget(row, 0, avatar_lbl)

                usn_item = QTableWidgetItem(_s(s.get("usn")))
                usn_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.tbl_students.setItem(row, 1, usn_item)

                self.tbl_students.setItem(row, 2, QTableWidgetItem(_s(s.get("name"))))
                self.tbl_students.setItem(row, 3, QTableWidgetItem(f"Year {_s(s.get('year'), '1')}"))
                self.tbl_students.setItem(row, 4, QTableWidgetItem(_s(s.get("department_code"), "N/A")))
                self.tbl_students.setItem(row, 5, QTableWidgetItem(_s(s.get("phone_number"))))

                btn_view = QPushButton("🔍 View Profile")
                btn_view.setStyleSheet(
                    "background-color: #F1F5F9; color: #2563EB; font-weight: bold; padding: 4px 10px;"
                )
                btn_view.clicked.connect(lambda _=False, st=s: self._show_profile(st))
                self.tbl_students.setCellWidget(row, 6, btn_view)
        finally:
            self.tbl_students.setUpdatesEnabled(True)

        self.lbl_count.setText(f"Showing {len(students)} Student(s)")

    def _on_row_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self.current_students):
            self._show_profile(self.current_students[row])

    def _show_profile(self, student_data: dict):
        dlg = StudentProfileDialog(student_data, self)
        dlg.exec()

    def _on_enroll(self):
        # Guard here too: the empty-state button isn't hidden by RBAC
        if not self._can_enroll():
            QMessageBox.warning(
                self, "Access Denied", "You do not have permission to enroll students."
            )
            return
        dlg = StudentFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_students()