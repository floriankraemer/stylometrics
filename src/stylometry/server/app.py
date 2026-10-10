"""HTTP API. VPS: `stylometry --serve --port N`. Lambda: see lambda_handler.py."""
import os
import secrets
import tempfile
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import requests
from fastapi import Depends, FastAPI, Form, Query, Request, UploadFile
from pydantic import BaseModel, Field, model_validator

from stylometry import __version__, pipeline
from stylometry.ingest import load_text
from stylometry.report import clone_prompt, profile_md
from stylometry.server import problems, ssrf
from stylometry.server.problems import Problem

PROVIDER_KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
RENDERERS = {"profile_md": profile_md.render, "clone_prompt": clone_prompt.render}
Include = Annotated[list[str], Query(description="extra renderings: profile_md, clone_prompt")]


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


class AnalyzeRequest(BaseModel):
    text: str | None = None
    url: str | None = None
    name: str | None = Field(None, description="source name used in the reports")
    crawl: bool = False
    max_pages: int = Field(50, ge=1)
    llm: bool = False
    provider: str = Field("anthropic", pattern="^(anthropic|openai)$")

    @model_validator(mode="after")
    def _one_source(self):
        if (self.text is None) == (self.url is None):
            raise ValueError("provide exactly one of 'text' or 'url'")
        return self


class BodyLimit:
    """ASGI middleware: reject bodies over MAX_BODY_BYTES, by Content-Length and by bytes actually received."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = _int_env("MAX_BODY_BYTES", 5 * 1024 * 1024)
        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return await self._reject(scope, receive, send, limit)
        seen, too_large = 0, False

        async def counting_receive():
            # raising here would be swallowed by the body parser (-> 400), so end the body and swap the response
            nonlocal seen, too_large
            if too_large:
                return {"type": "http.request", "body": b"", "more_body": False}
            message = await receive()
            seen += len(message.get("body", b""))
            if seen > limit:
                too_large = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def guarded_send(message):
            if not too_large:
                await send(message)

        await self.app(scope, counting_receive, guarded_send)
        if too_large:
            await self._reject(scope, receive, send, limit)

    @staticmethod
    async def _reject(scope, receive, send, limit):
        resp = problems.response(Request(scope), 413, "payload-too-large", "Payload Too Large",
                                 f"The request body exceeds {limit} bytes.")
        await resp(scope, receive, send)


def require_api_key(request: Request) -> None:
    expected = os.environ.get("STYLOMETRY_API_KEY")
    if not expected:
        return
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), expected.encode()):
        raise Problem(401, "unauthorized", "Unauthorized", "A valid bearer token is required.",
                      headers={"WWW-Authenticate": "Bearer"})


def _check_include(include: list[str]) -> None:
    unknown = sorted(set(include) - RENDERERS.keys())
    if unknown:
        raise Problem(422, "validation-error", "Invalid request",
                      f"Unknown include value(s): {', '.join(unknown)}.")


def _check_llm(llm: bool, provider: str) -> None:
    if llm and not os.environ.get(PROVIDER_KEYS[provider]):
        raise Problem(503, "llm-not-configured", "LLM Not Configured",
                      f"The server has no {PROVIDER_KEYS[provider]} configured.")


def _guard(url: str) -> None:
    try:
        ssrf.check(url)
    except ssrf.UrlNotAllowed as e:
        raise Problem(400, "url-not-allowed", "URL Not Allowed", str(e)) from e


def _analyze(text: str, name: str, llm: bool, provider: str, include: list[str]) -> dict:
    if not text.strip():
        raise Problem(422, "empty-text", "No Text", "No text could be extracted from the input.")
    try:
        profile = pipeline.run(text, name, llm=llm, provider=provider)
    except pipeline.LLMError as e:
        raise Problem(502, "llm-upstream-error", "LLM Provider Error", str(e)) from e
    if include:
        profile["rendered"] = {k: RENDERERS[k](profile) for k in include}
    return profile


def _load(source: str, **kw) -> str:
    try:
        return load_text(source, **kw)
    except ValueError as e:
        raise Problem(415, "unsupported-media-type", "Unsupported Input Type",
                      "Supported types: .pdf .docx .epub .html .htm .txt .md") from e
    except requests.RequestException as e:
        raise Problem(502, "upstream-fetch-failed", "Upstream Fetch Failed", str(e)) from e
    except Exception as e:
        if isinstance(e, Problem):
            raise
        # corrupt pdf/docx/epub etc.
        raise Problem(422, "unreadable-input", "Unreadable Input", "The input could not be parsed.") from e


def create_app() -> FastAPI:
    app = FastAPI(title="Stylometry", version=__version__)
    problems.install(app)
    app.add_middleware(BodyLimit)
    auth = [Depends(require_api_key)]

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": __version__}

    @app.post("/analyze", dependencies=auth)
    def analyze_json(body: AnalyzeRequest, include: Include = []):
        _check_include(include)
        _check_llm(body.llm, body.provider)
        if body.text is not None:
            return _analyze(body.text, body.name or "text", body.llm, body.provider, include)
        if os.environ.get("ALLOW_URL", "1") == "0":
            raise Problem(403, "url-not-allowed", "URL Not Allowed", "URL sources are disabled on this server.")
        text = _load(body.url, crawl=body.crawl, guard=_guard,
                     max_pages=min(body.max_pages, _int_env("MAX_PAGES_CAP", 50)))
        name = body.name or body.url.rstrip("/").split("/")[-1] or urlparse(body.url).hostname
        return _analyze(text, name, body.llm, body.provider, include)

    @app.post("/analyze/file", dependencies=auth)
    def analyze_file(file: UploadFile, name: Annotated[str | None, Form()] = None,
                     llm: Annotated[bool, Form()] = False,
                     provider: Annotated[str, Form(pattern="^(anthropic|openai)$")] = "anthropic",
                     include: Include = []):
        _check_include(include)
        _check_llm(llm, provider)
        filename = Path(file.filename or "upload").name
        # the client-supplied name only contributes its suffix to the temp path
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / f"upload{Path(filename).suffix.lower()}"
            path.write_bytes(file.file.read())
            text = _load(str(path))
        return _analyze(text, name or filename, llm, provider, include)

    return app


app = create_app()
