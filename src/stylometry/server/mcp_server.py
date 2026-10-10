"""MCP server exposing the analysis as a tool: stdio (`stylometry --mcp`) or Streamable HTTP at /mcp."""
from typing import Any

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import ValidationError

from stylometry.server.problems import Problem
from stylometry.server.service import AnalyzeRequest, analyze_request

INSTRUCTIONS = ("Stylometric analysis of writing: lexical diversity, function words, syntax, punctuation, "
                "sentence rhythm, and rule-based voice/stance heuristics. Pass text or a url.")


def build_mcp() -> FastMCP:
    # Host checking (DNS-rebinding protection) is for localhost-only servers; this one is meant to be reachable,
    # and /mcp is protected by the same bearer API key as the rest of the HTTP API.
    mcp = FastMCP("stylometry", instructions=INSTRUCTIONS, json_response=True, stateless_http=True,
                  transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

    @mcp.tool()
    async def analyze(text: str | None = None, url: str | None = None, name: str | None = None,
                      crawl: bool = False, max_pages: int = 50, llm: bool = False, provider: str = "anthropic",
                      include: list[str] | None = None) -> dict[str, Any]:
        """Analyze the writing style of a text or a web page.

        Give exactly one of `text` or `url`. `crawl` follows same-domain links up to `max_pages`.
        `llm` adds an LLM-assisted qualitative pass (needs a provider key on the server).
        `include` may contain "profile_md" and "clone_prompt" for rendered Markdown.
        """
        try:
            body = AnalyzeRequest(text=text, url=url, name=name, crawl=crawl, max_pages=max_pages, llm=llm,
                                  provider=provider)
        except ValidationError as e:
            raise ValueError("; ".join(err["msg"] for err in e.errors())) from e
        try:
            return await anyio.to_thread.run_sync(analyze_request, body, include or [])
        except Problem as p:
            raise ValueError(f"{p.title}: {p.detail}") from p

    return mcp


def run_stdio() -> None:
    build_mcp().run(transport="stdio")
