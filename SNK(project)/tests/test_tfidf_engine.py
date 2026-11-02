"""
Phase 11 TF-IDF Vectorization & Feature Engineering Unit Tests
Verifies TFIDFEngine (fitting, transform, vocabulary, n-grams, joblib persistence),
FeatureExtractor (metadata normalization, composite vector concatenation),
TFIDFService facade methods, and PySide6 FeatureView desktop interface.
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import pytest
import numpy as np
from PySide6.QtWidgets import QApplication, QLabel

from nlp.vectorizer import TFIDFEngine, tfidf_engine
from nlp.feature_extractor import FeatureExtractor, feature_extractor
from services.tfidf_service import TFIDFService, tfidf_service
from ui.feature_view import FeatureView


@pytest.fixture
def qapp():
    """Ensure a PySide6 QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_tfidf_engine_fit_transform_persistence():
    """Test TFIDFEngine vectorization, n-grams, top terms, and joblib save/load."""
    engine = TFIDFEngine(max_features=100, ngram_range=(1, 2))

    corpus = [
        "Doctor advised rest due to severe fever and infection.",
        "Attending national level conference on machine learning in Delhi.",
        "Family function emergency at native place needing casual leave.",
    ]

    # Fit and transform
    matrix = engine.fit_transform(corpus)
    assert engine.is_fitted is True
    assert isinstance(matrix, np.ndarray)
    assert matrix.shape[0] == 3
    assert matrix.shape[1] > 0

    # Feature names
    features = engine.get_feature_names()
    assert len(features) > 0
    assert any(" " in f for f in features)  # Check bigram present

    # Top terms for text
    top_terms = engine.get_top_terms_for_text("severe fever and doctor advice", top_k=5)
    assert len(top_terms) > 0
    assert isinstance(top_terms[0], tuple)
    assert top_terms[0][1] > 0

    # Test persistence (save and load)
    test_path = "models/test_tfidf.joblib"
    saved_path = engine.save_model(test_path)
    assert os.path.exists(saved_path)

    new_engine = TFIDFEngine()
    loaded = new_engine.load_model(test_path)
    assert loaded is True
    assert new_engine.is_fitted is True
    assert len(new_engine.get_feature_names()) == len(features)

    # Clean up test artifact
    if os.path.exists(test_path):
        os.remove(test_path)


def test_feature_extractor_composite_matrix():
    """Test metadata normalization and composite feature vector concatenation."""
    extractor = FeatureExtractor()

    metadata = {
        "requested_days": 3.0,
        "notice_period_days": 0.0,
        "has_medical_doc": True,
        "is_sandwich_leave": False,
    }

    # Metadata vector extraction
    meta_vec = extractor.extract_metadata_features(metadata)
    assert len(meta_vec) == 4
    assert meta_vec[0] == 0.3  # 3.0 / 10.0
    assert meta_vec[1] == 0.0  # 0.0 / 30.0
    assert meta_vec[2] == 1.0  # True
    assert meta_vec[3] == 0.0  # False

    # Ensure vectorizer is fitted first
    tfidf_engine.fit(["Doctor advised bed rest for severe fever.", "Attending conference in Bangalore."])

    # Composite vector extraction
    comp_vec = extractor.extract_composite_features("Doctor advised bed rest.", metadata)
    assert len(comp_vec) == len(tfidf_engine.get_feature_names()) + 4

    # Batch extraction
    batch_comp = extractor.batch_extract_composite_features(
        ["Doctor rest.", "Conference."],
        [metadata, metadata],
    )
    assert batch_comp.shape[0] == 2
    assert batch_comp.shape[1] == len(tfidf_engine.get_feature_names()) + 4


def test_tfidf_service_facade():
    """Test TFIDFService facade operations."""
    service = TFIDFService()
    fitted_engine = service.ensure_fitted(force_refit=True)
    assert fitted_engine.is_fitted is True

    # Summary
    summary = service.get_vocabulary_summary()
    assert summary["total_features"] > 0
    assert summary["unigram_count"] > 0
    assert summary["bigram_count"] > 0

    # Category top n-grams
    cat_ngrams = service.get_top_ngrams_per_category(top_k=5)
    assert "CL" in cat_ngrams
    assert "ML" in cat_ngrams
    assert len(cat_ngrams["ML"]) > 0

    # Inspection
    inspection = service.inspect_text_vector("Admitted to hospital for appendicitis surgery.")
    assert inspection["composite_dimension"] > 4
    assert len(inspection["top_tfidf_terms"]) > 0


def test_feature_view_gui(qapp):
    """Verify PySide6 FeatureView widget instantiates, displays vocabulary, and runs inspection."""
    view = FeatureView()
    assert view is not None
    assert view.sub_tabs.count() == 2

    # Check total features card
    val_lbl = view.card_total_feats.findChild(QLabel, "value_label")
    assert val_lbl is not None
    assert int(val_lbl.text()) > 0

    # Check category ngrams table rows populated
    assert view.tbl_category_ngrams.rowCount() > 0

    # Test vocabulary filter
    view.txt_vocab_search.setText("fever")
    view.filter_vocabulary_display()
    assert view.tbl_vocab.rowCount() >= 0

    # Test inspector tab action
    view.txt_inspect_input.setPlainText("Doctor advised rest for severe migraine headache.")
    view.spn_req_days.setValue(2.0)
    view.chk_med_doc.setChecked(True)
    view.run_vector_inspection()
    assert view.tbl_non_zero.rowCount() > 0
