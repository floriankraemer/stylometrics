# Stylometry Pipeline

Dockerized pipeline that analyzes an author's writing style and produces:

1. **`<name>_report.html`** — human-readable style report.
2. **`<name>_profile.md`** — the same analysis as structured Markdown, meant to be pasted straight into an LLM's context.
3. **`<name>_clone_prompt.md`** — a ready-to-use system prompt that encodes the measured voice, for cloning the author's style elsewhere.

It combines quantitative stylometrics (lexical diversity, function-word frequency, POS/syntax, punctuation profile, sentence-length burstiness) with rule-based qualitative heuristics (tone/stance signals, rhetorical questions, anaphora, rule-of-three). A true LLM-assisted qualitative pass is available as an opt-in flag.

## Requirements

- Docker
- `make`

## Quick start

```sh
make build

# analyze a local file — drop it in input/ first
cp ~/Downloads/some-book.pdf input/
make analyze FILE=input/some-book.pdf

# analyze one web page
make analyze URL=https://example.com/some-essay

# crawl a whole site (same domain, BFS, robots.txt respected)
make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100
```

Results land in `output/`.

## Download a prebuilt binary

Every release on the [Releases page](https://github.com/floriankraemer/stylometrics/releases) ships native binaries for Linux (x86_64, arm64), macOS (x86_64, arm64), and Windows (x86_64).
No Python or Docker needed.

- **`vX.Y.Z`** releases are stable, tagged versions.
- **`latest`** is a rolling prerelease rebuilt from the head of `main` on every push.

Each release includes a `SHA256SUMS` file.

```sh
tar -xzf stylometry_<version>_linux-x86_64.tar.gz
./stylometry_<version>_linux-x86_64/stylometry some-book.pdf --output out
```

The binaries are not code-signed.
On macOS, clear the quarantine flag once: `xattr -dr com.apple.quarantine stylometry_*`.
On Windows, SmartScreen may ask you to confirm the first run.

To cut a release, push a strict semver tag:

```sh
git tag v1.2.3 && git push origin v1.2.3
```

Tags with a suffix such as `v1.2.3-rc.1` are published as prereleases.
A tag that is not `vMAJOR.MINOR.PATCH[-pre]` fails the release workflow.

## Running locally without Docker

Needs Python 3.12.
`requirements.txt` pins `numpy==1.26.4` for spaCy 3.7 (see [docs/numpy-pin.md](docs/numpy-pin.md)), so use a dedicated virtualenv.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m spacy download en_core_web_sm
```

Run from the repo root.
Results go to `./output` by default.
Use `--output DIR` or `OUTPUT_DIR` to change that.

```sh
export PYTHONPATH=src

.venv/bin/python -m stylometry.cli input/some-book.pdf
.venv/bin/python -m stylometry.cli https://example.com/some-essay
.venv/bin/python -m stylometry.cli https://example.com --crawl --max-pages 100

# LLM pass
ANTHROPIC_API_KEY=sk-... .venv/bin/python -m stylometry.cli input/book.pdf --llm
OPENAI_API_KEY=sk-... .venv/bin/python -m stylometry.cli input/book.pdf --llm --provider openai

# tests (coverage must stay at 80% or more)
.venv/bin/pip install -r requirements-dev.txt
make test

# native binary into dist/stylometry/
make binary
```

## Supported input formats

PDF, DOCX, plain text / Markdown, EPUB, a single web page (URL or local `.html`), or a whole site via `CRAWL=1`.

## Optional LLM-assisted qualitative pass

Off by default (fully offline otherwise). Enable with `LLM=1`:

```sh
export ANTHROPIC_API_KEY=sk-...
make analyze FILE=input/book.pdf LLM=1
# or
export OPENAI_API_KEY=sk-...
make analyze FILE=input/book.pdf LLM=1 PROVIDER=openai
```

This sends a text sample plus the computed quantitative metrics to the chosen provider and adds a "Rhetoric" section (tone/register, rhetorical devices, cadence, persuasion style) to all three outputs.

## Examples

`examples/` contains two public-domain corpora with their generated reports: Marcus Aurelius's *Meditations* and a volume of Edgar Allan Poe's tales.
See [docs/examples.md](docs/examples.md) for where the texts come from, the measured results side by side, and how to read them.

## Commands

| Command | Does |
|---|---|
| `make build` | Build the Docker image |
| `make analyze FILE=...` | Analyze a local file under `input/` |
| `make analyze URL=...` | Analyze one web page |
| `make analyze URL=... CRAWL=1 [MAX_PAGES=N]` | Crawl a whole site (default `MAX_PAGES=50`) and analyze the combined text |
| `make examples` | Re-run the analysis for every text under `examples/` |
| `make test` | Run the tests with coverage locally (fails under 80%) |
| `make binary` | Build a native binary with PyInstaller into `dist/` |
| `make shell` | Drop into the container for debugging |
| `make clean` | Remove generated files from `output/` |

## Project layout

```
src/stylometry/
├── cli.py            entrypoint
├── ingest.py          PDF/DOCX/TXT/MD/EPUB/URL/site-crawl -> plain text
├── preprocess.py       single spaCy pass shared by all metrics
├── metrics/            lexical, function_words, syntax, punctuation, burstiness
├── qualitative/         heuristics.py (default), llm.py (opt-in)
└── report/              profile.py assembles the data; html_report/profile_md/clone_prompt render it
examples/               public-domain sample texts and their generated outputs
tests/                  pytest suite, run with `make test`
packaging/              PyInstaller entry point and spec
.github/workflows/      test, build matrix, release (tags) and latest (main)
```

See `docs/` for implementation notes (e.g. why `numpy` is pinned).

## License

Copyright (C) 2026 Florian Krämer

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
See [LICENSE](LICENSE) for the full text.
