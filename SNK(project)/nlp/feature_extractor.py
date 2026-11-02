"""
Composite Feature Extractor Module
Combines TF-IDF text vector features with normalized tabular metadata features for machine learning models.
"""
from typing import Dict, Any, List, Tuple
import numpy as np

from nlp.vectorizer import tfidf_engine, TFIDFEngine
from utils.logger import get_logger

logger = get_logger("nlp.feature_extractor")

METADATA_FEATURE_NAMES = [
    "meta_requested_days_norm",
    "meta_notice_period_days_norm",
    "meta_has_medical_doc",
    "meta_is_sandwich_leave",
]


class FeatureExtractor:
    """Combines TF-IDF text features and normalized tabular metadata into a composite feature matrix."""

    def __init__(self, vectorizer: TFIDFEngine = tfidf_engine):
        self.vectorizer = vectorizer

    def extract_metadata_features(self, metadata: Dict[str, Any]) -> np.ndarray:
        """
        Extracts and normalizes numerical metadata features into a 1D float array of size 4:
        1. requested_days (normalized by / 10.0, max 1.0)
        2. notice_period_days (normalized by / 30.0, max 1.0)
        3. has_medical_doc (0.0 or 1.0)
        4. is_sandwich_leave (0.0 or 1.0)
        """
        req_days = float(metadata.get("requested_days", 1.0))
        notice_days = float(metadata.get("notice_period_days", 0.0))
        med_doc = 1.0 if metadata.get("has_medical_doc", False) else 0.0
        sandwich = 1.0 if metadata.get("is_sandwich_leave", False) else 0.0

        # Normalization
        norm_req = min(req_days / 10.0, 1.0)
        norm_notice = min(notice_days / 30.0, 1.0)

        return np.array([norm_req, norm_notice, med_doc, sandwich], dtype=np.float32)

    def extract_composite_features(self, raw_text: str, metadata: Dict[str, Any]) -> np.ndarray:
        """
        Extracts concatenated 1D feature array: [TF-IDF features... + Metadata features...].
        """
        text_vec = self.vectorizer.transform([raw_text])[0]
        meta_vec = self.extract_metadata_features(metadata)
        return np.concatenate([text_vec, meta_vec])

    def batch_extract_composite_features(self, texts: List[str], metadata_list: List[Dict[str, Any]]) -> np.ndarray:
        """Extracts 2D feature matrix (N, num_tfidf + num_meta) for a batch of samples."""
        text_matrix = self.vectorizer.transform(texts)
        meta_matrix = np.array([self.extract_metadata_features(m) for m in metadata_list], dtype=np.float32)
        return np.hstack([text_matrix, meta_matrix])

    def get_composite_feature_names(self) -> List[str]:
        """Returns ordered feature names for composite vector."""
        tfidf_names = self.vectorizer.get_feature_names()
        return tfidf_names + METADATA_FEATURE_NAMES


feature_extractor = FeatureExtractor()
