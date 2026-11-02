"""
NLP Service Layer
Provides service facade for NLP leave corpus loading, text preprocessing, and dataset statistics.
"""
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

from nlp.preprocessor import preprocessor, TextPreprocessor
from nlp.dataset_generator import verify_and_build_dataset, LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("services.nlp_service")


class NLPService:
    """Service facade managing NLP corpus data and text preprocessing pipeline."""

    def __init__(self):
        self.preprocessor = preprocessor
        self.corpus_path = Path("dataset/leave_reasons_corpus.json")

    def load_corpus(self) -> List[Dict[str, Any]]:
        """Loads or generates the NLP leave reason corpus dataset."""
        if not self.corpus_path.exists():
            logger.info("NLP Corpus JSON not found. Initializing dataset generator...")
            verify_and_build_dataset()

        try:
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as exc:
            logger.warning(f"Failed to read corpus JSON: {exc}. Regenerating dataset...")
            stats = verify_and_build_dataset()
            with open(self.corpus_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def preprocess_text(self, raw_text: str) -> Dict[str, Any]:
        """Executes full NLP text cleaning, tokenization, stopword removal, and lemmatization."""
        return self.preprocessor.preprocess(raw_text)

    def get_corpus_statistics(self) -> Dict[str, Any]:
        """Calculates comprehensive corpus dataset statistics."""
        corpus = self.load_corpus()
        total_samples = len(corpus)

        class_counts = {code: 0 for code in LEAVE_CATEGORIES.keys()}
        total_words = 0
        total_lemmas = 0

        for item in corpus:
            lbl = item.get("label", "CL")
            class_counts[lbl] = class_counts.get(lbl, 0) + 1

            prep = self.preprocessor.preprocess(item.get("text", ""))
            total_words += prep["word_count"]
            total_lemmas += prep["lemma_count"]

        avg_words = round(total_words / total_samples, 1) if total_samples else 0.0
        avg_lemmas = round(total_lemmas / total_samples, 1) if total_samples else 0.0

        return {
            "total_samples": total_samples,
            "class_counts": class_counts,
            "category_names": LEAVE_CATEGORIES,
            "avg_words_per_sample": avg_words,
            "avg_lemmas_per_sample": avg_lemmas,
            "total_vocabulary_tokens": total_lemmas,
        }


nlp_service = NLPService()
