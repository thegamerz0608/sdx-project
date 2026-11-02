"""
TF-IDF Service Layer
Manages vectorizer training, corpus fitting, model loading/persisting, category top n-gram analysis, and vocabulary inspection.
"""
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from pathlib import Path

from nlp.vectorizer import tfidf_engine, TFIDFEngine
from nlp.feature_extractor import feature_extractor, FeatureExtractor
from services.nlp_service import nlp_service
from utils.logger import get_logger

logger = get_logger("services.tfidf_service")


class TFIDFService:
    """Service facade managing TF-IDF training, vocabulary inspection, and feature extraction."""

    def __init__(self):
        self.vectorizer = tfidf_engine
        self.extractor = feature_extractor
        self.model_path = Path("models/tfidf_vectorizer.joblib")

    def ensure_fitted(self, force_refit: bool = False) -> TFIDFEngine:
        """
        Ensures vectorizer is fitted.
        Attempts to load persisted model first; fits on corpus if absent or force_refit is True.
        """
        if not force_refit and self.vectorizer.is_fitted:
            return self.vectorizer

        if not force_refit and self.model_path.exists():
            success = self.vectorizer.load_model(str(self.model_path))
            if success:
                return self.vectorizer

        logger.info("Fitting TF-IDF Vectorizer on full NLP corpus dataset...")
        corpus = nlp_service.load_corpus()
        texts = [item.get("text", "") for item in corpus]
        self.vectorizer.fit(texts)
        self.vectorizer.save_model(str(self.model_path))
        return self.vectorizer

    def get_vocabulary_summary(self) -> Dict[str, Any]:
        """Returns vocabulary size, n-gram details, and sample feature list."""
        self.ensure_fitted()
        features = self.vectorizer.get_feature_names()
        unigrams = [f for f in features if " " not in f]
        bigrams = [f for f in features if " " in f]

        return {
            "total_features": len(features),
            "unigram_count": len(unigrams),
            "bigram_count": len(bigrams),
            "sample_unigrams": unigrams[:15],
            "sample_bigrams": bigrams[:15],
            "is_fitted": self.vectorizer.is_fitted,
        }

    def get_top_ngrams_per_category(self, top_k: int = 10) -> Dict[str, List[Tuple[str, float]]]:
        """
        Calculates mean TF-IDF weight vector for each leave category and returns top K n-grams per category.
        """
        self.ensure_fitted()
        corpus = nlp_service.load_corpus()
        features = self.vectorizer.get_feature_names()

        # Group texts by category
        cat_texts: Dict[str, List[str]] = {}
        for item in corpus:
            lbl = item.get("label", "CL")
            cat_texts.setdefault(lbl, []).append(item.get("text", ""))

        category_top_ngrams = {}

        for cat, texts in cat_texts.items():
            if not texts:
                continue
            matrix = self.vectorizer.transform(texts)
            mean_weights = np.mean(matrix, axis=0)

            # Sort by mean weight
            sorted_indices = np.argsort(mean_weights)[::-1]
            top_terms = [
                (features[idx], round(float(mean_weights[idx]), 4))
                for idx in sorted_indices[:top_k]
                if mean_weights[idx] > 0
            ]
            category_top_ngrams[cat] = top_terms

        return category_top_ngrams

    def inspect_text_vector(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Performs live vectorization inspection for a given text and metadata sample.
        Returns top TF-IDF n-grams, metadata vector, and composite vector dimension.
        """
        self.ensure_fitted()
        if metadata is None:
            metadata = {
                "requested_days": 1.0,
                "notice_period_days": 0.0,
                "has_medical_doc": False,
                "is_sandwich_leave": False,
            }

        top_terms = self.vectorizer.get_top_terms_for_text(raw_text, top_k=15)
        meta_vec = self.extractor.extract_metadata_features(metadata)
        composite_vec = self.extractor.extract_composite_features(raw_text, metadata)

        return {
            "raw_text": raw_text,
            "top_tfidf_terms": top_terms,
            "metadata_features": meta_vec.tolist(),
            "tfidf_dimension": len(self.vectorizer.get_feature_names()),
            "composite_dimension": len(composite_vec),
            "non_zero_terms_count": len(self.vectorizer.get_top_terms_for_text(raw_text, top_k=1000)),
        }

    def extract_features_for_text(self, raw_text: str) -> Dict[str, Any]:
        """Convenience method returning vectorized features and clean text."""
        res = self.inspect_text_vector(raw_text)
        res["clean_text"] = raw_text
        res["tfidf_vector"] = res["top_tfidf_terms"]
        return res


tfidf_service = TFIDFService()
