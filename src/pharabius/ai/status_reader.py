"""Read-only AI sidecar status reader.

Reads .ai-debt/ai/ sidecar artifacts and produces a human-readable summary.
Does not create, modify, or delete any files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.schemas.ai_enrichment import AIEnrichmentReport


def _load_json_safe(path: Path) -> dict[str, Any] | None:
    """Load JSON file, returning None on any failure."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


class SidecarStatus:
    """Structured summary of AI sidecar state."""

    def __init__(
        self,
        *,
        sidecar_present: bool = False,
        provider: str = "",
        model: str = "",
        generated_at: str = "",
        findings_selected: int = 0,
        enrichments_accepted: int = 0,
        enrichments_rejected: int = 0,
        evidence_referenced: int = 0,
        evidence_omitted: int = 0,
        canonical_artifacts_modified: bool = False,
        error_message: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
        provider_error_code: str = "",
    ) -> None:
        self.sidecar_present = sidecar_present
        self.provider = provider
        self.model = model
        self.generated_at = generated_at
        self.findings_selected = findings_selected
        self.enrichments_accepted = enrichments_accepted
        self.enrichments_rejected = enrichments_rejected
        self.evidence_referenced = evidence_referenced
        self.evidence_omitted = evidence_omitted
        self.canonical_artifacts_modified = canonical_artifacts_modified
        self.error_message = error_message
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms
        self.provider_error_code = provider_error_code

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON output."""
        return {
            "sidecar_present": self.sidecar_present,
            "provider": self.provider,
            "model": self.model,
            "generated_at": self.generated_at,
            "findings_selected": self.findings_selected,
            "enrichments_accepted": self.enrichments_accepted,
            "enrichments_rejected": self.enrichments_rejected,
            "evidence_referenced": self.evidence_referenced,
            "evidence_omitted": self.evidence_omitted,
            "canonical_artifacts_modified": self.canonical_artifacts_modified,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "provider_error_code": self.provider_error_code,
            "status": "review_recommended" if self.sidecar_present else "no_sidecar",
        }

    def to_human(self) -> str:
        """Convert to human-readable summary."""
        lines = [
            "AI Sidecar Status",
            "",
            f"  Provider:              {self.provider}",
            f"  Model:                 {self.model}",
            f"  Generated:             {self.generated_at}",
            "",
            f"  Findings selected:     {self.findings_selected}",
            f"  Enrichments accepted:  {self.enrichments_accepted}",
            f"  Enrichments rejected:  {self.enrichments_rejected}",
            f"  Evidence referenced:   {self.evidence_referenced}",
            f"  Evidence omitted:      {self.evidence_omitted}",
        ]
        if self.prompt_tokens > 0 or self.completion_tokens > 0:
            total = self.prompt_tokens + self.completion_tokens
            lines.append(
                f"  Token usage:           {self.prompt_tokens} prompt + "
                f"{self.completion_tokens} completion = {total} total"
            )
        if self.latency_ms > 0:
            lines.append(f"  Latency:               {self.latency_ms} ms")
        if self.provider_error_code:
            lines.append(f"  Last provider error:   {self.provider_error_code}")
        lines.extend(
            [
                "",
                "  Canonical artifacts:   not modified (by design)",
            ]
        )
        return "\n".join(lines)


def read_ai_status(repository_root: Path) -> tuple[SidecarStatus, int]:
    """Read AI sidecar status.

    Returns (SidecarStatus, exit_code).
    exit_code: 0 = success, 1 = error.
    """
    ai_dir = repository_root / ".ai-debt" / "ai"
    report_path = ai_dir / "enrichment-report.json"

    # No .ai-debt/ai/ directory at all
    if not ai_dir.exists():
        return (
            SidecarStatus(
                sidecar_present=False,
                error_message="No AI sidecar found. Run 'ai-debt enrich --provider mock' first.",
            ),
            0,
        )

    # ai/ exists but report is missing
    if not report_path.exists():
        return (
            SidecarStatus(
                sidecar_present=False,
                error_message="Sidecar directory exists but enrichment-report.json is missing.",
            ),
            1,
        )

    # Load and parse report
    raw = _load_json_safe(report_path)
    if raw is None:
        return (
            SidecarStatus(
                sidecar_present=False,
                error_message="AI sidecar is corrupted or unreadable.",
            ),
            1,
        )

    try:
        report = AIEnrichmentReport.model_validate(raw)
    except Exception as exc:
        return (
            SidecarStatus(
                sidecar_present=False,
                error_message=f"AI sidecar is corrupted or unreadable: {exc}",
            ),
            1,
        )

    # Count evidence referenced across all enrichments
    evidence_ids: set[str] = set()
    for enc in report.enrichments:
        evidence_ids.update(enc.evidence_ids)

    # Count evidence omitted from context summary
    omitted = report.context_summary.evidence_items_omitted

    # Get provider error code from last rejection if any
    last_error_code = ""
    if report.rejections and hasattr(report.usage, "provider_error_code"):
        last_error_code = report.usage.provider_error_code

    status = SidecarStatus(
        sidecar_present=True,
        provider=report.provider,
        model=report.model,
        generated_at=report.generated_at,
        findings_selected=report.usage.items_processed,
        enrichments_accepted=len(report.enrichments),
        enrichments_rejected=len(report.rejections),
        evidence_referenced=len(evidence_ids),
        evidence_omitted=omitted,
        canonical_artifacts_modified=False,
        prompt_tokens=getattr(report.usage, "prompt_tokens", 0),
        completion_tokens=getattr(report.usage, "completion_tokens", 0),
        latency_ms=getattr(report.usage, "latency_ms", 0),
        provider_error_code=last_error_code,
    )

    return status, 0
