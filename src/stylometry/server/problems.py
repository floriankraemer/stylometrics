"""RFC 9457 Problem Details responses."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("stylometry.server")
MEDIA_TYPE = "application/problem+json"
TYPE_PREFIX = "urn:stylometry:problem:"

_HTTP_SLUGS = {401: "unauthorized", 404: "not-found", 405: "method-not-allowed", 413: "payload-too-large"}


class Problem(Exception):
    def __init__(self, status: int, slug: str, title: str, detail: str | None = None, headers: dict | None = None,
                 **extensions):
        self.status, self.slug, self.title, self.detail = status, slug, title, detail
        self.headers, self.extensions = headers, extensions


def response(request: Request, status: int, slug: str, title: str, detail: str | None = None,
             headers: dict | None = None, **extensions) -> JSONResponse:
    body = {"type": TYPE_PREFIX + slug, "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body["instance"] = request.url.path
    body.update(extensions)
    return JSONResponse(body, status_code=status, media_type=MEDIA_TYPE, headers=headers)


def install(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def _problem(request: Request, exc: Problem):
        return response(request, exc.status, exc.slug, exc.title, exc.detail, exc.headers, **exc.extensions)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        slug = _HTTP_SLUGS.get(exc.status_code, "http-error")
        title = {404: "Not Found", 405: "Method Not Allowed"}.get(exc.status_code, "HTTP Error")
        return response(request, exc.status_code, slug, title, str(exc.detail), getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
        return response(request, 422, "validation-error", "Invalid request", "The request did not validate.",
                        errors=errors)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error on %s", request.url.path)
        return response(request, 500, "internal-error", "Internal Server Error",
                        "The server failed to process the request.")
