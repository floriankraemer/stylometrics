import pytest

from stylometry.report import clone_prompt, html_report, profile_md
from stylometry.report.profile import build

LLM = {"tone_and_register": "calm", "cadence_and_rhythm": "slow", "persuasion_style": "plain",
       "rhetorical_devices": [{"device": "anaphora", "example": "I came"}]}


@pytest.fixture(params=[None, LLM, {"raw_response": "not json"}], ids=["none", "llm", "raw"])
def profile(request, analysis):
    return build(analysis, "src.txt", llm_result=request.param)


def test_build_shape(analysis):
    p = build(analysis, "src.txt")
    assert p["source"] == "src.txt" and "llm" not in p["qualitative"]
    assert p["sentence_count"] == len(analysis.sentences)


@pytest.mark.parametrize("mod,ext", [(html_report, "html"), (profile_md, "md"), (clone_prompt, "md")])
def test_writers(profile, tmp_path, mod, ext):
    out = tmp_path / f"o.{ext}"
    mod.write(profile, out)
    text = out.read_text(encoding="utf-8")
    assert "src.txt" in text
    llm = profile["qualitative"].get("llm")
    if llm and "tone_and_register" in llm:
        assert "calm" in text
    if llm and "raw_response" in llm and mod is not clone_prompt:
        assert "not json" in text
