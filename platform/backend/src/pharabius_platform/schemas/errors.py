"""Platform error response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Standard error response envelope."""

    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    request_id: str = ""
