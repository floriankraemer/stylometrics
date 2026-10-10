from stylometry.preprocess import _chunk, analyze


def test_chunk_splits_on_paragraphs():
    text = "aaaa\n\nbbbb\n\ncccc"
    assert _chunk(text, target_size=6) == ["aaaa", "bbbb", "cccc"]


def test_chunk_single():
    assert _chunk("one paragraph") == ["one paragraph"]


def test_analyze_multi_chunk(monkeypatch):
    import stylometry.preprocess as p
    monkeypatch.setattr(p, "_chunk", lambda t: t.split("\n\n"))
    a = analyze("First one here.\n\nSecond one here.")
    assert len(a.sentences) == 2
    assert [w.text for w in a.words][:2] == ["First", "one"]
