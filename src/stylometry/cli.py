import argparse
import os
import sys
from pathlib import Path

from stylometry.ingest import load_text
from stylometry.preprocess import analyze
from stylometry.qualitative import llm as llm_qualitative
from stylometry.report import clone_prompt, html_report, profile_md
from stylometry.report.profile import build

OUTPUT_DIR = Path("/output")


def main():
    parser = argparse.ArgumentParser(prog="stylometry")
    parser.add_argument("source", help="path to input file (mounted under /input) or a URL")
    parser.add_argument("--llm", action="store_true", default=os.environ.get("LLM_ENABLED") == "1",
                         help="enable LLM-assisted qualitative analysis (opt-in)")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "anthropic"),
                         choices=["anthropic", "openai"])
    parser.add_argument("--crawl", action="store_true", default=os.environ.get("CRAWL") == "1",
                         help="crawl the whole site (same domain) starting from a URL source, instead of one page")
    parser.add_argument("--max-pages", type=int, default=int(os.environ.get("MAX_PAGES", 50)),
                         help="max pages to fetch when --crawl is set (default 50)")
    args = parser.parse_args()

    print(f"[stylometry] loading: {args.source}" + (f" (crawling up to {args.max_pages} pages)" if args.crawl else ""), file=sys.stderr)
    text = load_text(args.source, crawl=args.crawl, max_pages=args.max_pages)
    if not text.strip():
        print("[stylometry] error: no text extracted from source", file=sys.stderr)
        sys.exit(1)

    print("[stylometry] running spaCy analysis...", file=sys.stderr)
    analysis = analyze(text)

    llm_result = None
    if args.llm:
        print(f"[stylometry] running LLM-assisted qualitative pass ({args.provider})...", file=sys.stderr)
        preliminary = build(analysis, args.source)
        llm_result = llm_qualitative.compute(text, preliminary["quantitative"], args.provider)

    source_name = args.source.rstrip("/").split("/")[-1]
    profile = build(analysis, source_name, llm_result=llm_result)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = Path(source_name).stem or "output"

    html_report.write(profile, OUTPUT_DIR / f"{base}_report.html")
    profile_md.write(profile, OUTPUT_DIR / f"{base}_profile.md")
    clone_prompt.write(profile, OUTPUT_DIR / f"{base}_clone_prompt.md")

    print(f"[stylometry] wrote {base}_report.html, {base}_profile.md, {base}_clone_prompt.md to /output", file=sys.stderr)


if __name__ == "__main__":
    main()
