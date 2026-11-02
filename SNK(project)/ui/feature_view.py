"""
TF-IDF Feature Matrix & Vectorizer View (PySide6)
Displays vocabulary metrics, top n-grams per leave category, interactive vocabulary search, and live TF-IDF vector inspection.
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
    QSplitter,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from services.tfidf_service import tfidf_service
from nlp.dataset_generator import LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("ui.feature_view")


class FeatureView(QWidget):
    """PySide6 Desktop View displaying TF-IDF Vocabulary Explorer and Live Vector Inspector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_feature_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.sub_tabs = QTabWidget()

        # Sub-Tab 1: Vocabulary & Top N-Grams Explorer
        self.tab_vocab = QWidget()
        self._build_vocab_tab(self.tab_vocab)
        self.sub_tabs.addTab(self.tab_vocab, "Vocabulary & Category N-Grams Explorer")

        # Sub-Tab 2: Live TF-IDF Vector Inspector
        self.tab_inspector = QWidget()
        self._build_inspector_tab(self.tab_inspector)
        self.sub_tabs.addTab(self.tab_inspector, "Live TF-IDF & Feature Inspector")

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

    def _build_vocab_tab(self, parent_widget: QWidget):
        tab_layout = QVBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)

        # 1. KPI Metrics Cards
        cards_layout = QHBoxLayout()
        self.card_total_feats = self._create_kpi_card("Total TF-IDF Features", "0", "#1b365d")
        self.card_unigram_cnt = self._create_kpi_card("Unigrams (1-grams)", "0", "#2e7d32")
        self.card_bigram_cnt = self._create_kpi_card("Bigrams (2-grams)", "0", "#1565c0")
        self.card_model_status = self._create_kpi_card("Engine Status", "Fitted", "#c62828")

        cards_layout.addWidget(self.card_total_feats)
        cards_layout.addWidget(self.card_unigram_cnt)
        cards_layout.addWidget(self.card_bigram_cnt)
        cards_layout.addWidget(self.card_model_status)

        tab_layout.addLayout(cards_layout)

        # 2. Main Content Splitter: Top Category N-Grams (Left) & Full Vocabulary Table (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Category Top N-Grams
        left_group = QGroupBox("Top Discriminative N-Grams by Leave Category")
        left_layout = QVBoxLayout(left_group)

        self.tbl_category_ngrams = QTableWidget()
        self.tbl_category_ngrams.setColumnCount(3)
        self.tbl_category_ngrams.setHorizontalHeaderLabels(["Category", "N-Gram Feature", "Mean Weight"])
        self.tbl_category_ngrams.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_category_ngrams.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_category_ngrams.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_category_ngrams.setAlternatingRowColors(True)
        self.tbl_category_ngrams.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_category_ngrams.verticalHeader().setDefaultSectionSize(36)
        left_layout.addWidget(self.tbl_category_ngrams)

        splitter.addWidget(left_group)

        # Right: Full Vocabulary Search Table
        right_group = QGroupBox("Full Vocabulary N-Gram Feature Index")
        right_layout = QVBoxLayout(right_group)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("<b>Filter Vocabulary:</b>"))
        self.txt_vocab_search = QLineEdit()
        self.txt_vocab_search.setPlaceholderText("Search n-gram features...")
        self.txt_vocab_search.textChanged.connect(self.filter_vocabulary_display)
        search_layout.addWidget(self.txt_vocab_search)

        self.btn_refit = QPushButton("Re-Fit Vectorizer")
        self.btn_refit.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold;")
        self.btn_refit.clicked.connect(self.refit_vectorizer)
        search_layout.addWidget(self.btn_refit)

        right_layout.addLayout(search_layout)

        self.tbl_vocab = QTableWidget()
        self.tbl_vocab.setColumnCount(3)
        self.tbl_vocab.setHorizontalHeaderLabels(["Index", "N-Gram Feature", "Type"])
        self.tbl_vocab.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_vocab.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_vocab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_vocab.setAlternatingRowColors(True)
        self.tbl_vocab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_vocab.verticalHeader().setDefaultSectionSize(36)

        right_layout.addWidget(self.tbl_vocab)
        splitter.addWidget(right_group)

        splitter.setSizes([450, 550])
        tab_layout.addWidget(splitter, stretch=1)

    def _build_inspector_tab(self, parent_widget: QWidget):
        tab_layout = QHBoxLayout(parent_widget)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(15)

        # Left Column: Input Form & Controls
        left_group = QGroupBox("Live Text & Metadata Input")
        left_layout = QVBoxLayout(left_group)

        left_layout.addWidget(QLabel("<b>Raw Natural Language Reason:</b>"))
        self.txt_inspect_input = QTextEdit()
        self.txt_inspect_input.setPlaceholderText("e.g. Doctor advised 3 days bed rest due to severe fever and infection.")
        self.txt_inspect_input.setMinimumHeight(120)
        left_layout.addWidget(self.txt_inspect_input)

        # Tabular metadata controls
        meta_group = QGroupBox("Tabular Metadata Features")
        meta_layout = QVBoxLayout(meta_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Requested Days:"))
        self.spn_req_days = QDoubleSpinBox()
        self.spn_req_days.setRange(0.5, 30.0)
        self.spn_req_days.setValue(3.0)
        self.spn_req_days.setSingleStep(0.5)
        row1.addWidget(self.spn_req_days)

        row1.addWidget(QLabel("Notice Days:"))
        self.spn_notice_days = QSpinBox()
        self.spn_notice_days.setRange(0, 60)
        self.spn_notice_days.setValue(0)
        row1.addWidget(self.spn_notice_days)
        meta_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.chk_med_doc = QCheckBox("Medical Doc Attached")
        self.chk_med_doc.setChecked(True)
        self.chk_sandwich = QCheckBox("Sandwich Leave Flag")
        row2.addWidget(self.chk_med_doc)
        row2.addWidget(self.chk_sandwich)
        meta_layout.addLayout(row2)

        left_layout.addWidget(meta_group)

        self.btn_inspect = QPushButton("Extract & Inspect Feature Vector")
        self.btn_inspect.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 13px; padding: 8px;")
        self.btn_inspect.clicked.connect(self.run_vector_inspection)
        left_layout.addWidget(self.btn_inspect)

        left_layout.addStretch()
        tab_layout.addWidget(left_group, stretch=4)

        # Right Column: Extracted Non-Zero Features Table & Dimensionality Summary
        right_group = QGroupBox("Extracted Non-Zero Features & Weight Vector")
        right_layout = QVBoxLayout(right_group)

        # Dim Badge Banner
        self.lbl_dim_info = QLabel("<b>Composite Vector Dimension:</b> 0 (TF-IDF: 0 + Metadata: 4)")
        self.lbl_dim_info.setStyleSheet("background-color: #e8f4f8; border: 1px solid #bce8f1; padding: 6px; border-radius: 4px; color: #0c5460;")
        right_layout.addWidget(self.lbl_dim_info)

        self.tbl_non_zero = QTableWidget()
        self.tbl_non_zero.setColumnCount(3)
        self.tbl_non_zero.setHorizontalHeaderLabels(["Rank", "Feature (N-Gram / Metadata)", "Extracted Weight Score"])
        self.tbl_non_zero.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_non_zero.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_non_zero.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_non_zero.setAlternatingRowColors(True)
        self.tbl_non_zero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tbl_non_zero.verticalHeader().setDefaultSectionSize(36)

        right_layout.addWidget(self.tbl_non_zero)
        tab_layout.addWidget(right_group, stretch=6)

    def load_feature_data(self):
        """Loads fitted vectorizer statistics, category top n-grams, and vocabulary table."""
        try:
            summary = tfidf_service.get_vocabulary_summary()
            self._update_kpi_value(self.card_total_feats, str(summary["total_features"]))
            self._update_kpi_value(self.card_unigram_cnt, str(summary["unigram_count"]))
            self._update_kpi_value(self.card_bigram_cnt, str(summary["bigram_count"]))
            self._update_kpi_value(self.card_model_status, "Fitted & Saved" if summary["is_fitted"] else "Unfitted")

            # Load Top N-Grams per Category
            cat_ngrams = tfidf_service.get_top_ngrams_per_category(top_k=8)
            self.tbl_category_ngrams.setRowCount(0)

            row_idx = 0
            for cat, terms in cat_ngrams.items():
                cat_name = LEAVE_CATEGORIES.get(cat, cat)
                for term, weight in terms:
                    self.tbl_category_ngrams.insertRow(row_idx)
                    item_cat = QTableWidgetItem(f"{cat} ({cat_name})")
                    item_term = QTableWidgetItem(term)
                    item_wt = QTableWidgetItem(f"{weight:.4f}")
                    item_wt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if cat == "CL":
                        item_cat.setBackground(QColor("#d4edda"))
                    elif cat == "ML":
                        item_cat.setBackground(QColor("#f8d7da"))
                    elif cat in ["SCL", "OD"]:
                        item_cat.setBackground(QColor("#d1ecf1"))
                    else:
                        item_cat.setBackground(QColor("#fff3cd"))

                    self.tbl_category_ngrams.setItem(row_idx, 0, item_cat)
                    self.tbl_category_ngrams.setItem(row_idx, 1, item_term)
                    self.tbl_category_ngrams.setItem(row_idx, 2, item_wt)
                    row_idx += 1

            self.full_vocab = tfidf_service.vectorizer.get_feature_names()
            self.filter_vocabulary_display()

        except Exception as exc:
            logger.error(f"Failed to load TF-IDF feature data: {exc}")
            QMessageBox.warning(self, "Feature Error", f"Could not load TF-IDF features: {exc}")

    def filter_vocabulary_display(self):
        """Filters vocabulary search table based on query string."""
        kw = self.txt_vocab_search.text().strip().lower()

        filtered = [
            (idx, feat)
            for idx, feat in enumerate(self.full_vocab)
            if not kw or kw in feat.lower()
        ]

        self.tbl_vocab.setRowCount(0)
        for row_idx, (idx, feat) in enumerate(filtered):
            self.tbl_vocab.insertRow(row_idx)
            item_idx = QTableWidgetItem(str(idx))
            item_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_feat = QTableWidgetItem(feat)
            feat_type = "Bigram (2-gram)" if " " in feat else "Unigram (1-gram)"
            item_type = QTableWidgetItem(feat_type)

            self.tbl_vocab.setItem(row_idx, 0, item_idx)
            self.tbl_vocab.setItem(row_idx, 1, item_feat)
            self.tbl_vocab.setItem(row_idx, 2, item_type)

    def refit_vectorizer(self):
        """Forces refitting of TF-IDF vectorizer on corpus dataset."""
        try:
            tfidf_service.ensure_fitted(force_refit=True)
            self.load_feature_data()
            QMessageBox.information(self, "Success", "TF-IDF Vectorizer refitted and saved successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Refit Failed", f"Could not refit vectorizer: {exc}")

    def run_vector_inspection(self):
        """Executes feature extraction for live text and metadata input."""
        text = self.txt_inspect_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Input", "Please enter natural language text to inspect.")
            return

        metadata = {
            "requested_days": self.spn_req_days.value(),
            "notice_period_days": self.spn_notice_days.value(),
            "has_medical_doc": self.chk_med_doc.isChecked(),
            "is_sandwich_leave": self.chk_sandwich.isChecked(),
        }

        res = tfidf_service.inspect_text_vector(text, metadata)

        dim_msg = (
            f"<b>Composite Vector Dimension:</b> {res['composite_dimension']} "
            f"(TF-IDF Text Features: {res['tfidf_dimension']} + Metadata Features: 4)"
        )
        self.lbl_dim_info.setText(dim_msg)

        # Populate non-zero features table
        self.tbl_non_zero.setRowCount(0)

        # 1. TF-IDF Non-Zero Terms
        top_terms = res["top_tfidf_terms"]
        rank = 1
        for term, weight in top_terms:
            self.tbl_non_zero.insertRow(rank - 1)
            item_rank = QTableWidgetItem(str(rank))
            item_rank.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_term = QTableWidgetItem(f"[TF-IDF] {term}")
            item_wt = QTableWidgetItem(f"{weight:.4f}")
            item_wt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.tbl_non_zero.setItem(rank - 1, 0, item_rank)
            self.tbl_non_zero.setItem(rank - 1, 1, item_term)
            self.tbl_non_zero.setItem(rank - 1, 2, item_wt)
            rank += 1

        # 2. Metadata Features
        meta_vec = res["metadata_features"]
        meta_names = ["req_days_norm", "notice_days_norm", "has_medical_doc", "is_sandwich_leave"]
        for name, val in zip(meta_names, meta_vec):
            r_idx = self.tbl_non_zero.rowCount()
            self.tbl_non_zero.insertRow(r_idx)
            item_rank = QTableWidgetItem("-")
            item_rank.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_term = QTableWidgetItem(f"[Metadata] {name}")
            item_term.setBackground(QColor("#e2e3e5"))
            item_wt = QTableWidgetItem(f"{val:.4f}")
            item_wt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.tbl_non_zero.setItem(r_idx, 0, item_rank)
            self.tbl_non_zero.setItem(r_idx, 1, item_term)
            self.tbl_non_zero.setItem(r_idx, 2, item_wt)
