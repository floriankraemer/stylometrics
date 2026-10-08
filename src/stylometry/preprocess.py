"""Single spaCy pass shared by all downstream metrics."""
import re
import sys
from dataclasses import dataclass, field

import spacy

_nlp = None
_CHUNK_RE = re.compile(r"\n\s*\n")


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


def _chunk(text: str, target_size: int = 50_000) -> list:
    """Split text on paragraph breaks into ~target_size chunks, for pipe progress."""
    paras = _CHUNK_RE.split(text)
    chunks, buf = [], ""
    for p in paras:
        if buf and len(buf) + len(p) > target_size:
            chunks.append(buf)
            buf = p
        else:
            buf = buf + "\n\n" + p if buf else p
    if buf:
        chunks.append(buf)
    return chunks or [text]


def analyze(text: str) -> Analysis:
    nlp = get_nlp()
    # spaCy's default max_length is 1_000_000 chars; raise it for book-length input.
    nlp.max_length = max(nlp.max_length, len(text) + 1000)

    chunks = _chunk(text)
    docs = []
    for i, doc in enumerate(nlp.pipe(chunks), start=1):
        docs.append(doc)
        print(f"[stylometry] spaCy: {i}/{len(chunks)} chunks ({100 * i // len(chunks)}%)",
              file=sys.stderr)
    doc = spacy.tokens.Doc.from_docs(docs)

    sentences = list(doc.sents)
    words = [t for t in doc if t.is_alpha]
    return Analysis(doc=doc, sentences=sentences, words=words, raw_text=text)
