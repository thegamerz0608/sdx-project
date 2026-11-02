"""
Machine Learning Classifiers Module (Pure NumPy)
Provides Naïve Bayes, Softmax Logistic Regression, Random Forest, and Linear SVM classifiers for leave reason classification.
"""
import sys
import os
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import joblib
import numpy as np

from utils.logger import get_logger

logger = get_logger("nlp.classifiers")

CLASSES = ["CL", "ML", "EL", "SCL", "OD"]
CLASS_TO_IDX = {cls_name: i for i, cls_name in enumerate(CLASSES)}


def _ensure_2d_array(X: Any) -> np.ndarray:
    """Ensures input features are a float64 2D numpy array of shape (N, D)."""
    arr = np.asarray(X, dtype=np.float64)
    if arr.ndim == 0:
        return arr.reshape(1, 1)
    if arr.ndim == 1:
        return arr.reshape(1, -1)
    return arr


def _align_feature_dim(X: np.ndarray, expected_features: int) -> np.ndarray:
    """Safely aligns feature dimensionality by padding with zeros or truncating if needed."""
    if X.shape[1] == expected_features:
        return X
    if X.shape[1] < expected_features:
        pad = np.zeros((X.shape[0], expected_features - X.shape[1]), dtype=np.float64)
        return np.hstack([X, pad])
    return X[:, :expected_features]


class MultinomialNaiveBayes:
    """Multinomial Naïve Bayes classifier with Laplace smoothing and shape hardening."""

    def __init__(self, alpha: float = 1.0, temperature: float = 1.0):
        self.alpha = alpha
        self.temperature = temperature
        self.classes = CLASSES
        self.num_classes = len(CLASSES)
        self.class_log_prior_: Optional[np.ndarray] = None
        self.feature_log_prob_: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def fit(self, X: np.ndarray, y: List[str]) -> "MultinomialNaiveBayes":
        X = _ensure_2d_array(X)
        y_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y])
        num_samples, num_features = X.shape

        # Class priors
        counts = np.bincount(y_idx, minlength=self.num_classes)
        self.class_log_prior_ = np.log(counts / float(num_samples))

        # Feature log probabilities with Laplace smoothing
        feature_counts = np.zeros((self.num_classes, num_features), dtype=np.float64)
        for c in range(self.num_classes):
            feature_counts[c] = np.sum(X[y_idx == c], axis=0)

        smoothed_fc = feature_counts + self.alpha
        smoothed_cc = np.sum(smoothed_fc, axis=1, keepdims=True)
        self.feature_log_prob_ = np.log(smoothed_fc / smoothed_cc)

        self.is_fitted = True
        return self

    def predict_joint_log_likelihood(self, X: np.ndarray) -> np.ndarray:
        X = _ensure_2d_array(X)
        if self.feature_log_prob_ is None or self.class_log_prior_ is None:
            return np.zeros((X.shape[0], self.num_classes), dtype=np.float64)
        X = _align_feature_dim(X, self.feature_log_prob_.shape[1])
        return X @ self.feature_log_prob_.T + self.class_log_prior_

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = _ensure_2d_array(X)
        if self.feature_log_prob_ is None or self.class_log_prior_ is None:
            return np.ones((X.shape[0], self.num_classes), dtype=np.float64) / float(self.num_classes)
        jll = self.predict_joint_log_likelihood(X)
        temp = max(getattr(self, "temperature", 1.0), 1e-4)
        scaled_jll = jll / temp
        max_jll = np.max(scaled_jll, axis=1, keepdims=True)
        exp_jll = np.exp(scaled_jll - max_jll)
        denom = np.sum(exp_jll, axis=1, keepdims=True)
        denom = np.where(denom == 0, 1e-12, denom)
        return np.nan_to_num(exp_jll / denom, nan=1.0 / self.num_classes)

    def predict(self, X: np.ndarray) -> List[str]:
        X = _ensure_2d_array(X)
        probas = self.predict_proba(X)
        best_idx = np.argmax(probas, axis=1)
        return [self.classes[i] for i in best_idx]


class SoftmaxLogisticRegression:
    """
    Multinomial Logistic Regression using Softmax cross-entropy gradient descent,
    momentum acceleration, and calibrated temperature scaling for edge-case accuracy.
    """

    def __init__(self, lr: float = 0.15, max_iter: int = 350, reg: float = 1e-4, temperature: float = 1.0):
        self.lr = lr
        self.max_iter = max_iter
        self.reg = reg
        self.temperature = temperature
        self.classes = CLASSES
        self.num_classes = len(CLASSES)
        self.W: Optional[np.ndarray] = None
        self.b: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def fit(self, X: np.ndarray, y: List[str]) -> "SoftmaxLogisticRegression":
        X = _ensure_2d_array(X)
        num_samples, num_features = X.shape
        y_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y])

        Y_onehot = np.zeros((num_samples, self.num_classes))
        Y_onehot[np.arange(num_samples), y_idx] = 1.0

        np.random.seed(42)
        self.W = np.random.randn(num_features, self.num_classes) * 0.01
        self.b = np.zeros((1, self.num_classes))

        V_W = np.zeros_like(self.W)
        V_b = np.zeros_like(self.b)
        beta = 0.9

        for iter_idx in range(self.max_iter):
            scores = X @ self.W + self.b
            max_scores = np.max(scores, axis=1, keepdims=True)
            probs = np.exp(scores - max_scores)
            probs /= np.sum(probs, axis=1, keepdims=True)

            grad_W = (X.T @ (probs - Y_onehot)) / num_samples + self.reg * self.W
            grad_b = np.mean(probs - Y_onehot, axis=0, keepdims=True)

            # Momentum accelerated gradient update
            V_W = beta * V_W + (1.0 - beta) * grad_W
            V_b = beta * V_b + (1.0 - beta) * grad_b

            # Adaptive decay
            step_lr = self.lr / (1.0 + 0.001 * iter_idx)
            self.W -= step_lr * V_W
            self.b -= step_lr * V_b

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = _ensure_2d_array(X)
        if self.W is None or self.b is None:
            return np.ones((X.shape[0], self.num_classes), dtype=np.float64) / float(self.num_classes)
        X = _align_feature_dim(X, self.W.shape[0])
        # Calibrated temperature scaling
        t_val = max(getattr(self, "temperature", 1.0), 1e-4)
        scores = (X @ self.W + self.b) / t_val
        max_scores = np.max(scores, axis=1, keepdims=True)
        probs = np.exp(scores - max_scores)
        denom = np.sum(probs, axis=1, keepdims=True)
        denom = np.where(denom == 0, 1e-12, denom)
        return np.nan_to_num(probs / denom, nan=1.0 / self.num_classes)

    def predict(self, X: np.ndarray) -> List[str]:
        X = _ensure_2d_array(X)
        probs = self.predict_proba(X)
        best_idx = np.argmax(probs, axis=1)
        return [self.classes[i] for i in best_idx]


class DecisionNode:

    def __init__(
        self,
        feature: Optional[int] = None,
        threshold: Optional[float] = None,
        left: Optional["DecisionNode"] = None,
        right: Optional["DecisionNode"] = None,
        value: Optional[np.ndarray] = None,
    ):
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value

    @property
    def is_leaf(self) -> bool:
        return self.value is not None


class SimpleDecisionTree:
    """Decision Tree classifier for Random Forest ensemble."""

    def __init__(self, max_depth: int = 10, min_samples_split: int = 2, max_features: Optional[int] = None):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.root: Optional[DecisionNode] = None

    def _gini(self, y: np.ndarray) -> float:
        if len(y) == 0:
            return 0.0
        counts = np.bincount(y, minlength=5)
        probs = counts / len(y)
        return 1.0 - np.sum(probs**2)

    def _best_split(self, X: np.ndarray, y: np.ndarray) -> Tuple[Optional[int], Optional[float]]:
        best_gini = 1.0
        best_feat, best_thresh = None, None
        n_samples, n_feats = X.shape

        feat_indices = np.random.choice(n_feats, self.max_features, replace=False)

        for feat in feat_indices:
            thresholds = np.unique(X[:, feat])
            if len(thresholds) > 8:
                thresholds = np.percentile(thresholds, np.linspace(10, 90, 6))

            for thresh in thresholds:
                left_mask = X[:, feat] <= thresh
                right_mask = ~left_mask

                if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
                    continue

                gini_left = self._gini(y[left_mask])
                gini_right = self._gini(y[right_mask])
                weighted_gini = (np.sum(left_mask) * gini_left + np.sum(right_mask) * gini_right) / n_samples

                if weighted_gini < best_gini:
                    best_gini = weighted_gini
                    best_feat = feat
                    best_thresh = thresh

        return best_feat, best_thresh

    def _build_tree(self, X: np.ndarray, y: np.ndarray, depth: int = 0) -> DecisionNode:
        n_samples = X.shape[0]
        num_classes = 5

        if depth >= self.max_depth or n_samples < self.min_samples_split or len(np.unique(y)) == 1:
            counts = np.bincount(y, minlength=num_classes)
            probs = counts / float(n_samples) if n_samples > 0 else np.ones(num_classes) / num_classes
            return DecisionNode(value=probs)

        feat, thresh = self._best_split(X, y)
        if feat is None or thresh is None:
            counts = np.bincount(y, minlength=num_classes)
            probs = counts / float(n_samples)
            return DecisionNode(value=probs)

        left_mask = X[:, feat] <= thresh
        left_node = self._build_tree(X[left_mask], y[left_mask], depth + 1)
        right_node = self._build_tree(X[~left_mask], y[~left_mask], depth + 1)

        return DecisionNode(feature=feat, threshold=thresh, left=left_node, right=right_node)

    def fit(self, X: np.ndarray, y: np.ndarray):
        X = _ensure_2d_array(X)
        if self.max_features is None:
            self.max_features = max(1, int(np.sqrt(X.shape[1])))
        self.root = self._build_tree(X, y)

    def _predict_sample(self, sample: np.ndarray, node: Optional[DecisionNode]) -> np.ndarray:
        if node is None or node.is_leaf:
            return node.value if (node and node.value is not None) else np.ones(5, dtype=np.float64) / 5.0
        if node.feature is None or node.feature >= len(sample):
            return node.value if node.value is not None else np.ones(5, dtype=np.float64) / 5.0
        if sample[node.feature] <= (node.threshold if node.threshold is not None else 0.0):
            return self._predict_sample(sample, node.left)
        return self._predict_sample(sample, node.right)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = _ensure_2d_array(X)
        if self.root is None:
            return np.ones((X.shape[0], 5), dtype=np.float64) / 5.0
        return np.array([self._predict_sample(x, self.root) for x in X])


class RandomForest:
    """Random Forest Classifier ensemble with 1D/2D shape protection."""

    def __init__(self, n_estimators: int = 15, max_depth: int = 8):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.classes = CLASSES
        self.trees: List[SimpleDecisionTree] = []
        self.is_fitted: bool = False

    def fit(self, X: np.ndarray, y: List[str]) -> "RandomForest":
        X = _ensure_2d_array(X)
        y_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y])
        num_samples = X.shape[0]

        np.random.seed(42)
        self.trees = []

        for _ in range(self.n_estimators):
            boot_idx = np.random.choice(num_samples, num_samples, replace=True)
            tree = SimpleDecisionTree(max_depth=self.max_depth)
            tree.fit(X[boot_idx], y_idx[boot_idx])
            self.trees.append(tree)

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = _ensure_2d_array(X)
        if not self.trees:
            return np.ones((X.shape[0], len(self.classes)), dtype=np.float64) / float(len(self.classes))
        all_probs = np.array([tree.predict_proba(X) for tree in self.trees])
        return np.nan_to_num(np.mean(all_probs, axis=0), nan=1.0 / len(self.classes))

    def predict(self, X: np.ndarray) -> List[str]:
        X = _ensure_2d_array(X)
        probs = self.predict_proba(X)
        best_idx = np.argmax(probs, axis=1)
        return [self.classes[i] for i in best_idx]


class LinearSVM:
    """One-vs-Rest Linear SVM Classifier with Hinge loss optimization and shape hardening."""

    def __init__(self, lr: float = 0.05, max_iter: int = 300, C: float = 1.0, temperature: float = 1.0):
        self.lr = lr
        self.max_iter = max_iter
        self.C = C
        self.temperature = temperature
        self.classes = CLASSES
        self.num_classes = len(CLASSES)
        self.W: Optional[np.ndarray] = None
        self.b: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def fit(self, X: np.ndarray, y: List[str]) -> "LinearSVM":
        X = _ensure_2d_array(X)
        num_samples, num_features = X.shape
        y_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y])

        np.random.seed(42)
        self.W = np.random.randn(num_features, self.num_classes) * 0.01
        self.b = np.zeros((1, self.num_classes))

        Y_ovr = np.ones((num_samples, self.num_classes)) * -1.0
        for i in range(num_samples):
            Y_ovr[i, y_idx[i]] = 1.0

        for _ in range(self.max_iter):
            scores = X @ self.W + self.b
            margins = Y_ovr * scores
            active = margins < 1.0

            grad_W = self.W.copy()
            grad_b = np.zeros((1, self.num_classes))

            for c in range(self.num_classes):
                active_c = active[:, c]
                if np.sum(active_c) > 0:
                    grad_W[:, c] -= self.C * (X[active_c].T @ Y_ovr[active_c, c]) / num_samples
                    grad_b[0, c] -= self.C * np.mean(Y_ovr[active_c, c])

            self.W -= self.lr * grad_W
            self.b -= self.lr * grad_b

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = _ensure_2d_array(X)
        if self.W is None or self.b is None:
            return np.ones((X.shape[0], self.num_classes), dtype=np.float64) / float(self.num_classes)
        X = _align_feature_dim(X, self.W.shape[0])
        temp = max(getattr(self, "temperature", 1.0), 1e-4)
        raw_scores = (X @ self.W + self.b) / temp
        max_scores = np.max(raw_scores, axis=1, keepdims=True)
        probs = np.exp(raw_scores - max_scores)
        denom = np.sum(probs, axis=1, keepdims=True)
        denom = np.where(denom == 0, 1e-12, denom)
        return np.nan_to_num(probs / denom, nan=1.0 / self.num_classes)

    def predict(self, X: np.ndarray) -> List[str]:
        X = _ensure_2d_array(X)
        if self.W is None or self.b is None:
            return [self.classes[0] for _ in range(X.shape[0])]
        X = _align_feature_dim(X, self.W.shape[0])
        raw_scores = X @ self.W + self.b
        best_idx = np.argmax(raw_scores, axis=1)
        return [self.classes[i] for i in best_idx]
