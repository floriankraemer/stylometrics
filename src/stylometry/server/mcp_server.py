"""MCP server exposing the analysis: stdio (`stylometry --mcp`) or Streamable HTTP at /mcp."""
import os
import sys
from collections.abc import Callable
from typing import Annotated, Any, Literal

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field, ValidationError

from stylometry import compare as compare_mod
from stylometry.report import clone_prompt
from stylometry.server import service
from stylometry.server.problems import Problem
from stylometry.server.service import AnalyzeRequest

INSTRUCTIONS = ("Stylometric analysis of writing: lexical diversity, function words, syntax, punctuation, "
                "sentence rhythm, and rule-based voice/stance heuristics. Pass text or a url. "
                "Use compare to contrast two sources, and the write_like prompt to write in a source's style.")
DEFAULT_TASK = "Write a short passage in this style."
Provider = Literal["anthropic", "openai"]


async def _run(fn: Callable, *args) -> Any:
    """Run a blocking service call in a worker thread, mapping failures to the ValueError MCP reports as isError."""
    try:
        return await anyio.to_thread.run_sync(fn, *args)
    except Problem as p:
        raise ValueError(f"{p.title}: {p.detail}") from p


def _request(**kw) -> AnalyzeRequest:
    try:
        return AnalyzeRequest(**kw)
    except ValidationError as e:
        raise ValueError("; ".join(err["msg"] for err in e.errors())) from e


def build_mcp(local_files: bool = False) -> FastMCP:
    # Host checking (DNS-rebinding protection) is for localhost-only servers; this one is meant to be reachable,
    # and /mcp is protected by the same bearer API key as the rest of the HTTP API.
    mcp = FastMCP("stylometry", instructions=INSTRUCTIONS, json_response=True, stateless_http=True,
                  transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

    @mcp.tool()
    async def analyze(text: str | None = None, url: str | None = None, name: str | None = None,
                      crawl: bool = False, max_pages: Annotated[int, Field(ge=1)] = 50, llm: bool = False,
                      provider: Provider = "anthropic", include: list[str] | None = None) -> dict[str, Any]:
        """Analyze the writing style of a text or a web page.

        Give exactly one of `text` or `url`. `crawl` follows same-domain links up to `max_pages`.
        `llm` adds an LLM-assisted qualitative pass (needs a provider key on the server).
        `include` may contain "profile_md" and "clone_prompt" for rendered Markdown.
        """
        body = _request(text=text, url=url, name=name, crawl=crawl, max_pages=max_pages, llm=llm, provider=provider)
        return await _run(service.analyze_request, body, include or [])

    @mcp.tool()
    async def compare(a: AnalyzeRequest, b: AnalyzeRequest) -> dict[str, Any]:
        """Compare the writing style of two sources (each a `text` or a `url`).

        Returns every numeric metric of both with its delta (b - a), and the cosine similarity
        of their function-word frequencies (1.0 = identical, 0.0 = nothing in common).
        """
        pa, pb = [await _run(service.analyze_request, side, []) for side in (a, b)]
        return compare_mod.compare(pa, pb)

    @mcp.prompt()
    async def write_like(source: str, task: str = "") -> str:
        """Write in the style of a source: a http(s) URL or literal text. `task` says what to write."""
        key = "url" if source.lower().startswith(("http://", "https://")) else "text"
        profile = await _run(service.analyze_request, _request(**{key: source}), [])
        return f"{clone_prompt.render(profile)}\n\n{task or DEFAULT_TASK}"

    if local_files:
        @mcp.tool()
        async def analyze_file(path: str, name: str | None = None, llm: bool = False, provider: Provider = "anthropic",
                               include: list[str] | None = None) -> dict[str, Any]:
            """Analyze the writing style of a file on this machine (.pdf .docx .epub .html .htm .txt .md)."""
            return await _run(service.analyze_path, path, name, llm, provider, include or [])

    return mcp


def run_stdio() -> None:
    # The SDK wraps sys.stdout.buffer and closes it on exit; hand it a duplicate so the real stdout stays usable
    # (a PyInstaller binary flushes sys.stdout after main() returns).
    real = sys.stdout
    sys.stdout = open(os.dup(real.fileno()), "w")
    try:
        build_mcp(local_files=True).run(transport="stdio")
    finally:
        sys.stdout = real
