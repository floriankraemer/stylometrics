import argparse
import os
import sys
from pathlib import Path

from stylometry import __version__
from stylometry.ingest import load_text
from stylometry import pipeline
from stylometry.report import clone_prompt, html_report, profile_md



def main(argv=None):
    parser = argparse.ArgumentParser(prog="stylometry")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("source", nargs="?", help="path to input file or a URL (not needed with --serve)")
    parser.add_argument("--serve", action="store_true", help="run the HTTP API server instead of analyzing a source")
    parser.add_argument("--host", default="127.0.0.1", help="bind address for --serve (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)),
                         help="port for --serve (default: $PORT or 8000)")
    parser.add_argument("--llm", action="store_true", default=os.environ.get("LLM_ENABLED") == "1",
                         help="enable LLM-assisted qualitative analysis (opt-in)")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "anthropic"),
                         choices=["anthropic", "openai"])
    parser.add_argument("--crawl", action="store_true", default=os.environ.get("CRAWL") == "1",
                         help="crawl the whole site (same domain) starting from a URL source, instead of one page")
    parser.add_argument("--max-pages", type=int, default=int(os.environ.get("MAX_PAGES", 50)),
                         help="max pages to fetch when --crawl is set (default 50)")
    parser.add_argument("--output", type=Path, default=Path(os.environ.get("OUTPUT_DIR", "output")),
                         help="directory for the generated files (default: $OUTPUT_DIR or ./output)")
    args = parser.parse_args(argv)

    if args.serve:
        import uvicorn

        from stylometry.server.app import app

        uvicorn.run(app, host=args.host, port=args.port)
        return
    if not args.source:
        parser.error("source is required unless --serve is given")

    print(f"[stylometry] loading: {args.source}" + (f" (crawling up to {args.max_pages} pages)" if args.crawl else ""), file=sys.stderr)
    text = load_text(args.source, crawl=args.crawl, max_pages=args.max_pages)
    if not text.strip():
        print("[stylometry] error: no text extracted from source", file=sys.stderr)
        sys.exit(1)

    print("[stylometry] running spaCy analysis...", file=sys.stderr)
    source_name = args.source.rstrip("/").split("/")[-1]
    if args.llm:
        print(f"[stylometry] running LLM-assisted qualitative pass ({args.provider})...", file=sys.stderr)
    profile = pipeline.run(text, source_name, llm=args.llm, provider=args.provider)

    args.output.mkdir(parents=True, exist_ok=True)
    base = Path(source_name).stem or "output"

    html_report.write(profile, args.output / f"{base}_report.html")
    profile_md.write(profile, args.output / f"{base}_profile.md")
    clone_prompt.write(profile, args.output / f"{base}_clone_prompt.md")

    print(f"[stylometry] wrote {base}_report.html, {base}_profile.md, {base}_clone_prompt.md to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
