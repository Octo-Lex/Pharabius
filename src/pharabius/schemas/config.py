"""Configuration schema for Pharabius.

Safe defaults only. No credentials, no provider SDK config, no consent fields.
Config is read after workspace path is known — it does not relocate `.ai-debt/`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# ── Sub-models ────────────────────────────────────────────────────────────


class ProjectConfig(BaseModel):
    """Project metadata (informational, not behavior-changing)."""

    name: str = ""
    criticality: str = "unknown"
    lifecycle: str = "unknown"


class AnalysisConfig(BaseModel):
    """Analysis behavior settings."""

    mode: str = "baseline"
    include_git_history: bool = False
    max_file_size_kb: int = 500
    exclude_paths: list[str] = Field(default_factory=list)

    @field_validator("max_file_size_kb")
    @classmethod
    def _positive_kb(cls, v: int) -> int:
        if v < 1:
            return 500
        return v


class AIConfig(BaseModel):
    """AI settings. Cannot enable real providers without CLI consent."""

    enabled: bool = False
    provider: str = "disabled"
    require_evidence_ids: bool = True

    @field_validator("provider")
    @classmethod
    def _safe_provider(cls, v: str) -> str:
        # Normalize but do not reject — CLI consent gate is the safety boundary
        return v.strip().lower() if v else "disabled"


class OutputConfig(BaseModel):
    """Output settings. directory is parsed but does not relocate workspace."""

    directory: str = ".ai-debt"
    formats: list[str] = Field(default_factory=lambda: ["markdown", "json"])


class PoliciesConfig(BaseModel):
    """Policy flags. All default to safe/true."""

    no_code_modifications: bool = True
    require_confidence: bool = True
    mark_inferred_business_impact: bool = True


# ── Root config ───────────────────────────────────────────────────────────


class PharabiusConfig(BaseModel):
    """Root configuration model.

    No credential fields exist. No model selection. No provider SDK config.
    CLI flags always override config values.
    """

    model_config = {"extra": "allow"}  # unknown keys → caught by loader

    schema_version: str = "1.0"
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    policies: PoliciesConfig = Field(default_factory=PoliciesConfig)
