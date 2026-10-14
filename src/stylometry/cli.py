import argparse
import ipaddress
import logging
import os
import sys
from pathlib import Path

from stylometry import __version__
from stylometry.ingest import load_text
from stylometry import pipeline
from stylometry.report import clone_prompt, html_report, profile_md

log = logging.getLogger("stylometry")

USAGE = """stylometry SOURCE [--output DIR] [--llm [--provider NAME]] [--crawl [--max-pages N]]
       stylometry --serve [--host HOST] [--port PORT]
       stylometry --mcp"""
EPILOG = """examples:
  stylometry book.pdf
  stylometry https://example.com/essay --output out
  stylometry --serve --port 8080
  claude mcp add stylometry -- stylometry --mcp"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stylometry", usage=USAGE, epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Measure an author's writing style and write an HTML report, a Markdown profile, "
                    "and a style-clone prompt.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    analyze = parser.add_argument_group("analyze a source")
    analyze.add_argument("source", nargs="?", help="file (.pdf .docx .epub .html .txt .md) or URL")
    analyze.add_argument("--output", type=Path, metavar="DIR", default=Path(os.environ.get("OUTPUT_DIR", "output")),
                         help="directory for the generated files (default: $OUTPUT_DIR or ./output)")
    analyze.add_argument("--llm", action="store_true", default=os.environ.get("LLM_ENABLED") == "1",
                         help="add an LLM-assisted qualitative pass (needs a provider API key)")
    analyze.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "anthropic"),
                         choices=["anthropic", "openai"], help="LLM provider for --llm (default: anthropic)")
    analyze.add_argument("--crawl", action="store_true", default=os.environ.get("CRAWL") == "1",
                         help="crawl the whole site (same domain) starting from a URL source")
    analyze.add_argument("--max-pages", type=int, metavar="N", default=int(os.environ.get("MAX_PAGES", 50)),
                         help="max pages to fetch with --crawl (default: 50)")
    servers = parser.add_argument_group("run as a server")
    servers.add_argument("--serve", action="store_true", help="HTTP API, with MCP over Streamable HTTP at /mcp")
    servers.add_argument("--mcp", action="store_true",
                         help="MCP server on stdin/stdout, for MCP clients such as Claude Code or Claude Desktop")
    servers.add_argument("--host", default="127.0.0.1", help="bind address for --serve (default: 127.0.0.1)")
    servers.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)),
                         help="port for --serve (default: $PORT or 8000)")
    return parser


def _setup_logging() -> None:
    """One line format for uvicorn, the MCP SDK and our own messages.

    Must run before the SDK builds its server: it only installs its own (Rich) handler when the root logger has none.
    """
    from uvicorn.logging import DefaultFormatter

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=sys.stderr.isatty()))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    logging.getLogger("mcp").setLevel(logging.WARNING)  # session-manager start/stop chatter


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def _serve(host: str, port: int) -> None:
    import uvicorn

    from stylometry.server.app import app
    from stylometry.server.service import PROVIDER_KEYS

    log.info("stylometry %s HTTP API: POST /analyze, POST /analyze/file, GET /healthz, MCP at /mcp", __version__)
    if os.environ.get("STYLOMETRY_API_KEY"):
        log.info("Auth: bearer token required (STYLOMETRY_API_KEY)")
    elif _is_loopback(host):
        log.info("Auth: off (set STYLOMETRY_API_KEY to require a bearer token)")
    else:
        log.warning("Auth: off on %s, anyone who can reach this port can use the API. Set STYLOMETRY_API_KEY.", host)
    providers = [p for p, key in PROVIDER_KEYS.items() if os.environ.get(key)]
    log.info("LLM pass: %s", ", ".join(providers) if providers else "unavailable (no provider API key set)")
    uvicorn.run(app, host=host, port=port)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = _parser()
    if not argv:
        parser.print_help(sys.stderr)
        sys.exit(2)
    args = parser.parse_args(argv)
    _setup_logging()
    try:
        _main(args, parser)
    except KeyboardInterrupt:
        log.warning("Interrupted.")
        sys.exit(130)


def _main(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.mcp:
        from stylometry.server.mcp_server import run_stdio

        run_stdio()
        return
    if args.serve:
        _serve(args.host, args.port)
        return
    if not args.source:
        parser.error("source is required unless --serve or --mcp is given")

    log.info("Loading %s%s", args.source, f" (crawling up to {args.max_pages} pages)" if args.crawl else "")
    text = load_text(args.source, crawl=args.crawl, max_pages=args.max_pages)
    if not text.strip():
        log.error("No text could be extracted from %s", args.source)
        sys.exit(1)

    log.info("Running spaCy analysis")
    source_name = args.source.rstrip("/").split("/")[-1]
    if args.llm:
        log.info("Running LLM-assisted qualitative pass (%s)", args.provider)
    profile = pipeline.run(text, source_name, llm=args.llm, provider=args.provider)

    args.output.mkdir(parents=True, exist_ok=True)
    base = Path(source_name).stem or "output"

    html_report.write(profile, args.output / f"{base}_report.html")
    profile_md.write(profile, args.output / f"{base}_profile.md")
    clone_prompt.write(profile, args.output / f"{base}_clone_prompt.md")

    log.info("Wrote %s_report.html, %s_profile.md, %s_clone_prompt.md to %s", base, base, base, args.output)


if __name__ == "__main__":
    main()
