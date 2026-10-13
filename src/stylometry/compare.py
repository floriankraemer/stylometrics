"""Side-by-side comparison of two style profiles."""
import math

SECTIONS = ("lexical", "burstiness", "syntax", "punctuation")


def _metrics(profile: dict) -> dict[str, float]:
    q = profile["quantitative"]
    return {f"{s}.{k}": v for s in SECTIONS for k, v in q[s].items() if isinstance(v, (int, float))}


def _cosine(u: dict[str, float], v: dict[str, float]) -> float:
    dot = sum(u[w] * v[w] for w in u.keys() & v.keys())
    norm = math.sqrt(sum(x * x for x in u.values())) * math.sqrt(sum(x * x for x in v.values()))
    return round(dot / norm, 4) if norm else 0.0


def compare(a: dict, b: dict) -> dict:
    ma, mb = _metrics(a), _metrics(b)
    fw = [{fw["word"]: fw["per_1000"] for fw in p["quantitative"]["function_words"]} for p in (a, b)]
    return {
        "sources": [a["source"], b["source"]],
        "metrics": {k: {"a": ma[k], "b": mb[k], "delta": round(mb[k] - ma[k], 4)}
                    for k in sorted(ma.keys() & mb.keys())},
        "function_word_similarity": _cosine(*fw),
    }
