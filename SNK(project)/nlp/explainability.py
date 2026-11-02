"""
Model Explainability & Feature Attribution Engine (Pure NumPy)
Extracts top positive and negative predictive features/n-grams per leave category
from trained linear, logistic, and probabilistic classifiers.
"""
from typing import Dict, List, Tuple, Any
import numpy as np

from nlp.classifiers import CLASSES


def explain_model_features(
    model: Any,
    feature_names: List[str],
    top_k: int = 10,
) -> Dict[str, Dict[str, List[Tuple[str, float]]]]:
    """
    Extracts top-k positive and top-k negative predictive features for each leave class.
    
    Supports:
    - MultinomialNaiveBayes: uses log-odds ratio of class feature prob vs rest of classes.
    - SoftmaxLogisticRegression: uses weight vectors W[:, c].
    - LinearSVM: uses hyperplane normal vectors W[:, c].
    """
    num_classes = len(CLASSES)
    explanations: Dict[str, Dict[str, List[Tuple[str, float]]]] = {}

    if hasattr(model, "W") and model.W is not None:
        # Linear / Logistic model: W has shape (num_features, num_classes)
        W = model.W
        num_feats = min(len(feature_names), W.shape[0])

        for c_idx, c_name in enumerate(CLASSES):
            if c_idx >= W.shape[1]:
                continue
            class_weights = W[:num_feats, c_idx]
            pos_sorted = np.argsort(class_weights)[::-1]
            neg_sorted = np.argsort(class_weights)

            top_pos = [
                (feature_names[i], round(float(class_weights[i]), 4))
                for i in pos_sorted[:top_k]
            ]
            top_neg = [
                (feature_names[i], round(float(class_weights[i]), 4))
                for i in neg_sorted[:top_k]
            ]

            explanations[c_name] = {
                "positive_features": top_pos,
                "negative_features": top_neg,
            }

    elif hasattr(model, "feature_log_prob_") and model.feature_log_prob_ is not None:
        # Naive Bayes: feature_log_prob_ has shape (num_classes, num_features)
        log_probs = model.feature_log_prob_
        num_feats = min(len(feature_names), log_probs.shape[1])

        for c_idx, c_name in enumerate(CLASSES):
            if c_idx >= log_probs.shape[0]:
                continue
            # Contrast log prob of class c against mean log prob of all other classes
            other_classes = [i for i in range(log_probs.shape[0]) if i != c_idx]
            rest_mean_log_prob = np.mean(log_probs[other_classes, :num_feats], axis=0)
            log_odds = log_probs[c_idx, :num_feats] - rest_mean_log_prob

            pos_sorted = np.argsort(log_odds)[::-1]
            neg_sorted = np.argsort(log_odds)

            top_pos = [
                (feature_names[i], round(float(log_odds[i]), 4))
                for i in pos_sorted[:top_k]
            ]
            top_neg = [
                (feature_names[i], round(float(log_odds[i]), 4))
                for i in neg_sorted[:top_k]
            ]

            explanations[c_name] = {
                "positive_features": top_pos,
                "negative_features": top_neg,
            }

    else:
        # Fallback for models without direct linear weight inspectability
        for c_name in CLASSES:
            explanations[c_name] = {
                "positive_features": [],
                "negative_features": [],
            }

    return explanations
