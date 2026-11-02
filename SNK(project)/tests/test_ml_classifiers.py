"""
Phase 12 ML Leave Classification Unit Tests
Verifies Multinomial Naïve Bayes, Softmax Logistic Regression, Random Forest, Linear SVM,
ModelEvaluator train/test split & metrics, ModelTrainingService facade, model persistence, and PySide6 ModelView.
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

from nlp.classifiers import (
    MultinomialNaiveBayes,
    SoftmaxLogisticRegression,
    RandomForest,
    LinearSVM,
    CLASSES,
)
from nlp.model_evaluator import ModelEvaluator, evaluator
from services.model_training_service import ModelTrainingService, model_training_service
from ui.model_view import ModelView


@pytest.fixture
def qapp():
    """Ensure a PySide6 QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_individual_classifiers_fit_predict():
    """Test fit, predict, and predict_proba across all 4 candidate ML classifiers."""
    np.random.seed(42)
    num_samples = 40
    num_feats = 20

    X = np.random.rand(num_samples, num_feats)
    y = [CLASSES[i % 5] for i in range(num_samples)]

    classifiers = [
        ("Multinomial Naïve Bayes", MultinomialNaiveBayes(alpha=1.0)),
        ("Softmax Logistic Regression", SoftmaxLogisticRegression(lr=0.1, max_iter=50)),
        ("Random Forest", RandomForest(n_estimators=5, max_depth=4)),
        ("Linear SVM", LinearSVM(lr=0.05, max_iter=50)),
    ]

    for name, clf in classifiers:
        clf.fit(X, y)
        assert clf.is_fitted is True

        preds = clf.predict(X)
        assert len(preds) == num_samples
        assert all(p in CLASSES for p in preds)

        probs = clf.predict_proba(X)
        assert probs.shape == (num_samples, 5)
        # Check rows sum to ~1.0
        row_sums = np.sum(probs, axis=1)
        assert np.allclose(row_sums, 1.0, atol=1e-3)


def test_model_evaluator_metrics():
    """Test train/test split and evaluation metrics calculation."""
    eval_engine = ModelEvaluator()
    np.random.seed(42)

    X = np.random.rand(50, 15)
    y = [CLASSES[i % 5] for i in range(50)]

    X_tr, X_te, y_tr, y_te = eval_engine.train_test_split(X, y, test_size=0.2, seed=42)
    assert len(y_tr) == 40
    assert len(y_te) == 10

    clf = MultinomialNaiveBayes(alpha=1.0)
    clf.fit(X_tr, y_tr)

    metrics = eval_engine.evaluate_model(clf, X_te, y_te)
    assert "accuracy" in metrics
    assert "macro_precision" in metrics
    assert "macro_recall" in metrics
    assert "macro_f1" in metrics
    assert "confusion_matrix" in metrics
    assert metrics["test_sample_count"] == 10

    cm = metrics["confusion_matrix"]
    assert len(cm) == 5
    for cat in CLASSES:
        assert cat in cm
        assert len(cm[cat]) == 5


def test_model_training_service_facade():
    """Test service facade multi-model training, model persistence, and prediction."""
    service = ModelTrainingService()
    leaderboard = service.train_and_evaluate_all_models()

    assert isinstance(leaderboard, list)
    assert len(leaderboard) == 4

    # Verify ranked by macro_f1
    for i in range(len(leaderboard) - 1):
        assert leaderboard[i]["macro_f1"] >= leaderboard[i + 1]["macro_f1"]

    # Champion model persistence check
    best_path = Path("models/best_leave_classifier.joblib")
    assert best_path.exists()

    # Prediction service test
    pred = service.predict_leave_reason(
        "Doctor advised 3 days bed rest due to severe feverish infection.",
        metadata={"requested_days": 3.0, "has_medical_doc": True},
    )

    assert "predicted_category" in pred
    assert pred["predicted_category"] in CLASSES
    assert "confidence_score" in pred
    assert pred["confidence_score"] > 0.0
    assert "probabilities" in pred
    assert len(pred["probabilities"]) == 5
    assert "routing_advice" in pred


def test_model_view_gui(qapp):
    """Verify PySide6 ModelView widget instantiates, displays leaderboard, and runs live prediction."""
    view = ModelView()
    assert view is not None
    assert view.sub_tabs.count() == 2

    # Check KPI cards populated
    assert view.card_champion.findChild(QLabel, "value_label").text() != ""
    assert view.card_f1.findChild(QLabel, "value_label").text() != ""

    # Check leaderboard table rows
    assert view.tbl_leaderboard.rowCount() == 4

    # Check confusion matrix table
    assert view.tbl_cm.rowCount() == 5
    assert view.tbl_cm.columnCount() == 5

    # Run live predictor test
    view.txt_pred_input.setPlainText("Attending 5-day Faculty Development Program on Machine Learning.")
    view.spn_pred_days.setValue(5.0)
    view.run_ml_prediction()
    assert "PREDICTED CATEGORY:" in view.lbl_pred_result.text()
