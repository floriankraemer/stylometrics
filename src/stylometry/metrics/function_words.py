"""Function-word frequency profile, per 1000 tokens."""
from collections import Counter


def compute(words: list, top_n: int = 30) -> list[dict]:
    n = len(words)
    if n == 0:
        return []

    function_tokens = [t.text.lower() for t in words if t.is_stop]
    counts = Counter(function_tokens)
    return [
        {"word": word, "per_1000": round(count / n * 1000, 2)}
        for word, count in counts.most_common(top_n)
    ]
