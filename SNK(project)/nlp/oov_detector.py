"""
Out-of-Vocabulary (OOV) & Gibberish Rejection Engine
Detects uninformative, gibberish, out-of-vocabulary, and highly uncertain text inputs
to prevent spurious, high-confidence bogus predictions on malformed leave requests.
"""
import re
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from nlp.preprocessor import preprocessor, TextPreprocessor
from nlp.vectorizer import tfidf_engine, TFIDFEngine
from utils.logger import get_logger

logger = get_logger("nlp.oov_detector")

VOWELS = set("aeiou")


class OOVDetector:
    """Detects out-of-vocabulary terms, repetitive gibberish, and prediction uncertainty."""

    def __init__(
        self,
        vectorizer: Optional[TFIDFEngine] = None,
        min_confidence_threshold: float = 0.35,
        max_entropy_threshold: float = 0.90,
    ):
        self.vectorizer = vectorizer or tfidf_engine
        self.min_confidence_threshold = min_confidence_threshold
        self.max_entropy_threshold = max_entropy_threshold
        self.preprocessor = preprocessor

    def is_gibberish_string(self, text: Optional[str]) -> Tuple[bool, str]:
        """
        Analyzes raw string for non-linguistic gibberish patterns:
        - Excessive repeated characters (e.g., 'aaaaaa', 'zzzzzz')
        - Lack of vowels in long tokens (e.g., 'asdfghjkl', 'qwrtpsdf')
        - Extremely short or all-numeric tokens
        """
        if not text or not isinstance(text, str):
            return True, "TEXT_TOO_SHORT_OR_EMPTY"

        cleaned = self.preprocessor.clean_text(text)
        if not cleaned or len(cleaned) < 3:
            return True, "TEXT_TOO_SHORT_OR_EMPTY"

        # Check for excessive character repetition (4+ identical characters in a row)
        if re.search(r"(.)\1{3,}", cleaned):
            return True, "REPETITIVE_CHARACTER_SEQUENCE"

        tokens = cleaned.split()
        if not tokens:
            return True, "NO_VALID_TOKENS"

        # Check if ANY token of length >= 5 has no vowels (e.g., 'qwrtpsdf', 'zxcvbnm')
        for tok in tokens:
            if len(tok) >= 5 and sum(1 for ch in tok if ch in VOWELS) == 0:
                return True, "CONSONANT_KEYBOARD_SMASH"

        # Check home row keyboard smash sequences
        home_row_patterns = ["asdfgh", "dfghjk", "fghjkl", "qwerty", "zxcvbn", "qwert"]
        for p in home_row_patterns:
            if p in cleaned:
                return True, "KEYBOARD_ROW_SEQUENCE"

        return False, "VALID"

    def assess_input_vocabulary(self, raw_text: Optional[str]) -> Dict[str, Any]:
        """
        Inspects whether the input text contains known domain n-grams from the TF-IDF vocabulary.
        """
        if not raw_text or not isinstance(raw_text, str):
            return {
                "is_oov": True,
                "reason": "TEXT_TOO_SHORT_OR_EMPTY",
                "known_ngrams": [],
                "unknown_tokens": [],
                "vocab_overlap_ratio": 0.0,
            }

        # 1. Structural gibberish check
        is_gib, gib_reason = self.is_gibberish_string(raw_text)
        if is_gib:
            return {
                "is_oov": True,
                "reason": gib_reason,
                "known_ngrams": [],
                "unknown_tokens": raw_text.split() if isinstance(raw_text, str) else [],
                "vocab_overlap_ratio": 0.0,
            }

        # 2. Extract n-grams using vectorizer pipeline
        lemmas = self.preprocessor.preprocess(raw_text).get("lemmatized_tokens", [])
        if not lemmas:
            return {
                "is_oov": True,
                "reason": "NO_EXTRACTABLE_LEMMAS",
                "known_ngrams": [],
                "unknown_tokens": [],
                "vocab_overlap_ratio": 0.0,
            }

        vocab = getattr(self.vectorizer, "vocabulary_", {})
        if not vocab:
            try:
                from services.tfidf_service import tfidf_service
                tfidf_service.ensure_fitted()
                vocab = getattr(tfidf_service.vectorizer, "vocabulary_", {})
            except Exception:
                pass

        if not vocab:
            # Vectorizer still not fitted; cannot definitively flag OOV
            return {
                "is_oov": False,
                "reason": "VECTORIZER_NOT_FITTED",
                "known_ngrams": [],
                "unknown_tokens": lemmas,
                "vocab_overlap_ratio": 1.0,
            }

        # Check unigrams and bigrams
        extracted_ngrams = list(lemmas)
        if len(lemmas) >= 2:
            for i in range(len(lemmas) - 1):
                extracted_ngrams.append(f"{lemmas[i]} {lemmas[i+1]}")

        known = [ng for ng in extracted_ngrams if ng in vocab]
        overlap_ratio = len(known) / float(len(extracted_ngrams)) if extracted_ngrams else 0.0

        is_oov = len(known) == 0

        return {
            "is_oov": is_oov,
            "reason": "ZERO_VOCABULARY_OVERLAP" if is_oov else "DOMAIN_VOCABULARY_DETECTED",
            "known_ngrams": known,
            "unknown_tokens": [t for t in lemmas if t not in vocab],
            "vocab_overlap_ratio": round(overlap_ratio, 4),
        }

    def assess_prediction_uncertainty(self, probs: np.ndarray) -> Dict[str, Any]:
        """
        Evaluates calibrated probability distribution for excessive uncertainty or uniform dispersion.
        """
        probs = np.asarray(probs, dtype=np.float64)
        if probs.ndim == 2:
            probs = probs[0]

        num_classes = len(probs)
        if num_classes <= 1:
            return {"is_uncertain": False, "entropy": 0.0, "max_prob": 1.0}

        max_prob = float(np.max(probs))

        # Normalized Shannon entropy in [0, 1]
        clipped = np.clip(probs, 1e-12, 1.0)
        entropy = -float(np.sum(clipped * np.log(clipped))) / math.log(num_classes)

        is_uncertain = (max_prob < self.min_confidence_threshold) or (entropy > self.max_entropy_threshold)

        return {
            "is_uncertain": is_uncertain,
            "max_confidence": round(max_prob, 4),
            "normalized_entropy": round(entropy, 4),
            "uncertainty_reason": "MAX_PROB_BELOW_THRESHOLD" if max_prob < self.min_confidence_threshold else (
                "ENTROPY_ABOVE_THRESHOLD" if entropy > self.max_entropy_threshold else "CONFIDENT"
            ),
        }


# Type alias helper
Tuple_Bool_Reason = Any

oov_detector = OOVDetector()
