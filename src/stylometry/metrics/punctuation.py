"""Punctuation frequency profile, per 1000 words."""
import re

from stylometry.language import LANGUAGES

_PATTERNS = {
    "semicolon": r";",
    "colon": r":",
    "parentheses": r"\(",
    "ellipsis": r"\.\.\.|…",
    "exclamation": r"!",
    "question_mark": r"\?",
    "comma": r",",
}


def compute(raw_text: str, word_count: int, lang: str = "en") -> dict:
    patterns = {"em_dash": LANGUAGES[lang]["em_dash"], **_PATTERNS}
    if word_count == 0:
        return {name: 0.0 for name in patterns}
    return {
        name: round(len(re.findall(pattern, raw_text)) / word_count * 1000, 2)
        for name, pattern in patterns.items()
    }
