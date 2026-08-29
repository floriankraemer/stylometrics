def _kv_lines(d: dict) -> str:
    return "\n".join(f"- **{k}**: {v}" for k, v in d.items())


def render(profile: dict) -> str:
    q = profile["quantitative"]
    h = profile["qualitative"]["heuristics"]
    llm = profile["qualitative"].get("llm")

    fw_lines = "\n".join(f"- {fw['word']}: {fw['per_1000']} per 1000 tokens" for fw in q["function_words"])
    anaphora_lines = "\n".join(f"- \"{a['opener']}\" ({a['count']}x)" for a in h["anaphora_patterns"]) or "- none detected"
    pronoun_lines = "\n".join(f"- {k}: {v}" for k, v in h["pronoun_distribution"].items())

    parts = [
        f"# Style Profile: {profile['source']}",
        "",
        f"Sentences: {profile['sentence_count']}, Tokens: {q['lexical']['token_count']}",
        "",
        "## Lexical Diversity",
        _kv_lines(q["lexical"]),
        "",
        "## Function Word Frequency (per 1000 tokens)",
        fw_lines,
        "",
        "## Syntax",
        _kv_lines(q["syntax"]),
        "",
        "## Punctuation Profile (per 1000 words)",
        _kv_lines(q["punctuation"]),
        "",
        "## Burstiness (Sentence-Length Rhythm)",
        _kv_lines(q["burstiness"]),
        "",
        "## Perspective & Stance (heuristic)",
        f"- rhetorical_question_rate_per_100_sentences: {h['rhetorical_question_rate_per_100_sentences']}",
        f"- hedging_rate_per_1000_words: {h['hedging_rate_per_1000_words']}",
        f"- assertiveness_rate_per_1000_words: {h['assertiveness_rate_per_1000_words']}",
        f"- rule_of_three_occurrences: {h['rule_of_three_occurrences']}",
        "",
        "### Pronoun distribution",
        pronoun_lines,
        "",
        "### Anaphora (repeated sentence openers)",
        anaphora_lines,
    ]

    if llm:
        parts += ["", "## Rhetoric (LLM-assisted)"]
        if "raw_response" in llm:
            parts.append(llm["raw_response"])
        else:
            parts += [
                f"**Tone & Register:** {llm['tone_and_register']}",
                "",
                f"**Cadence & Rhythm:** {llm['cadence_and_rhythm']}",
                "",
                f"**Persuasion Style:** {llm['persuasion_style']}",
                "",
                "**Rhetorical Devices:**",
                *[f"- {d['device']} — \"{d['example']}\"" for d in llm["rhetorical_devices"]],
            ]

    return "\n".join(parts) + "\n"


def write(profile: dict, out_path):
    out_path.write_text(render(profile), encoding="utf-8")
