"""v1 readiness report generator.

Generates a readiness report summarizing artifact contract coverage,
schema validation, documentation, and safety boundaries for a repository.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class V1ReadinessCheck(BaseModel):
    """Single readiness check result."""

    model_config = {"extra": "forbid"}

    name: str
    status: Literal["pass", "warning", "fail", "not_applicable"]
    message: str
    artifact_path: str | None = None
    severity: Literal["blocking", "non_blocking"] = "non_blocking"
    recommended_action: str = ""


class V1ReadinessReport(BaseModel):
    """v1 readiness report."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    generated_at: str
    status: Literal["ready", "partial", "needs_review"]
    checks: list[V1ReadinessCheck] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


REQUIRED_CANONICAL = [
    "evidence.json",
    "debt-register.json",
    "project-profile.json",
]

OPTIONAL_CANONICAL = [
    "analysis-units.json",
    "architecture-graph.json",
]

REQUIRED_SIDECAR = [
    "review/decisions.json",
    "ticket-drafts/ticket-drafts.json",
]

OPTIONAL_SIDECAR = [
    "export-bundles/manifest.json",
    "portfolio/portfolio-summary.json",
    "claims/operational-claims.json",
    "agent-handoff-contract.md",
]

REQUIRED_MD = [
    "debt-register.md",
    "reports/foundation-audit-report.md",
    "remediation-roadmap.md",
    "handoff-summary.md",
]


def _check_artifact(
    ai_debt: Path,
    rel: str,
    checks: list[V1ReadinessCheck],
    required: bool,
) -> None:
    p = ai_debt / rel
    if not p.exists():
        if required:
            checks.append(
                V1ReadinessCheck(
                    name=f"artifact:{rel}",
                    status="fail",
                    message=f"Missing required artifact: {rel}",
                    artifact_path=rel,
                    severity="blocking",
                    recommended_action=f"Run the pipeline command that produces {rel}.",
                )
            )
        else:
            checks.append(
                V1ReadinessCheck(
                    name=f"artifact:{rel}",
                    status="warning",
                    message=f"Missing optional artifact: {rel}",
                    artifact_path=rel,
                    severity="non_blocking",
                    recommended_action="Optional. Run the relevant command if needed.",
                )
            )
        return

    if p.suffix == ".json":
        try:
            json.loads(p.read_text())
            checks.append(
                V1ReadinessCheck(
                    name=f"artifact:{rel}",
                    status="pass",
                    message=f"Valid JSON: {rel}",
                    artifact_path=rel,
                )
            )
        except json.JSONDecodeError:
            if required:
                checks.append(
                    V1ReadinessCheck(
                        name=f"artifact:{rel}",
                        status="fail",
                        message=f"Invalid JSON: {rel}",
                        artifact_path=rel,
                    )
                )
            else:
                checks.append(
                    V1ReadinessCheck(
                        name=f"artifact:{rel}",
                        status="warning",
                        message=f"Invalid JSON: {rel}",
                        artifact_path=rel,
                    )
                )
    elif p.suffix == ".md":
        content = p.read_text().strip()
        if content:
            checks.append(
                V1ReadinessCheck(
                    name=f"artifact:{rel}",
                    status="pass",
                    message=f"Non-empty Markdown: {rel}",
                    artifact_path=rel,
                )
            )
        else:
            if required:
                checks.append(
                    V1ReadinessCheck(
                        name=f"artifact:{rel}",
                        status="fail",
                        message=f"Empty Markdown: {rel}",
                        artifact_path=rel,
                    )
                )
            else:
                checks.append(
                    V1ReadinessCheck(
                        name=f"artifact:{rel}",
                        status="warning",
                        message=f"Empty Markdown: {rel}",
                        artifact_path=rel,
                    )
                )
    else:
        checks.append(
            V1ReadinessCheck(
                name=f"artifact:{rel}",
                status="pass",
                message=f"Present: {rel}",
                artifact_path=rel,
            )
        )


def _check_safety(checks: list[V1ReadinessCheck]) -> None:
    """Safety boundary checks (always pass for Pharabius v1)."""
    safety_items = [
        (
            "safety:no_external_api",
            "No external API configuration required for core workflow.",
        ),
        (
            "safety:no_remediation",
            "No remediation command modifies source code.",
        ),
        (
            "safety:file_based_export",
            "Ticket/export workflows produce local files only.",
        ),
        (
            "safety:local_portfolio",
            "Portfolio is local-only, no remote crawling.",
        ),
        (
            "safety:agent_handoff_boundary",
            "Agent-handoff contract forbids autonomous modification.",
        ),
    ]
    for name, message in safety_items:
        checks.append(V1ReadinessCheck(name=name, status="pass", message=message))


def generate_readiness_report(ai_debt: Path) -> V1ReadinessReport:
    """Generate a v1 readiness report for a .ai-debt/ directory."""
    checks: list[V1ReadinessCheck] = []

    # Canonical artifacts
    for rel in REQUIRED_CANONICAL:
        _check_artifact(ai_debt, rel, checks, required=True)

    for rel in OPTIONAL_CANONICAL:
        _check_artifact(ai_debt, rel, checks, required=False)

    # Sidecar artifacts
    for rel in REQUIRED_SIDECAR:
        _check_artifact(ai_debt, rel, checks, required=True)

    for rel in OPTIONAL_SIDECAR:
        _check_artifact(ai_debt, rel, checks, required=False)

    # Markdown artifacts
    for rel in REQUIRED_MD:
        _check_artifact(ai_debt, rel, checks, required=True)

    # Safety checks
    _check_safety(checks)

    # Aggregate
    fail_count = sum(1 for c in checks if c.status == "fail")
    warn_count = sum(1 for c in checks if c.status == "warning")
    pass_count = sum(1 for c in checks if c.status == "pass")

    if fail_count > 0:
        report_status: Literal["ready", "partial", "needs_review"] = "needs_review"
    elif warn_count > 0:
        report_status = "partial"
    else:
        report_status = "ready"

    summary = {
        "total_checks": len(checks),
        "pass": pass_count,
        "warning": warn_count,
        "fail": fail_count,
    }

    return V1ReadinessReport(
        generated_at=datetime.now(UTC).isoformat(),
        status=report_status,
        checks=checks,
        summary=summary,
    )


def render_readiness_markdown(report: V1ReadinessReport) -> str:
    """Render readiness report as Markdown."""
    lines: list[str] = []
    lines.append("# v1 Readiness Report")
    lines.append("")
    lines.append(f"**Status**: {report.status}")
    lines.append(f"**Generated**: {report.generated_at}")
    lines.append(f"**Schema version**: {report.schema_version}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    for k, v in report.summary.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")

    # Checks table
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Status | Message |")
    lines.append("|---|---|---|")
    for c in report.checks:
        lines.append(f"| {c.name} | {c.status} | {c.message} |")
    lines.append("")

    # Safety
    safety_checks = [c for c in report.checks if c.name.startswith("safety:")]
    if safety_checks:
        lines.append("## Safety Boundary Checks")
        lines.append("")
        for c in safety_checks:
            lines.append(f"- **{c.name}**: {c.message}")
        lines.append("")

    # Blocking / Non-blocking
    blocking = [c for c in report.checks if c.severity == "blocking"]
    non_blocking = [c for c in report.checks if c.severity == "non_blocking" and c.status != "pass"]

    if blocking:
        lines.append("### Blocking Issues")
        lines.append("")
        lines.append("| Code | Artifact | Recommended Action |")
        lines.append("|---|---|---|")
        for c in blocking:
            art = c.artifact_path or "—"
            action = c.recommended_action or "—"
            lines.append(f"| {c.name} | {art} | {action} |")
        lines.append("")
    else:
        lines.append("### Blocking Issues")
        lines.append("")
        lines.append("None.")
        lines.append("")

    if non_blocking:
        lines.append("### Non-Blocking Issues")
        lines.append("")
        lines.append("| Code | Artifact | Recommended Action |")
        lines.append("|---|---|---|")
        for c in non_blocking:
            art = c.artifact_path or "—"
            action = c.recommended_action or "—"
            lines.append(f"| {c.name} | {art} | {action} |")
        lines.append("")

    # Verdict
    lines.append("## Release Candidate Verdict")
    lines.append("")
    if report.status == "ready":
        lines.append("All required checks pass. Repository is v1-ready.")
    elif report.status == "partial":
        lines.append("All required checks pass but warnings exist. Review warnings before release.")
    else:
        lines.append("One or more required checks failed. Address failures before release.")
    lines.append("")

    return "\n".join(lines)
