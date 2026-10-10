# HTTP and MCP server mode

The same analysis as the CLI, behind a JSON API and as an MCP tool.
It runs as a normal process on a VPS and as a container image on AWS Lambda.

## Run on a VPS

```sh
stylometry --serve --host 0.0.0.0 --port 8080
```

`--port` defaults to `$PORT`, then `8000`.
`--host` defaults to `127.0.0.1`, so put a reverse proxy (TLS) in front, or pass `0.0.0.0` deliberately.

Docker works the same way:

```sh
docker run --rm -p 8080:8080 -e STYLOMETRY_API_KEY=changeme stylometry --serve --host 0.0.0.0 --port 8080
```

From source: `make serve PORT=8080`.

## Run on AWS Lambda

```sh
docker build -f Dockerfile.lambda -t stylometry-lambda .
```

Push the image to ECR and create a function from it.
Use at least 2048 MB memory and a timeout that fits your inputs.
Expose it with a Function URL or API Gateway HTTP API (payload format 2.0).
The handler is `stylometry.server.lambda_handler.handler` (Mangum).

Limits to plan for:
- A synchronous Lambda payload is 6 MB, API Gateway allows 10 MB and 29 seconds.
  The default `MAX_BODY_BYTES` is 5 MiB.
- Larger books or crawls need a Function URL with a longer timeout, or the CLI.
- Cold start loads the spaCy model once per instance.

## MCP server

The server exposes one MCP tool, `analyze`, with the same inputs as `POST /analyze`: `text` or `url`, `name`, `crawl`, `max_pages`, `llm`, `provider`, `include`.
It returns the profile as structured JSON.
Failures come back as tool errors (`isError`) with the problem title and detail.
Local file paths are not accepted, so use `text` or `url`, or the `/analyze/file` endpoint.

### stdio (local clients)

```sh
stylometry --mcp
```

Claude Code:

```sh
claude mcp add stylometry -- /path/to/stylometry --mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{"mcpServers": {"stylometry": {"command": "/path/to/stylometry", "args": ["--mcp"]}}}
```

Provider keys for `llm` come from the environment of that process.

### Streamable HTTP (remote clients)

The HTTP server serves MCP at `/mcp`, in stateless JSON mode, so it works on a VPS and on Lambda alike.

```sh
claude mcp add --transport http stylometry https://example.com/mcp --header "Authorization: Bearer $KEY"
```

`/mcp` uses the same `STYLOMETRY_API_KEY` bearer check, body size limit, and URL guard as the REST endpoints.
It does not check the `Host` header (the SDK's DNS-rebinding protection is off), so put the key on it whenever the server is reachable beyond localhost.

## Configuration

All settings are environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `STYLOMETRY_API_KEY` | unset | If set, `/analyze*` require `Authorization: Bearer <key>`. Unset means open. |
| `MAX_BODY_BYTES` | `5242880` | Maximum request body size. |
| `MAX_PAGES_CAP` | `50` | Upper bound for `max_pages` when crawling. |
| `ALLOW_URL` | `1` | Set to `0` to refuse `url` sources. |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | unset | Needed for `"llm": true`. |

Set `STYLOMETRY_API_KEY` whenever LLM calls are possible, because they spend the server's provider key.
On Lambda you can use IAM auth on the Function URL instead.

## Endpoints

### `POST /analyze` (JSON)

```sh
curl -s localhost:8080/analyze -H 'content-type: application/json' \
  -d '{"text": "I walked home. It was late."}'
```

Send exactly one of `text` or `url`.

| Field | Default | Meaning |
|---|---|---|
| `text` | | The text to analyze. |
| `url` | | A web page to fetch and analyze. |
| `crawl` | `false` | With `url`: crawl the same domain. |
| `max_pages` | `50` | With `crawl`: page limit, capped by `MAX_PAGES_CAP`. |
| `name` | `text` or the URL's last segment | Source name used in the output. |
| `llm` | `false` | Add the LLM-assisted qualitative pass. |
| `provider` | `anthropic` | `anthropic` or `openai`. |

### `POST /analyze/file` (multipart)

```sh
curl -s localhost:8080/analyze/file -F file=@book.pdf -F name=book
```

Accepts `.pdf .docx .epub .html .htm .txt .md`.
Optional form fields: `name`, `llm`, `provider`.

### Response

`200` with the profile: `source`, `sentence_count`, `quantitative`, `qualitative`.
Add `?include=profile_md&include=clone_prompt` to also get the rendered Markdown under `rendered`.

### `GET /healthz`

Returns `{"status": "ok", "version": "..."}`.
No authentication.

### `GET /docs`

Interactive OpenAPI documentation (`/openapi.json` for the schema).

## Errors

Every error is an [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) Problem Details document with media type `application/problem+json`.

```json
{
  "type": "urn:stylometry:problem:empty-text",
  "title": "No Text",
  "status": 422,
  "detail": "No text could be extracted from the input.",
  "instance": "/analyze"
}
```

| Status | `type` suffix | Cause |
|---|---|---|
| 400 | `url-not-allowed` | URL is not public http(s), or a redirect led somewhere internal. |
| 401 | `unauthorized` | Missing or wrong bearer token. |
| 403 | `url-not-allowed` | `ALLOW_URL=0`. |
| 404, 405 | `not-found`, `method-not-allowed` | Unknown route or method. |
| 413 | `payload-too-large` | Body over `MAX_BODY_BYTES`. |
| 415 | `unsupported-media-type` | Unsupported file extension. |
| 422 | `validation-error` | Bad JSON or fields. The `errors` member lists each problem. |
| 422 | `empty-text` | No text extracted. |
| 422 | `unreadable-input` | The file could not be parsed. |
| 500 | `internal-error` | Unexpected failure. Details are only in the server log. |
| 502 | `upstream-fetch-failed` | The `url` could not be fetched. |
| 502 | `llm-upstream-error` | The LLM provider call failed. |
| 503 | `llm-not-configured` | `llm: true` but the provider key is not set on the server. |

## Security notes

- URL sources are checked against private, loopback, link-local and metadata addresses before every request, including redirects.
  A DNS-rebinding window remains between the check and the connection, so restrict egress at the network level for untrusted callers.
- The `robots.txt` fetch for crawls is made by the standard library after the start URL has been checked.
- Uploaded file names are never used as paths. Only the suffix is kept.
