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
    QTabWidget,
    QFrame,
    QSplitter,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.analytics_service import analytics_service
from utils.logger import get_logger

logger = get_logger("ui.analytics_view")


class AnalyticsView(QWidget):
    """PySide6 Desktop View displaying Attendance Analytics and Anomaly Outlier Inspector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_anomalies = []
        self._init_ui()
        self.load_analytics_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Institutional Attendance & Trend Dashboard
        self.tab_dashboard = QWidget()
        self._build_dashboard_tab(self.tab_dashboard)
        self.sub_tabs.addTab(self.tab_dashboard, "Institutional Attendance & Trend Dashboard")

        # Sub-Tab 2: Anomaly Detection & Outlier Inspector
        self.tab_anomalies = QWidget()
        self._build_anomalies_tab(self.tab_anomalies)
        self.sub_tabs.addTab(self.tab_anomalies, "Anomaly Detection & Outlier Inspector")

        main_layout.addWidget(self.sub_tabs)

    def _create_kpi_card(self, title: str, initial_value: str, color_hex: str = "#1b365d") -> QGroupBox:
        box = QGroupBox()
        box.setStyleSheet("""
            QGroupBox {
                background-color: #f8f9fa;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
            }
        """)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 9))
        lbl_t.setStyleSheet("color: #666666;")

        lbl_v = QLabel(initial_value)
        lbl_v.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {color_hex};")
        lbl_v.setObjectName("value_label")

        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return box

    def _update_kpi_value(self, card_box: QGroupBox, new_text: str):
        lbl = card_box.findChild(QLabel, "value_label")
        if lbl:
            lbl.setText(new_text)

    def _build_dashboard_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. KPI Cards
        cards_layout = QHBoxLayout()
        self.card_att_rate = self._create_kpi_card("Overall Attendance Rate", "0.0%", "#2e7d32")
        self.card_avg_late = self._create_kpi_card("Avg Late Arrival Mins", "0.0 mins", "#f57c00")
        self.card_unexcused = self._create_kpi_card("Unexcused Absences", "0", "#c62828")
        self.card_anomalies_cnt = self._create_kpi_card("Active Anomaly Flags", "0 Flags", "#1565c0")

        cards_layout.addWidget(self.card_att_rate)
        cards_layout.addWidget(self.card_avg_late)
        cards_layout.addWidget(self.card_unexcused)
        cards_layout.addWidget(self.card_anomalies_cnt)

        tab_layout.addLayout(cards_layout)

        # 2. Main Splitter: Department Breakdown (Left) & Monthly Trends (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Department Breakdown Table
        left_group = QGroupBox("Department Attendance Performance Summary")
        left_layout = QVBoxLayout(left_group)

        self.tbl_dept_perf = QTableWidget()
        self.tbl_dept_perf.setColumnCount(5)
        self.tbl_dept_perf.setHorizontalHeaderLabels(["Dept Code", "Department Name", "Faculty Count", "Attendance Rate", "Avg Late Mins"])
        self.tbl_dept_perf.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_dept_perf.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_dept_perf.setAlternatingRowColors(True)
        self.tbl_dept_perf.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_dept_perf.verticalHeader().setDefaultSectionSize(36)
        left_layout.addWidget(self.tbl_dept_perf)

        splitter.addWidget(left_group)

        # Right: Monthly Trend Table
        right_group = QGroupBox("Monthly Attendance & Leave Compliance Trends (May - Sep 2026)")
        right_layout = QVBoxLayout(right_group)

        self.tbl_monthly_trends = QTableWidget()
        self.tbl_monthly_trends.setColumnCount(5)
        self.tbl_monthly_trends.setHorizontalHeaderLabels(["Month", "Attendance Rate", "Present Logs", "Late Logs", "Leave Applications"])
        self.tbl_monthly_trends.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_monthly_trends.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_monthly_trends.setAlternatingRowColors(True)
        self.tbl_monthly_trends.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_monthly_trends.verticalHeader().setDefaultSectionSize(36)

        right_layout.addWidget(self.tbl_monthly_trends)
        splitter.addWidget(right_group)

        splitter.setSizes([500, 500])
        tab_layout.addWidget(splitter, stretch=1)

    def _build_anomalies_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # Filter Control Panel
        filter_group = QGroupBox("Anomaly Engine Controls")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("<b>Filter Anomaly Type:</b>"))
        self.combo_anomaly_type = QComboBox()
        self.combo_anomaly_type.addItems(["ALL", "LATE_ARRIVAL_OUTLIER", "FREQUENT_SHORT_LEAVE", "UNEXCUSED_ABSENCE"])
        self.combo_anomaly_type.currentTextChanged.connect(self.filter_anomalies_display)
        filter_layout.addWidget(self.combo_anomaly_type)

        self.btn_rerun = QPushButton("Re-Run Anomaly Detection Engine")
        self.btn_rerun.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold;")
        self.btn_rerun.clicked.connect(self.load_analytics_data)
        filter_layout.addWidget(self.btn_rerun)

        filter_layout.addStretch()
        tab_layout.addWidget(filter_group)

        # Anomaly Inspector Table
        tbl_group = QGroupBox("Detected Attendance & Pattern Anomalies (Z-Score & Policy Outliers)")
        tbl_layout = QVBoxLayout(tbl_group)

        self.tbl_anomalies = QTableWidget()
        self.tbl_anomalies.setColumnCount(8)
        self.tbl_anomalies.setHorizontalHeaderLabels([
            "Anomaly ID",
            "Code",
            "Faculty Name",
            "Dept",
            "Anomaly Type",
            "Severity",
            "Metric / Z-Score",
            "Recommended Action",
        ])
        self.tbl_anomalies.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_anomalies.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_anomalies.setAlternatingRowColors(True)
        self.tbl_anomalies.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_anomalies.verticalHeader().setDefaultSectionSize(38)

        tbl_layout.addWidget(self.tbl_anomalies)
        tab_layout.addWidget(tbl_group, stretch=1)

    def load_analytics_data(self):
        """Loads KPIs, department performance, monthly trends, and anomaly detection logs."""
        try:
            kpis = analytics_service.get_institutional_kpis()
            self._update_kpi_value(self.card_att_rate, f"{kpis['overall_attendance_rate']:.1f}%")
            self._update_kpi_value(self.card_avg_late, f"{kpis['avg_late_minutes']:.1f} mins")
            self._update_kpi_value(self.card_unexcused, str(kpis["unexcused_absences"]))
            self._update_kpi_value(self.card_anomalies_cnt, f"{kpis['active_anomalies_count']} Active")

            # Department breakdown
            depts = analytics_service.get_department_breakdown()
            self.tbl_dept_perf.setRowCount(len(depts))
            for idx, d in enumerate(depts):
                self.tbl_dept_perf.setItem(idx, 0, QTableWidgetItem(d["department_code"]))
                self.tbl_dept_perf.setItem(idx, 1, QTableWidgetItem(d["department_name"]))
                self.tbl_dept_perf.setItem(idx, 2, QTableWidgetItem(str(d["faculty_count"])))
                self.tbl_dept_perf.setItem(idx, 3, QTableWidgetItem(f"{d['attendance_rate']:.1f}%"))
                self.tbl_dept_perf.setItem(idx, 4, QTableWidgetItem(f"{d['avg_late_minutes']:.1f} mins"))

            # Monthly trends
            trends = analytics_service.get_monthly_attendance_trends()
            self.tbl_monthly_trends.setRowCount(len(trends))
            for idx, m in enumerate(trends):
                self.tbl_monthly_trends.setItem(idx, 0, QTableWidgetItem(m["month_name"]))
                self.tbl_monthly_trends.setItem(idx, 1, QTableWidgetItem(f"{m['attendance_rate']:.1f}%"))
                self.tbl_monthly_trends.setItem(idx, 2, QTableWidgetItem(str(m["present_cnt"])))
                self.tbl_monthly_trends.setItem(idx, 3, QTableWidgetItem(str(m["late_cnt"])))
                self.tbl_monthly_trends.setItem(idx, 4, QTableWidgetItem(str(m["leave_cnt"])))

            # Anomalies
            self.all_anomalies = analytics_service.detect_attendance_anomalies()
            self.filter_anomalies_display()

        except Exception as exc:
            logger.error(f"Failed to load analytics data: {exc}")
            QMessageBox.warning(self, "Analytics Error", f"Could not load analytics data: {exc}")

    def filter_anomalies_display(self):
        """Filters anomaly table display by selected anomaly type."""
        filter_type = self.combo_anomaly_type.currentText()

        filtered = [
            a for a in self.all_anomalies
            if filter_type == "ALL" or a.get("anomaly_type") == filter_type
        ]

        self.tbl_anomalies.setRowCount(0)
        for idx, item in enumerate(filtered):
            self.tbl_anomalies.insertRow(idx)

            id_item = QTableWidgetItem(item.get("anomaly_id", ""))
            code_item = QTableWidgetItem(item.get("employee_code", ""))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            name_item = QTableWidgetItem(item.get("faculty_name", ""))
            dept_item = QTableWidgetItem(item.get("department_code", ""))
            type_item = QTableWidgetItem(item.get("anomaly_name", ""))

            sev = item.get("severity", "LOW")
            sev_item = QTableWidgetItem(sev)
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if sev == "HIGH":
                sev_item.setBackground(QColor("#f8d7da"))
                sev_item.setForeground(QColor("#721c24"))
                sev_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            elif sev == "MEDIUM":
                sev_item.setBackground(QColor("#fff3cd"))
                sev_item.setForeground(QColor("#856404"))

            metric_item = QTableWidgetItem(item.get("metric_value", ""))
            action_item = QTableWidgetItem(item.get("recommendation", ""))

            self.tbl_anomalies.setItem(idx, 0, id_item)
            self.tbl_anomalies.setItem(idx, 1, code_item)
            self.tbl_anomalies.setItem(idx, 2, name_item)
            self.tbl_anomalies.setItem(idx, 3, dept_item)
            self.tbl_anomalies.setItem(idx, 4, type_item)
            self.tbl_anomalies.setItem(idx, 5, sev_item)
            self.tbl_anomalies.setItem(idx, 6, metric_item)
            self.tbl_anomalies.setItem(idx, 7, action_item)
