import json
import socket
import types

import pytest
import requests
from fastapi.testclient import TestClient

from stylometry import __version__, pipeline
from stylometry.server import app as app_mod
from stylometry.server import ssrf

TEXT = "I walked home. It was late, and the night was cold."


@pytest.fixture
def client():
    return TestClient(app_mod.create_app(), raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("STYLOMETRY_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ALLOW_URL", "MAX_BODY_BYTES",
              "MAX_PAGES_CAP"):
        monkeypatch.delenv(k, raising=False)


def assert_problem(r, status, slug):
    assert r.status_code == status
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["status"] == status and body["type"] == f"urn:stylometry:problem:{slug}"
    assert body["title"] and body["instance"].startswith("/")
    return body


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok", "version": __version__}


def test_analyze_text(client):
    r = client.post("/analyze", json={"text": TEXT, "name": "n.txt"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "n.txt" and body["sentence_count"] == 2 and "rendered" not in body


def test_include_rendered(client):
    r = client.post("/analyze?include=profile_md&include=clone_prompt", json={"text": TEXT})
    assert set(r.json()["rendered"]) == {"profile_md", "clone_prompt"}
    assert r.json()["rendered"]["profile_md"].startswith("# Style Profile")


def test_unknown_include(client):
    assert_problem(client.post("/analyze?include=nope", json={"text": TEXT}), 422, "validation-error")


@pytest.mark.parametrize("payload", [{}, {"text": "a", "url": "http://x.test"}, {"text": "a", "provider": "bad"},
                                     {"text": 5}])
def test_validation_errors(client, payload):
    body = assert_problem(client.post("/analyze", json=payload), 422, "validation-error")
    assert body["errors"]


def test_invalid_json(client):
    r = client.post("/analyze", content=b"{nope", headers={"content-type": "application/json"})
    assert_problem(r, 422, "validation-error")


def test_empty_text(client):
    assert_problem(client.post("/analyze", json={"text": "  \n"}), 422, "empty-text")


def test_404_and_405_are_problems(client):
    assert_problem(client.get("/nope"), 404, "not-found")
    assert_problem(client.get("/analyze"), 405, "method-not-allowed")


def test_unhandled_error_does_not_leak(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret detail")
    monkeypatch.setattr(pipeline, "run", boom)
    r = client.post("/analyze", json={"text": TEXT})
    body = assert_problem(r, 500, "internal-error")
    assert "secret" not in json.dumps(body)


def test_file_txt(client):
    r = client.post("/analyze/file", files={"file": ("../../etc/essay.txt", TEXT.encode())})
    assert r.status_code == 200 and r.json()["source"] == "essay.txt"


def test_file_name_override_and_include(client):
    r = client.post("/analyze/file?include=profile_md", files={"file": ("a.md", TEXT.encode())},
                    data={"name": "mine"})
    assert r.json()["source"] == "mine" and "rendered" in r.json()


def test_file_docx(client, tmp_path):
    import docx
    d = docx.Document()
    d.add_paragraph(TEXT)
    d.save(tmp_path / "a.docx")
    r = client.post("/analyze/file", files={"file": ("a.docx", (tmp_path / "a.docx").read_bytes())})
    assert r.status_code == 200 and r.json()["sentence_count"] == 2


def test_file_unsupported_type_does_not_leak_path(client):
    body = assert_problem(client.post("/analyze/file", files={"file": ("a.xyz", b"x")}), 415,
                          "unsupported-media-type")
    assert "/tmp" not in json.dumps(body)


def test_file_unreadable(client):
    assert_problem(client.post("/analyze/file", files={"file": ("a.pdf", b"not a pdf")}), 422, "unreadable-input")


def test_file_missing(client):
    assert_problem(client.post("/analyze/file", data={"name": "x"}), 422, "validation-error")


def test_body_limit_content_length(client, monkeypatch):
    monkeypatch.setenv("MAX_BODY_BYTES", "100")
    assert_problem(client.post("/analyze", json={"text": "x" * 500}), 413, "payload-too-large")


def test_body_limit_without_content_length(client, monkeypatch):
    monkeypatch.setenv("MAX_BODY_BYTES", "100")
    r = client.post("/analyze", content=iter([b'{"text": "', b"x" * 500, b'"}']),
                    headers={"content-type": "application/json"})
    assert_problem(r, 413, "payload-too-large")


def test_auth(client, monkeypatch):
    monkeypatch.setenv("STYLOMETRY_API_KEY", "s3cret")
    r = client.post("/analyze", json={"text": TEXT})
    assert_problem(r, 401, "unauthorized")
    assert r.headers["www-authenticate"] == "Bearer"
    assert_problem(client.post("/analyze", json={"text": TEXT}, headers={"Authorization": "Bearer nope"}), 401,
                   "unauthorized")
    assert_problem(client.post("/analyze/file", files={"file": ("a.txt", b"x")}), 401, "unauthorized")
    ok = client.post("/analyze", json={"text": TEXT}, headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200
    assert client.get("/healthz").status_code == 200


def test_llm_not_configured(client):
    assert_problem(client.post("/analyze", json={"text": TEXT, "llm": True}), 503, "llm-not-configured")
    r = client.post("/analyze/file", files={"file": ("a.txt", TEXT.encode())}, data={"llm": "true",
                                                                                      "provider": "openai"})
    assert_problem(r, 503, "llm-not-configured")


def test_llm_ok_and_upstream_error(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    from stylometry.qualitative import llm
    monkeypatch.setattr(llm, "compute", lambda *a: {"tone_and_register": "calm"})
    r = client.post("/analyze", json={"text": TEXT, "llm": True})
    assert r.json()["qualitative"]["llm"] == {"tone_and_register": "calm"}

    def boom(*a):
        raise RuntimeError("rate limited")
    monkeypatch.setattr(llm, "compute", boom)
    assert_problem(client.post("/analyze", json={"text": TEXT, "llm": True}), 502, "llm-upstream-error")


def fake_web(monkeypatch, pages, public=True):
    monkeypatch.setattr(ssrf.socket, "getaddrinfo", lambda host, *a, **k: [
        (socket.AF_INET, 0, 0, "", ("93.184.216.34" if public and host != "internal.test" else "10.0.0.5", 0))])
    calls = []

    def get(url, **kw):
        calls.append((url, kw))
        status, payload = pages[url]
        headers = {"Location": payload} if status in (301, 302) else {}
        return types.SimpleNamespace(
            text=payload, status_code=status, headers=headers, is_redirect=status in (301, 302),
            raise_for_status=lambda: None if status < 400 else (_ for _ in ()).throw(requests.HTTPError(str(status))))

    monkeypatch.setattr(requests, "get", get)
    return calls


def test_url(client, monkeypatch):
    calls = fake_web(monkeypatch, {"http://x.test/essay": (200, f"<p>{TEXT}</p>")})
    r = client.post("/analyze", json={"url": "http://x.test/essay"})
    assert r.status_code == 200 and r.json()["source"] == "essay"
    assert calls[0][1]["allow_redirects"] is False


def test_url_follows_public_redirect(client, monkeypatch):
    fake_web(monkeypatch, {"http://x.test/a": (302, "/b"), "http://x.test/b": (200, f"<p>{TEXT}</p>")})
    assert client.post("/analyze", json={"url": "http://x.test/a"}).status_code == 200


def test_url_blocks_private_target(client, monkeypatch):
    calls = fake_web(monkeypatch, {}, public=False)
    assert_problem(client.post("/analyze", json={"url": "http://169.254.169.254/latest"}), 400, "url-not-allowed")
    assert calls == []


def test_url_blocks_redirect_to_private(client, monkeypatch):
    calls = fake_web(monkeypatch, {"http://x.test/a": (302, "http://internal.test/secret")})
    assert_problem(client.post("/analyze", json={"url": "http://x.test/a"}), 400, "url-not-allowed")
    assert [c[0] for c in calls] == ["http://x.test/a"]


def test_url_redirect_loop(client, monkeypatch):
    fake_web(monkeypatch, {"http://x.test/a": (302, "/a")})
    assert_problem(client.post("/analyze", json={"url": "http://x.test/a"}), 502, "upstream-fetch-failed")


def test_url_upstream_failure(client, monkeypatch):
    fake_web(monkeypatch, {"http://x.test/a": (500, "")})
    assert_problem(client.post("/analyze", json={"url": "http://x.test/a"}), 502, "upstream-fetch-failed")


def test_url_disabled(client, monkeypatch):
    monkeypatch.setenv("ALLOW_URL", "0")
    assert_problem(client.post("/analyze", json={"url": "http://x.test/a"}), 403, "url-not-allowed")


def test_crawl_clamps_max_pages(client, monkeypatch):
    monkeypatch.setenv("MAX_PAGES_CAP", "2")
    seen = {}
    from stylometry.server import app as mod
    monkeypatch.setattr(mod, "load_text", lambda src, **kw: seen.update(kw) or TEXT)
    client.post("/analyze", json={"url": "http://x.test/", "crawl": True, "max_pages": 99})
    assert seen["max_pages"] == 2 and seen["crawl"] is True


def test_crawl_blocks_private_start(client, monkeypatch):
    fake_web(monkeypatch, {}, public=False)
    assert_problem(client.post("/analyze", json={"url": "http://10.0.0.1/", "crawl": True}), 400, "url-not-allowed")


def test_lambda_handler():
    from stylometry.server import lambda_handler

    def event(method, path, body=None):
        return {"version": "2.0", "routeKey": "$default", "rawPath": path, "rawQueryString": "",
                "headers": {"content-type": "application/json"}, "body": body, "isBase64Encoded": False,
                "requestContext": {"http": {"method": method, "path": path, "sourceIp": "1.2.3.4",
                                            "protocol": "HTTP/1.1", "userAgent": "t"},
                                   "stage": "$default"}}

    r = lambda_handler.handler(event("GET", "/healthz"), None)
    assert r["statusCode"] == 200 and json.loads(r["body"])["status"] == "ok"
    r = lambda_handler.handler(event("POST", "/analyze", json.dumps({"text": TEXT})), None)
    assert r["statusCode"] == 200 and json.loads(r["body"])["sentence_count"] == 2
    r = lambda_handler.handler(event("POST", "/analyze", "{}"), None)
    assert r["statusCode"] == 422 and r["headers"]["content-type"] == "application/problem+json"
