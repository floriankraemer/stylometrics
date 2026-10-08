"""Offline, rule-based approximation of tone/rhetoric/stance. Always runs."""
import re
from collections import Counter

HEDGE_WORDS = {"might", "perhaps", "maybe", "possibly", "could", "seem", "seems", "somewhat", "arguably"}
ASSERTIVE_WORDS = {"must", "always", "never", "certainly", "clearly", "obviously", "definitely"}

# Personal pronouns and possessives only; relative/demonstrative/indefinite pronouns
# carry no grammatical person. "it" is grammatically third person but refers to things,
# so it gets its own bucket. Matched on lowercased text because spaCy often mis-tags
# archaic forms (e.g. "Thou" as PROPN, "Ye" as NOUN).
PERSONAL_PRONOUNS = {
    "first_person": {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"},
    "second_person": {"you", "your", "yours", "yourself", "yourselves",
                      "thou", "thee", "thy", "thine", "thyself", "ye"},
    "third_person": {"he", "him", "his", "himself", "she", "her", "hers", "herself",
                     "they", "them", "their", "theirs", "themselves"},
    "impersonal": {"it", "its", "itself"},
}

OPEN_QUOTES = {"“", "«"}
CLOSE_QUOTES = {"”", "»"}

# Third-person pronouns occur in any text about anything, so narrative voice is decided by
# first/second-person pronouns in the narration: first or second person once either reaches
# this rate, third person otherwise.
# ponytail: fixed threshold calibrated on the examples (third-person "Masque of the Red Death"
# 2.5, first-person Poe tales 12-80, Meditations second person 30); revisit if a corpus lands near 10.
VOICE_THRESHOLD_PER_1000 = 10


def _narration_words(doc) -> list:
    """Lowercased words outside quotation marks, so characters' dialogue doesn't set the voice."""
    in_quote, out = False, []
    for t in doc:
        if t.is_space and t.text.count("\n") >= 2:
            in_quote = False  # multi-paragraph quotes leave the closing mark off each paragraph
        elif t.text in OPEN_QUOTES:
            in_quote = True
        elif t.text in CLOSE_QUOTES:
            in_quote = False
        elif t.text == '"':
            in_quote = not in_quote
        elif t.is_alpha and not in_quote:
            out.append(t.text.lower())
    return out


def _narrative_voice(narration: list) -> str:
    n = len(narration) or 1
    rates = {person: sum(w in PERSONAL_PRONOUNS[person] for w in narration) / n * 1000
             for person in ("first_person", "second_person")}
    person = max(rates, key=rates.get)
    return person if rates[person] >= VOICE_THRESHOLD_PER_1000 else "third_person"


def compute(sentences: list, words: list) -> dict:
    n_sentences = len(sentences) or 1
    n_words = len(words) or 1

    rhetorical_questions = sum(1 for s in sentences if s.text.strip().endswith("?"))

    # first word of each sentence, skipping leading quotes/dashes
    openers = [next((t.lemma_.lower() for t in s if t.is_alpha), None) for s in sentences]
    openers = [o for o in openers if o]
    opener_counts = Counter(openers)
    anaphora = [{"opener": w, "count": c} for w, c in opener_counts.most_common(5) if c > 1]

    lowered = [t.text.lower() for t in words]
    hedge_count = sum(1 for w in lowered if w in HEDGE_WORDS)
    assertive_count = sum(1 for w in lowered if w in ASSERTIVE_WORDS)

    pronoun_counts = Counter()
    for w in lowered:
        for person, forms in PERSONAL_PRONOUNS.items():
            if w in forms:
                pronoun_counts[person] += 1

    narration = _narration_words(words[0].doc) if words else []

    rule_of_three = len(re.findall(r"\b(\w+),\s*\w+,\s*(?:and|or)\s+\w+\b", " ".join(s.text for s in sentences)))

    return {
        "rhetorical_question_rate_per_100_sentences": round(rhetorical_questions / n_sentences * 100, 2),
        "anaphora_patterns": anaphora,
        "hedging_rate_per_1000_words": round(hedge_count / n_words * 1000, 2),
        "assertiveness_rate_per_1000_words": round(assertive_count / n_words * 1000, 2),
        "pronoun_distribution": dict(pronoun_counts),
        "narrative_voice": _narrative_voice(narration),
        "rule_of_three_occurrences": rule_of_three,
    }
