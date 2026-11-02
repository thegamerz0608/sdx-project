"""
Unit Tests for Phase 1 Machine Learning Improvements:
- Post-Hoc Temperature Scaling (Golden-Section Search)
- Expected Calibration Error (ECE)
- Wilson Score & Bootstrap 95% Confidence Intervals
- Out-of-Vocabulary (OOV) & Gibberish Rejection
- Model Feature Explainability (Top-10 Positive/Negative Words)
"""
import sys
import os
from pathlib import Path
import pytest
import numpy as np

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from nlp.calibration import (
    TemperatureScaler,
    compute_ece,
    compute_wilson_score_interval,
    compute_bootstrap_ci,
)
from nlp.oov_detector import OOVDetector, oov_detector
from nlp.explainability import explain_model_features
from nlp.classifiers import MultinomialNaiveBayes, SoftmaxLogisticRegression, CLASSES
from services.model_training_service import model_training_service
from services.tfidf_service import tfidf_service


def test_temperature_scaler_golden_section():
    """Verify TemperatureScaler fits T using 1-D Golden-Section Search and minimizes NLL."""
    np.random.seed(42)
    n_samples = 150
    n_classes = 5

    # Simulate overconfident logits
    logits = np.random.randn(n_samples, n_classes) * 4.0
    y_true = np.random.randint(0, n_classes, size=n_samples)

    scaler = TemperatureScaler()
    scaler.fit(logits, y_true)

    assert scaler.is_fitted is True
    assert 0.05 <= scaler.temperature <= 10.0

    # Calibrated probabilities
    cal_probs = scaler.predict_proba(logits)
    assert cal_probs.shape == (n_samples, n_classes)
    assert np.allclose(np.sum(cal_probs, axis=1), 1.0, atol=1e-4)

    # Inverted softmax pseudo-logit calibration
    uncal_probs = TemperatureScaler._softmax(logits, 1.0)
    cal_from_probs = scaler.calibrate_probabilities(uncal_probs)
    assert cal_from_probs.shape == (n_samples, n_classes)
    assert np.allclose(np.sum(cal_from_probs, axis=1), 1.0, atol=1e-4)


def test_expected_calibration_error():
    """Verify compute_ece produces valid metrics and measures calibration gap."""
    # Case 1: Perfectly calibrated probabilities (100% confidence, 100% accuracy)
    probs_perfect = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]])
    y_perfect = np.array([0, 0, 1, 1])
    ece_perfect = compute_ece(probs_perfect, y_perfect, n_bins=5)
    assert ece_perfect == 0.0

    # Case 2: Highly overconfident but completely wrong (100% confidence, 0% accuracy)
    probs_wrong = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]])
    y_wrong = np.array([1, 1, 0, 0])
    ece_wrong = compute_ece(probs_wrong, y_wrong, n_bins=5)
    assert ece_wrong >= 0.95


def test_wilson_and_bootstrap_intervals():
    """Verify Wilson score and Bootstrap confidence intervals return mathematically sound bounds."""
    # Wilson Score: 90 correct out of 100
    low_w, high_w = compute_wilson_score_interval(90, 100, confidence=0.95)
    assert 0.0 <= low_w <= 0.90 <= high_w <= 1.0
    assert high_w - low_w < 0.20

    # Edge cases
    assert compute_wilson_score_interval(0, 0) == (0.0, 0.0)

    # Bootstrap CI
    y_true = [0] * 50 + [1] * 50
    y_pred = [0] * 45 + [1] * 5 + [1] * 45 + [0] * 5  # 90% accuracy
    low_b, high_b = compute_bootstrap_ci(y_true, y_pred, n_bootstraps=500, seed=42)
    assert 0.80 <= low_b <= 0.90 <= high_b <= 0.98


def test_oov_and_gibberish_rejection():
    """Verify OOV detector flags keyboard smash, repeated chars, and non-vocabulary text."""
    detector = oov_detector

    # Empty / whitespace
    res_empty = detector.assess_input_vocabulary("   ")
    assert res_empty["is_oov"] is True

    # Keyboard smash / repetitive chars
    res_rep = detector.assess_input_vocabulary("zzzzzzzzzzzz")
    assert res_rep["is_oov"] is True
    assert res_rep["reason"] == "REPETITIVE_CHARACTER_SEQUENCE"

    # Consonant smash
    res_smash = detector.assess_input_vocabulary("asdfghjkl qwrtpsdf")
    assert res_smash["is_oov"] is True
    assert res_smash["reason"] == "CONSONANT_KEYBOARD_SMASH"

    # Valid domain sentence
    tfidf_service.ensure_fitted()
    res_valid = detector.assess_input_vocabulary("Doctor advised bed rest for severe viral fever infection.")
    assert res_valid["is_oov"] is False
    assert res_valid["vocab_overlap_ratio"] > 0.5
    assert len(res_valid["known_ngrams"]) > 0


def test_model_training_service_oov_fallback():
    """Verify ModelTrainingService gracefully rejects gibberish inputs with UNCERTAIN fallback."""
    # Gibberish input
    pred_gibberish = model_training_service.predict_leave_reason("asdfghjkl qwerty 1234567")
    assert pred_gibberish["predicted_category"] == "UNCERTAIN"
    assert pred_gibberish["is_oov"] is True
    assert pred_gibberish["confidence_score"] == 0.20
    assert "MANUAL_REVIEW" in pred_gibberish["routing_advice"]

    # Legitimate medical leave reason
    pred_legit = model_training_service.predict_leave_reason(
        "I am suffering from severe viral fever and doctor advised 3 days bed rest.",
        metadata={"requested_days": 3.0, "has_medical_doc": True},
    )
    assert pred_legit["predicted_category"] == "ML"
    assert pred_legit["is_oov"] is False
    assert pred_legit["confidence_score"] > 0.80


def test_model_feature_explainability():
    """Verify explainability engine extracts top-10 positive and negative n-grams per class."""
    explanations = model_training_service.get_champion_feature_explanations(top_k=10)
    assert len(explanations) == len(CLASSES)

    for cat in CLASSES:
        assert cat in explanations
        assert "positive_features" in explanations[cat]
        assert "negative_features" in explanations[cat]
        assert len(explanations[cat]["positive_features"]) == 10
        assert len(explanations[cat]["negative_features"]) == 10

        # Verify items are (feature_name, weight) tuples
        feat_name, weight = explanations[cat]["positive_features"][0]
        assert isinstance(feat_name, str)
        assert isinstance(weight, float)
