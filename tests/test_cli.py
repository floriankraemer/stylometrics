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


def test_no_arguments_prints_help(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "stylometry --serve" in err and "analyze a source" in err and "examples:" in err


def test_source_required_without_serve():
    with pytest.raises(SystemExit) as e:
        cli.main(["--llm"])
    assert e.value.code == 2


@pytest.mark.parametrize("env,host,level,msg", [
    ({"STYLOMETRY_API_KEY": "k"}, "0.0.0.0", "INFO", "Auth: bearer token required"),
    ({}, "127.0.0.1", "INFO", "Auth: off (set STYLOMETRY_API_KEY"),
    ({}, "localhost", "INFO", "Auth: off (set STYLOMETRY_API_KEY"),
    ({}, "0.0.0.0", "WARNING", "Auth: off on 0.0.0.0"),
])
def test_serve_banner_auth(monkeypatch, caplog, env, host, level, msg):
    import uvicorn
    for k in ("STYLOMETRY_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: None)
    with caplog.at_level("INFO", logger="stylometry"):
        cli.main(["--serve", "--host", host])
    assert any(r.levelname == level and msg in r.getMessage() for r in caplog.records)
    assert "MCP at /mcp" in caplog.text and "LLM pass: unavailable" in caplog.text


def test_serve_banner_llm_providers(monkeypatch, caplog):
    import uvicorn
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: None)
    with caplog.at_level("INFO", logger="stylometry"):
        cli.main(["--serve"])
    assert "LLM pass: openai" in caplog.text


def test_keyboard_interrupt_exits_130(monkeypatch, caplog):
    def interrupted(*a, **kw):
        raise KeyboardInterrupt
    monkeypatch.setattr(cli, "load_text", interrupted)
    with pytest.raises(SystemExit) as e:
        cli.main(["some.txt"])
    assert e.value.code == 130 and "Interrupted." in caplog.text


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
