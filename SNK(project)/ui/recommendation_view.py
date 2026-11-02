"""
AI Recommendation & Auto-Approval View (PySide6)
Displays policy risk scoring rules, threshold configuration, and real-time multi-factor application risk evaluation playground.
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
    QTabWidget,
    QTextEdit,
    QDateEdit,
    QCheckBox,
    QFrame,
    QProgressBar,
    QSplitter,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from services.recommendation_engine import recommendation_engine
from repositories.faculty_repository import faculty_repository
from nlp.dataset_generator import LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("ui.recommendation_view")


class RecommendationView(QWidget):
    """PySide6 Desktop View displaying AI Auto-Approval Rules and Live Application Risk Evaluator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.faculty_list = []
        self._init_ui()
        self.load_reference_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Risk Scoring Rules & Policy Thresholds
        self.tab_rules = QWidget()
        self._build_rules_tab(self.tab_rules)
        self.sub_tabs.addTab(self.tab_rules, "Risk Scoring Rules & Threshold Settings")

        # Sub-Tab 2: Live Application Risk Evaluator
        self.tab_evaluator = QWidget()
        self._build_evaluator_tab(self.tab_evaluator)
        self.sub_tabs.addTab(self.tab_evaluator, "Live Application Risk Evaluator & Decision Tester")

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

    def _build_rules_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. Threshold KPI Banner
        cards_layout = QHBoxLayout()
        card_auto = self._create_kpi_card("AUTO-APPROVE Threshold", "Risk < 25.0", "#2e7d32")
        card_flag = self._create_kpi_card("FLAG HOD REVIEW Threshold", "25.0 <= Risk <= 65.0", "#f57c00")
        card_reject = self._create_kpi_card("REJECT POLICY Threshold", "Risk > 65.0", "#c62828")
        card_signals = self._create_kpi_card("Active AI Signals", "6 Multi-Factor Rules", "#1b365d")

        cards_layout.addWidget(card_auto)
        cards_layout.addWidget(card_flag)
        cards_layout.addWidget(card_reject)
        cards_layout.addWidget(card_signals)

        tab_layout.addLayout(cards_layout)

        # 2. Rules Table
        rules_group = QGroupBox("Multi-Signal Policy Risk Factor Specifications")
        rules_layout = QVBoxLayout(rules_group)

        self.tbl_rules = QTableWidget()
        self.tbl_rules.setColumnCount(5)
        self.tbl_rules.setHorizontalHeaderLabels(["Factor Code", "Signal Name", "Severity", "Risk Weight Points", "Evaluation Logic & Description"])
        self.tbl_rules.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_rules.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_rules.setAlternatingRowColors(True)
        self.tbl_rules.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_rules.verticalHeader().setDefaultSectionSize(36)

        # Pre-populate specifications
        spec_data = [
            ("INSUFFICIENT_BALANCE", "Leave Balance Availability", "HIGH", "+40.0 pts", "Triggered when requested leave duration exceeds accrued available balance."),
            ("MISSING_MEDICAL_DOC", "Medical Documentation Check", "HIGH", "+30.0 pts", "Triggered when Medical Leave application > 2 days lacks attached doctor certificate."),
            ("ML_INTENT_MISMATCH", "NLP Intent Alignment Check", "MEDIUM", "+25.0 pts", "Triggered when ML NLP reason classification differs from requested leave type code."),
            ("SUBSTITUTE_COLLISION", "Substitute Faculty Availability", "MEDIUM", "+20.0 pts", "Triggered when no eligible substitute faculty is available without timetable collision."),
            ("SANDWICH_LEAVE_FLAG", "Sandwich Leave Boundary Check", "MEDIUM", "+15.0 pts", "Triggered when application adjoins or spans weekends/institutional holidays."),
            ("POOR_PUNCTUALITY_HISTORY", "Attendance Punctuality History", "LOW", "+10.0 pts", "Triggered when faculty has 3+ late arrival entries in recent grace ledger."),
        ]

        self.tbl_rules.setRowCount(len(spec_data))
        for r_idx, row in enumerate(spec_data):
            for c_idx, val in enumerate(row):
                cell = QTableWidgetItem(val)
                if c_idx in [2, 3]:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c_idx == 2:
                    if val == "HIGH":
                        cell.setForeground(QColor("#c62828"))
                        cell.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    elif val == "MEDIUM":
                        cell.setForeground(QColor("#f57c00"))
                        cell.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    else:
                        cell.setForeground(QColor("#1565c0"))

                self.tbl_rules.setItem(r_idx, c_idx, cell)

        rules_layout.addWidget(self.tbl_rules)
        tab_layout.addWidget(rules_group, stretch=1)

    def _build_evaluator_tab(self, parent_widget: QWidget):
        tab_layout = QHBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(15)

        # Left Column: Interactive Form
        left_group = QGroupBox("Leave Application Input Form")
        left_layout = QVBoxLayout(left_group)

        left_layout.addWidget(QLabel("<b>Select Faculty:</b>"))
        self.combo_faculty = QComboBox()
        left_layout.addWidget(self.combo_faculty)

        left_layout.addWidget(QLabel("<b>Leave Type:</b>"))
        self.combo_leave_type = QComboBox()
        for code, name in LEAVE_CATEGORIES.items():
            self.combo_leave_type.addItem(f"{code} - {name}", code)
        left_layout.addWidget(self.combo_leave_type)

        # Date pickers
        dates_layout = QHBoxLayout()
        dates_layout.addWidget(QLabel("Start Date:"))
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate.currentDate())
        dates_layout.addWidget(self.dt_start)

        dates_layout.addWidget(QLabel("End Date:"))
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate())
        dates_layout.addWidget(self.dt_end)

        left_layout.addLayout(dates_layout)

        left_layout.addWidget(QLabel("<b>Natural Language Reason:</b>"))
        self.txt_reason = QTextEdit()
        self.txt_reason.setPlaceholderText("Enter natural language leave application reason...")
        self.txt_reason.setMinimumHeight(100)
        left_layout.addWidget(self.txt_reason)

        # Presets
        presets_layout = QHBoxLayout()
        btn_p1 = QPushButton("Preset: Low Risk CL")
        btn_p1.clicked.connect(lambda: self._set_preset("CL", "Personal work at home regarding bank documentation.", False))
        btn_p2 = QPushButton("Preset: High Risk ML")
        btn_p2.clicked.connect(lambda: self._set_preset("ML", "High viral fever doctor advised rest.", False, add_days=3))
        presets_layout.addWidget(btn_p1)
        presets_layout.addWidget(btn_p2)
        left_layout.addLayout(presets_layout)

        self.chk_doc = QCheckBox("Medical Certificate Document Attached")
        left_layout.addWidget(self.chk_doc)

        self.btn_eval = QPushButton("Evaluate AI Decision & Risk Score")
        self.btn_eval.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; font-size: 13px; padding: 10px;")
        self.btn_eval.clicked.connect(self.run_risk_evaluation)
        left_layout.addWidget(self.btn_eval)

        left_layout.addStretch()
        tab_layout.addWidget(left_group, stretch=4)

        # Right Column: Risk Gauge & Factor Breakdown Results
        right_group = QGroupBox("AI Decision Recommendation & Multi-Factor Risk Assessment")
        right_layout = QVBoxLayout(right_group)

        # Recommendation Banner
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet("background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; padding: 12px;")
        banner_lay = QVBoxLayout(self.banner_frame)

        self.lbl_decision = QLabel("DECISION: AUTO-APPROVE (Low Risk)")
        self.lbl_decision.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_decision.setStyleSheet("color: #2e7d32;")

        self.lbl_score_bar = QLabel("Composite Risk Score: 0.0 / 100.0")
        self.lbl_score_bar.setFont(QFont("Segoe UI", 10))

        self.progress_risk = QProgressBar()
        self.progress_risk.setRange(0, 100)
        self.progress_risk.setValue(0)
        self.progress_risk.setStyleSheet("QProgressBar::chunk { background-color: #2e7d32; }")

        banner_lay.addWidget(self.lbl_decision)
        banner_lay.addWidget(self.lbl_score_bar)
        banner_lay.addWidget(self.progress_risk)

        right_layout.addWidget(self.banner_frame)

        # Active Risk Factors Table
        factors_group = QGroupBox("Active Risk Factor Breakdown")
        factors_lay = QVBoxLayout(factors_group)

        self.tbl_factors = QTableWidget()
        self.tbl_factors.setColumnCount(4)
        self.tbl_factors.setHorizontalHeaderLabels(["Severity", "Risk Factor Name", "Points", "Detailed Policy Context"])
        self.tbl_factors.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_factors.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_factors.setAlternatingRowColors(True)
        self.tbl_factors.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_factors.verticalHeader().setDefaultSectionSize(36)

        factors_lay.addWidget(self.tbl_factors)
        right_layout.addWidget(factors_group)

        # ML & Substitute Summary
        summary_group = QGroupBox("Intelligence Signals (NLP & Substitute Coverage)")
        summary_lay = QVBoxLayout(summary_group)

        self.lbl_signals_summary = QLabel("<b>NLP Intent:</b> Casual Leave (95.0% confidence) | <b>Substitute:</b> Recommended candidate available")
        self.lbl_signals_summary.setWordWrap(True)
        summary_lay.addWidget(self.lbl_signals_summary)

        right_layout.addWidget(summary_group)
        right_layout.addStretch()

        tab_layout.addWidget(right_group, stretch=6)

    def load_reference_data(self):
        """Loads faculty dropdown list."""
        try:
            self.faculty_list = faculty_repository.get_all()
            self.combo_faculty.clear()
            for fac in self.faculty_list:
                f_id = fac.get("id")
                f_name = fac.get("full_name", "")
                f_code = fac.get("employee_code", "")
                self.combo_faculty.addItem(f"{f_name} ({f_code})", f_id)
        except Exception as exc:
            logger.error(f"Failed to load faculty list: {exc}")

    def _set_preset(self, code: str, reason: str, doc: bool, add_days: int = 0):
        idx = self.combo_leave_type.findData(code)
        if idx >= 0:
            self.combo_leave_type.setCurrentIndex(idx)
        self.txt_reason.setPlainText(reason)
        self.chk_doc.setChecked(doc)

        today = QDate.currentDate()
        self.dt_start.setDate(today)
        self.dt_end.setDate(today.addDays(add_days))

        self.run_risk_evaluation()

    def run_risk_evaluation(self):
        if self.combo_faculty.count() == 0:
            QMessageBox.warning(self, "No Faculty", "Please select a faculty member.")
            return

        fac_id = self.combo_faculty.currentData()
        code = self.combo_leave_type.currentData()
        start_str = self.dt_start.date().toString("yyyy-MM-dd")
        end_str = self.dt_end.date().toString("yyyy-MM-dd")
        reason = self.txt_reason.toPlainText().strip()
        doc = self.chk_doc.isChecked()

        res = recommendation_engine.evaluate_leave_application(
            faculty_id=fac_id,
            leave_type_code=code,
            start_date=start_str,
            end_date=end_str,
            reason_text=reason,
            has_medical_doc=doc,
        )

        score = res["risk_score"]
        label = res["decision_label"]
        color = res["decision_color"]

        self.lbl_decision.setText(f"DECISION: {label}")
        self.lbl_decision.setStyleSheet(f"color: {color}; font-weight: bold;")

        self.lbl_score_bar.setText(f"Composite Risk Score: {score:.1f} / 100.0 (Available Balance: {res['available_balance']} days, Requested: {res['duration_days']} days)")

        self.progress_risk.setValue(int(score))
        self.progress_risk.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")

        # Active risk factors table
        factors = res["risk_factors"]
        self.tbl_factors.setRowCount(0)

        for idx, f in enumerate(factors):
            self.tbl_factors.insertRow(idx)

            sev_item = QTableWidgetItem(f["severity"])
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if f["severity"] == "HIGH":
                sev_item.setForeground(QColor("#c62828"))
                sev_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            elif f["severity"] == "MEDIUM":
                sev_item.setForeground(QColor("#f57c00"))
                sev_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

            name_item = QTableWidgetItem(f["factor_name"])
            wt_item = QTableWidgetItem(f"+{f['weight']:.1f}")
            wt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            desc_item = QTableWidgetItem(f["description"])

            self.tbl_factors.setItem(idx, 0, sev_item)
            self.tbl_factors.setItem(idx, 1, name_item)
            self.tbl_factors.setItem(idx, 2, wt_item)
            self.tbl_factors.setItem(idx, 3, desc_item)

        # Intelligence signals summary
        ml = res["ml_prediction"]
        sub = res["substitute_recommendation"]

        sub_msg = f"{sub['faculty_name']} (score {sub['score']:.1f})" if sub else "None available"
        sig_str = (
            f"<b>NLP Intent Classification:</b> {ml['predicted_name']} ({ml['confidence_pct']} confidence) | "
            f"<b>Substitute Candidate:</b> {sub_msg}"
        )
        self.lbl_signals_summary.setText(sig_str)
