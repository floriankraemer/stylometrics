"""Request handling shared by the HTTP API and the MCP tool."""
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field, model_validator

from stylometry import pipeline
from stylometry.ingest import load_text
from stylometry.report import clone_prompt, profile_md
from stylometry.server import ssrf
from stylometry.server.problems import Problem

PROVIDER_KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
RENDERERS = {"profile_md": profile_md.render, "clone_prompt": clone_prompt.render}


def int_env(name: str, default: int) -> int:
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


def analyze_request(body: AnalyzeRequest, include: list[str]) -> dict:
    """Validate the server-side preconditions and analyze a text or URL source. Raises Problem."""
    _check_include(include)
    _check_llm(body.llm, body.provider)
    if body.text is not None:
        return _analyze(body.text, body.name or "text", body.llm, body.provider, include)
    if os.environ.get("ALLOW_URL", "1") == "0":
        raise Problem(403, "url-not-allowed", "URL Not Allowed", "URL sources are disabled on this server.")
    text = _load(body.url, crawl=body.crawl, guard=_guard,
                 max_pages=min(body.max_pages, int_env("MAX_PAGES_CAP", 50)))
    name = body.name or body.url.rstrip("/").split("/")[-1] or urlparse(body.url).hostname
    return _analyze(text, name, body.llm, body.provider, include)


def analyze_path(path: str, name: str | None, llm: bool, provider: str, include: list[str]) -> dict:
    """Analyze a file on the local filesystem. Only for trusted callers (stdio), never exposed over HTTP."""
    _check_include(include)
    _check_llm(llm, provider)
    if not Path(path).is_file():
        raise Problem(404, "file-not-found", "File Not Found", f"No such file: {path}")
    return _analyze(_load(path), name or Path(path).name, llm, provider, include)
