"""
Comprehensive Model Evaluation Suite (Pure NumPy)
Performs Stratified 5-Fold Cross-Validation, Expected Calibration Error (ECE) analysis
before and after temperature scaling, Wilson score and Bootstrap 95% Confidence Intervals,
model feature explainability (top-10 positive/negative n-grams per class), and
Out-of-Vocabulary (OOV) / gibberish rejection testing.
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nlp.classifiers import (
    MultinomialNaiveBayes,
    SoftmaxLogisticRegression,
    LinearSVM,
    CLASSES,
    CLASS_TO_IDX,
)
from nlp.model_evaluator import evaluator
from nlp.calibration import (
    compute_ece,
    compute_wilson_score_interval,
    compute_bootstrap_ci,
    TemperatureScaler,
)
from nlp.explainability import explain_model_features
from nlp.oov_detector import oov_detector
from services.nlp_service import nlp_service
from services.tfidf_service import tfidf_service
from nlp.dataset_generator import LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("tools.evaluate_model")


def run_stratified_5fold_cv(
    model_class=MultinomialNaiveBayes,
    model_kwargs=None,
    n_splits: int = 5,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Executes Stratified 5-Fold Cross-Validation on the full 500-sample NLP leave corpus.
    Evaluates accuracy, macro metrics, raw ECE, and post-hoc temperature-scaled ECE.
    """
    if model_kwargs is None:
        model_kwargs = {"alpha": 0.5}

    tfidf_service.ensure_fitted()
    corpus = nlp_service.load_corpus()

    texts = [item.get("text", "") for item in corpus]
    labels = [item.get("label", "CL") for item in corpus]
    metadata_list = [
        {
            "requested_days": 1.0,
            "notice_period_days": 0.0,
            "has_medical_doc": item.get("label") == "ML",
            "is_sandwich_leave": False,
        }
        for item in corpus
    ]

    X = tfidf_service.extractor.batch_extract_composite_features(texts, metadata_list)
    y = labels

    splits = evaluator.stratified_k_fold(X, y, n_splits=n_splits, seed=seed)

    fold_results = []
    aggregated_cm = {actual: {pred: 0 for pred in CLASSES} for actual in CLASSES}
    all_y_true = []
    all_y_pred = []
    all_raw_probs = []
    all_cal_probs = []

    for fold_idx, (train_idx, test_idx) in enumerate(splits, 1):
        X_train, y_train = X[train_idx], [y[i] for i in train_idx]
        X_test, y_test = X[test_idx], [y[i] for i in test_idx]
        y_test_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y_test])

        # Subdivide train into train (75%) and calibration validation (25%)
        X_tr, X_val, y_tr, y_val = evaluator.train_test_split(X_train, y_train, test_size=0.25, seed=seed + fold_idx)
        y_val_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y_val])

        # Instantiate and fit model on training split
        clf = model_class(**model_kwargs)
        clf.fit(X_tr, y_tr)

        # Fit post-hoc Temperature Scaling on validation split
        val_probs = clf.predict_proba(X_val)
        scaler = TemperatureScaler()
        scaler.fit(np.log(np.clip(val_probs, 1e-12, 1.0)), y_val_idx)
        opt_T = scaler.temperature

        # Test set uncalibrated evaluation
        raw_test_probs = clf.predict_proba(X_test)
        raw_ece = compute_ece(raw_test_probs, y_test_idx)

        # Apply temperature scaling
        if hasattr(clf, "temperature"):
            clf.temperature = opt_T
        cal_test_probs = clf.predict_proba(X_test)
        cal_ece = compute_ece(cal_test_probs, y_test_idx)

        preds = clf.predict(X_test)
        metrics = evaluator.evaluate_model(clf, X_test, y_test)

        # Accumulate metrics
        for act, pred in zip(y_test, preds):
            aggregated_cm[act][pred] += 1

        all_y_true.extend(y_test)
        all_y_pred.extend(preds)
        all_raw_probs.append(raw_test_probs)
        all_cal_probs.append(cal_test_probs)

        fold_results.append(
            {
                "fold": fold_idx,
                "accuracy": metrics["accuracy"],
                "macro_precision": metrics["macro_precision"],
                "macro_recall": metrics["macro_recall"],
                "macro_f1": metrics["macro_f1"],
                "raw_ece": raw_ece,
                "cal_ece": cal_ece,
                "temperature": opt_T,
            }
        )

    # Compute averages across folds
    mean_acc = float(np.mean([f["accuracy"] for f in fold_results]))
    std_acc = float(np.std([f["accuracy"] for f in fold_results]))
    mean_f1 = float(np.mean([f["macro_f1"] for f in fold_results]))
    std_f1 = float(np.std([f["macro_f1"] for f in fold_results]))
    mean_raw_ece = float(np.mean([f["raw_ece"] for f in fold_results]))
    mean_cal_ece = float(np.mean([f["cal_ece"] for f in fold_results]))

    # Statistical Confidence Intervals on aggregated test predictions
    total_samples = len(all_y_true)
    total_correct = sum(1 for yt, yp in zip(all_y_true, all_y_pred) if yt == yp)
    wilson_ci = compute_wilson_score_interval(total_correct, total_samples, confidence=0.95)
    bootstrap_ci = compute_bootstrap_ci(all_y_true, all_y_pred, n_bootstraps=1000, seed=seed)

    return {
        "model_name": model_class.__name__,
        "n_splits": n_splits,
        "fold_results": fold_results,
        "mean_accuracy": round(mean_acc, 4),
        "std_accuracy": round(std_acc, 4),
        "mean_macro_f1": round(mean_f1, 4),
        "std_macro_f1": round(std_f1, 4),
        "mean_raw_ece": round(mean_raw_ece, 4),
        "mean_calibrated_ece": round(mean_cal_ece, 4),
        "aggregated_confusion_matrix": aggregated_cm,
        "wilson_ci_95": wilson_ci,
        "bootstrap_ci_95": bootstrap_ci,
    }


def evaluate_oov_rejection() -> Dict[str, Any]:
    """
    Evaluates OOV detector and model rejection against valid domain samples vs.
    keyboard smash, gibberish strings, and non-vocabulary text.
    """
    from services.model_training_service import model_training_service

    valid_samples = [
        ("I am suffering from severe viral fever and doctor advised 3 days bed rest.", "ML"),
        ("Personal work at the local RTO office for driving license renewal.", "CL"),
        ("Attending IEEE International Conference on AI to present research paper.", "SCL"),
        ("Official visit to State Higher Education Council for syllabus revision.", "OD"),
        ("Availing earned leave for long planned family vacation tour to Kerala.", "EL"),
    ]

    gibberish_samples = [
        "asdfghjkl qwerty zxcvbnm",
        "zzzzzzzzzzzzzzzzzz",
        "12345 67890 98765",
        "foo bar baz qux quux corge",
        "random nonsense bla bla bla xyz123",
    ]

    valid_results = []
    for text, expected in valid_samples:
        pred = model_training_service.predict_leave_reason(text)
        valid_results.append(
            {
                "text": text,
                "expected": expected,
                "predicted": pred.get("predicted_category"),
                "confidence": pred.get("confidence_score"),
                "is_oov": pred.get("is_oov", False),
            }
        )

    gibberish_results = []
    for text in gibberish_samples:
        pred = model_training_service.predict_leave_reason(text)
        gibberish_results.append(
            {
                "text": text,
                "predicted": pred.get("predicted_category"),
                "confidence": pred.get("confidence_score"),
                "is_oov": pred.get("is_oov", False),
                "is_uncertain": pred.get("is_uncertain", False),
                "routing_advice": pred.get("routing_advice"),
            }
        )

    return {
        "valid_samples_tested": len(valid_samples),
        "valid_results": valid_results,
        "gibberish_samples_tested": len(gibberish_samples),
        "gibberish_rejected_count": sum(1 for g in gibberish_results if g["is_oov"] or g["is_uncertain"]),
        "gibberish_results": gibberish_results,
    }


def print_evaluation_report():
    """Prints a full formatted terminal evaluation report."""
    print("=" * 80)
    print("AI-ENABLED FACULTY ERP — NLP MODEL EVALUATION BENCHMARK (PURE NUMPY)")
    print("=" * 80)

    # 1. Stratified 5-Fold CV
    print("\n[1] STRATIFIED 5-FOLD CROSS-VALIDATION")
    cv_res = run_stratified_5fold_cv(MultinomialNaiveBayes, {"alpha": 0.5}, n_splits=5)

    print(f"Model: {cv_res['model_name']} (Laplace alpha=0.5)")
    print(f"{'Fold':<6}{'Accuracy':<12}{'Macro-F1':<12}{'Raw ECE':<12}{'Cal ECE':<12}{'Optimal T':<10}")
    print("-" * 64)
    for f in cv_res["fold_results"]:
        print(f"{f['fold']:<6}{f['accuracy']:<12.4f}{f['macro_f1']:<12.4f}{f['raw_ece']:<12.4f}{f['cal_ece']:<12.4f}{f['temperature']:<10.4f}")
    print("-" * 64)
    print(f"Mean Accuracy:       {cv_res['mean_accuracy']:.4f} (+/- {cv_res['std_accuracy']:.4f})")
    print(f"Mean Macro-F1:       {cv_res['mean_macro_f1']:.4f} (+/- {cv_res['std_macro_f1']:.4f})")
    print(f"Mean Raw ECE:        {cv_res['mean_raw_ece']:.4f}")
    print(f"Mean Calibrated ECE: {cv_res['mean_calibrated_ece']:.4f} (ECE reduced by {((cv_res['mean_raw_ece'] - cv_res['mean_calibrated_ece']) / max(cv_res['mean_raw_ece'], 1e-4))*100:.1f}%)")

    # 2. Statistical Confidence Intervals
    print("\n[2] STATISTICAL CONFIDENCE INTERVALS (95% LEVEL)")
    print(f"Wilson Score 95% CI: [{cv_res['wilson_ci_95'][0]:.4f}, {cv_res['wilson_ci_95'][1]:.4f}]")
    print(f"Bootstrap 95% CI:    [{cv_res['bootstrap_ci_95'][0]:.4f}, {cv_res['bootstrap_ci_95'][1]:.4f}] (1000 resamples)")

    # 3. 5x5 Aggregated Confusion Matrix
    print("\n[3] AGGREGATED 5x5 CONFUSION MATRIX (500 SAMPLES)")
    cm = cv_res["aggregated_confusion_matrix"]
    header = f"{'Actual \\ Pred':<15}" + "".join(f"{c:<10}" for c in CLASSES)
    print(header)
    print("-" * len(header))
    for actual in CLASSES:
        row = f"{actual:<15}" + "".join(f"{cm[actual][pred]:<10}" for pred in CLASSES)
        print(row)

    # 4. Feature Explainability (Top-10 Words)
    print("\n[4] FEATURE EXPLAINABILITY (TOP-10 POSITIVE & NEGATIVE WORDS PER CLASS)")
    from services.model_training_service import model_training_service
    explanations = model_training_service.get_champion_feature_explanations(top_k=10)
    for cat in CLASSES:
        cat_name = LEAVE_CATEGORIES.get(cat, cat)
        print(f"\n--- Class {cat} ({cat_name}) ---")
        pos_words = [f"{w} ({val:+.2f})" for w, val in explanations[cat]["positive_features"][:10]]
        neg_words = [f"{w} ({val:+.2f})" for w, val in explanations[cat]["negative_features"][:10]]
        print("  Top Positive: " + ", ".join(pos_words))
        print("  Top Negative: " + ", ".join(neg_words))

    # 5. OOV & Gibberish Rejection
    print("\n[5] OUT-OF-VOCABULARY (OOV) & GIBBERISH REJECTION TEST")
    oov_eval = evaluate_oov_rejection()
    print(f"Tested {oov_eval['gibberish_samples_tested']} gibberish queries -> {oov_eval['gibberish_rejected_count']} successfully rejected.")
    for g in oov_eval["gibberish_results"]:
        status = "REJECTED" if (g["is_oov"] or g["is_uncertain"]) else "ACCEPTED"
        print(f"  [{status}] '{g['text'][:30]}...' -> Category: {g['predicted']} (Conf: {g['confidence']:.2f})")

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    print_evaluation_report()
