"""
ML Leave Classifiers & Benchmarks View (PySide6)
Displays model benchmark leaderboard, confusion matrix visualizer, re-training triggers, and real-time ML leave prediction playground.
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
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QFrame,
    QProgressBar,
    QSplitter,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.model_training_service import model_training_service
from nlp.classifiers import CLASSES
from nlp.dataset_generator import LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("ui.model_view")


class ModelView(QWidget):
    """PySide6 Desktop View displaying ML Benchmark Leaderboard and Live ML Predictor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_leaderboard = []
        self._init_ui()
        self.load_model_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Model Leaderboard & Confusion Matrix
        self.tab_leaderboard = QWidget()
        self._build_leaderboard_tab(self.tab_leaderboard)
        self.sub_tabs.addTab(self.tab_leaderboard, "Model Benchmark Leaderboard & Confusion Matrix")

        # Sub-Tab 2: Live ML Predictor & Decision Engine (Wrapped in QScrollArea for responsive scrolling)
        scroll_predictor = QScrollArea()
        scroll_predictor.setWidgetResizable(True)
        scroll_predictor.setFrameShape(QFrame.NoFrame)
        scroll_predictor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_predictor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.tab_predictor = QWidget()
        self._build_predictor_tab(self.tab_predictor)
        scroll_predictor.setWidget(self.tab_predictor)
        self.sub_tabs.addTab(scroll_predictor, "Live ML Leave Predictor & Decision Engine")

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

    def _build_leaderboard_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. KPI Cards
        cards_layout = QHBoxLayout()
        self.card_champion = self._create_kpi_card("Champion Model", "Naïve Bayes", "#1b365d")
        self.card_f1 = self._create_kpi_card("Champion Macro F1", "0.0%", "#2e7d32")
        self.card_accuracy = self._create_kpi_card("Champion Accuracy", "0.0%", "#1565c0")
        self.card_test_samples = self._create_kpi_card("Test Set Size", "100", "#c62828")

        cards_layout.addWidget(self.card_champion)
        cards_layout.addWidget(self.card_f1)
        cards_layout.addWidget(self.card_accuracy)
        cards_layout.addWidget(self.card_test_samples)

        tab_layout.addLayout(cards_layout)

        # 2. Main Splitter: Leaderboard Table (Left) & Confusion Matrix (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Model Benchmark Table
        left_group = QGroupBox("Model Performance Leaderboard (80/20 Stratified Split)")
        left_layout = QVBoxLayout(left_group)

        btn_layout = QHBoxLayout()
        self.btn_train_all = QPushButton("Train & Benchmark All Models")
        self.btn_train_all.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_train_all.clicked.connect(self.train_all_models)
        btn_layout.addWidget(self.btn_train_all)
        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)

        self.tbl_leaderboard = QTableWidget()
        self.tbl_leaderboard.setColumnCount(6)
        self.tbl_leaderboard.setHorizontalHeaderLabels(["Rank", "Classifier Model", "Accuracy", "Precision", "Recall", "Macro F1"])
        self.tbl_leaderboard.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_leaderboard.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_leaderboard.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_leaderboard.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_leaderboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_leaderboard.verticalHeader().setDefaultSectionSize(36)
        self.tbl_leaderboard.setAlternatingRowColors(True)
        self.tbl_leaderboard.itemSelectionChanged.connect(self.on_model_selection_changed)

        left_layout.addWidget(self.tbl_leaderboard)
        splitter.addWidget(left_group)

        # Right: 5x5 Confusion Matrix
        right_group = QGroupBox("Confusion Matrix (Actual vs Predicted)")
        right_layout = QVBoxLayout(right_group)

        self.lbl_cm_title = QLabel("<b>Model:</b> Champion Model")
        right_layout.addWidget(self.lbl_cm_title)

        self.tbl_cm = QTableWidget()
        self.tbl_cm.setColumnCount(5)
        self.tbl_cm.setRowCount(5)
        self.tbl_cm.setHorizontalHeaderLabels(CLASSES)
        self.tbl_cm.setVerticalHeaderLabels(CLASSES)
        self.tbl_cm.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_cm.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_cm.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_cm.verticalHeader().setDefaultSectionSize(36)
        self.tbl_cm.setAlternatingRowColors(True)

        right_layout.addWidget(self.tbl_cm)
        splitter.addWidget(right_group)

        splitter.setSizes([550, 450])
        tab_layout.addWidget(splitter, stretch=1)

    def _build_predictor_tab(self, parent_widget: QWidget):
        tab_layout = QHBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(15)

        # Left Column: Input Form & Test Presets
        left_group = QGroupBox("Leave Application Natural Language Input")
        left_layout = QVBoxLayout(left_group)

        left_layout.addWidget(QLabel("<b>Leave Reason Text:</b>"))
        self.txt_pred_input = QTextEdit()
        self.txt_pred_input.setPlaceholderText("e.g. Diagnosed with acute typhoid fever, doctor advised 5 days hospital bed rest.")
        self.txt_pred_input.setMinimumHeight(120)
        left_layout.addWidget(self.txt_pred_input)

        # Preset sample buttons
        presets_layout = QHBoxLayout()
        btn_p1 = QPushButton("Preset: Medical Leave")
        btn_p1.clicked.connect(lambda: self._set_preset("I am suffering from high viral fever and doctor advised 3 days bed rest.", 3.0, True))
        btn_p2 = QPushButton("Preset: Special Leave")
        btn_p2.clicked.connect(lambda: self._set_preset("Attending IEEE International Conference to present paper on Machine Learning.", 2.0, False))
        presets_layout.addWidget(btn_p1)
        presets_layout.addWidget(btn_p2)
        left_layout.addLayout(presets_layout)

        # Metadata Features Panel
        meta_group = QGroupBox("Contextual Metadata Features")
        meta_layout = QVBoxLayout(meta_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Requested Days:"))
        self.spn_pred_days = QDoubleSpinBox()
        self.spn_pred_days.setRange(0.5, 30.0)
        self.spn_pred_days.setValue(3.0)
        self.spn_pred_days.setSingleStep(0.5)
        row1.addWidget(self.spn_pred_days)

        row1.addWidget(QLabel("Notice Days:"))
        self.spn_pred_notice = QSpinBox()
        self.spn_pred_notice.setRange(0, 60)
        self.spn_pred_notice.setValue(0)
        row1.addWidget(self.spn_pred_notice)
        meta_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.chk_pred_doc = QCheckBox("Medical Doc Attached")
        self.chk_pred_doc.setChecked(True)
        self.chk_pred_sandwich = QCheckBox("Sandwich Leave Flag")
        row2.addWidget(self.chk_pred_doc)
        row2.addWidget(self.chk_pred_sandwich)
        meta_layout.addLayout(row2)

        left_layout.addWidget(meta_group)

        self.btn_predict = QPushButton("Classify Leave Reason (ML Inference)")
        self.btn_predict.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 13px; padding: 10px;")
        self.btn_predict.clicked.connect(self.run_ml_prediction)
        left_layout.addWidget(self.btn_predict)

        left_layout.addStretch()
        tab_layout.addWidget(left_group, stretch=4)

        # Right Column: Prediction Results & Probability Breakdown
        right_group = QGroupBox("ML Classification Prediction & Policy Recommendation")
        right_layout = QVBoxLayout(right_group)

        # Banner Box
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet("background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; padding: 12px;")
        banner_lay = QVBoxLayout(self.banner_frame)

        self.lbl_pred_result = QLabel("PREDICTED CATEGORY: ML (Medical Leave)")
        self.lbl_pred_result.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_pred_result.setStyleSheet("color: #2e7d32;")

        self.lbl_pred_confidence = QLabel("Confidence Score: 96.5% | Model: Multinomial Naïve Bayes")
        self.lbl_pred_confidence.setFont(QFont("Segoe UI", 10))
        self.lbl_pred_confidence.setStyleSheet("color: #444444;")

        banner_lay.addWidget(self.lbl_pred_result)
        banner_lay.addWidget(self.lbl_pred_confidence)
        right_layout.addWidget(self.banner_frame)

        # Probability Bars
        prob_group = QGroupBox("Class Probability Distribution")
        prob_lay = QVBoxLayout(prob_group)

        self.prob_bars = {}
        for cat in CLASSES:
            cat_name = LEAVE_CATEGORIES.get(cat, cat)
            row = QHBoxLayout()
            lbl = QLabel(f"<b>{cat}</b> ({cat_name}):")
            lbl.setFixedWidth(160)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)

            row.addWidget(lbl)
            row.addWidget(bar)
            prob_lay.addLayout(row)
            self.prob_bars[cat] = bar

        right_layout.addWidget(prob_group)

        # Policy Advice Alert Box
        advice_group = QGroupBox("Automated ERP Approval Workflow Advice")
        advice_lay = QVBoxLayout(advice_group)

        self.lbl_advice = QLabel("ROUTE: Medical Leave application automatically flagged for HOD verification.")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setStyleSheet("font-size: 11px; color: #1565c0; font-weight: bold;")
        advice_lay.addWidget(self.lbl_advice)

        right_layout.addWidget(advice_group)
        right_layout.addStretch()

        tab_layout.addWidget(right_group, stretch=6)

    def _set_preset(self, text: str, days: float, doc: bool):
        self.txt_pred_input.setPlainText(text)
        self.spn_pred_days.setValue(days)
        self.chk_pred_doc.setChecked(doc)
        self.run_ml_prediction()

    def load_model_data(self):
        """Loads or trains ML classifiers and populates leaderboard table."""
        try:
            if model_training_service.leaderboard_cache:
                leaderboard = model_training_service.leaderboard_cache
            elif model_training_service.model_path.exists():
                model_training_service.ensure_best_model_loaded()
                leaderboard = model_training_service.leaderboard_cache
            else:
                leaderboard = None

            if not leaderboard:
                leaderboard = model_training_service.train_and_evaluate_all_models()

            self.current_leaderboard = leaderboard
            self._update_leaderboard_display(leaderboard)

        except Exception as exc:
            logger.error(f"Failed to load ML model data: {exc}")
            QMessageBox.warning(self, "ML Error", f"Could not load ML models: {exc}")

    def train_all_models(self):
        """Forces re-training of all 4 ML candidate models asynchronously without freezing the GUI."""
        from ui.worker import WorkerThread

        self.btn_train_all.setEnabled(False)
        self.btn_train_all.setText("Training Models in Background...")

        def _bg_train():
            return model_training_service.train_and_evaluate_all_models()

        worker = WorkerThread(_bg_train)

        def _on_success(leaderboard):
            self.current_leaderboard = leaderboard
            self._update_leaderboard_display(leaderboard)
            self.btn_train_all.setEnabled(True)
            self.btn_train_all.setText("Train & Benchmark All Models")
            QMessageBox.information(self, "Success", "All ML classifiers trained and benchmarked successfully.")

        def _on_error(err_str):
            self.btn_train_all.setEnabled(True)
            self.btn_train_all.setText("Train & Benchmark All Models")
            QMessageBox.critical(self, "Training Error", f"Could not train models:\n{err_str}")

        worker.result.connect(_on_success)
        worker.error.connect(_on_error)
        worker.start()
        self._training_worker = worker

    def _update_leaderboard_display(self, leaderboard):
        if not leaderboard:
            return

        champion = leaderboard[0]
        self._update_kpi_value(self.card_champion, champion["model_name"])
        self._update_kpi_value(self.card_f1, f"{champion['macro_f1']*100:.1f}%")
        self._update_kpi_value(self.card_accuracy, f"{champion['accuracy']*100:.1f}%")
        self._update_kpi_value(self.card_test_samples, str(champion["test_sample_count"]))

        self.tbl_leaderboard.setRowCount(0)
        for idx, item in enumerate(leaderboard):
            self.tbl_leaderboard.insertRow(idx)

            rank_item = QTableWidgetItem(f"#{idx + 1}")
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            name_item = QTableWidgetItem(item["model_name"])

            if idx == 0:
                name_item.setText(f"⭐ {item['model_name']} (CHAMPION)")
                name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                name_item.setBackground(QColor("#d4edda"))

            acc_item = QTableWidgetItem(f"{item['accuracy']*100:.1f}%")
            prec_item = QTableWidgetItem(f"{item['macro_precision']*100:.1f}%")
            rec_item = QTableWidgetItem(f"{item['macro_recall']*100:.1f}%")
            f1_item = QTableWidgetItem(f"{item['macro_f1']*100:.1f}%")

            for it in [acc_item, prec_item, rec_item, f1_item]:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.tbl_leaderboard.setItem(idx, 0, rank_item)
            self.tbl_leaderboard.setItem(idx, 1, name_item)
            self.tbl_leaderboard.setItem(idx, 2, acc_item)
            self.tbl_leaderboard.setItem(idx, 3, prec_item)
            self.tbl_leaderboard.setItem(idx, 4, rec_item)
            self.tbl_leaderboard.setItem(idx, 5, f1_item)

        self.tbl_leaderboard.selectRow(0)

    def on_model_selection_changed(self):
        selected_rows = self.tbl_leaderboard.selectedIndexes()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < len(self.current_leaderboard):
            item = self.current_leaderboard[row]
            self.lbl_cm_title.setText(f"<b>Confusion Matrix for:</b> {item['model_name']} (Macro F1: {item['macro_f1']*100:.1f}%)")

            cm = item["confusion_matrix"]
            for r_idx, actual in enumerate(CLASSES):
                for c_idx, pred in enumerate(CLASSES):
                    val = cm.get(actual, {}).get(pred, 0)
                    cell = QTableWidgetItem(str(val))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if r_idx == c_idx:
                        cell.setBackground(QColor("#c8e6c9"))  # Diagonal correct prediction
                        cell.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                    elif val > 0:
                        cell.setBackground(QColor("#ffcdd2"))  # Misclassification

                    self.tbl_cm.setItem(r_idx, c_idx, cell)

    def run_ml_prediction(self):
        text = self.txt_pred_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Input", "Please enter natural language text to classify.")
            return

        metadata = {
            "requested_days": self.spn_pred_days.value(),
            "notice_period_days": self.spn_pred_notice.value(),
            "has_medical_doc": self.chk_pred_doc.isChecked(),
            "is_sandwich_leave": self.chk_pred_sandwich.isChecked(),
        }

        def _apply_result(res):
            pred_cat = res["predicted_category"]
            cat_name = res["category_name"]
            conf_pct = res["confidence_percentage"]
            champion = res["champion_model"]

            self.lbl_pred_result.setText(f"PREDICTED CATEGORY: {pred_cat} ({cat_name})")
            self.lbl_pred_confidence.setText(f"Confidence Score: {conf_pct} | Model: {champion}")

            probs = res["probabilities"]
            for cat in CLASSES:
                prob_val = int(probs.get(cat, 0.0) * 100)
                if cat in self.prob_bars:
                    self.prob_bars[cat].setValue(prob_val)

            self.lbl_advice.setText(res["routing_advice"])

        # If testing under pytest without an active event loop, execute synchronously
        if "pytest" in sys.modules:
            res = model_training_service.predict_leave_reason(text, metadata)
            _apply_result(res)
            return

        from ui.worker import WorkerThread
        def _bg_infer():
            return model_training_service.predict_leave_reason(text, metadata)

        worker = WorkerThread(_bg_infer)
        worker.result.connect(_apply_result)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._pred_worker = worker

    def closeEvent(self, event):
        if hasattr(self, "_training_worker") and self._training_worker:
            self._training_worker.stop()
        if hasattr(self, "_pred_worker") and self._pred_worker:
            self._pred_worker.stop()
        super().closeEvent(event)
