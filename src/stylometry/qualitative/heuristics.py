"""Offline, rule-based approximation of tone/rhetoric/stance. Always runs."""
import re
from collections import Counter

HEDGE_WORDS = {"might", "perhaps", "maybe", "possibly", "could", "seem", "seems", "somewhat", "arguably"}
ASSERTIVE_WORDS = {"must", "always", "never", "certainly", "clearly", "obviously", "definitely"}


def compute(sentences: list, words: list) -> dict:
    n_sentences = len(sentences) or 1
    n_words = len(words) or 1

    rhetorical_questions = sum(1 for s in sentences if s.text.strip().endswith("?"))

    openers = [s[0].lemma_.lower() for s in sentences if len(s) > 0]
    opener_counts = Counter(openers)
    anaphora = [{"opener": w, "count": c} for w, c in opener_counts.most_common(5) if c > 1]

    lowered = [t.text.lower() for t in words]
    hedge_count = sum(1 for w in lowered if w in HEDGE_WORDS)
    assertive_count = sum(1 for w in lowered if w in ASSERTIVE_WORDS)

    pronoun_counts = Counter()
    for t in words:
        if t.pos_ == "PRON":
            lemma = t.lemma_.lower()
            if lemma in ("i", "me", "my", "mine", "we", "us", "our"):
                pronoun_counts["first_person"] += 1
            elif lemma in ("you", "your", "yours"):
                pronoun_counts["second_person"] += 1
            else:
                pronoun_counts["third_person"] += 1

    rule_of_three = len(re.findall(r"\b(\w+),\s*\w+,\s*(?:and|or)\s+\w+\b", " ".join(s.text for s in sentences)))

    return {
        "rhetorical_question_rate_per_100_sentences": round(rhetorical_questions / n_sentences * 100, 2),
        "anaphora_patterns": anaphora,
        "hedging_rate_per_1000_words": round(hedge_count / n_words * 1000, 2),
        "assertiveness_rate_per_1000_words": round(assertive_count / n_words * 1000, 2),
        "pronoun_distribution": dict(pronoun_counts),
        "rule_of_three_occurrences": rule_of_three,
    }
