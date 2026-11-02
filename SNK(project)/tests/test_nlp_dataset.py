"""
Phase 10 NLP Dataset & Text Preprocessing Unit Tests
Verifies TextPreprocessor (cleaning, tokenization, stopword removal, lemmatization),
dataset generation (500+ records across 5 categories), NLPService facade methods,
and PySide6 NLPView desktop interface instantiation and filtering.
"""
import sys
import os
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QLabel

from nlp.preprocessor import TextPreprocessor, preprocessor
from nlp.dataset_generator import verify_and_build_dataset, LEAVE_CATEGORIES
from services.nlp_service import NLPService, nlp_service
from ui.nlp_view import NLPView


@pytest.fixture
def qapp():
    """Ensure a PySide6 QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_text_preprocessor_pipeline():
    """Test individual components and end-to-end preprocessing pipeline."""
    tp = TextPreprocessor()

    raw_sample = "<b>URGENT:</b> I am suffering from severe feverish temperature and doctor's advice!!"
    
    # Clean text
    cleaned = tp.clean_text(raw_sample)
    assert "<" not in cleaned and ">" not in cleaned
    assert "!!" not in cleaned
    assert cleaned == "urgent i am suffering from severe feverish temperature and doctor s advice"

    # Tokenize
    tokens = tp.tokenize(cleaned)
    assert "urgent" in tokens
    assert "suffering" in tokens
    assert "feverish" in tokens

    # Stopwords removal
    filtered = tp.remove_stopwords(tokens)
    assert "i" not in filtered
    assert "am" not in filtered
    assert "from" not in filtered
    assert "and" not in filtered

    # Lemmatization
    lemmas = tp.lemmatize(filtered)
    assert "fever" in lemmas or "feverish" in lemmas
    assert "suffer" in lemmas or "suffering" in lemmas

    # Full process
    res = tp.preprocess(raw_sample)
    assert "cleaned_text" in res
    assert "raw_tokens" in res
    assert "filtered_tokens" in res
    assert "lemmatized_tokens" in res
    assert res["word_count"] > 0
    assert res["lemma_count"] > 0


def test_nlp_dataset_generation():
    """Verify dataset generation creates >= 500 records across 5 categories."""
    stats = verify_and_build_dataset()
    assert stats["total_samples"] >= 500

    # Verify JSON file exists
    json_path = Path("dataset/leave_reasons_corpus.json")
    csv_path = Path("dataset/leave_reasons_corpus.csv")
    assert json_path.exists()
    assert csv_path.exists()

    # Check categories
    class_counts = stats["class_counts"]
    for cat in LEAVE_CATEGORIES.keys():
        assert cat in class_counts
        assert class_counts[cat] >= 50


def test_nlp_service_facade():
    """Test NLPService facade for loading corpus, preprocessing, and metrics."""
    corpus = nlp_service.load_corpus()
    assert isinstance(corpus, list)
    assert len(corpus) >= 500

    item = corpus[0]
    assert "id" in item
    assert "text" in item
    assert "label" in item
    assert "leave_type_name" in item

    # Test preprocess service
    prep = nlp_service.preprocess_text("I need leave for attending conference in Delhi.")
    assert len(prep["lemmatized_tokens"]) > 0

    # Test corpus statistics service
    metrics = nlp_service.get_corpus_statistics()
    assert metrics["total_samples"] >= 500
    assert "CL" in metrics["class_counts"]
    assert metrics["avg_words_per_sample"] > 0
    assert metrics["avg_lemmas_per_sample"] > 0


def test_nlp_view_gui(qapp):
    """Verify PySide6 NLPView widget instantiates and filters corpus records correctly."""
    view = NLPView()
    assert view is not None
    assert view.sub_tabs.count() == 2

    # Check KPI card total samples populated
    val_lbl = view.card_total_samples.findChild(QLabel, "value_label")
    assert val_lbl is not None
    assert int(val_lbl.text()) >= 500

    # Test filtering by category CL
    view.combo_category.setCurrentText("CL")
    view.filter_corpus_display()
    assert view.tbl_corpus.rowCount() > 0

    # Test tester tab preprocessor action
    view.txt_test_input.setPlainText("Doctor advised rest due to severe migraine headache.")
    view.on_process_click()
    assert view.txt_out_clean.toPlainText() != ""
    assert view.txt_out_lemmas.toPlainText() != ""
