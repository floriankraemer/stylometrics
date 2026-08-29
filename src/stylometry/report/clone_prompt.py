def render(profile: dict) -> str:
    q = profile["quantitative"]
    h = profile["qualitative"]["heuristics"]
    llm = profile["qualitative"].get("llm")

    top_fw = ", ".join(f"\"{fw['word']}\"" for fw in q["function_words"][:10])
    pron = h["pronoun_distribution"]
    dominant_person = max(pron, key=pron.get) if pron else "unknown"

    lines = [
        f"# Style-Clone System Prompt — derived from: {profile['source']}",
        "",
        "You are a writer who replicates the measured style below with precision. "
        "Do not describe the style — write in it.",
        "",
        "## Sentence Mechanics",
        f"- Average sentence length: {q['burstiness']['mean_sentence_length']} words "
        f"(stdev {q['burstiness']['stdev_sentence_length']}, range "
        f"{q['burstiness']['min_sentence_length']}-{q['burstiness']['max_sentence_length']}).",
        f"- Burstiness coefficient: {q['burstiness']['burstiness']} "
        "(closer to +1 = highly variable/bursty rhythm, closer to -1 = uniform sentence lengths).",
        f"- Average dependency-parse depth: {q['syntax']['avg_parse_tree_depth']} "
        "(higher = more nested/subordinate clauses).",
        "",
        "## Vocabulary & Word Choice",
        f"- Type-token ratio: {q['lexical']['ttr']} ({'high' if q['lexical']['ttr'] > 0.5 else 'moderate-to-low'} lexical diversity).",
        f"- Yule's K: {q['lexical']['yules_k']} (lower = more diverse vocabulary).",
        f"- Noun-to-verb ratio: {q['syntax']['noun_to_verb_ratio']} "
        f"({'dense/nominal' if q['syntax']['noun_to_verb_ratio'] > 1.5 else 'action/verb-driven'} style).",
        f"- Signature function words, in order of frequency: {top_fw}.",
        "",
        "## Punctuation Habits",
        f"- Em-dashes: {q['punctuation']['em_dash']} per 1000 words.",
        f"- Semicolons: {q['punctuation']['semicolon']} per 1000 words.",
        f"- Parentheticals: {q['punctuation']['parentheses']} per 1000 words.",
        f"- Ellipses: {q['punctuation']['ellipsis']} per 1000 words.",
        f"- Exclamation marks: {q['punctuation']['exclamation']} per 1000 words.",
        "",
        "## Voice & Stance",
        f"- Dominant grammatical person: {dominant_person}.",
        f"- Hedging rate: {h['hedging_rate_per_1000_words']} per 1000 words "
        f"({'hedges frequently' if h['hedging_rate_per_1000_words'] > 3 else 'rarely hedges, prefers direct assertions'}).",
        f"- Assertiveness rate: {h['assertiveness_rate_per_1000_words']} per 1000 words.",
        f"- Rhetorical questions: {h['rhetorical_question_rate_per_100_sentences']} per 100 sentences.",
        f"- Rule-of-three constructions: {h['rule_of_three_occurrences']} occurrences observed.",
    ]

    if llm and "raw_response" not in llm:
        lines += [
            "",
            "## Rhetorical Style",
            f"- Tone & register: {llm['tone_and_register']}",
            f"- Cadence & rhythm: {llm['cadence_and_rhythm']}",
            f"- Persuasion style: {llm['persuasion_style']}",
            "- Characteristic devices: " + "; ".join(d["device"] for d in llm["rhetorical_devices"]) + ".",
        ]

    lines += [
        "",
        "## Instruction",
        "When writing, match every characteristic above: sentence rhythm and burstiness, "
        "vocabulary richness and function-word habits, punctuation density, noun/verb balance, "
        "and voice/stance. Prioritize matching the measured mechanics over generic 'good writing' instincts.",
    ]

    return "\n".join(lines) + "\n"


def write(profile: dict, out_path):
    out_path.write_text(render(profile), encoding="utf-8")
