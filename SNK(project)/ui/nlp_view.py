"""
NLP Leave Reason Corpus & Preprocessing View (PySide6)
Displays NLP corpus dataset metrics, category distribution, search explorer, and live text preprocessing pipeline inspection.
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
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.nlp_service import nlp_service
from utils.logger import get_logger

logger = get_logger("ui.nlp_view")


class NLPView(QWidget):
    """PySide6 Desktop View displaying Corpus Dataset Explorer and Live NLP Preprocessing Tester."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_corpus_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Corpus Dataset Explorer
        self.tab_explorer = QWidget()
        self._build_explorer_tab(self.tab_explorer)
        self.sub_tabs.addTab(self.tab_explorer, "Corpus Dataset Explorer & Class Distribution")

        # Sub-Tab 2: Live Text Preprocessing Tester
        self.tab_tester = QWidget()
        self._build_tester_tab(self.tab_tester)
        self.sub_tabs.addTab(self.tab_tester, "Live Text Preprocessing Tester")

        main_layout.addWidget(self.sub_tabs)

    def _build_explorer_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. KPI Metrics Banner
        cards_layout = QHBoxLayout()
        self.card_total_samples = self._create_kpi_card("Total Corpus Samples", "0", "#1b365d")
        self.card_cl_cnt = self._create_kpi_card("CL (Casual Leave)", "0", "#2e7d32")
        self.card_ml_cnt = self._create_kpi_card("ML (Medical Leave)", "0", "#c62828")
        self.card_other_cnt = self._create_kpi_card("EL / SCL / OD Counts", "0", "#1565c0")

        cards_layout.addWidget(self.card_total_samples)
        cards_layout.addWidget(self.card_cl_cnt)
        cards_layout.addWidget(self.card_ml_cnt)
        cards_layout.addWidget(self.card_other_cnt)

        tab_layout.addLayout(cards_layout)

        # 2. Filter & Search Control Panel
        filter_group = QGroupBox("Corpus Explorer Controls")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("<b>Leave Category:</b>"))
        self.combo_category = QComboBox()
        self.combo_category.addItems(["ALL", "CL", "ML", "EL", "SCL", "OD"])
        filter_layout.addWidget(self.combo_category)

        filter_layout.addWidget(QLabel("<b>Search Keyword:</b>"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filter text reasons...")
        filter_layout.addWidget(self.txt_search)

        self.btn_filter = QPushButton("Filter Corpus")
        self.btn_filter.clicked.connect(self.filter_corpus_display)
        filter_layout.addWidget(self.btn_filter)

        self.btn_reload = QPushButton("Regenerate / Reload Corpus")
        self.btn_reload.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold;")
        self.btn_reload.clicked.connect(self.load_corpus_data)
        filter_layout.addWidget(self.btn_reload)

        filter_layout.addStretch()
        tab_layout.addWidget(filter_group)

        # 3. Dataset Table
        tbl_group = QGroupBox("Leave Reasons Dataset (500+ Natural Language Applications)")
        tbl_layout = QVBoxLayout(tbl_group)

        self.tbl_corpus = QTableWidget()
        self.tbl_corpus.setColumnCount(5)
        self.tbl_corpus.setHorizontalHeaderLabels(
            [
                "Sample ID",
                "Code",
                "Leave Category Name",
                "Raw Natural Language Text Reason",
                "Preprocessed String Output",
            ]
        )
        self.tbl_corpus.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_corpus.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_corpus.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_corpus.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_corpus.setAlternatingRowColors(True)
        self.tbl_corpus.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_corpus.verticalHeader().setDefaultSectionSize(36)

        tbl_layout.addWidget(self.tbl_corpus)
        tab_layout.addWidget(tbl_group, stretch=1)

    def _build_tester_tab(self, parent_widget: QWidget):
        tab_layout = QHBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(15)

        # Left Column: Input Controls & Presets
        left_group = QGroupBox("Text Input & Test Presets")
        left_layout = QVBoxLayout(left_group)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("<b>Enter Natural Language Leave Reason:</b>"))
        self.txt_test_input = QTextEdit()
        self.txt_test_input.setPlaceholderText(
            "Type or paste any leave reason text here (e.g., 'I am suffering from severe high fever and doctor advised 3 days bed rest')..."
        )
        self.txt_test_input.setMaximumHeight(120)
        left_layout.addWidget(self.txt_test_input)

        # Quick Preset Buttons
        left_layout.addWidget(QLabel("<b>Quick Test Presets:</b>"))
        btn_preset1 = QPushButton("Preset 1: High Fever & Doctor Bed Rest (ML)")
        btn_preset1.clicked.connect(
            lambda: self.txt_test_input.setText("I am suffering from severe viral fever and doctor advised 3 days bed rest.")
        )
        left_layout.addWidget(btn_preset1)

        btn_preset2 = QPushButton("Preset 2: IEEE Conference Presentation (SCL)")
        btn_preset2.clicked.connect(
            lambda: self.txt_test_input.setText("Attending IEEE International Conference on Artificial Intelligence to present research paper.")
        )
        left_layout.addWidget(btn_preset2)

        btn_preset3 = QPushButton("Preset 3: Family Function & RTO Work (CL)")
        btn_preset3.clicked.connect(
            lambda: self.txt_test_input.setText("Need 2 days leave to attend family wedding function and personal work at RTO office.")
        )
        left_layout.addWidget(btn_preset3)

        btn_preset4 = QPushButton("Preset 4: University Exam Valuation Duty (OD)")
        btn_preset4.clicked.connect(
            lambda: self.txt_test_input.setText("Deputed for university semester practical examination central evaluation duty as external examiner.")
        )
        left_layout.addWidget(btn_preset4)

        self.btn_process = QPushButton("Process Text Through Pipeline")
        self.btn_process.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; padding: 10px;")
        self.btn_process.clicked.connect(self.on_process_click)
        left_layout.addWidget(self.btn_process)

        left_layout.addStretch()
        tab_layout.addWidget(left_group, stretch=1)

        # Right Column: Pipeline Stages Output Display
        right_group = QGroupBox("Preprocessing Pipeline Stage Inspection Results")
        right_layout = QVBoxLayout(right_group)
        right_layout.setSpacing(8)

        right_layout.addWidget(QLabel("<b>Stage 1: Cleaned Text (Lowercased & Punctuation Stripped):</b>"))
        self.txt_out_clean = QTextEdit()
        self.txt_out_clean.setReadOnly(True)
        self.txt_out_clean.setMaximumHeight(60)
        right_layout.addWidget(self.txt_out_clean)

        right_layout.addWidget(QLabel("<b>Stage 2: Filtered Tokens (Stopwords Removed):</b>"))
        self.txt_out_tokens = QTextEdit()
        self.txt_out_tokens.setReadOnly(True)
        self.txt_out_tokens.setMaximumHeight(60)
        right_layout.addWidget(self.txt_out_tokens)

        right_layout.addWidget(QLabel("<b>Stage 3: Lemmatized Base Tokens:</b>"))
        self.txt_out_lemmas = QTextEdit()
        self.txt_out_lemmas.setReadOnly(True)
        self.txt_out_lemmas.setMaximumHeight(60)
        right_layout.addWidget(self.txt_out_lemmas)

        right_layout.addWidget(QLabel("<b>Stage 4: Final Normalized Preprocessed String Output:</b>"))
        self.txt_out_final = QTextEdit()
        self.txt_out_final.setReadOnly(True)
        self.txt_out_final.setStyleSheet("background-color: #1e1e1e; color: #00ff66; font-weight: bold;")
        self.txt_out_final.setMaximumHeight(60)
        right_layout.addWidget(self.txt_out_final)

        tab_layout.addWidget(right_group, stretch=1)

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

    def load_corpus_data(self):
        """Loads dataset and updates statistics & table."""
        try:
            stats = nlp_service.get_corpus_statistics()
            self._update_kpi_value(self.card_total_samples, str(stats["total_samples"]))

            counts = stats["class_counts"]
            self._update_kpi_value(self.card_cl_cnt, str(counts.get("CL", 0)))
            self._update_kpi_value(self.card_ml_cnt, str(counts.get("ML", 0)))

            other_total = counts.get("EL", 0) + counts.get("SCL", 0) + counts.get("OD", 0)
            self._update_kpi_value(self.card_other_cnt, f"{other_total} (EL:{counts.get('EL',0)} SCL:{counts.get('SCL',0)} OD:{counts.get('OD',0)})")

            self.full_corpus = nlp_service.load_corpus()
            self.filter_corpus_display()

        except Exception as exc:
            logger.error(f"Failed to load NLP corpus: {exc}")
            QMessageBox.warning(self, "Corpus Error", f"Could not load NLP corpus: {exc}")

    def filter_corpus_display(self):
        """Filters displayed table rows based on category combo and search text."""
        cat_flt = self.combo_category.currentText()
        search_kw = self.txt_search.text().strip().lower()

        filtered = []
        for item in self.full_corpus:
            if cat_flt != "ALL" and item.get("label") != cat_flt:
                continue
            if search_kw and search_kw not in item.get("text", "").lower():
                continue
            filtered.append(item)

        self.tbl_corpus.setRowCount(0)
        for row_idx, item in enumerate(filtered):
            self.tbl_corpus.insertRow(row_idx)

            item_id = QTableWidgetItem(str(item.get("id", "")))
            item_code = QTableWidgetItem(item.get("label", ""))
            item_code.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl = item.get("label", "CL")
            if lbl == "CL":
                item_code.setBackground(QColor("#d4edda"))
                item_code.setForeground(QColor("#155724"))
            elif lbl == "ML":
                item_code.setBackground(QColor("#f8d7da"))
                item_code.setForeground(QColor("#721c24"))
            elif lbl in ["SCL", "OD"]:
                item_code.setBackground(QColor("#d1ecf1"))
                item_code.setForeground(QColor("#0c5460"))
            else:
                item_code.setBackground(QColor("#fff3cd"))
                item_code.setForeground(QColor("#856404"))

            item_name = QTableWidgetItem(item.get("leave_type_name", ""))
            raw_text = item.get("text", "")
            item_text = QTableWidgetItem(raw_text)

            prep = nlp_service.preprocess_text(raw_text)
            item_prep = QTableWidgetItem(prep.get("processed_string", ""))

            self.tbl_corpus.setItem(row_idx, 0, item_id)
            self.tbl_corpus.setItem(row_idx, 1, item_code)
            self.tbl_corpus.setItem(row_idx, 2, item_name)
            self.tbl_corpus.setItem(row_idx, 3, item_text)
            self.tbl_corpus.setItem(row_idx, 4, item_prep)

    def on_process_click(self):
        raw_input = self.txt_test_input.toPlainText().strip()
        if not raw_input:
            QMessageBox.warning(self, "Empty Input", "Please enter natural language text to process.")
            return

        res = nlp_service.preprocess_text(raw_input)

        self.txt_out_clean.setText(res.get("cleaned_text", ""))
        self.txt_out_tokens.setText(", ".join(res.get("filtered_tokens", [])))
        self.txt_out_lemmas.setText(", ".join(res.get("lemmatized_tokens", [])))
        self.txt_out_final.setText(res.get("processed_string", ""))
