from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import version as _pkg_version

from pydantic import BaseModel, Field


def _get_version() -> str:
    try:
        return _pkg_version("pharabius")
    except Exception:
        return "0.0.0"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def generate_run_id() -> str:
    now = datetime.now(UTC)
    return f"RUN-{now.strftime('%Y%m%d-%H%M%S')}"


class RunSummary(BaseModel):
    evidence_count: int = 0
    finding_count: int = 0
    work_package_count: int = 0
    analysis_unit_count: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0


class RunMetadata(BaseModel):
    schema_version: str = "1.0"
    run_id: str = Field(default_factory=generate_run_id)
    timestamp: str = Field(default_factory=utc_now_iso)
    repository: str = ""
    commit: str = ""
    branch: str = ""
    tool_version: str = Field(default_factory=_get_version)
    analysis_mode: str = "deterministic-no-ai"
    commands_run: list[str] = Field(default_factory=list)
    files_written: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: RunSummary = Field(default_factory=RunSummary)
