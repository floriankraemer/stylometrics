# MCP server

Stylometry runs as a [Model Context Protocol](https://modelcontextprotocol.io) server, so an assistant such as Claude can analyze and compare writing styles and write in a measured style.
It offers three tools and one prompt over two transports.

| Transport | Start | Tools | Who it is for |
|---|---|---|---|
| stdio | `stylometry --mcp` | `analyze`, `compare`, `analyze_file` | A client on the same machine that launches the process. |
| Streamable HTTP | `POST /mcp` on the [HTTP server](server.md) | `analyze`, `compare` | Remote clients. |

Both transports offer the `write_like` prompt.

## Tools

Each tool returns its result twice, as `structuredContent` and as JSON text in `content`.
Failures come back as a tool result with `isError: true` and a text message, not as a JSON-RPC error.

### `analyze`

Analyzes a text or a web page and returns the same profile as [`POST /analyze`](server.md#response).

| Argument | Default | Meaning |
|---|---|---|
| `text` | | The text to analyze. |
| `url` | | A web page to fetch and analyze. |
| `name` | `text` or the URL's last segment | Source name used in the output. |
| `crawl` | `false` | With `url`: crawl the same domain. |
| `max_pages` | `50` | With `crawl`: page limit, at least 1, clamped to `MAX_PAGES_CAP`. |
| `llm` | `false` | Add the LLM-assisted qualitative pass. |
| `provider` | `anthropic` | `anthropic` or `openai`. |
| `include` | none | List with `profile_md` and/or `clone_prompt`, added under `rendered`. |

Give exactly one of `text` or `url`.

### `compare`

Analyzes two sources and puts their numbers side by side.

| Argument | Meaning |
|---|---|
| `a` | First source: an object with the `analyze` arguments except `include`. |
| `b` | Second source, same shape. |

```json
{"a": {"text": "I walked home. It was late, and the night was cold.", "name": "a"},
 "b": {"url": "https://example.com/essay", "name": "b"}}
```

The result has three members:

| Member | Meaning |
|---|---|
| `sources` | The two source names, `[a, b]`. |
| `metrics` | Every numeric metric from the `lexical`, `burstiness`, `syntax` and `punctuation` sections, keyed `section.metric`, each with `a`, `b`, and `delta` (`b - a`, rounded to 4 places). |
| `function_word_similarity` | Cosine similarity of the two function-word frequency vectors, from 0.0 (nothing in common) to 1.0 (identical), rounded to 4 places. |

Real output for two short texts, with `metrics` cut to three entries:

```json
{
  "sources": ["a", "b"],
  "metrics": {
    "burstiness.burstiness": {"a": -0.375, "b": -0.4776, "delta": -0.1026},
    "burstiness.max_sentence_length": {"a": 8, "b": 2, "delta": -6},
    "burstiness.mean_sentence_length": {"a": 5.5, "b": 1.33, "delta": -4.17}
  },
  "function_word_similarity": 0.0
}
```

The two sources are analyzed one after the other, so a compare takes as long as two analyses.
If either side fails, the whole call fails.

### `analyze_file` (stdio only)

Analyzes a file on the machine that runs the server.

| Argument | Default | Meaning |
|---|---|---|
| `path` | required | Path to a `.pdf .docx .epub .html .htm .txt .md` file. |
| `name` | the file name | Source name used in the output. |
| `llm` | `false` | Add the LLM-assisted qualitative pass. |
| `provider` | `anthropic` | `anthropic` or `openai`. |
| `include` | none | As for `analyze`. |

The tool is registered only for stdio.
Over HTTP it does not exist (`Unknown tool: analyze_file`), so a remote client cannot read files from the server.
To analyze a file remotely, upload it to [`POST /analyze/file`](server.md#post-analyzefile).

## Prompt: `write_like`

Builds a prompt that asks the model to write in the measured style of a source.

| Argument | Required | Meaning |
|---|---|---|
| `source` | yes | A URL if it starts with `http://` or `https://`, otherwise the literal text to imitate. |
| `task` | no | What to write. Defaults to `Write a short passage in this style.` |

The server analyzes `source`, then returns one `user` message: the style-clone prompt (the same text as `<name>_clone_prompt.md` in CLI mode), a blank line, and the task.

```text
# Style-Clone System Prompt — derived from: text

You are a writer who replicates the measured style below with precision. Do not describe the style — write in it.

## Sentence Mechanics
- Average sentence length: 5.5 words (stdev 2.5, range 3-8).
...

Write a poem.
```

URL sources go through the same checks as the `url` argument of `analyze`.
If the analysis fails, the client gets a JSON-RPC error instead of a result.
The code is `-32602` (invalid params) when the source is at fault and `-32603` (internal error) when the cause is a server-side failure with a 5xx status, such as a failed fetch.
The message is the problem title and detail, or the validation message for a bad source, for example:

```json
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "URL Not Allowed: host '127.0.0.1' resolves to a non-public address"}}
```

A missing `source` is rejected by the SDK before the server runs, with code `0` and the message `Missing required arguments: {'source'}`.

## Errors

Tool errors carry the problem title and detail from the [HTTP error table](server.md#errors), prefixed by the SDK:

```text
Error executing tool compare: No Text: No text could be extracted from the input.
Error executing tool analyze: URL Not Allowed: host '127.0.0.1' resolves to a non-public address
Error executing tool analyze: Value error, provide exactly one of 'text' or 'url'
```

Arguments that do not match the tool's schema (a missing `b` for `compare`, a bad `provider`, `max_pages` below 1) fail in the SDK before the tool runs.
Their text is the pydantic validation report after the same prefix:

```text
Error executing tool analyze: 1 validation error for analyzeArguments
max_pages
  Input should be greater than or equal to 1 [type=greater_than_equal, input_value=0, input_type=int]
    For further information visit https://errors.pydantic.dev/...
```

`analyze_file` adds `File Not Found: No such file: <path>` for a missing file.

## stdio

```sh
stylometry --mcp
```

The process reads JSON-RPC from stdin and writes to stdout.
Provider keys for `llm` come from the environment of that process.
`STYLOMETRY_API_KEY` does not apply, because only the launching client can talk to it.
`ALLOW_URL` and `MAX_PAGES_CAP` do apply.

On start it logs one line to stderr with the version, tools, and prompts.
Started by hand in a terminal, it also explains that MCP clients normally launch it themselves.
Ctrl+C stops it at once with exit code 130.
The process also exits when the client closes stdin.

### Claude Code

```sh
claude mcp add stylometry -- /path/to/stylometry --mcp
```

With a provider key for the `llm` option:

```sh
claude mcp add stylometry -e ANTHROPIC_API_KEY=sk-... -- /path/to/stylometry --mcp
```

From a source checkout, run the module with the virtualenv's Python:

```sh
claude mcp add stylometry -e PYTHONPATH=/abs/path/to/stylometry/src -- /abs/path/to/stylometry/.venv/bin/python -m stylometry.cli --mcp
```

### Claude Desktop

Add the server to `claude_desktop_config.json` and restart Claude Desktop:

```json
{
  "mcpServers": {
    "stylometry": {
      "command": "/path/to/stylometry",
      "args": ["--mcp"],
      "env": {"ANTHROPIC_API_KEY": "sk-..."}
    }
  }
}
```

Leave out `env` if you do not use the `llm` option.

The Docker image works too.
Keep `-i`, because stdio needs an open stdin:

```json
{
  "mcpServers": {
    "stylometry": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "stylometry", "--mcp"]
    }
  }
}
```

In a container, `analyze_file` only sees the container's file system.
Mount the folders you want to analyze, for example `"-v", "/home/me/books:/books:ro"`, and pass paths under `/books`.

## Streamable HTTP

The [HTTP server](server.md) serves MCP at `/mcp`.
It runs in stateless mode with plain JSON responses (no server-sent events), so every request stands alone and it works on a VPS and on Lambda alike.

`/mcp` shares the HTTP server's protections:
- the `STYLOMETRY_API_KEY` bearer check, with a `401` Problem Details response on failure,
- the `MAX_BODY_BYTES` limit,
- the URL guard, `ALLOW_URL` and `MAX_PAGES_CAP`,
- the provider keys from the server's environment for `llm`.

It does not check the `Host` header (the SDK's DNS-rebinding protection is off), so set the key whenever the server is reachable beyond localhost.

### Claude Code

```sh
claude mcp add --transport http stylometry https://example.com/mcp --header "Authorization: Bearer $STYLOMETRY_API_KEY"
```

Leave out `--header` if the server has no key set.

### Claude Desktop

`claude_desktop_config.json` only starts local commands.
Either add the server as a custom connector in the app's settings, or bridge to it with [`mcp-remote`](https://www.npmjs.com/package/mcp-remote):

```json
{
  "mcpServers": {
    "stylometry": {
      "command": "npx",
      "args": ["mcp-remote", "https://example.com/mcp", "--header", "Authorization:${AUTH_HEADER}"],
      "env": {"AUTH_HEADER": "Bearer changeme"}
    }
  }
}
```

### Raw requests

Any HTTP client can call `/mcp` directly.
Only `POST` is supported.
The `Accept` header must allow `application/json`; `application/*` and `*/*` also pass.
Sending `Accept: application/json, text/event-stream` is still a good idea, because the MCP spec asks clients to list both, but responses are always JSON.
The body must be sent as `Content-Type: application/json`.
No `initialize` call is needed first, because the endpoint is stateless.

```sh
curl -s localhost:8080/mcp -H "Authorization: Bearer $STYLOMETRY_API_KEY" \
  -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
       "params": {"name": "analyze", "arguments": {"text": "I walked home. It was late."}}}'
```

The response, shortened:

```text
{"jsonrpc": "2.0", "id": 1, "result": {
  "content": [{"text": "{\n  \"source\": \"text\",\n  \"sentence_count\": 2, ...}", "type": "text"}],
  "isError": false,
  "structuredContent": {"source": "text", "sentence_count": 2, "quantitative": {...}, "qualitative": {...}}}}
```

`tools/list`, `prompts/list` and `prompts/get` work the same way.

Before the request reaches the MCP SDK, `/mcp` checks it in this order and answers with [Problem Details](server.md#errors) on failure:

| Check | Status | `type` slug |
|---|---|---|
| Bearer token, if `STYLOMETRY_API_KEY` is set | 401 | `unauthorized` |
| Method is `POST` (the response carries `Allow: POST`) | 405 | `method-not-allowed` |
| `Accept` allows `application/json` | 406 | `not-acceptable` |
| `Content-Type` is `application/json` | 415 | `unsupported-media-type` |

A `GET` does not open a server-sent event stream; it gets the `405` like any other method except `POST`.
A `POST` that accepts only `text/event-stream` gets this response:

```text
HTTP/1.1 406 Not Acceptable
content-type: application/problem+json

{"type":"urn:stylometry:problem:not-acceptable","title":"Not Acceptable","status":406,"detail":"The client must accept application/json.","instance":"/mcp"}
```
