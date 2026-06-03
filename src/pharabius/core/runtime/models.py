"""Runtime evidence internal representation.

Canonical models for runtime evidence, constraints, conflicts, and policy.
All runtime parsing and analysis flows through these types.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────


class RuntimeEcosystem(str, Enum):
    PYTHON = "Python"
    NODE = "Node.js"
    RUBY = "Ruby"
    JAVA = "Java"
    GO = "Go"
    RUST = "Rust"
    DOTNET = ".NET"
    PHP = "PHP"


class RuntimeConstraintKind(str, Enum):
    EXACT = "exact"
    RANGE = "range"
    UNPINNED = "unpinned"
    MISSING = "missing"
    UNKNOWN = "unknown"


class RuntimeSourceType(str, Enum):
    VERSION_FILE = "version_file"
    TOOL_VERSIONS = "tool_versions"
    MANIFEST = "manifest"
    CONTAINER = "container"
    CI = "ci"


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RuntimeConflictKind(str, Enum):
    EXACT_EXACT_MISMATCH = "exact_vs_exact_disagreement"
    RANGE_EXCLUDES_EXACT = "range_excludes_exact"
    DOCKERFILE_DIFFERS = "dockerfile_differs_from_manifest"
    CI_DIFFERS = "ci_differs_from_project_pin"


class RuntimeSignalClassification(str, Enum):
    FINDING = "finding"
    ADVISORY = "advisory"
    INFORMATIONAL = "informational"


# ── Data models ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class RuntimeConstraint:
    """A parsed runtime version constraint."""

    kind: RuntimeConstraintKind
    value: str | None = None
    lower_bound: str | None = None
    upper_bound: str | None = None
    raw: str | None = None


@dataclass(frozen=True)
class RuntimeEvidence:
    """Canonical internal representation of a runtime version declaration.

    Produced by ecosystem parsers. Consumed by conflict detection,
    policy classification, and the detector (which converts to EvidenceItem).
    """

    runtime_evidence_id: str
    ecosystem: RuntimeEcosystem
    runtime_name: str
    constraint: RuntimeConstraint
    source_type: RuntimeSourceType
    source_path: str
    source_detail: str | None = None
    confidence: Confidence = Confidence.HIGH
    raw_version: str | None = None


@dataclass(frozen=True)
class RuntimeConflictGroup:
    """A group of contradictory runtime evidence for a single runtime."""

    ecosystem: RuntimeEcosystem
    runtime_name: str
    conflict_kind: RuntimeConflictKind
    evidence: list[RuntimeEvidence]
    explanation: str


@dataclass(frozen=True)
class RuntimeSignalAction:
    """Policy decision for a runtime signal."""

    classification: RuntimeSignalClassification
    issue_type: str  # "technical_debt" or "advisory"
    severity: Severity
    confidence: Confidence
    category: str  # "TD-DEP"


@dataclass(frozen=True)
class RuntimeEvidenceSummary:
    """Prepared summary for reporting — rendering only, no re-analysis."""

    ecosystems_detected: list[RuntimeEcosystem]
    ecosystems_with_pins: list[RuntimeEcosystem]
    ecosystems_missing_pins: list[RuntimeEcosystem]
    runtime_conflicts: int
    runtime_advisories: int
    runtime_findings: int
