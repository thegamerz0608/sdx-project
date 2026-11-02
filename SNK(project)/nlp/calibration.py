"""
Post-Hoc Probability Calibration & Temperature Scaling (Pure NumPy)
Implements temperature scaling via 1-D negative log-likelihood (NLL) optimization
(golden-section search), Expected Calibration Error (ECE), and statistical confidence intervals
(Wilson score and bootstrap CI) without external SciPy or sklearn dependencies.
"""
import math
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np

from utils.logger import get_logger

logger = get_logger("nlp.calibration")


def compute_ece(probs: np.ndarray, y_true: Union[np.ndarray, List[int]], n_bins: int = 10) -> float:
    """
    Computes Expected Calibration Error (ECE) across equal-width confidence bins.
    
    ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    probs = np.asarray(probs, dtype=np.float64)
    y_true = np.asarray(y_true, dtype=np.int64)

    if probs.ndim == 1:
        probs = probs.reshape(-1, 1)

    n_samples = probs.shape[0]
    if n_samples == 0:
        return 0.0

    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == y_true).astype(np.float64)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            in_bin = (confidences >= low) & (confidences <= high)
        else:
            in_bin = (confidences >= low) & (confidences < high)

        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            ece += (bin_size / n_samples) * abs(bin_acc - bin_conf)

    return float(round(ece, 4))


def compute_wilson_score_interval(
    correct: int, total: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculates the 95% (or specified) Wilson score confidence interval for a binomial proportion.
    Accurate for both small and large sample sizes.
    """
    if total <= 0:
        return (0.0, 0.0)

    p_hat = correct / float(total)

    # Standard normal z-value (1.96 for 95% CI)
    z_map = {0.90: 1.6449, 0.95: 1.95996, 0.99: 2.5758}
    z = z_map.get(confidence, 1.95996)

    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p_hat + z2 / (2.0 * total)) / denom
    spread = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)

    return (round(lower, 4), round(upper, 4))


def compute_bootstrap_ci(
    y_true: Union[np.ndarray, List[Any]],
    y_pred: Union[np.ndarray, List[Any]],
    n_bootstraps: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Computes a non-parametric bootstrap confidence interval for classification accuracy.
    """
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    n = len(y_true_arr)

    if n == 0:
        return (0.0, 0.0)

    rng = np.random.default_rng(seed)
    boot_accs = np.zeros(n_bootstraps, dtype=np.float64)

    for i in range(n_bootstraps):
        indices = rng.integers(0, n, size=n)
        boot_accs[i] = np.mean(y_true_arr[indices] == y_pred_arr[indices])

    alpha = (1.0 - confidence) / 2.0
    lower = float(np.percentile(boot_accs, alpha * 100))
    upper = float(np.percentile(boot_accs, (1.0 - alpha) * 100))

    return (round(lower, 4), round(upper, 4))


class TemperatureScaler:
    """
    Post-hoc temperature scaling calibrator for multi-class classification (Guo et al., ICML 2017).
    Calibrates logits: p_k(T) = softmax(z_k / T)
    Optimizes T in pure NumPy using Golden-Section search to minimize Negative Log-Likelihood (NLL).
    """

    def __init__(self, temperature: float = 1.0):
        self.temperature: float = max(temperature, 1e-4)
        self.is_fitted: bool = False

    @staticmethod
    def _softmax(logits: np.ndarray, temp: float) -> np.ndarray:
        """Numerically stable softmax with temperature scaling."""
        scaled = logits / max(temp, 1e-6)
        max_scores = np.max(scaled, axis=1, keepdims=True)
        exp_scores = np.exp(scaled - max_scores)
        denom = np.sum(exp_scores, axis=1, keepdims=True)
        denom = np.where(denom == 0, 1e-12, denom)
        return exp_scores / denom

    @classmethod
    def _nll_loss(cls, temp: float, logits: np.ndarray, y_indices: np.ndarray) -> float:
        """Computes Negative Log-Likelihood for given temperature."""
        probs = cls._softmax(logits, temp)
        n = logits.shape[0]
        # Pick probability of the true label
        correct_probs = probs[np.arange(n), y_indices]
        # Clip to prevent log(0)
        clipped = np.clip(correct_probs, 1e-12, 1.0)
        return -float(np.mean(np.log(clipped)))

    def fit(
        self,
        logits: np.ndarray,
        y_true: Union[np.ndarray, List[int]],
        bounds: Tuple[float, float] = (0.05, 10.0),
        tol: float = 1e-4,
    ) -> "TemperatureScaler":
        """
        Fits optimal temperature T on validation logits and true class indices using Golden-Section Search.
        """
        logits = np.asarray(logits, dtype=np.float64)
        y_idx = np.asarray(y_true, dtype=np.int64)

        if logits.ndim == 1:
            logits = logits.reshape(-1, 1)

        a, b = bounds
        # Golden ratio conjugate: (sqrt(5) - 1) / 2 ~= 0.6180339887
        inv_phi = (math.sqrt(5.0) - 1.0) / 2.0

        c = b - inv_phi * (b - a)
        d = a + inv_phi * (b - a)

        fc = self._nll_loss(c, logits, y_idx)
        fd = self._nll_loss(d, logits, y_idx)

        # Golden-Section Search loop
        max_iters = 60
        iteration = 0
        while abs(b - a) > tol and iteration < max_iters:
            iteration += 1
            if fc < fd:
                b = d
                d = c
                fd = fc
                c = b - inv_phi * (b - a)
                fc = self._nll_loss(c, logits, y_idx)
            else:
                a = c
                c = d
                fc = fd
                d = a + inv_phi * (b - a)
                fd = self._nll_loss(d, logits, y_idx)

        best_t = (a + b) / 2.0
        self.temperature = float(round(best_t, 4))
        self.is_fitted = True

        logger.info(f"Optimal Temperature Scaling T={self.temperature:.4f} fitted via Golden-Section Search.")
        return self

    def predict_proba(self, logits: np.ndarray) -> np.ndarray:
        """Produces calibrated probability distribution from raw logits."""
        logits = np.asarray(logits, dtype=np.float64)
        return self._softmax(logits, self.temperature)

    def calibrate_probabilities(self, uncalibrated_probs: np.ndarray) -> np.ndarray:
        """
        Calibrates uncalibrated probabilities by inverting softmax to pseudo-logits:
        logits ~= log(probs) and applying T.
        """
        probs = np.asarray(uncalibrated_probs, dtype=np.float64)
        probs = np.clip(probs, 1e-12, 1.0)
        pseudo_logits = np.log(probs)
        return self.predict_proba(pseudo_logits)
