import json
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from stylometry.server import app as app_mod

TEXT = "I walked home. It was late, and the night was cold."
HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
SRC = str(Path(__file__).resolve().parent.parent / "src")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("STYLOMETRY_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ALLOW_URL"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def client():
    with TestClient(app_mod.create_app()) as c:  # the context manager runs the lifespan that starts /mcp
        yield c


def rpc(client, method, params=None, headers=None, id=1):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}},
                    headers={**HEADERS, **(headers or {})})
    return r


def call(client, args, name="analyze", **kw):
    r = rpc(client, "tools/call", {"name": name, "arguments": args}, **kw)
    assert r.status_code == 200, r.text
    return r.json()["result"]


def test_tools_list(client):
    tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert [t["name"] for t in tools] == ["analyze", "compare"]
    assert {"text", "url", "llm", "include"} <= tools[0]["inputSchema"]["properties"].keys()
    assert {"a", "b"} <= tools[1]["inputSchema"]["properties"].keys()
    props = tools[0]["inputSchema"]["properties"]
    assert props["max_pages"]["minimum"] == 1 and props["provider"]["enum"] == ["anthropic", "openai"]


def test_compare(client):
    result = call(client, {"a": {"text": TEXT, "name": "x"}, "b": {"text": "Short. Very short. Tiny."}}, "compare")
    assert not result["isError"]
    out = result["structuredContent"]
    assert out["sources"] == ["x", "text"] and "lexical.ttr" in out["metrics"]
    assert 0 <= out["function_word_similarity"] <= 1


@pytest.mark.parametrize("args,msg", [({"a": {"text": TEXT}, "b": {}}, "exactly one"),
                                      ({"a": {"text": TEXT}, "b": {"text": " "}}, "No Text")])
def test_compare_errors(client, args, msg):
    result = call(client, args, "compare")
    assert result["isError"] and msg in result["content"][0]["text"]


def test_write_like_prompt(client):
    assert [p["name"] for p in rpc(client, "prompts/list").json()["result"]["prompts"]] == ["write_like"]
    r = rpc(client, "prompts/get", {"name": "write_like", "arguments": {"source": TEXT, "task": "Write a poem."}})
    msg = r.json()["result"]["messages"][0]
    assert msg["role"] == "user"
    assert msg["content"]["text"].startswith("# Style-Clone System Prompt")
    assert msg["content"]["text"].endswith("Write a poem.")


def test_write_like_default_task(client):
    r = rpc(client, "prompts/get", {"name": "write_like", "arguments": {"source": TEXT}})
    assert r.json()["result"]["messages"][0]["content"]["text"].endswith("Write a short passage in this style.")


@pytest.mark.parametrize("source", ["http://127.0.0.1/", "HTTP://127.0.0.1/"])
def test_write_like_url_blocked(client, source, caplog):
    r = rpc(client, "prompts/get", {"name": "write_like", "arguments": {"source": source}})
    assert r.json()["error"]["code"] == -32602 and "URL Not Allowed" in r.json()["error"]["message"]
    assert not [x for x in caplog.records if x.levelno >= logging.ERROR]


def test_analyze_text(client):
    result = call(client, {"text": TEXT, "name": "n"})
    assert not result["isError"]
    assert json.loads(result["content"][0]["text"])["sentence_count"] == 2
    assert result["structuredContent"]["source"] == "n"


def test_include(client):
    result = call(client, {"text": TEXT, "include": ["profile_md"]})
    assert result["structuredContent"]["rendered"]["profile_md"].startswith("# Style Profile")


@pytest.mark.parametrize("args,msg", [({}, "exactly one"), ({"text": " "}, "No Text"),
                                      ({"text": TEXT, "llm": True}, "LLM Not Configured"),
                                      ({"url": "http://127.0.0.1/"}, "URL Not Allowed"),
                                      ({"text": TEXT, "include": ["x"]}, "Invalid request")])
def test_tool_errors(client, args, msg, caplog):
    result = call(client, args)
    assert result["isError"] and msg in result["content"][0]["text"]
    assert not [x for x in caplog.records if x.levelno >= logging.ERROR]


def test_auth(client, monkeypatch):
    monkeypatch.setenv("STYLOMETRY_API_KEY", "s3cret")
    r = rpc(client, "tools/list")
    assert r.status_code == 401 and r.headers["content-type"] == "application/problem+json"
    assert r.headers["www-authenticate"] == "Bearer"
    assert rpc(client, "tools/list", headers={"authorization": "Bearer s3cret"}).status_code == 200


def assert_problem(r, status, slug):
    assert r.status_code == status and r.headers["content-type"] == "application/problem+json"
    assert r.json()["type"] == f"urn:stylometry:problem:{slug}" and r.json()["instance"] == "/mcp"


@pytest.mark.parametrize("method", ["GET", "DELETE", "PUT"])
def test_mcp_rejects_non_post(client, method):
    # GET used to open an SSE stream that never sends, hanging the client
    r = client.request(method, "/mcp", headers={"accept": "text/event-stream"})
    assert_problem(r, 405, "method-not-allowed") and r.headers["allow"] == "POST"


@pytest.mark.parametrize("accept", [None, "text/event-stream", "text/html"])
def test_mcp_not_acceptable(client, accept):
    r = rpc(client, "tools/list", headers={"accept": accept} if accept else {"accept": ""})
    assert_problem(r, 406, "not-acceptable")


@pytest.mark.parametrize("content_type", ["text/plain", ""])
def test_mcp_unsupported_media_type(client, content_type):
    r = rpc(client, "tools/list", headers={"content-type": content_type})
    assert_problem(r, 415, "unsupported-media-type")


def test_mcp_accepts_what_the_sdk_accepts(client):
    assert rpc(client, "tools/list", headers={"accept": "application/*"}).status_code == 200
    assert rpc(client, "tools/list", headers={"content-type": "application/json; charset=utf-8"}).status_code == 200


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_mcp_auth_comes_first(client, monkeypatch, method):
    monkeypatch.setenv("STYLOMETRY_API_KEY", "s3cret")
    r = client.request(method, "/mcp", headers={"accept": "text/html", "content-type": "text/plain"})
    assert_problem(r, 401, "unauthorized")


def test_lifespan_restarts():
    app = app_mod.create_app()  # Mangum runs the lifespan once per Lambda invocation
    for _ in range(2):
        with TestClient(app) as c:
            assert rpc(c, "tools/list").status_code == 200


def stdio_session(fn):
    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "stylometry.cli", "--mcp"],
                                       env={**os.environ, "PYTHONPATH": SRC})
        async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            return await fn(session)

    return anyio.run(go)


def test_stdio_server(tmp_path):
    good = tmp_path / "a.txt"
    good.write_text(TEXT)
    odd = tmp_path / "a.xyz"
    odd.write_text(TEXT)

    async def run(session):
        names = [t.name for t in (await session.list_tools()).tools]
        return (names, await session.call_tool("analyze", {"text": TEXT}),
                await session.call_tool("analyze_file", {"path": str(good)}),
                await session.call_tool("analyze_file", {"path": str(tmp_path / "nope.txt")}),
                await session.call_tool("analyze_file", {"path": str(odd)}))

    names, res, file_res, missing, unsupported = stdio_session(run)
    assert names == ["analyze", "compare", "analyze_file"]
    assert not res.is_error and res.structured_content["sentence_count"] == 2
    assert not file_res.is_error and file_res.structured_content["source"] == "a.txt"
    assert missing.is_error and "File Not Found" in missing.content[0].text
    assert unsupported.is_error and "Unsupported Input Type" in unsupported.content[0].text


def test_stdio_leaves_stdout_open():
    # the SDK's stdio transport closes the stdout it wraps; a PyInstaller binary flushes sys.stdout after main()
    code = "import sys; from stylometry.server.mcp_server import run_stdio; run_stdio(); sys.stdout.flush()"
    r = subprocess.run([sys.executable, "-c", code], input=b"", capture_output=True,
                       env={**os.environ, "PYTHONPATH": SRC})
    assert r.returncode == 0, r.stderr.decode()
    assert b"Traceback" not in r.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT cannot be sent to a child process on Windows")
def test_stdio_ctrl_c_exits_at_once():
    # stdin stays open, as in a terminal: the SDK's reader thread is blocked in read() when Ctrl+C arrives
    p = subprocess.Popen([sys.executable, "-m", "stylometry.cli", "--mcp"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "PYTHONPATH": SRC})
    try:
        banner = p.stderr.readline().decode()
        p.send_signal(signal.SIGINT)
        assert p.wait(timeout=10) == 130
    finally:
        p.kill()
        p.stdin.close()
    err = p.stderr.read().decode()
    p.stderr.close()
    p.stdout.close()
    assert "MCP server on stdio. Tools: analyze, compare, analyze_file. Prompts: write_like." in banner
    assert "Stopped." in err and "Traceback" not in err
