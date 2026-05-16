from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def generate_run_id() -> str:
    now = datetime.now(UTC)
    return f"RUN-{now.strftime('%Y%m%d-%H%M%S')}"


class RunSummary(BaseModel):
    evidence_count: int = 0
    finding_count: int = 0
    work_package_count: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0


class RunMetadata(BaseModel):
    run_id: str = Field(default_factory=generate_run_id)
    timestamp: str = Field(default_factory=utc_now_iso)
    repository: str = ""
    commit: str = ""
    branch: str = ""
    tool_version: str = "0.1.0"
    analysis_mode: str = "deterministic-no-ai"
    commands_run: list[str] = Field(default_factory=list)
    files_written: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: RunSummary = Field(default_factory=RunSummary)
