from stylometry.metrics import burstiness, function_words, lexical, punctuation, syntax


def test_lexical(analysis):
    r = lexical.compute(analysis.words)
    assert r["token_count"] == len(analysis.words)
    assert 0 < r["ttr"] <= 1
    assert lexical.compute([])["token_count"] == 0


def test_lexical_all_hapax():
    class W:
        def __init__(self, t):
            self.text = t
    assert lexical.compute([W("a"), W("b")])["honores_r"] == 0.0


def test_function_words(analysis):
    r = function_words.compute(analysis.words)
    assert r and {"word", "per_1000"} <= r[0].keys()
    assert function_words.compute([]) == []


def test_syntax(analysis):
    r = syntax.compute(analysis.sentences, analysis.words)
    assert r["avg_parse_tree_depth"] > 0
    assert syntax.compute([], [])["noun_ratio"] == 0.0


def test_punctuation():
    r = punctuation.compute("a, b; c: d! e? (f) ... -- ", 10)
    assert r["comma"] == 100.0 and r["semicolon"] == 100.0 and r["ellipsis"] == 100.0
    assert punctuation.compute("x", 0)["comma"] == 0.0


def test_burstiness(analysis):
    r = burstiness.compute(analysis.sentences)
    assert r["min_sentence_length"] <= r["max_sentence_length"]
    assert -1 <= r["burstiness"] <= 1
    assert burstiness.compute([])["burstiness"] == 0.0
