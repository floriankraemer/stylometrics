from stylometry.compare import compare


def profile(words, source="s", ttr=0.5):
    return {"source": source, "quantitative": {
        "lexical": {"ttr": ttr}, "burstiness": {"burstiness": 0.1}, "syntax": {"depth": 3.0},
        "punctuation": {"commas_per_1000": 40},
        "function_words": [{"word": w, "per_1000": n} for w, n in words.items()]}}


def test_identical_profiles():
    p = profile({"the": 50, "of": 20})
    r = compare(p, p)
    assert r["function_word_similarity"] == 1.0
    assert all(m["delta"] == 0 for m in r["metrics"].values())
    assert r["metrics"]["lexical.ttr"] == {"a": 0.5, "b": 0.5, "delta": 0}


def test_disjoint_function_words_and_delta():
    r = compare(profile({"the": 5}, "x", ttr=0.4), profile({"of": 5}, "y", ttr=0.7))
    assert r["function_word_similarity"] == 0.0
    assert r["sources"] == ["x", "y"]
    assert r["metrics"]["lexical.ttr"]["delta"] == 0.3


def test_empty_function_words():
    assert compare(profile({}), profile({}))["function_word_similarity"] == 0.0
