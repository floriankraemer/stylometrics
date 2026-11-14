import pytest
from fastapi.testclient import TestClient

from stylometry import language, pipeline
from stylometry.preprocess import analyze
from stylometry.qualitative import heuristics
from stylometry.report import clone_prompt
from stylometry.server import app as app_mod

DE = ("Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett "
      "zu einem ungeheueren Ungeziefer verwandelt. Er lag auf seinem panzerartig harten Rücken.")
EN = "When Gregor Samsa woke one morning from troubled dreams, he found himself changed into a monstrous vermin."


def test_detect():
    assert language.detect(DE) == "de"
    assert language.detect(EN) == "en"
    assert language.detect("") == "en"
    assert language.resolve("de", EN) == "de" and language.resolve("auto", DE) == "de"


def test_german_pipeline_and_clone_prompt():
    p = pipeline.run(DE, "d.txt")
    assert p["language"] == "de" and p["sentence_count"] == 2
    assert p["quantitative"]["lexical"]["token_count"] > 20
    assert "Write in German." in clone_prompt.render(p)
    assert "Write in" not in clone_prompt.render(pipeline.run(EN, "e.txt"))


def test_german_dialogue_does_not_set_voice():
    text = ("Der Förster ging in den Wald. „Ich finde dich“, sagte er, „und du wirst mich kennen.“\n\n"
            "Das Haus stand still hinter ihm, und die Wächter beobachteten die Straße.")
    a = analyze(text, "de")
    assert heuristics.compute(a.sentences, a.words, "de")["narrative_voice"] == "third_person"


def test_german_first_person_and_dash():
    a = analyze("Ich ging nach Hause. Ich war müde, und ich legte mich nieder – es war spät.", "de")
    h = heuristics.compute(a.sentences, a.words, "de")
    assert h["narrative_voice"] == "first_person"
    assert pipeline.run(a.raw_text, "s", lang="de")["quantitative"]["punctuation"]["em_dash"] > 0


def test_missing_model(monkeypatch):
    import spacy
    from stylometry import preprocess

    monkeypatch.setattr(preprocess, "_models", {})
    monkeypatch.setattr(spacy, "load", lambda m: (_ for _ in ()).throw(OSError("nope")))
    with pytest.raises(OSError, match="spacy download de_core_news_sm"):
        preprocess.get_nlp("de")


def test_api_lang():
    client = TestClient(app_mod.create_app())
    assert client.post("/analyze", json={"text": DE}).json()["language"] == "de"
    assert client.post("/analyze", json={"text": DE, "lang": "en"}).json()["language"] == "en"
    assert client.post("/analyze", json={"text": DE, "lang": "fr"}).status_code == 422
