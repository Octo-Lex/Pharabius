"""Bundle validation against the Pharabius artifact contract."""

from __future__ import annotations

from pathlib import Path

# Minimal set of artifacts expected in a valid bundle
REQUIRED_ARTIFACTS = [
    "evidence.json",
    "debt-register.json",
    "project-profile.json",
]

OPTIONAL_ARTIFACTS = [
    "analysis-units.json",
    "architecture-graph.json",
    "review/decisions.json",
    "ticket-drafts/ticket-drafts.json",
    "portfolio/portfolio-summary.json",
    "claims/operational-claims.json",
]


class ValidationResult:
    """Result of bundle validation."""

    def __init__(self) -> None:
        self.is_valid: bool = True
        self.missing_required: list[str] = []
        self.found_required: list[str] = []
        self.found_optional: list[str] = []
        self.extra_files: list[str] = []

    def to_dict(self) -> dict[str, object]:
        return {
            "is_valid": self.is_valid,
            "missing_required": self.missing_required,
            "found_required": self.found_required,
            "found_optional": self.found_optional,
            "extra_files": self.extra_files,
        }


def validate_bundle(extract_dir: Path) -> ValidationResult:
    """Validate extracted bundle against artifact contract.

    Checks for required artifacts and catalogs what was found.
    """
    result = ValidationResult()

    # Find .ai-debt directory (may be at root or nested)
    ai_debt = _find_ai_debt_dir(extract_dir)
    if ai_debt is None:
        result.is_valid = False
        result.missing_required = list(REQUIRED_ARTIFACTS)
        return result

    all_files = set()
    for p in ai_debt.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(ai_debt)).replace("\\", "/")
            all_files.add(rel)

    # Check required
    for artifact in REQUIRED_ARTIFACTS:
        if artifact in all_files:
            result.found_required.append(artifact)
        else:
            result.is_valid = False
            result.missing_required.append(artifact)

    # Check optional
    for artifact in OPTIONAL_ARTIFACTS:
        if artifact in all_files:
            result.found_optional.append(artifact)

    # Catalog extras
    known = set(REQUIRED_ARTIFACTS) | set(OPTIONAL_ARTIFACTS)
    # Also allow directories and common artifacts
    known_prefixes = (
        "runs/",
        "reports/",
        "work-packages/",
        "export-bundles/",
        "traceability/",
        "ai/",
    )
    for f in all_files:
        if f in known:
            continue
        if f.endswith(".md") and any(f.startswith(p) for p in known_prefixes):
            continue
        if f in (
            "config.yaml",
            "governance.yaml",
            "architecture-policy.yaml",
            "debt-register.md",
            "handoff-summary.md",
            "remediation-roadmap.md",
            "agent-handoff-contract.md",
            "test-health.md",
        ):
            continue
        # Files in known directories
        if any(f.startswith(p) for p in known_prefixes):
            continue
        result.extra_files.append(f)

    return result


def _find_ai_debt_dir(root: Path) -> Path | None:
    """Find the .ai-debt directory in extracted bundle."""
    # Direct .ai-debt/
    if (root / ".ai-debt").is_dir():
        return root / ".ai-debt"

    # Nested (e.g., repo-name/.ai-debt/)
    for child in root.iterdir():
        if child.is_dir() and (child / ".ai-debt").is_dir():
            return child / ".ai-debt"

    # Bundle may be .ai-debt contents directly (no wrapping dir)
    if (root / "evidence.json").exists() and (root / "debt-register.json").exists():
        return root

    return None
