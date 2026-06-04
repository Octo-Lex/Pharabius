"""Artifact contract drift checks.

Compares generated .ai-debt/ artifacts against the documented v1 artifact
contract. Detects missing, undocumented, and mismatched artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ArtifactContractDriftIssue(BaseModel):
    """Single drift issue."""

    model_config = {"extra": "forbid"}

    severity: Literal["error", "warning"]
    code: str
    artifact_path: str | None = None
    schema_name: str | None = None
    message: str


class ArtifactContractDriftReport(BaseModel):
    """Drift check report."""

    model_config = {"extra": "forbid"}

    total_issues: int
    errors: int
    warnings: int
    status: Literal["pass", "pass_with_warnings", "fail"]
    issues: list[ArtifactContractDriftIssue] = Field(default_factory=list)


# Required artifacts in the v1 contract
REQUIRED_ARTIFACTS = [
    "evidence.json",
    "debt-register.json",
    "project-profile.json",
    "debt-register.md",
    "reports/foundation-audit-report.md",
    "remediation-roadmap.md",
    "handoff-summary.md",
]

# Optional artifacts
OPTIONAL_ARTIFACTS = [
    "analysis-units.json",
    "architecture-graph.json",
    "review/decisions.json",
    "ticket-drafts/ticket-drafts.json",
    "portfolio/portfolio-summary.json",
    "portfolio/repository-index.json",
    "portfolio/portfolio-summary.md",
    "portfolio/validation-rollup.md",
    "claims/operational-claims.json",
    "claims/operational-claims.md",
    "claims/confidence-report.md",
    "claims/gaps.md",
    "claims/questions.md",
    "agent-handoff-contract.md",
    "traceability/evidence-finding-matrix.md",
    "traceability/finding-claim-matrix.md",
    "traceability/claim-workpackage-matrix.md",
]

# Known generated artifact directories (for detecting undocumented)
KNOWN_DIRS = {
    "evidence.json",
    "debt-register.json",
    "debt-register.md",
    "project-profile.json",
    "analysis-units.json",
    "architecture-graph.json",
    "runs",
    "reports",
    "work-packages",
    "review",
    "ticket-drafts",
    "export-bundles",
    "exports/governance-summary.json",
    "portfolio",
    "claims",
    "traceability",
    "ai",
    "config.yaml",
    "governance.yaml",
    "agent-handoff-contract.md",
    "handoff-summary.md",
    "remediation-roadmap.md",
    "test-health.md",
}


def check_artifact_contract_drift(ai_debt: Path) -> ArtifactContractDriftReport:
    """Check generated artifacts against the v1 contract."""
    issues: list[ArtifactContractDriftIssue] = []

    if not ai_debt.exists():
        return ArtifactContractDriftReport(
            total_issues=1,
            errors=1,
            warnings=0,
            status="fail",
            issues=[
                ArtifactContractDriftIssue(
                    severity="error",
                    code="missing_ai_debt_dir",
                    message=f".ai-debt/ directory not found: {ai_debt}",
                )
            ],
        )

    # Check required artifacts
    for rel in REQUIRED_ARTIFACTS:
        p = ai_debt / rel
        if not p.exists():
            issues.append(
                ArtifactContractDriftIssue(
                    severity="error",
                    code="required_artifact_missing",
                    artifact_path=rel,
                    message=f"Required artifact missing: {rel}",
                )
            )

    # Check optional artifacts (warning only)
    for rel in OPTIONAL_ARTIFACTS:
        p = ai_debt / rel
        if not p.exists():
            issues.append(
                ArtifactContractDriftIssue(
                    severity="warning",
                    code="optional_artifact_missing",
                    artifact_path=rel,
                    message=f"Optional artifact missing: {rel}",
                )
            )

    # Check for undocumented top-level artifacts
    if ai_debt.is_dir():
        for entry in ai_debt.iterdir():
            name = entry.name
            if name not in KNOWN_DIRS and not name.startswith("."):
                issues.append(
                    ArtifactContractDriftIssue(
                        severity="warning",
                        code="undocumented_artifact",
                        artifact_path=name,
                        message=f"Undocumented artifact: {name}",
                    )
                )

    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")

    if errors > 0:
        status: Literal["pass", "pass_with_warnings", "fail"] = "fail"
    elif warnings > 0:
        status = "pass_with_warnings"
    else:
        status = "pass"

    return ArtifactContractDriftReport(
        total_issues=len(issues),
        errors=errors,
        warnings=warnings,
        status=status,
        issues=issues,
    )
