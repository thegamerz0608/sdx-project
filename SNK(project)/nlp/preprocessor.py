"""
NLP Text Preprocessing Engine
Provides text cleaning, tokenization, stopword filtering, and lemmatization pipeline.
"""
import re
from typing import List, Dict, Any
from utils.logger import get_logger

logger = get_logger("nlp.preprocessor")

# Comprehensive built-in English stopwords list for 100% offline execution
ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how",
    "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "please",
    "kindly", "grant", "request", "sir", "madam", "application", "due", "taking", "want", "need", "days"
}

# Rule-based suffix lemmatizer map for common domain terms
LEMMATIZER_SUFFIX_RULES = [
    ("ing", ""),
    ("ed", ""),
    ("ies", "y"),
    ("es", "e"),
    ("s", ""),
]

CUSTOM_LEMMA_MAP = {
    "feverish": "fever",
    "fevers": "fever",
    "doctor's": "doctor",
    "doctors": "doctor",
    "hospitals": "hospital",
    "hospitalization": "hospital",
    "hospitalized": "hospital",
    "conferences": "conference",
    "workshops": "workshop",
    "evaluations": "evaluate",
    "evaluating": "evaluate",
    "examinations": "examine",
    "examiners": "examiner",
    "travelling": "travel",
    "traveling": "travel",
    "attending": "attend",
    "attended": "attend",
    "suffering": "suffer",
    "suffered": "suffer",
}


class TextPreprocessor:
    """Text Preprocessing Engine for Leave Reason Classification."""

    def __init__(self):
        self.stopwords = ENGLISH_STOPWORDS

    def clean_text(self, raw_text: str) -> str:
        """
        Cleans input string: lowercasing, HTML tag stripping, punctuation removal, whitespace normalization.
        """
        if not raw_text or not isinstance(raw_text, str):
            return ""

        # Lowercase
        text = raw_text.lower().strip()

        # Remove HTML tags if present
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove non-alphanumeric characters (keep letters, digits, whitespace)
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        # Normalize multiple spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def tokenize(self, text: str) -> List[str]:
        """Splits cleaned text into word tokens (length >= 2)."""
        if not text:
            return []
        tokens = text.split()
        return [t for t in tokens if len(t) >= 2 and not t.isdigit()]

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Filters out common English and boilerplate stopwords."""
        return [t for t in tokens if t not in self.stopwords]

    def lemmatize_token(self, token: str) -> str:
        """Reduces a word token to its base lemma."""
        if token in CUSTOM_LEMMA_MAP:
            return CUSTOM_LEMMA_MAP[token]

        if len(token) <= 4:
            return token

        # Suffix rules
        for suffix, replacement in LEMMATIZER_SUFFIX_RULES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                return token[: -len(suffix)] + replacement

        return token

    def lemmatize(self, tokens: List[str]) -> List[str]:
        """Lemmatizes a list of tokens."""
        return [self.lemmatize_token(t) for t in tokens]

    def preprocess(self, raw_text: str) -> Dict[str, Any]:
        """
        Executes full preprocessing pipeline on raw text input.
        Returns detailed structured pipeline stage dictionary.
        """
        cleaned = self.clean_text(raw_text)
        tokens = self.tokenize(cleaned)
        filtered = self.remove_stopwords(tokens)
        lemmas = self.lemmatize(filtered)

        processed_str = " ".join(lemmas)

        return {
            "raw_text": raw_text,
            "cleaned_text": cleaned,
            "raw_tokens": tokens,
            "filtered_tokens": filtered,
            "lemmatized_tokens": lemmas,
            "processed_string": processed_str,
            "word_count": len(tokens),
            "lemma_count": len(lemmas),
        }

    def preprocess_text(self, raw_text: str) -> List[str]:
        """Convenience method returning lemmatized tokens directly."""
        return self.preprocess(raw_text)["lemmatized_tokens"]


preprocessor = TextPreprocessor()
