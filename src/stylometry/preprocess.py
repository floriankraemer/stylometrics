"""Single spaCy pass shared by all downstream metrics."""
from dataclasses import dataclass, field

import spacy

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


@dataclass
class Analysis:
    doc: "spacy.tokens.Doc"
    sentences: list = field(default_factory=list)
    words: list = field(default_factory=list)  # alpha tokens, lowercased text
    raw_text: str = ""


def analyze(text: str) -> Analysis:
    nlp = get_nlp()
    # spaCy's default max_length is 1_000_000 chars; raise it for book-length input.
    nlp.max_length = max(nlp.max_length, len(text) + 1000)
    doc = nlp(text)
    sentences = list(doc.sents)
    words = [t for t in doc if t.is_alpha]
    return Analysis(doc=doc, sentences=sentences, words=words, raw_text=text)
