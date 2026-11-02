"""
Stationery Requisition & HOD Approval View
Modern PySide6 interface for faculty and staff to indent consumable stationery items,
and for Department Heads (HOD) to review, approve, and reject departmental requisitions.
"""
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QMessageBox, QScrollArea, QInputDialog
)

from services.stationery_service import stationery_service
from services.auth_service import auth_service
from utils.logger import get_logger

logger = get_logger("ui.stationery_view")


class StationeryView(QWidget):
    """Modern, de-congested stationery requisition and HOD approval interface."""

    request_processed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stationeryView")
        self.service = stationery_service

        self._init_ui()
        self.refresh_all_views()

    def _init_ui(self):
        # Outer scroll area wrapper to prevent clipping on standard desktop monitors
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("stationeryScrollArea")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Header Banner
        header_card = QFrame()
        header_card.setObjectName("cardFrame")
        header_card.setStyleSheet(
            "#cardFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1B365D, stop:1 #0288D1); "
            "border-radius: 8px; padding: 12px; }"
        )
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.setSpacing(4)

        lbl_title = QLabel("📦 Departmental Stationery & Consumable Requisitions")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        lbl_subtitle = QLabel(
            "Indent academic stationery (markers, paper reams, box files, printer toner), "
            "track status in real-time, and process departmental HOD approvals."
        )
        lbl_subtitle.setStyleSheet("font-size: 11px; color: #E0E1DD;")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_subtitle)
        layout.addWidget(header_card)

        # 2. Requisition Submission Card (For Faculty / Staff)
        req_card = QFrame()
        req_card.setObjectName("reqCard")
        req_card.setStyleSheet(
            "#reqCard { background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 14px; }"
        )
        r_layout = QVBoxLayout(req_card)
        r_layout.setContentsMargins(14, 12, 14, 12)
        r_layout.setSpacing(12)

        lbl_sec1 = QLabel("➕ Submit New Stationery Indent Request")
        lbl_sec1.setStyleSheet("font-size: 13px; font-weight: bold; color: #1B365D;")
        r_layout.addWidget(lbl_sec1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        # Predefined Item Dropdown
        grid.addWidget(QLabel("Stationery Item:"), 0, 0)
        self.combo_item = QComboBox()
        self.combo_item.setFixedHeight(34)
        for item in self.service.get_predefined_items():
            self.combo_item.addItem(item)
        grid.addWidget(self.combo_item, 0, 1)

        # Quantity Spinbox
        grid.addWidget(QLabel("Quantity:"), 0, 2)
        self.spin_qty = QSpinBox()
        self.spin_qty.setFixedHeight(34)
        self.spin_qty.setRange(1, 100)
        self.spin_qty.setValue(1)
        grid.addWidget(self.spin_qty, 0, 3)

        # Urgency Dropdown
        grid.addWidget(QLabel("Urgency:"), 0, 4)
        self.combo_urgency = QComboBox()
        self.combo_urgency.setFixedHeight(34)
        self.combo_urgency.addItems(["NORMAL", "LOW", "HIGH", "URGENT"])
        grid.addWidget(self.combo_urgency, 0, 5)

        # Purpose / Note Input
        grid.addWidget(QLabel("Purpose / Location:"), 1, 0)
        self.txt_purpose = QLineEdit()
        self.txt_purpose.setFixedHeight(34)
        self.txt_purpose.setPlaceholderText("e.g., Lab 204 semester exams, lecture hall whiteboard...")
        grid.addWidget(self.txt_purpose, 1, 1, 1, 4)

        # Submit Button
        self.btn_submit = QPushButton("🚀 Submit Requisition")
        self.btn_submit.setFixedHeight(34)
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.setStyleSheet(
            "background-color: #2E7D32; color: #FFFFFF; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        self.btn_submit.clicked.connect(self.on_submit_request)
        grid.addWidget(self.btn_submit, 1, 5)

        r_layout.addLayout(grid)
        layout.addWidget(req_card)

        # 3. HOD Approval Queue Card (Only for HOD or ADMIN)
        self.hod_card = QFrame()
        self.hod_card.setObjectName("hodCard")
        self.hod_card.setStyleSheet(
            "#hodCard { background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 14px; }"
        )
        h_box = QVBoxLayout(self.hod_card)
        h_box.setContentsMargins(14, 12, 14, 12)
        h_box.setSpacing(10)

        h_title_row = QHBoxLayout()
        lbl_sec2 = QLabel("⚖️ Departmental Requisitions (HOD Approval Grid)")
        lbl_sec2.setStyleSheet("font-size: 13px; font-weight: bold; color: #1B365D;")
        h_title_row.addWidget(lbl_sec2)

        self.btn_refresh = QPushButton("🔄 Refresh Queue")
        self.btn_refresh.setFixedHeight(28)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            "background-color: #ECEFF1; color: #263238; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
        )
        self.btn_refresh.clicked.connect(self.refresh_all_views)
        h_title_row.addWidget(self.btn_refresh)
        h_box.addLayout(h_title_row)

        self.table_hod = QTableWidget()
        self.table_hod.setColumnCount(9)
        self.table_hod.setHorizontalHeaderLabels([
            "ID", "Requester", "Role", "Item Requested", "Qty", "Urgency", "Purpose", "Status", "HOD Actions"
        ])
        self.table_hod.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_hod.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_hod.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_hod.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_hod.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_hod.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_hod.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table_hod.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table_hod.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table_hod.setAlternatingRowColors(True)
        self.table_hod.verticalHeader().setDefaultSectionSize(40)
        self.table_hod.setStyleSheet(
            "QTableWidget { gridline-color: #ECEFF1; font-size: 11.5px; } "
            "QHeaderView::section { background-color: #1B365D; color: #FFFFFF; font-weight: bold; padding: 6px; }"
        )
        h_box.addWidget(self.table_hod)
        layout.addWidget(self.hod_card)

        # 4. Personal Requisition History Card
        hist_card = QFrame()
        hist_card.setObjectName("histCard")
        hist_card.setStyleSheet(
            "#histCard { background: #FFFFFF; border: 1px solid #CFD8DC; border-radius: 8px; padding: 14px; }"
        )
        hist_layout = QVBoxLayout(hist_card)
        hist_layout.setContentsMargins(14, 12, 14, 12)
        hist_layout.setSpacing(10)

        lbl_sec3 = QLabel("📋 My Submitted Requisition History")
        lbl_sec3.setStyleSheet("font-size: 13px; font-weight: bold; color: #1B365D;")
        hist_layout.addWidget(lbl_sec3)

        self.table_my = QTableWidget()
        self.table_my.setColumnCount(8)
        self.table_my.setHorizontalHeaderLabels([
            "ID", "Item Requested", "Qty", "Urgency", "Purpose", "Date", "Status", "HOD Remarks"
        ])
        self.table_my.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_my.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_my.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_my.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_my.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_my.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_my.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_my.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table_my.setAlternatingRowColors(True)
        self.table_my.verticalHeader().setDefaultSectionSize(36)
        self.table_my.setStyleSheet(
            "QTableWidget { gridline-color: #ECEFF1; font-size: 11.5px; } "
            "QHeaderView::section { background-color: #37474F; color: #FFFFFF; font-weight: bold; padding: 6px; }"
        )
        hist_layout.addWidget(self.table_my)
        layout.addWidget(hist_card)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

    def refresh_all_views(self):
        """Refreshes HOD approval queue and personal requisition ledger."""
        session = auth_service.current_user

        # 1. Check HOD Visibility
        is_hod_or_admin = session and (session.is_hod() or session.is_admin())
        self.hod_card.setVisible(bool(is_hod_or_admin))

        if is_hod_or_admin:
            dept_requests = self.service.get_department_requests_for_hod(session)
            self._populate_hod_table(dept_requests)

        # 2. Populate personal requests
        my_requests = self.service.get_my_requests(session)
        self._populate_my_table(my_requests)

    def _populate_hod_table(self, requests_list):
        self.table_hod.setRowCount(len(requests_list))
        for row_idx, r in enumerate(requests_list):
            req_id = r["id"]
            self.table_hod.setItem(row_idx, 0, QTableWidgetItem(f"#{req_id}"))
            self.table_hod.setItem(row_idx, 1, QTableWidgetItem(r.get("requester_name", "")))
            self.table_hod.setItem(row_idx, 2, QTableWidgetItem(r.get("requester_role", "")))
            self.table_hod.setItem(row_idx, 3, QTableWidgetItem(r.get("item_name", "")))
            self.table_hod.setItem(row_idx, 4, QTableWidgetItem(str(r.get("quantity", 1))))
            self.table_hod.setItem(row_idx, 5, QTableWidgetItem(r.get("urgency", "NORMAL")))
            self.table_hod.setItem(row_idx, 6, QTableWidgetItem(r.get("purpose", "")))

            # Status Item
            status = r.get("status", "PENDING")
            st_item = QTableWidgetItem(status)
            st_item.setTextAlignment(Qt.AlignCenter)
            if status == "APPROVED":
                st_item.setForeground(Qt.darkGreen)
            elif status == "REJECTED":
                st_item.setForeground(Qt.darkRed)
            else:
                st_item.setForeground(Qt.darkYellow)
            self.table_hod.setItem(row_idx, 7, st_item)

            # Action Buttons widget
            if status == "PENDING":
                act_widget = QWidget()
                act_layout = QHBoxLayout(act_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(6)

                btn_app = QPushButton("✓ Approve")
                btn_app.setFixedHeight(26)
                btn_app.setCursor(Qt.PointingHandCursor)
                btn_app.setStyleSheet(
                    "background-color: #2E7D32; color: #FFFFFF; font-weight: bold; border-radius: 3px; padding: 2px 8px;"
                )
                btn_app.clicked.connect(lambda _, rid=req_id: self.review_request(rid, "APPROVE"))

                btn_rej = QPushButton("✗ Reject")
                btn_rej.setFixedHeight(26)
                btn_rej.setCursor(Qt.PointingHandCursor)
                btn_rej.setStyleSheet(
                    "background-color: #C62828; color: #FFFFFF; font-weight: bold; border-radius: 3px; padding: 2px 8px;"
                )
                btn_rej.clicked.connect(lambda _, rid=req_id: self.review_request(rid, "REJECT"))

                act_layout.addWidget(btn_app)
                act_layout.addWidget(btn_rej)
                self.table_hod.setCellWidget(row_idx, 8, act_widget)
            else:
                lbl_done = QLabel(f"{status} by HOD")
                lbl_done.setAlignment(Qt.AlignCenter)
                lbl_done.setStyleSheet("color: #78909C; font-size: 10px; font-weight: bold;")
                self.table_hod.setCellWidget(row_idx, 8, lbl_done)

    def _populate_my_table(self, requests_list):
        self.table_my.setRowCount(len(requests_list))
        for row_idx, r in enumerate(requests_list):
            self.table_my.setItem(row_idx, 0, QTableWidgetItem(f"#{r['id']}"))
            self.table_my.setItem(row_idx, 1, QTableWidgetItem(r.get("item_name", "")))
            self.table_my.setItem(row_idx, 2, QTableWidgetItem(str(r.get("quantity", 1))))
            self.table_my.setItem(row_idx, 3, QTableWidgetItem(r.get("urgency", "NORMAL")))
            self.table_my.setItem(row_idx, 4, QTableWidgetItem(r.get("purpose", "")))
            self.table_my.setItem(row_idx, 5, QTableWidgetItem(r.get("created_at", "")))

            status = r.get("status", "PENDING")
            st_item = QTableWidgetItem(status)
            st_item.setTextAlignment(Qt.AlignCenter)
            if status == "APPROVED":
                st_item.setForeground(Qt.darkGreen)
            elif status == "REJECTED":
                st_item.setForeground(Qt.darkRed)
            else:
                st_item.setForeground(Qt.darkYellow)
            self.table_my.setItem(row_idx, 6, st_item)

            remarks = r.get("hod_remarks", "") or "—"
            self.table_my.setItem(row_idx, 7, QTableWidgetItem(remarks))

    def on_submit_request(self):
        """Validates and submits a new requisition."""
        session = auth_service.current_user
        if not session:
            QMessageBox.warning(self, "Authentication Error", "You must be logged in to submit a stationery request.")
            return

        item = self.combo_item.currentText().strip()
        qty = self.spin_qty.value()
        urgency = self.combo_urgency.currentText().strip()
        purpose = self.txt_purpose.text().strip()

        try:
            res = self.service.submit_request(
                user_session=session,
                item_name=item,
                quantity=qty,
                urgency=urgency,
                purpose=purpose,
            )
            QMessageBox.information(
                self,
                "Requisition Submitted",
                f"Your stationery request #{res['request_id']} for {qty}x '{item}' "
                "has been submitted and forwarded to your Department Head (HOD)."
            )
            self.txt_purpose.clear()
            self.spin_qty.setValue(1)
            self.refresh_all_views()
            self.request_processed.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Submission Error", str(exc))

    def review_request(self, request_id: int, action: str):
        """HOD action handler to approve or reject requests."""
        session = auth_service.current_user
        if not session:
            return

        action_name = "Approve" if action == "APPROVE" else "Reject"
        remarks, ok = QInputDialog.getText(
            self,
            f"{action_name} Stationery Request #{request_id}",
            f"Enter optional HOD remarks for {action_name.lower()}al:",
        )
        if not ok:
            return

        try:
            self.service.review_request(
                request_id=request_id,
                reviewer_session=session,
                action=action,
                remarks=remarks,
            )
            QMessageBox.information(
                self,
                "Request Updated",
                f"Stationery request #{request_id} has been {action.lower()}d."
            )
            self.refresh_all_views()
            self.request_processed.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Review Error", str(exc))
