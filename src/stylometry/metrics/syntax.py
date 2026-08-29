"""POS distribution and dependency-parse-tree depth."""
from collections import Counter


def _tree_depth(token) -> int:
    depth = 0
    node = token
    while node.head.i != node.i:
        depth += 1
        node = node.head
    return depth


def compute(sentences: list, words: list) -> dict:
    n = len(words)
    pos_counts = Counter(t.pos_ for t in words)

    def ratio(tag: str) -> float:
        return round(pos_counts.get(tag, 0) / n, 4) if n else 0.0

    depths = [max((_tree_depth(t) for t in sent), default=0) for sent in sentences]
    avg_depth = round(sum(depths) / len(depths), 2) if depths else 0.0

    noun = pos_counts.get("NOUN", 0) + pos_counts.get("PROPN", 0)
    verb = pos_counts.get("VERB", 0) + pos_counts.get("AUX", 0)
    noun_verb_ratio = round(noun / verb, 2) if verb else 0.0

    return {
        "noun_ratio": ratio("NOUN"),
        "verb_ratio": ratio("VERB"),
        "adj_ratio": ratio("ADJ"),
        "adv_ratio": ratio("ADV"),
        "noun_to_verb_ratio": noun_verb_ratio,
        "avg_parse_tree_depth": avg_depth,
    }
