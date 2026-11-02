"""
Pure Python & NumPy TF-IDF Vectorization Engine
Provides n-gram TF-IDF text vectorization, vocabulary extraction, model persistence, and term weight analysis without external C-DLL dependencies like SciPy.
"""
import sys
import os
import math
import collections
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import joblib
import numpy as np

from nlp.preprocessor import preprocessor, TextPreprocessor
from utils.logger import get_logger

logger = get_logger("nlp.vectorizer")


class TFIDFEngine:
    """Pure Python & NumPy TF-IDF Vectorization Engine supporting unigrams + bigrams."""

    def __init__(self, max_features: int = 1000, ngram_range: Tuple[int, int] = (1, 2)):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.preprocessor: TextPreprocessor = preprocessor

        self.vocabulary_: Dict[str, int] = {}
        self.feature_names_: List[str] = []
        self.idf_diag_: np.ndarray = np.array([])
        self.doc_count_: int = 0
        self.is_fitted: bool = False

    def _extract_ngrams(self, text: str) -> List[str]:
        """Preprocesses raw text and extracts unigrams and bigrams."""
        res = self.preprocessor.preprocess(text)
        lemmas = res.get("lemmatized_tokens", [])

        ngrams = []
        min_n, max_n = self.ngram_range

        if 1 in range(min_n, max_n + 1):
            ngrams.extend(lemmas)

        if 2 in range(min_n, max_n + 1) and len(lemmas) >= 2:
            for i in range(len(lemmas) - 1):
                ngrams.append(f"{lemmas[i]} {lemmas[i+1]}")

        return ngrams

    def fit(self, corpus_texts: List[str]) -> "TFIDFEngine":
        """Fits vocabulary and computes smooth IDF weights on corpus texts."""
        if not corpus_texts:
            raise ValueError("Corpus texts list cannot be empty for fitting.")

        self.doc_count_ = len(corpus_texts)
        df_counter = collections.Counter()
        total_tf_counter = collections.Counter()

        for text in corpus_texts:
            ngrams = self._extract_ngrams(text)
            unique_ngrams = set(ngrams)
            for ng in unique_ngrams:
                df_counter[ng] += 1
            for ng in ngrams:
                total_tf_counter[ng] += 1

        # Select top max_features by document frequency then total term frequency
        sorted_terms = sorted(
            df_counter.keys(),
            key=lambda x: (df_counter[x], total_tf_counter[x]),
            reverse=True,
        )

        if self.max_features and len(sorted_terms) > self.max_features:
            sorted_terms = sorted_terms[: self.max_features]

        # Sort feature names alphabetically for consistent feature order
        self.feature_names_ = sorted(sorted_terms)
        self.vocabulary_ = {term: idx for idx, term in enumerate(self.feature_names_)}

        # Compute Smooth IDF: ln((1 + N) / (1 + df)) + 1
        N = self.doc_count_
        idf_list = []
        for term in self.feature_names_:
            df = df_counter[term]
            idf = math.log((1.0 + N) / (1.0 + df)) + 1.0
            idf_list.append(idf)

        self.idf_diag_ = np.array(idf_list, dtype=np.float32)
        self.is_fitted = True
        logger.info(f"Fitted TF-IDF Engine on {N} documents. Vocabulary size: {len(self.feature_names_)}")
        return self

    def transform(self, raw_texts: List[str]) -> np.ndarray:
        """Transforms raw texts into L2-normalized TF-IDF feature matrix."""
        if not self.is_fitted:
            raise RuntimeError("TF-IDF Vectorizer is not fitted. Call fit() or load_model() first.")

        if isinstance(raw_texts, str):
            raw_texts = [raw_texts]

        num_samples = len(raw_texts)
        num_features = len(self.feature_names_)
        matrix = np.zeros((num_samples, num_features), dtype=np.float32)

        for i, text in enumerate(raw_texts):
            ngrams = self._extract_ngrams(text)
            counts = collections.Counter(ngrams)

            for term, count in counts.items():
                if term in self.vocabulary_:
                    idx = self.vocabulary_[term]
                    # Sublinear TF scaling: 1 + log(count)
                    sublinear_tf = 1.0 + math.log(count)
                    matrix[i, idx] = sublinear_tf * self.idf_diag_[idx]

            # L2 Normalization per row
            norm = np.linalg.norm(matrix[i])
            if norm > 0:
                matrix[i] = matrix[i] / norm

        return matrix

    def fit_transform(self, corpus_texts: List[str]) -> np.ndarray:
        """Fits vectorizer and returns transformed TF-IDF dense matrix."""
        self.fit(corpus_texts)
        return self.transform(corpus_texts)

    def get_feature_names(self) -> List[str]:
        """Returns list of vocabulary n-gram feature names."""
        return list(self.feature_names_)

    def get_top_terms_for_text(self, raw_text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Extracts non-zero TF-IDF features and their weights for a given text, sorted by highest weight.
        """
        if not self.is_fitted:
            return []

        vec = self.transform([raw_text])[0]
        non_zero_idx = np.where(vec > 0)[0]
        term_scores = [(self.feature_names_[i], float(vec[i])) for i in non_zero_idx]
        term_scores.sort(key=lambda x: x[1], reverse=True)
        return term_scores[:top_k]

    def save_model(self, model_path: str = "models/tfidf_vectorizer.joblib") -> str:
        """Saves fitted TF-IDF vectorizer engine to disk using joblib."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted TF-IDF Vectorizer.")

        out_path = Path(model_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "max_features": self.max_features,
            "ngram_range": self.ngram_range,
            "vocabulary_": self.vocabulary_,
            "feature_names_": self.feature_names_,
            "idf_diag_": self.idf_diag_,
            "doc_count_": self.doc_count_,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(data, out_path)
        logger.info(f"TF-IDF model saved successfully to {out_path.resolve()}")
        return str(out_path.resolve())

    def load_model(self, model_path: str = "models/tfidf_vectorizer.joblib") -> bool:
        """Loads fitted TF-IDF vectorizer engine from disk using joblib."""
        in_path = Path(model_path)
        if not in_path.exists():
            logger.warning(f"TF-IDF model file not found at {in_path.resolve()}")
            return False

        try:
            data = joblib.load(in_path)
            self.max_features = data.get("max_features", 1000)
            self.ngram_range = data.get("ngram_range", (1, 2))
            self.vocabulary_ = data.get("vocabulary_", {})
            self.feature_names_ = data.get("feature_names_", [])
            self.idf_diag_ = data.get("idf_diag_", np.array([]))
            self.doc_count_ = data.get("doc_count_", 0)
            self.is_fitted = data.get("is_fitted", True)
            logger.info(f"TF-IDF model loaded from {in_path.resolve()}. Vocabulary: {len(self.feature_names_)}")
            return True
        except Exception as exc:
            logger.error(f"Failed to load TF-IDF model from {in_path.resolve()}: {exc}")
            return False


tfidf_engine = TFIDFEngine()
