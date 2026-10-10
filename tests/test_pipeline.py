import pytest

from stylometry import pipeline
from stylometry.qualitative import llm


def test_run_without_llm():
    p = pipeline.run("I walked home. It was late.", "s.txt")
    assert p["source"] == "s.txt" and "llm" not in p["qualitative"]


def test_run_with_llm(monkeypatch):
    monkeypatch.setattr(llm, "compute", lambda text, q, provider: {"provider": provider, "has_q": "lexical" in q})
    p = pipeline.run("I walked home.", "s", llm=True, provider="openai")
    assert p["qualitative"]["llm"] == {"provider": "openai", "has_q": True}


def test_llm_failure_wrapped(monkeypatch):
    def boom(*a):
        raise RuntimeError("quota")
    monkeypatch.setattr(llm, "compute", boom)
    with pytest.raises(pipeline.LLMError, match="quota"):
        pipeline.run("I walked home.", "s", llm=True)
