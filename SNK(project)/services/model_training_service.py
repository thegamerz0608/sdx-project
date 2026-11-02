"""
Model Training & Live Classification Service Layer
Executes multi-model ML training, benchmark evaluation, best model persistence, and real-time leave reason classification with probability scores.
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import joblib
import numpy as np

from nlp.classifiers import (
    MultinomialNaiveBayes,
    SoftmaxLogisticRegression,
    RandomForest,
    LinearSVM,
    CLASSES,
    CLASS_TO_IDX,
)
from nlp.model_evaluator import evaluator, ModelEvaluator
from nlp.calibration import TemperatureScaler, compute_ece
from nlp.oov_detector import oov_detector
from nlp.explainability import explain_model_features
from services.tfidf_service import tfidf_service
from services.nlp_service import nlp_service
from nlp.dataset_generator import LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("services.model_training_service")


class ModelTrainingService:
    """Service facade managing ML classifier training, benchmarking, persistence, and live prediction."""

    def __init__(self):
        self.model_path = Path("models/best_leave_classifier.joblib")
        self.best_model: Optional[Any] = None
        self.best_model_name: str = "Multinomial Naïve Bayes"
        self.leaderboard_cache: List[Dict[str, Any]] = []

    def train_and_evaluate_all_models(self) -> List[Dict[str, Any]]:
        """
        Trains Naïve Bayes, Softmax Logistic Regression, Random Forest, and Linear SVM classifiers.
        Evaluates test performance, ranks models by Macro F1 score, and saves best model.
        """
        logger.info("Initializing multi-model ML training pipeline...")

        # 1. Ensure TF-IDF vectorizer is fitted
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

        # 2. Extract composite feature matrix
        X = tfidf_service.extractor.batch_extract_composite_features(texts, metadata_list)
        y = labels

        # 3. Stratified Train / Validation / Test split
        X_train_full, X_test, y_train_full, y_test = evaluator.train_test_split(X, y, test_size=0.2, seed=42)
        X_train, X_val, y_train, y_val = evaluator.train_test_split(X_train_full, y_train_full, test_size=0.25, seed=42)
        y_val_idx = np.array([CLASS_TO_IDX.get(lbl, 0) for lbl in y_val])

        # 4. Instantiate Candidate Classifiers
        models = [
            ("Multinomial Naïve Bayes", MultinomialNaiveBayes(alpha=0.5)),
            ("Softmax Logistic Regression", SoftmaxLogisticRegression(lr=0.2, max_iter=350)),
            ("Random Forest", RandomForest(n_estimators=20, max_depth=8)),
            ("Linear SVM (One-vs-Rest)", LinearSVM(lr=0.1, max_iter=350)),
        ]

        leaderboard = []

        for name, clf in models:
            logger.info(f"Training {name} on {X_train.shape[0]} samples...")
            clf.fit(X_train, y_train)

            # Fit post-hoc Temperature Scaling on validation split if model supports probabilities
            if hasattr(clf, "predict_proba"):
                val_probs = clf.predict_proba(X_val)
                scaler = TemperatureScaler()
                scaler.fit(np.log(np.clip(val_probs, 1e-12, 1.0)), y_val_idx)
                if hasattr(clf, "temperature"):
                    clf.temperature = scaler.temperature

            metrics = evaluator.evaluate_model(clf, X_test, y_test)
            metrics["model_name"] = name
            metrics["model_obj"] = clf
            metrics["temperature"] = getattr(clf, "temperature", 1.0)
            leaderboard.append(metrics)

        # 5. Rank by Macro F1-score
        leaderboard.sort(key=lambda item: (item["macro_f1"], item["accuracy"]), reverse=True)
        self.leaderboard_cache = leaderboard

        # 6. Set Champion Model and save to disk
        champion = leaderboard[0]
        self.best_model_name = champion["model_name"]
        self.best_model = champion["model_obj"]

        out_data = {
            "model_name": self.best_model_name,
            "model_obj": self.best_model,
            "leaderboard": [
                {k: v for k, v in item.items() if k != "model_obj"}
                for item in leaderboard
            ],
        }
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(out_data, self.model_path)
        logger.info(f"Champion Model '{self.best_model_name}' (F1: {champion['macro_f1']}) saved to {self.model_path.resolve()}")

        return leaderboard

    def ensure_best_model_loaded(self) -> Any:
        """Loads champion model from disk or trains all models if missing."""
        if self.best_model is not None:
            return self.best_model

        if self.model_path.exists():
            try:
                data = joblib.load(self.model_path)
                self.best_model_name = data.get("model_name", "Multinomial Naïve Bayes")
                self.best_model = data.get("model_obj")
                self.leaderboard_cache = data.get("leaderboard", [])
                if self.best_model is not None:
                    return self.best_model
            except Exception as exc:
                logger.warning(f"Could not load best model file: {exc}. Retraining...")

        self.train_and_evaluate_all_models()
        return self.best_model

    def predict_leave_reason(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Predicts leave category for raw text and metadata.
        Returns predicted category code, full name, probability distribution, and policy routing advice.
        Includes OOV/gibberish rejection and uncertainty detection.
        """
        model = self.ensure_best_model_loaded()
        tfidf_service.ensure_fitted()

        # Sanitize text input against None/empty/non-string
        raw_text = str(raw_text or "").strip()

        # OOV & Gibberish Screening
        oov_assessment = oov_detector.assess_input_vocabulary(raw_text)
        if oov_assessment["is_oov"]:
            logger.info(f"Input rejected as OOV/gibberish: {oov_assessment['reason']}")
            uniform_prob = round(1.0 / len(CLASSES), 4)
            return {
                "raw_text": raw_text,
                "predicted_category": "UNCERTAIN",
                "predicted_type": "UNCERTAIN",
                "category_name": "Uncertain / Out-of-Vocabulary",
                "confidence_score": uniform_prob,
                "confidence": uniform_prob,
                "confidence_percentage": f"{uniform_prob * 100:.1f}%",
                "probabilities": {cat: uniform_prob for cat in CLASSES},
                "champion_model": self.best_model_name,
                "routing_advice": "MANUAL_REVIEW: Application text contains insufficient or uninformative domain vocabulary. Manual review required by HOD.",
                "is_oov": True,
                "is_uncertain": True,
                "oov_reason": oov_assessment["reason"],
            }

        if metadata is None:
            metadata = {
                "requested_days": 1.0,
                "notice_period_days": 0.0,
                "has_medical_doc": False,
                "is_sandwich_leave": False,
            }

        comp_vec = tfidf_service.extractor.extract_composite_features(raw_text, metadata).reshape(1, -1)

        # Probabilities
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(comp_vec)[0]
        else:
            probs = np.ones(len(CLASSES)) / len(CLASSES)

        pred_label = model.predict(comp_vec)[0]
        pred_idx = CLASSES.index(pred_label) if pred_label in CLASSES else 0
        confidence = float(probs[pred_idx])

        # Evaluate Prediction Uncertainty
        unc_assessment = oov_detector.assess_prediction_uncertainty(probs)
        is_uncertain = unc_assessment["is_uncertain"]

        # Probability breakdown dict
        prob_dist = {cat: round(float(probs[i]), 4) for i, cat in enumerate(CLASSES)}

        # Policy routing recommendation logic
        category_name = LEAVE_CATEGORIES.get(pred_label, pred_label)
        routing_advice = self._generate_routing_advice(pred_label, metadata, confidence)
        if is_uncertain:
            routing_advice = f"CAUTION: High prediction uncertainty ({confidence*100:.1f}%). {routing_advice}"

        return {
            "raw_text": raw_text,
            "predicted_category": pred_label,
            "predicted_type": pred_label,
            "category_name": category_name,
            "confidence_score": confidence,
            "confidence": confidence,
            "confidence_percentage": f"{confidence * 100:.1f}%",
            "probabilities": prob_dist,
            "champion_model": self.best_model_name,
            "routing_advice": routing_advice,
            "is_oov": False,
            "is_uncertain": is_uncertain,
            "uncertainty_reason": unc_assessment.get("uncertainty_reason"),
        }

    def get_champion_feature_explanations(self, top_k: int = 10) -> Dict[str, Any]:
        """Returns top positive and negative predictive features per class for champion model."""
        model = self.ensure_best_model_loaded()
        tfidf_service.ensure_fitted()
        fnames = tfidf_service.extractor.get_composite_feature_names()
        return explain_model_features(model, fnames, top_k=top_k)

    def _generate_routing_advice(self, category: str, metadata: Dict[str, Any], confidence: float) -> str:
        req_days = metadata.get("requested_days", 1.0)
        has_doc = metadata.get("has_medical_doc", False)

        if category == "ML":
            if req_days > 2.0 and not has_doc:
                return "WARNING: Medical Leave exceeding 2 days requires doctor certificate verification before HOD approval."
            return "ROUTE: Medical Leave application automatically flagged for HOD verification and balance deduction."
        elif category in ["SCL", "OD"]:
            return "ROUTE: Special/On Duty leave requires official university invitation or FDP deputation proof attachment."
        elif category == "EL":
            return "ROUTE: Earned Leave requires advance notice verification and HOD approval."
        else:
            return "ROUTE: Standard Casual Leave. Direct processing based on available balance."


model_training_service = ModelTrainingService()
