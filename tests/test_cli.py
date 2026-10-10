import pytest

from stylometry import __version__, cli
from stylometry.qualitative import llm

TEXT = "I walked home. It was late, and the night was cold.\n\nWhy did she leave? She must never return."


def test_writes_three_files(tmp_path):
    src = tmp_path / "essay.txt"
    src.write_text(TEXT)
    out = tmp_path / "out"
    cli.main([str(src), "--output", str(out)])
    assert sorted(p.name for p in out.iterdir()) == [
        "essay_clone_prompt.md", "essay_profile.md", "essay_report.html"]


def test_empty_source_exits_1(tmp_path):
    src = tmp_path / "empty.txt"
    src.write_text("  \n")
    with pytest.raises(SystemExit) as e:
        cli.main([str(src), "--output", str(tmp_path / "o")])
    assert e.value.code == 1


def test_llm_flag(tmp_path, monkeypatch):
    src = tmp_path / "essay.txt"
    src.write_text(TEXT)
    monkeypatch.setattr(llm, "compute", lambda *a: {"raw_response": "LLMOUT"})
    cli.main([str(src), "--output", str(tmp_path / "o"), "--llm", "--provider", "openai"])
    assert "LLMOUT" in (tmp_path / "o" / "essay_profile.md").read_text()


def test_bad_provider_exits_2(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.main(["x.txt", "--provider", "nope"])
    assert e.value.code == 2


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_output_env_default(tmp_path, monkeypatch):
    src = tmp_path / "essay.txt"
    src.write_text(TEXT)
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "envout"))
    cli.main([str(src)])
    assert (tmp_path / "envout" / "essay_profile.md").exists()


def test_source_required_without_serve():
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2


def test_serve_passes_host_and_port(monkeypatch):
    import uvicorn
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: calls.append(kw))
    cli.main(["--serve", "--host", "0.0.0.0", "--port", "8123"])
    assert calls == [{"host": "0.0.0.0", "port": 8123}]


def test_serve_port_from_env(monkeypatch):
    import uvicorn
    calls = []
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: calls.append(kw))
    cli.main(["--serve"])
    assert calls == [{"host": "127.0.0.1", "port": 9001}]


def test_mcp_flag_runs_stdio(monkeypatch):
    from stylometry.server import mcp_server
    calls = []
    monkeypatch.setattr(mcp_server, "run_stdio", lambda: calls.append(1))
    cli.main(["--mcp"])
    assert calls == [1]
