"""HTTP API. VPS: `stylometry --serve --port N`. Lambda: see lambda_handler.py."""
import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Query, Request, UploadFile
from starlette.routing import Route

from stylometry import __version__
from stylometry.server import problems
from stylometry.server.mcp_server import build_mcp
from stylometry.server.problems import Problem
from stylometry.server.service import (AnalyzeRequest, _analyze, _check_include, _check_llm, _load, analyze_request,
                                       int_env)

Include = Annotated[list[str], Query(description="extra renderings: profile_md, clone_prompt")]


class BodyLimit:
    """ASGI middleware: reject bodies over MAX_BODY_BYTES, by Content-Length and by bytes actually received."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = int_env("MAX_BODY_BYTES", 5 * 1024 * 1024)
        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return await self._reject(scope, receive, send, limit)
        seen, too_large = 0, False

        async def counting_receive():
            # raising here would be swallowed by the body parser (-> 400), so end the body and swap the response
            nonlocal seen, too_large
            if too_large:
                return {"type": "http.request", "body": b"", "more_body": False}
            message = await receive()
            seen += len(message.get("body", b""))
            if seen > limit:
                too_large = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def guarded_send(message):
            if not too_large:
                await send(message)

        await self.app(scope, counting_receive, guarded_send)
        if too_large:
            await self._reject(scope, receive, send, limit)

    @staticmethod
    async def _reject(scope, receive, send, limit):
        resp = problems.response(Request(scope), 413, "payload-too-large", "Payload Too Large",
                                 f"The request body exceeds {limit} bytes.")
        await resp(scope, receive, send)


def require_api_key(request: Request) -> None:
    expected = os.environ.get("STYLOMETRY_API_KEY")
    if not expected:
        return
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), expected.encode()):
        raise Problem(401, "unauthorized", "Unauthorized", "A valid bearer token is required.",
                      headers={"WWW-Authenticate": "Bearer"})


class McpEndpoint:
    """ASGI endpoint for /mcp: API-key check, then the MCP Streamable HTTP app that the lifespan currently runs."""

    app = None

    async def __call__(self, scope, receive, send):
        request = Request(scope)
        try:
            require_api_key(request)
        except Problem as p:
            resp = problems.response(request, p.status, p.slug, p.title, p.detail, p.headers)
            return await resp(scope, receive, send)
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    mcp_endpoint = McpEndpoint()

    @asynccontextmanager
    async def lifespan(_app):
        # Built per startup: a session manager can only run once, and Mangum runs the lifespan per Lambda invocation.
        mcp = build_mcp()
        mcp_app = mcp.streamable_http_app()
        async with mcp.session_manager.run():
            mcp_endpoint.app = mcp_app
            yield

    app = FastAPI(title="Stylometry", version=__version__, lifespan=lifespan)
    problems.install(app)
    app.add_middleware(BodyLimit)
    app.router.routes.append(Route("/mcp", endpoint=mcp_endpoint))
    auth = [Depends(require_api_key)]

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": __version__}

    @app.post("/analyze", dependencies=auth)
    def analyze_json(body: AnalyzeRequest, include: Include = []):
        return analyze_request(body, include)

    @app.post("/analyze/file", dependencies=auth)
    def analyze_file(file: UploadFile, name: Annotated[str | None, Form()] = None,
                     llm: Annotated[bool, Form()] = False,
                     provider: Annotated[str, Form(pattern="^(anthropic|openai)$")] = "anthropic",
                     include: Include = []):
        _check_include(include)
        _check_llm(llm, provider)
        filename = Path(file.filename or "upload").name
        # the client-supplied name only contributes its suffix to the temp path
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / f"upload{Path(filename).suffix.lower()}"
            path.write_bytes(file.file.read())
            text = _load(str(path))
        return _analyze(text, name or filename, llm, provider, include)

    return app


app = create_app()
