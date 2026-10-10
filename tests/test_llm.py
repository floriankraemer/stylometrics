import sys
import types

import pytest

from stylometry.qualitative import llm


def test_valid_json(monkeypatch):
    monkeypatch.setattr(llm, "_call_anthropic", lambda p: '{"a": 1}')
    assert llm.compute("text", {"m": 1}, "anthropic") == {"a": 1}


def test_invalid_json_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "_call_openai", lambda p: "nope")
    assert llm.compute("text", {}, "openai") == {"raw_response": "nope"}


def test_prompt_truncates_sample(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "_call_anthropic", lambda p: seen.append(p) or "{}")
    llm.compute("x" * 9000, {}, "anthropic")
    assert "x" * 8000 in seen[0] and "x" * 8001 not in seen[0]


def test_unknown_provider():
    with pytest.raises(ValueError):
        llm.compute("t", {}, "nope")


def test_call_anthropic(monkeypatch):
    class Client:
        def __init__(self, api_key):
            assert api_key == "k"
            self.messages = types.SimpleNamespace(create=lambda **kw: types.SimpleNamespace(
                content=[types.SimpleNamespace(text="hi")]))
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=Client))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert llm._call_anthropic("p") == "hi"


def test_call_openai(monkeypatch):
    class Client:
        def __init__(self, api_key):
            assert api_key == "k"
            msg = types.SimpleNamespace(content="hey")
            create = lambda **kw: types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=Client))
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert llm._call_openai("p") == "hey"
