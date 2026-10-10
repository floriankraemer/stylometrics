import json
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


def call(client, args, **kw):
    r = rpc(client, "tools/call", {"name": "analyze", "arguments": args}, **kw)
    assert r.status_code == 200, r.text
    return r.json()["result"]


def test_tools_list(client):
    tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert [t["name"] for t in tools] == ["analyze"]
    assert {"text", "url", "llm", "include"} <= tools[0]["inputSchema"]["properties"].keys()


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


def test_stdio_server():
    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "stylometry.cli", "--mcp"],
                                       env={"PYTHONPATH": SRC, "PATH": ""})
        async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
            await session.initialize()
            assert [t.name for t in (await session.list_tools()).tools] == ["analyze"]
            res = await session.call_tool("analyze", {"text": TEXT})
            return res

    res = anyio.run(go)
    assert not res.isError and res.structuredContent["sentence_count"] == 2
