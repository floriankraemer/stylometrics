# Stylometry Pipeline

[Stylometry](https://en.wikipedia.org/wiki/Stylometry) is the statistical study of writing style.
It measures habits such as word choice, sentence length, and punctuation, which are consistent enough to tell authors apart.

Dockerized pipeline that analyzes an author's writing style and produces:

1. **`<name>_report.html`** — human-readable style report.
2. **`<name>_profile.md`** — the same analysis as structured Markdown, meant to be pasted straight into an LLM's context.
3. **`<name>_clone_prompt.md`** — a ready-to-use system prompt that encodes the measured voice, for cloning the author's style elsewhere.

It combines quantitative stylometrics (lexical diversity, function-word frequency, POS/syntax, punctuation profile, sentence-length burstiness) with rule-based qualitative heuristics (tone/stance signals, rhetorical questions, anaphora, rule-of-three).
A true LLM-assisted qualitative pass is available as an opt-in flag.

## Install

### Docker

Needs Docker and `make`.

```sh
make build
```

### Prebuilt binary

Every release on the [Releases page](https://github.com/floriankraemer/stylometrics/releases) ships native binaries for Linux (x86_64, arm64), macOS (arm64), and Windows (x86_64).
No Python or Docker needed.
`latest` is a rolling prerelease built from `main`, and each release includes a `SHA256SUMS` file.

```sh
tar -xzf stylometry_<version>_linux-x86_64.tar.gz
./stylometry_<version>_linux-x86_64/stylometry some-book.pdf --output out
```

The binaries are not code-signed.
On macOS, clear the quarantine flag once: `xattr -dr com.apple.quarantine stylometry_*`.
On Windows, SmartScreen may ask you to confirm the first run.

### From source

Needs Python 3.12 and a dedicated virtualenv.
See [docs/development.md](docs/development.md) for the setup, tests, and builds.

## Quick start

```sh
# analyze a local file — drop it in input/ first
cp ~/Downloads/some-book.pdf input/
make analyze FILE=input/some-book.pdf

# analyze one web page
make analyze URL=https://example.com/some-essay

# crawl a whole site (same domain, BFS, robots.txt respected)
make analyze URL=https://example.com CRAWL=1 MAX_PAGES=100
```

Results land in `output/`.
Supported inputs are PDF, DOCX, plain text / Markdown, EPUB, a single web page (URL or local `.html`), or a whole site via `CRAWL=1`.
With a binary, pass the file or URL directly: `stylometry some-book.pdf`, plus `--crawl --max-pages N` for sites.
`make help` and [docs/development.md](docs/development.md#make-targets) list all `make` targets.

### Optional LLM-assisted qualitative pass

Off by default (fully offline otherwise).
Enable with `LLM=1` (`--llm` on the CLI):

```sh
export ANTHROPIC_API_KEY=sk-...
make analyze FILE=input/book.pdf LLM=1
# or
export OPENAI_API_KEY=sk-...
make analyze FILE=input/book.pdf LLM=1 PROVIDER=openai
```

This sends a text sample plus the computed quantitative metrics to the chosen provider and adds a "Rhetoric" section (tone/register, rhetorical devices, cadence, persuasion style) to all three outputs.

## Server mode

`stylometry --serve --port 8080` starts an HTTP API: post JSON or a file, get the analysis back as JSON.
Errors use RFC 9457 Problem Details.
It also runs on AWS Lambda through `Dockerfile.lambda`.
See [docs/server.md](docs/server.md) for endpoints, configuration, and deployment.

The same analysis is available as an MCP server, over stdio (`stylometry --mcp`) or Streamable HTTP (`/mcp` on the HTTP server).
Its tools are `analyze`, `compare` (two sources side by side, with per-metric deltas and a function-word similarity score), and `analyze_file` (local files, stdio only).
The `write_like` prompt turns a text or URL into a style-clone prompt plus your writing task.
See [docs/mcp.md](docs/mcp.md) for the reference and client setup for Claude Code and Claude Desktop.

## Examples

`examples/` contains seven public-domain texts with their generated reports, from Marcus Aurelius's *Meditations* to Thoreau's *Walden*.
See [docs/examples.md](docs/examples.md) for where the texts come from, the measured results side by side, and how to read them.

## Documentation

| Document | Covers |
|---|---|
| [docs/server.md](docs/server.md) | HTTP API: endpoints, request and response shapes, errors, configuration, Docker and Lambda deployment. |
| [docs/mcp.md](docs/mcp.md) | MCP server: tools, the `write_like` prompt, transports, and client setup. |
| [docs/examples.md](docs/examples.md) | The bundled example texts, their sources, and how to read the results. |
| [docs/development.md](docs/development.md) | Running from source, tests, binaries, releases, `make` targets, and the project layout. |
| [docs/numpy-pin.md](docs/numpy-pin.md) | Why `numpy` is pinned to 1.26.4. |

## License

Copyright (C) 2026 Florian Krämer

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
See [LICENSE](LICENSE) for the full text.
