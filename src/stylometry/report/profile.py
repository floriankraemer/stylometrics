"""Assembles the single structured profile dict all writers render from."""
from stylometry.metrics import burstiness, function_words, lexical, punctuation, syntax
from stylometry.preprocess import Analysis
from stylometry.qualitative import heuristics


def build(analysis: Analysis, source_name: str, llm_result: dict | None = None) -> dict:
    quantitative = {
        "lexical": lexical.compute(analysis.words),
        "function_words": function_words.compute(analysis.words),
        "syntax": syntax.compute(analysis.sentences, analysis.words),
        "punctuation": punctuation.compute(analysis.raw_text, len(analysis.words)),
        "burstiness": burstiness.compute(analysis.sentences),
    }

    qualitative = {"heuristics": heuristics.compute(analysis.sentences, analysis.words)}
    if llm_result is not None:
        qualitative["llm"] = llm_result

    return {
        "source": source_name,
        "sentence_count": len(analysis.sentences),
        "quantitative": quantitative,
        "qualitative": qualitative,
    }
