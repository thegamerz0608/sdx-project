"""
Model Evaluation Engine
Provides stratified train/test split, accuracy, macro precision/recall/F1-score calculation, and confusion matrix generation.
"""
import sys
import os
from typing import List, Dict, Any, Tuple
import numpy as np

from nlp.classifiers import CLASSES, CLASS_TO_IDX
from nlp.calibration import (
    compute_ece,
    compute_wilson_score_interval,
    compute_bootstrap_ci,
    TemperatureScaler,
)
from utils.logger import get_logger

logger = get_logger("nlp.model_evaluator")


class ModelEvaluator:
    """Evaluates machine learning classifiers and calculates metric benchmarks."""

    def train_test_split(
        self, X: np.ndarray, y: List[str], test_size: float = 0.2, seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
        """Stratified train/test split preserving category proportions."""
        np.random.seed(seed)
        num_samples = X.shape[0]

        indices = np.arange(num_samples)
        y_arr = np.array(y)

        train_indices = []
        test_indices = []

        for cat in CLASSES:
            cat_idx = indices[y_arr == cat]
            np.random.shuffle(cat_idx)

            n_test = int(len(cat_idx) * test_size)
            test_indices.extend(cat_idx[:n_test])
            train_indices.extend(cat_idx[n_test:])

        np.random.shuffle(train_indices)
        np.random.shuffle(test_indices)

        X_train, X_test = X[train_indices], X[test_indices]
        y_train = [y[i] for i in train_indices]
        y_test = [y[i] for i in test_indices]

        return X_train, X_test, y_train, y_test

    def evaluate_model(self, model: Any, X_test: np.ndarray, y_test: List[str]) -> Dict[str, Any]:
        """
        Calculates accuracy, precision, recall, macro F1-score, and 5x5 confusion matrix.
        """
        y_pred = model.predict(X_test)
        num_samples = len(y_test)

        # Accuracy
        correct = sum(1 for p, t in zip(y_pred, y_test) if p == t)
        accuracy = round(correct / float(num_samples), 4)

        # 5x5 Confusion Matrix
        cm = {actual: {pred: 0 for pred in CLASSES} for actual in CLASSES}
        for actual, pred in zip(y_test, y_pred):
            if actual in cm and pred in cm[actual]:
                cm[actual][pred] += 1

        # Per-class & Macro metrics
        precisions = []
        recalls = []
        f1_scores = []
        per_class_metrics = {}

        for cat in CLASSES:
            tp = cm[cat][cat]
            fp = sum(cm[other][cat] for other in CLASSES if other != cat)
            fn = sum(cm[cat][other] for other in CLASSES if other != cat)

            prec = round(tp / float(tp + fp), 4) if (tp + fp) > 0 else 0.0
            rec = round(tp / float(tp + fn), 4) if (tp + fn) > 0 else 0.0
            f1 = round(2 * prec * rec / (prec + rec), 4) if (prec + rec) > 0 else 0.0

            precisions.append(prec)
            recalls.append(rec)
            f1_scores.append(f1)

            per_class_metrics[cat] = {
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }

        macro_precision = round(float(np.mean(precisions)), 4)
        macro_recall = round(float(np.mean(recalls)), 4)
        macro_f1 = round(float(np.mean(f1_scores)), 4)

        # Probabilities & Calibration Error (ECE)
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_test)
        else:
            probs = np.ones((num_samples, len(CLASSES))) / float(len(CLASSES))

        y_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y_test])
        ece = compute_ece(probs, y_idx)

        # Statistical Confidence Intervals (95%)
        wilson_ci = compute_wilson_score_interval(correct, num_samples, 0.95)
        boot_ci = compute_bootstrap_ci(y_test, y_pred, n_bootstraps=500, seed=42)

        return {
            "accuracy": accuracy,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
            "confusion_matrix": cm,
            "per_class_metrics": per_class_metrics,
            "test_sample_count": num_samples,
            "ece": ece,
            "wilson_ci_95": wilson_ci,
            "bootstrap_ci_95": boot_ci,
        }

    def stratified_k_fold(
        self, X: np.ndarray, y: List[str], n_splits: int = 5, seed: int = 42
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Generates stratified K-fold cross-validation train/test index splits in pure NumPy.
        """
        np.random.seed(seed)
        num_samples = X.shape[0]
        y_arr = np.array(y)
        indices = np.arange(num_samples)

        # Partition indices per class into k buckets
        class_buckets: Dict[str, List[List[int]]] = {cat: [[] for _ in range(n_splits)] for cat in CLASSES}

        for cat in CLASSES:
            cat_idx = indices[y_arr == cat]
            np.random.shuffle(cat_idx)
            for i, idx in enumerate(cat_idx):
                bucket_idx = i % n_splits
                class_buckets[cat][bucket_idx].append(idx)

        splits = []
        for fold in range(n_splits):
            test_indices = []
            train_indices = []

            for cat in CLASSES:
                test_indices.extend(class_buckets[cat][fold])
                for other_fold in range(n_splits):
                    if other_fold != fold:
                        train_indices.extend(class_buckets[cat][other_fold])

            np.random.shuffle(train_indices)
            np.random.shuffle(test_indices)

            splits.append((np.array(train_indices, dtype=np.int64), np.array(test_indices, dtype=np.int64)))

        return splits


evaluator = ModelEvaluator()
