"""
Automated Reports & PDF Generator View (PySide6)
Displays PDF Report Studio for generating ReportLab PDF reports and CSV data export controls.
"""
import sys
import os
import subprocess
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
    QMessageBox,
    QHeaderView,
    QTabWidget,
    QFileDialog,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QColor, QDesktopServices

from services.report_service import report_service
from repositories.department_repository import department_repository
from ui.worker import WorkerThread, LoadingOverlay
from utils.logger import get_logger

logger = get_logger("ui.report_view")


class ReportView(QWidget):
    """PySide6 Desktop View displaying PDF Report Studio and CSV Data Exporters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recent_reports = []
        self._pdf_worker = None
        self._csv_worker = None
        self._init_ui()
        self.overlay = LoadingOverlay(self)
        self.load_departments()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setUsesScrollButtons(True)
        self.sub_tabs.setElideMode(Qt.ElideRight)

        # Sub-Tab 1: PDF Report Studio (Wrapped in QScrollArea)
        scroll_pdf = QScrollArea()
        scroll_pdf.setWidgetResizable(True)
        scroll_pdf.setFrameShape(QFrame.NoFrame)
        scroll_pdf.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_pdf.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.tab_pdf = QWidget()
        self._build_pdf_tab(self.tab_pdf)
        scroll_pdf.setWidget(self.tab_pdf)
        self.sub_tabs.addTab(scroll_pdf, "ReportLab PDF Report Studio")

        # Sub-Tab 2: CSV Data Exporter
        self.tab_csv = QWidget()
        self._build_csv_tab(self.tab_csv)
        self.sub_tabs.addTab(self.tab_csv, "CSV Data Exporter & Audit Exporters")

        main_layout.addWidget(self.sub_tabs)

    def _build_pdf_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # PDF Generator Controls Box
        ctrl_group = QGroupBox("PDF Report Generation Studio")
        ctrl_layout = QVBoxLayout(ctrl_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b>Report Template Type:</b>"))
        self.combo_pdf_type = QComboBox()
        self.combo_pdf_type.addItem("Faculty Attendance & Punctuality Summary Report", "ATTENDANCE_SUMMARY")
        self.combo_pdf_type.addItem("Faculty Leave Entitlement & Usage Ledger Report", "LEAVE_LEDGER")
        self.combo_pdf_type.addItem("Attendance Anomaly & HR Compliance Audit Report", "ANOMALY_AUDIT")
        row1.addWidget(self.combo_pdf_type, stretch=1)

        row1.addWidget(QLabel("<b>Department Scope:</b>"))
        self.combo_dept_scope = QComboBox()
        self.combo_dept_scope.addItem("ALL Departments (Institutional)", None)
        row1.addWidget(self.combo_dept_scope)

        ctrl_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_gen_pdf = QPushButton("Generate PDF Report")
        self.btn_gen_pdf.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 13px; padding: 8px 16px;")
        self.btn_gen_pdf.clicked.connect(self.generate_pdf_clicked)
        row2.addWidget(self.btn_gen_pdf)

        self.btn_open_folder = QPushButton("Open PDF Output Folder")
        self.btn_open_folder.setStyleSheet("background-color: #5c6bc0; color: white; font-weight: bold; padding: 8px 16px;")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        row2.addWidget(self.btn_open_folder)

        row2.addStretch()
        ctrl_layout.addLayout(row2)

        tab_layout.addWidget(ctrl_group)

        # Status Banner Frame
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dcdfe6; border-radius: 6px; padding: 10px;")
        banner_lay = QVBoxLayout(self.banner_frame)

        self.lbl_pdf_status = QLabel("Ready to generate PDF reports. Output directory: <b>reports_output/</b>")
        self.lbl_pdf_status.setWordWrap(True)
        banner_lay.addWidget(self.lbl_pdf_status)

        tab_layout.addWidget(self.banner_frame)

        # Recent Generated PDF Table
        tbl_group = QGroupBox("Generated PDF Documents History")
        tbl_layout = QVBoxLayout(tbl_group)

        self.tbl_recent_pdfs = QTableWidget()
        self.tbl_recent_pdfs.setColumnCount(4)
        self.tbl_recent_pdfs.setHorizontalHeaderLabels(["PDF File Name", "File Size (KB)", "Path Location", "Created Timestamp"])
        self.tbl_recent_pdfs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_recent_pdfs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_recent_pdfs.setAlternatingRowColors(True)
        self.tbl_recent_pdfs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_recent_pdfs.verticalHeader().setDefaultSectionSize(36)

        tbl_layout.addWidget(self.tbl_recent_pdfs)
        tab_layout.addWidget(tbl_group, stretch=1)

    def _build_csv_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(15)

        group = QGroupBox("Instant Tabular CSV Data Exporters")
        lay = QVBoxLayout(group)

        # Export 1: Attendance Logs
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b>1. Attendance Logs Dataset:</b> Exports full clock-in/out logs with late minutes."))
        btn_exp_att = QPushButton("Export Attendance CSV")
        btn_exp_att.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 14px;")
        btn_exp_att.clicked.connect(lambda: self.export_csv_action("ATTENDANCE"))
        row1.addWidget(btn_exp_att)
        lay.addLayout(row1)

        lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Export 2: Leave Ledger
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("<b>2. Faculty Leave Balances:</b> Exports allocated, used, pending, and remaining balances."))
        btn_exp_leave = QPushButton("Export Leave Balances CSV")
        btn_exp_leave.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold; padding: 6px 14px;")
        btn_exp_leave.clicked.connect(lambda: self.export_csv_action("LEAVE_LEDGER"))
        row2.addWidget(btn_exp_leave)
        lay.addLayout(row2)

        lay.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

        # Export 3: Anomalies Audit Log
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("<b>3. Attendance Anomaly Logs:</b> Exports Z-score late outliers and pattern flags."))
        btn_exp_ano = QPushButton("Export Anomalies CSV")
        btn_exp_ano.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 6px 14px;")
        btn_exp_ano.clicked.connect(lambda: self.export_csv_action("ANOMALIES"))
        row3.addWidget(btn_exp_ano)
        lay.addLayout(row3)

        tab_layout.addWidget(group)
        tab_layout.addStretch()

    def load_departments(self):
        """Loads department scope dropdown options."""
        try:
            depts = department_repository.get_all()
            for d in depts:
                self.combo_dept_scope.addItem(f"{d['code']} - {d['name']}", d['id'])
        except Exception as exc:
            logger.error(f"Failed to load department scope options: {exc}")

    def generate_pdf_clicked(self):
        """Triggers PDF report build based on selected template type."""
        in_test = "pytest" in sys.modules
        if not in_test:
            self._generate_pdf_async()
        else:
            self._generate_pdf_sync()

    def _generate_pdf_sync(self):
        """Synchronous PDF generation (used in unit test suites)."""
        try:
            report_type = self.combo_pdf_type.currentData()
            dept_id = self.combo_dept_scope.currentData()

            pdf_path = report_service.generate_pdf_report(report_type, department_id=dept_id)

            file_size_kb = round(os.path.getsize(pdf_path) / 1024.0, 1)
            filename = os.path.basename(pdf_path)

            self.lbl_pdf_status.setText(
                f"SUCCESS: Generated PDF report -> <b>{filename}</b> ({file_size_kb} KB)<br/>Path: {pdf_path}"
            )
            self.lbl_pdf_status.setStyleSheet("color: #155724; font-size: 11px;")

            self._add_to_recent_table(filename, file_size_kb, pdf_path)
            QMessageBox.information(self, "PDF Report Generated", f"Report successfully created:\n{filename}\n\nSaved to: {pdf_path}")

        except Exception as exc:
            logger.error(f"Failed to generate PDF report: {exc}")
            QMessageBox.critical(self, "PDF Generation Failed", f"Could not generate PDF report: {exc}")

    def _generate_pdf_async(self):
        """Asynchronous non-blocking PDF generation with background WorkerThread."""
        report_type = self.combo_pdf_type.currentData()
        dept_id = self.combo_dept_scope.currentData()

        self.btn_gen_pdf.setEnabled(False)
        self.btn_gen_pdf.setText("Rendering PDF in Background...")
        self.lbl_pdf_status.setText("<i>Rendering ReportLab document in background thread...</i>")
        self.lbl_pdf_status.setStyleSheet("color: #2563EB; font-size: 11px;")
        self.overlay.show_message("Generating PDF Report...", "Compiling data tables and building PDF document...")

        def _do_work():
            return report_service.generate_pdf_report(report_type, department_id=dept_id)

        worker = WorkerThread(_do_work)

        def _on_success(pdf_path):
            self.overlay.hide()
            file_size_kb = round(os.path.getsize(pdf_path) / 1024.0, 1)
            filename = os.path.basename(pdf_path)

            self.lbl_pdf_status.setText(
                f"SUCCESS: Generated PDF report -> <b>{filename}</b> ({file_size_kb} KB)<br/>Path: {pdf_path}"
            )
            self.lbl_pdf_status.setStyleSheet("color: #155724; font-size: 11px;")
            self._add_to_recent_table(filename, file_size_kb, pdf_path)
            self.btn_gen_pdf.setEnabled(True)
            self.btn_gen_pdf.setText("Generate PDF Report")
            QMessageBox.information(self, "PDF Report Generated", f"Report successfully created:\n{filename}\n\nSaved to: {pdf_path}")

        def _on_error(err_str):
            self.overlay.hide()
            self.btn_gen_pdf.setEnabled(True)
            self.btn_gen_pdf.setText("Generate PDF Report")
            self.lbl_pdf_status.setText("Failed to generate PDF report.")
            self.lbl_pdf_status.setStyleSheet("color: #DC2626; font-size: 11px;")
            logger.error(f"Async PDF generation error: {err_str}")
            self.overlay.show_error(
                "PDF Generation Error",
                f"Could not generate PDF report:\n{err_str[:120]}",
                retry_callback=self._generate_pdf_async,
            )

        worker.result.connect(_on_success)
        worker.error.connect(_on_error)
        worker.start()
        self._pdf_worker = worker

    def open_output_folder(self):
        """Opens reports_output/ directory in OS file explorer."""
        out_dir = str(report_service.output_dir.resolve())
        try:
            if os.name == "nt":
                os.startfile(out_dir)
            else:
                subprocess.Popen(["xdg-open", out_dir])
        except Exception as exc:
            QMessageBox.information(self, "Output Folder", f"Output folder location:\n{out_dir}")

    def export_csv_action(self, export_type: str):
        """Executes CSV data export action."""
        in_test = "pytest" in sys.modules
        if not in_test:
            self._export_csv_async(export_type)
        else:
            self._export_csv_sync(export_type)

    def _export_csv_sync(self, export_type: str):
        try:
            dept_id = self.combo_dept_scope.currentData()
            csv_path = report_service.export_csv_dataset(export_type, department_id=dept_id)
            filename = os.path.basename(csv_path)
            QMessageBox.information(self, "CSV Export Successful", f"CSV file exported successfully:\n{filename}\n\nSaved to: {csv_path}")
        except Exception as exc:
            logger.error(f"CSV export failed: {exc}")
            QMessageBox.critical(self, "Export Failed", f"Could not export CSV data: {exc}")

    def _export_csv_async(self, export_type: str):
        dept_id = self.combo_dept_scope.currentData()
        self.overlay.show_message("Exporting CSV Data...", f"Exporting {export_type} records...")

        def _do_work():
            return report_service.export_csv_dataset(export_type, department_id=dept_id)

        worker = WorkerThread(_do_work)

        def _on_success(csv_path):
            self.overlay.hide()
            filename = os.path.basename(csv_path)
            QMessageBox.information(self, "CSV Export Successful", f"CSV file exported successfully:\n{filename}\n\nSaved to: {csv_path}")

        def _on_error(err_str):
            self.overlay.hide()
            logger.error(f"CSV async export failed: {err_str}")
            self.overlay.show_error(
                "Export Error",
                f"Could not export CSV data:\n{err_str[:120]}",
                retry_callback=lambda: self._export_csv_async(export_type),
            )

        worker.result.connect(_on_success)
        worker.error.connect(_on_error)
        worker.start()
        self._csv_worker = worker

    def closeEvent(self, event):
        if hasattr(self, "_pdf_worker") and self._pdf_worker:
            self._pdf_worker.stop()
        if hasattr(self, "_csv_worker") and self._csv_worker:
            self._csv_worker.stop()
        super().closeEvent(event)

    def _add_to_recent_table(self, filename: str, size_kb: float, full_path: str):
        row_idx = self.tbl_recent_pdfs.rowCount()
        self.tbl_recent_pdfs.insertRow(row_idx)

        item_name = QTableWidgetItem(filename)
        item_size = QTableWidgetItem(f"{size_kb} KB")
        item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_path = QTableWidgetItem(full_path)
        item_stamp = QTableWidgetItem(os.path.basename(filename).replace(".pdf", "").split("_")[-1])

        self.tbl_recent_pdfs.setItem(row_idx, 0, item_name)
        self.tbl_recent_pdfs.setItem(row_idx, 1, item_size)
        self.tbl_recent_pdfs.setItem(row_idx, 2, item_path)
        self.tbl_recent_pdfs.setItem(row_idx, 3, item_stamp)
