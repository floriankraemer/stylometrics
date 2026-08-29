"""Sentence-length distribution and burstiness coefficient."""
import numpy as np


def compute(sentences: list) -> dict:
    lengths = [len([t for t in sent if t.is_alpha]) for sent in sentences]
    lengths = [l for l in lengths if l > 0]
    if not lengths:
        return {"mean_sentence_length": 0.0, "stdev_sentence_length": 0.0,
                "min_sentence_length": 0, "max_sentence_length": 0, "burstiness": 0.0}

    arr = np.array(lengths, dtype=float)
    mean = arr.mean()
    std = arr.std()
    burstiness = (std - mean) / (std + mean) if (std + mean) else 0.0

    return {
        "mean_sentence_length": round(float(mean), 2),
        "stdev_sentence_length": round(float(std), 2),
        "min_sentence_length": int(arr.min()),
        "max_sentence_length": int(arr.max()),
        "burstiness": round(float(burstiness), 4),
    }
