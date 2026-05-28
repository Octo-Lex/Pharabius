"""Pharabius platform FastAPI application."""

from __future__ import annotations

import os
import typing
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from pharabius_platform.api import all_routers
from pharabius_platform.middleware.errors import register_error_handlers


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Pharabius Platform",
        version="2.3.0",
        description="Hosted Pharabius artifact visibility and CI ingestion.",
    )

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(
        request: Request, call_next: typing.Callable[..., typing.Any]
    ) -> typing.Any:
        request.state.request_id = str(uuid.uuid4())[:12]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # Error handlers
    register_error_handlers(app)

    # Routers
    for router in all_routers:
        app.include_router(router)

    # Startup: initialize database
    @app.on_event("startup")
    async def startup() -> None:
        from pharabius_platform.db import init_db

        database_url = os.environ.get("DATABASE_URL", "")
        if database_url:
            init_db(database_url)

    return app


app = create_app()
