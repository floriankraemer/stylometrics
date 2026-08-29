"""Lexical diversity: TTR, Yule's K, Honore's R."""
import math
from collections import Counter


def compute(words: list) -> dict:
    tokens = [t.text.lower() for t in words]
    n = len(tokens)
    if n == 0:
        return {"token_count": 0, "type_count": 0, "ttr": 0.0, "yules_k": 0.0, "honores_r": 0.0}

    freqs = Counter(tokens)
    v = len(freqs)  # vocabulary size (types)
    v1 = sum(1 for c in freqs.values() if c == 1)  # hapax legomena

    ttr = v / n

    freq_of_freq = Counter(freqs.values())
    yules_k = 1e4 * (sum(m * m * count for m, count in freq_of_freq.items()) - n) / (n * n)

    if v1 == v:  # every word occurs exactly once, log term below explodes to 0
        honores_r = 0.0
    else:
        honores_r = 100 * math.log(n) / (1 - (v1 / v))

    return {
        "token_count": n,
        "type_count": v,
        "ttr": round(ttr, 4),
        "yules_k": round(yules_k, 2),
        "honores_r": round(honores_r, 2),
    }
