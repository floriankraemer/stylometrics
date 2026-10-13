import json
import os
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
def test_write_like_url_blocked(client, source):
    r = rpc(client, "prompts/get", {"name": "write_like", "arguments": {"source": source}})
    assert "URL Not Allowed" in r.text


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
def test_tool_errors(client, args, msg):
    result = call(client, args)
    assert result["isError"] and msg in result["content"][0]["text"]


def test_auth(client, monkeypatch):
    monkeypatch.setenv("STYLOMETRY_API_KEY", "s3cret")
    r = rpc(client, "tools/list")
    assert r.status_code == 401 and r.headers["content-type"] == "application/problem+json"
    assert r.headers["www-authenticate"] == "Bearer"
    assert rpc(client, "tools/list", headers={"authorization": "Bearer s3cret"}).status_code == 200


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
    assert not res.isError and res.structuredContent["sentence_count"] == 2
    assert not file_res.isError and file_res.structuredContent["source"] == "a.txt"
    assert missing.isError and "File Not Found" in missing.content[0].text
    assert unsupported.isError and "Unsupported Input Type" in unsupported.content[0].text


def test_stdio_leaves_stdout_open():
    # the SDK's stdio transport closes the stdout it wraps; a PyInstaller binary flushes sys.stdout after main()
    code = "import sys; from stylometry.server.mcp_server import run_stdio; run_stdio(); sys.stdout.flush()"
    r = subprocess.run([sys.executable, "-c", code], input=b"", capture_output=True,
                       env={**os.environ, "PYTHONPATH": SRC})
    assert r.returncode == 0, r.stderr.decode()
