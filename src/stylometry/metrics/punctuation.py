"""Punctuation frequency profile, per 1000 words."""
import re

_PATTERNS = {
    "em_dash": r"—|--",
    "semicolon": r";",
    "colon": r":",
    "parentheses": r"\(",
    "ellipsis": r"\.\.\.|…",
    "exclamation": r"!",
    "question_mark": r"\?",
    "comma": r",",
}


def compute(raw_text: str, word_count: int) -> dict:
    if word_count == 0:
        return {name: 0.0 for name in _PATTERNS}
    return {
        name: round(len(re.findall(pattern, raw_text)) / word_count * 1000, 2)
        for name, pattern in _PATTERNS.items()
    }
