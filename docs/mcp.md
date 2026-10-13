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
If the analysis fails, the client gets a JSON-RPC error such as `Error rendering prompt write_like: URL Not Allowed: ...`.

## Errors

Tool errors carry the problem title and detail from the [HTTP error table](server.md#errors), prefixed by the SDK:

```text
Error executing tool compare: No Text: No text could be extracted from the input.
Error executing tool analyze: Value error, provide exactly one of 'text' or 'url'
```

Argument validation errors (missing source, bad `provider`, `max_pages` below 1) list the validation messages instead.
`analyze_file` adds `File Not Found: No such file: <path>` for a missing file.

## stdio

```sh
stylometry --mcp
```

The process reads JSON-RPC from stdin and writes to stdout.
Provider keys for `llm` come from the environment of that process.
`STYLOMETRY_API_KEY` does not apply, because only the launching client can talk to it.
`ALLOW_URL` and `MAX_PAGES_CAP` do apply.

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
Send `Accept: application/json, text/event-stream`, even though responses are always JSON.
Without both types the SDK answers `406` with a JSON-RPC error (not Problem Details).
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
  "content": [{"type": "text", "text": "{\"source\": \"text\", \"sentence_count\": 2, ...}"}],
  "structuredContent": {"source": "text", "sentence_count": 2, "quantitative": {...}, "qualitative": {...}},
  "isError": false}}
```

`tools/list`, `prompts/list` and `prompts/get` work the same way.
