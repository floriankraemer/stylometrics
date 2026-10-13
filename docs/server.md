# HTTP server mode

The same analysis as the CLI, behind a JSON API.
It runs as a normal process on a VPS and as a container image on AWS Lambda.
The server also speaks MCP at `/mcp`; see [mcp.md](mcp.md) for the tools, the prompt, and client setup.

## Run it

### Locally or on a VPS

```sh
stylometry --serve --host 0.0.0.0 --port 8080
```

| Flag | Default | Meaning |
|---|---|---|
| `--serve` | | Run the HTTP server instead of analyzing a source. |
| `--host` | `127.0.0.1` | Bind address. |
| `--port` | `$PORT`, then `8000` | Listen port. |

The default host only accepts local connections.
Put a reverse proxy with TLS in front, or pass `0.0.0.0` deliberately.

From a source checkout, `make serve` does the same with the virtualenv (`HOST` and `PORT` override the defaults):

```sh
make serve PORT=8080
```

Without `make`, set `PYTHONPATH=src` and run `.venv/bin/python -m stylometry.cli --serve`.

### Docker

The image from `make build` (tag `stylometry`) has `stylometry` as its entry point, so pass the server flags straight through:

```sh
docker run --rm -p 8080:8080 -e STYLOMETRY_API_KEY=changeme stylometry --serve --host 0.0.0.0 --port 8080
```

Inside a container the host must be `0.0.0.0`, or the published port reaches nothing.

### AWS Lambda

```sh
docker build -f Dockerfile.lambda -t stylometry-lambda .
```

Push the image to ECR and create a function from it.
Use at least 2048 MB memory and a timeout that fits your inputs.
Expose it with a Function URL or API Gateway HTTP API (payload format 2.0).
The handler is `stylometry.server.lambda_handler.handler` (Mangum).
It loads the spaCy model at import time, so the cost lands in the cold start and not in the first request.
Set the variables from [Configuration](#configuration) on the function.

Limits to plan for:
- A synchronous Lambda payload is 6 MB, API Gateway allows 10 MB and 29 seconds.
  The default `MAX_BODY_BYTES` is 5 MiB.
- Larger books or crawls need a Function URL with a longer timeout, or the CLI.
- The MCP endpoint is stateless, so it works across Lambda instances without sticky sessions.

## Configuration

All settings are environment variables, read on each request.

| Variable | Default | Meaning |
|---|---|---|
| `STYLOMETRY_API_KEY` | unset | If set, `/analyze`, `/analyze/file` and `/mcp` require `Authorization: Bearer <key>`. Unset means open. |
| `MAX_BODY_BYTES` | `5242880` | Maximum request body size in bytes, for every route. |
| `MAX_PAGES_CAP` | `50` | Upper bound for `max_pages` when crawling. Larger requested values are clamped silently. |
| `ALLOW_URL` | `1` | Set to `0` to refuse `url` sources. |
| `ANTHROPIC_API_KEY` | unset | Needed for `"llm": true` with `provider` `anthropic`. |
| `OPENAI_API_KEY` | unset | Needed for `"llm": true` with `provider` `openai`. |
| `PORT` | `8000` | Default for `--port`. |

## Authentication

With `STYLOMETRY_API_KEY` set, send the key as a bearer token:

```sh
curl -s localhost:8080/analyze -H "Authorization: Bearer $STYLOMETRY_API_KEY" \
  -H 'content-type: application/json' -d '{"text": "I walked home. It was late."}'
```

A missing or wrong token gets `401` with `WWW-Authenticate: Bearer`.
`/healthz`, `/docs` and `/openapi.json` stay open.

Set the key whenever the server is reachable by others, and always when LLM calls are possible, because they spend the server's provider key.
On Lambda you can use IAM auth on the Function URL instead.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/healthz` | no | Liveness check. |
| `POST` | `/analyze` | yes | Analyze text or a URL (JSON body). |
| `POST` | `/analyze/file` | yes | Analyze an uploaded file (multipart). |
| `POST` | `/mcp` | yes | MCP over Streamable HTTP, see [mcp.md](mcp.md). |
| `GET` | `/docs` | no | Interactive OpenAPI documentation. `/mcp` is not listed there. |
| `GET` | `/openapi.json` | no | OpenAPI schema. |

### `GET /healthz`

```sh
curl -s localhost:8080/healthz
```

```json
{"status": "ok", "version": "0.0.0+dev"}
```

A source checkout and the Docker images report `0.0.0+dev`.
The prebuilt release binaries report their release version.

### `POST /analyze`

```sh
curl -s localhost:8080/analyze -H 'content-type: application/json' \
  -d '{"text": "I walked home. It was late, and the night was cold."}'
```

Send exactly one of `text` or `url`.

| Field | Default | Meaning |
|---|---|---|
| `text` | | The text to analyze. |
| `url` | | A web page to fetch and analyze. Must resolve to a public address. |
| `crawl` | `false` | With `url`: crawl the same domain (BFS, `robots.txt` respected). |
| `max_pages` | `50` | With `crawl`: page limit, at least 1, clamped to `MAX_PAGES_CAP`. |
| `name` | see below | Source name used in the output. |
| `llm` | `false` | Add the LLM-assisted qualitative pass. |
| `provider` | `anthropic` | `anthropic` or `openai`. |

Without `name`, the source is called `text` for text input.
For a URL it is the last path segment, or the host name if the path is empty.

Crawling a site:

```sh
curl -s localhost:8080/analyze -H 'content-type: application/json' \
  -d '{"url": "https://example.com/", "crawl": true, "max_pages": 20}'
```

### `POST /analyze/file`

```sh
curl -s localhost:8080/analyze/file -F file=@book.pdf -F name=book
```

| Form field | Default | Meaning |
|---|---|---|
| `file` | required | The document. Accepts `.pdf .docx .epub .html .htm .txt .md`, judged by the file name's suffix. |
| `name` | the uploaded file name | Source name used in the output. |
| `llm` | `false` | Add the LLM-assisted qualitative pass. |
| `provider` | `anthropic` | `anthropic` or `openai`. |

### Rendered Markdown (`include`)

Both `/analyze` and `/analyze/file` accept a repeatable `include` query parameter.
Each value adds a rendering under `rendered` in the response:

| Value | Adds |
|---|---|
| `profile_md` | The Markdown style profile (`<name>_profile.md` in CLI mode). |
| `clone_prompt` | The style-clone system prompt (`<name>_clone_prompt.md` in CLI mode). |

```sh
curl -s 'localhost:8080/analyze?include=profile_md&include=clone_prompt' \
  -H 'content-type: application/json' -d '{"text": "I walked home. It was late."}'
```

An unknown value returns `422 validation-error`.

### Response

`200` with the profile as JSON.
This is the real output for the `/analyze` example above, with the `function_words` list cut to three entries:

```json
{
  "source": "text",
  "sentence_count": 2,
  "quantitative": {
    "lexical": {"token_count": 11, "type_count": 10, "ttr": 0.9091, "yules_k": 165.29, "honores_r": 2397.9},
    "function_words": [
      {"word": "was", "per_1000": 181.82},
      {"word": "i", "per_1000": 90.91},
      {"word": "it", "per_1000": 90.91}
    ],
    "syntax": {"noun_ratio": 0.0909, "verb_ratio": 0.0909, "adj_ratio": 0.1818, "adv_ratio": 0.0909,
               "noun_to_verb_ratio": 0.33, "avg_parse_tree_depth": 2.0},
    "punctuation": {"em_dash": 0.0, "semicolon": 0.0, "colon": 0.0, "parentheses": 0.0, "ellipsis": 0.0,
                    "exclamation": 0.0, "question_mark": 0.0, "comma": 90.91},
    "burstiness": {"mean_sentence_length": 5.5, "stdev_sentence_length": 2.5, "min_sentence_length": 3,
                   "max_sentence_length": 8, "burstiness": -0.375}
  },
  "qualitative": {
    "heuristics": {
      "rhetorical_question_rate_per_100_sentences": 0.0,
      "anaphora_patterns": [],
      "hedging_rate_per_1000_words": 0.0,
      "assertiveness_rate_per_1000_words": 0.0,
      "pronoun_distribution": {"first_person": 1, "impersonal": 1},
      "narrative_voice": "first_person",
      "rule_of_three_occurrences": 0
    }
  }
}
```

With `"llm": true`, `qualitative` also has an `llm` object with the provider's answer.
With `include`, the response has a `rendered` object keyed by the requested values.

## Errors

Every error is an [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details document with media type `application/problem+json`.
`type` is `urn:stylometry:problem:` plus a slug, and `instance` is the request path.

```json
{
  "type": "urn:stylometry:problem:empty-text",
  "title": "No Text",
  "status": 422,
  "detail": "No text could be extracted from the input.",
  "instance": "/analyze"
}
```

Request validation failures add an `errors` member with one entry per problem:

```json
{
  "type": "urn:stylometry:problem:validation-error",
  "title": "Invalid request",
  "status": 422,
  "detail": "The request did not validate.",
  "instance": "/analyze",
  "errors": [
    {"loc": ["body", "max_pages"], "msg": "Input should be greater than or equal to 1"},
    {"loc": ["body", "provider"], "msg": "String should match pattern '^(anthropic|openai)$'"}
  ]
}
```

| Status | `type` slug | Title | Cause |
|---|---|---|---|
| 400 | `url-not-allowed` | URL Not Allowed | URL is not http(s), its host does not resolve, or it resolves (or redirects) to a non-public address. |
| 401 | `unauthorized` | Unauthorized | Missing or wrong bearer token. |
| 403 | `url-not-allowed` | URL Not Allowed | `url` sent while `ALLOW_URL=0`. |
| 404 | `not-found` | Not Found | Unknown route. |
| 405 | `method-not-allowed` | Method Not Allowed | Wrong method for the route, including any method other than `POST` on `/mcp` (with `Allow: POST`). |
| 406 | `not-acceptable` | Not Acceptable | `/mcp` only: the `Accept` header does not allow `application/json`. |
| 413 | `payload-too-large` | Payload Too Large | Body over `MAX_BODY_BYTES`, by `Content-Length` or by bytes received. |
| 415 | `unsupported-media-type` | Unsupported Input Type | Uploaded file has an unsupported suffix. |
| 415 | `unsupported-media-type` | Unsupported Media Type | `/mcp` only: `Content-Type` is not `application/json`. |
| 422 | `validation-error` | Invalid request | Bad JSON, missing or invalid fields (with `errors`), or an unknown `include` value (without `errors`). |
| 422 | `empty-text` | No Text | No text extracted. |
| 422 | `unreadable-input` | Unreadable Input | The file could not be parsed, for example a corrupt PDF. |
| 500 | `internal-error` | Internal Server Error | Unexpected failure. Details are only in the server log. |
| 502 | `upstream-fetch-failed` | Upstream Fetch Failed | The `url` could not be fetched, including more than the allowed number of redirects. |
| 502 | `llm-upstream-error` | LLM Provider Error | The LLM provider call failed. |
| 503 | `llm-not-configured` | LLM Not Configured | `llm: true` but the provider's key is not set on the server. |

Any other HTTP error raised by the framework uses the slug `http-error`.

## Security notes

- URL sources are checked against private, loopback, link-local, reserved, multicast and unspecified addresses before every request, including each redirect hop.
  This also blocks cloud metadata addresses.
  A DNS-rebinding window remains between the check and the connection, so restrict egress at the network level for untrusted callers.
- The `robots.txt` fetch for crawls is made by the standard library after the start URL has been checked.
- Uploaded file names are never used as paths.
  Only the suffix is kept.
- The HTTP API never reads files from the server's disk.
  The MCP `analyze_file` tool only exists over stdio, see [mcp.md](mcp.md#analyze_file-stdio-only).
