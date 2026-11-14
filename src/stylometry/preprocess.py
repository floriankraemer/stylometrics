"""Single spaCy pass shared by all downstream metrics."""
import logging
import re
from dataclasses import dataclass, field

import spacy

from stylometry.language import LANGUAGES

log = logging.getLogger("stylometry")
_models = {}
_CHUNK_RE = re.compile(r"\n\s*\n")


def get_nlp(lang: str = "en"):
    if lang not in _models:
        model = LANGUAGES[lang]["model"]
        try:
            _models[lang] = spacy.load(model)
        except OSError as e:
            raise OSError(f"spaCy model {model} is not installed: python -m spacy download {model}") from e
    return _models[lang]


@dataclass
class Analysis:
    doc: "spacy.tokens.Doc"
    sentences: list = field(default_factory=list)
    words: list = field(default_factory=list)  # alpha tokens, lowercased text
    raw_text: str = ""
    lang: str = "en"


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


def analyze(text: str, lang: str = "en") -> Analysis:
    nlp = get_nlp(lang)
    # spaCy's default max_length is 1_000_000 chars; raise it for book-length input.
    nlp.max_length = max(nlp.max_length, len(text) + 1000)

    chunks = _chunk(text)
    docs = []
    for i, doc in enumerate(nlp.pipe(chunks), start=1):
        docs.append(doc)
        log.info("spaCy: %d/%d chunks (%d%%)", i, len(chunks), 100 * i // len(chunks))
    doc = spacy.tokens.Doc.from_docs(docs)

    sentences = list(doc.sents)
    words = [t for t in doc if t.is_alpha]
    return Analysis(doc=doc, sentences=sentences, words=words, raw_text=text, lang=lang)
