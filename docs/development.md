# Development

How to run the code from a checkout, test it, build binaries, and cut releases.

## Run from source

Needs Python 3.12.
`requirements.txt` pins `numpy==1.26.4` for spaCy 3.7 (see [numpy-pin.md](numpy-pin.md)), so use a dedicated virtualenv.

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
```

## Tests

Coverage must stay at 80% or more.

```sh
.venv/bin/pip install -r requirements-dev.txt
make test
```

## Native binary

```sh
make binary
```

This builds a native binary with PyInstaller into `dist/stylometry/`.

## Releases

Every release on the [Releases page](https://github.com/floriankraemer/stylometrics/releases) ships native binaries for Linux (x86_64, arm64), macOS (arm64), and Windows (x86_64), plus a `SHA256SUMS` file.

- `vX.Y.Z` releases are stable, tagged versions.
- `latest` is a rolling prerelease rebuilt from the head of `main` on every push.

To cut a release, push a strict semver tag:

```sh
git tag v1.2.3 && git push origin v1.2.3
```

Tags with a suffix such as `v1.2.3-rc.1` are published as prereleases.
A tag that is not `vMAJOR.MINOR.PATCH[-pre]` fails the release workflow.

## Make targets

| Command | Does |
|---|---|
| `make build` | Build the Docker image |
| `make analyze FILE=...` | Analyze a local file under `input/` |
| `make analyze URL=...` | Analyze one web page |
| `make analyze URL=... CRAWL=1 [MAX_PAGES=N]` | Crawl a whole site (default `MAX_PAGES=50`) and analyze the combined text |
| `make examples` | Re-run the analysis for every text under `examples/` |
| `make test` | Run the tests with coverage locally (fails under 80%) |
| `make serve [PORT=8000] [HOST=127.0.0.1]` | Run the HTTP API locally |
| `make binary` | Build a native binary with PyInstaller into `dist/` |
| `make shell` | Drop into the container for debugging |
| `make clean` | Remove generated files from `output/` |

## Project layout

```
src/stylometry/
├── cli.py            entrypoint
├── pipeline.py        text -> profile, shared by CLI and server
├── compare.py         side-by-side comparison of two profiles (MCP compare tool)
├── server/            FastAPI app, MCP server, RFC 9457 problems, SSRF guard, Lambda handler
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
