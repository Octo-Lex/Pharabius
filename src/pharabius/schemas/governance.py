"""Governance schema — controls Markdown presentation and handoff policy only.

Separate from config.yaml:
  config.yaml     → scanner/runtime settings
  governance.yaml → output style, handoff policy, template overrides
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ReviewConfig(BaseModel):
    """Review requirements for handoff output."""

    require_evidence_review: bool = True
    require_business_impact_review: bool = True
    review_checklist: bool = True


class HandoffConfig(BaseModel):
    """Handoff summary customization."""

    include_escalation_guide: bool = True
    include_triage_guide: bool = True
    max_work_packages: int = 10


class TemplateConfig(BaseModel):
    """Template override settings."""

    override_dir: str = ""


class GovernanceSafety(BaseModel):
    """Safety invariants — read-only documentation.

    These are enforced by the engine regardless of what this file says.
    """

    no_finding_suppression: bool = True
    no_severity_escalation: bool = True
    no_evidence_id_changes: bool = True
    no_canonical_json_mutation: bool = True
    no_ai_canonical_mutation: bool = True
    no_remediation_execution: bool = True


class GovernanceConfig(BaseModel):
    """Root governance model.

    Controls how findings are presented, not what findings are generated.
    """

    preset: str = "default"
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    handoff: HandoffConfig = Field(default_factory=HandoffConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    safety: GovernanceSafety = Field(default_factory=GovernanceSafety)

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def _warn_unknown_keys(self) -> GovernanceConfig:
        # This runs after parsing; extra keys are already ignored.
        # The loader handles warning for unknown top-level keys.
        return self
