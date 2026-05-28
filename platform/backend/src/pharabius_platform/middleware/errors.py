"""Standard error envelope middleware."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _request_id() -> str:
    return str(uuid.uuid4())[:12]


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors with standard envelope."""
    req_id = getattr(request.state, "request_id", _request_id())
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": str(exc),
                "details": {},
                "request_id": req_id,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors with standard envelope."""
    req_id = getattr(request.state, "request_id", _request_id())
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred.",
                "details": {},
                "request_id": req_id,
            }
        },
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 404 errors with standard envelope."""
    req_id = getattr(request.state, "request_id", _request_id())
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "not_found",
                "message": f"Resource not found: {request.url.path}",
                "details": {},
                "request_id": req_id,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register error handlers on the FastAPI app."""
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle HTTPException with standard envelope."""
    from starlette.exceptions import HTTPException as StarletteHTTPException

    req_id = getattr(request.state, "request_id", _request_id())
    if isinstance(exc, StarletteHTTPException):
        status = exc.status_code
        message = exc.detail
    else:
        status = 500
        message = "An unexpected error occurred."

    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": "http_error",
                "message": str(message),
                "details": {},
                "request_id": req_id,
            }
        },
    )
