"""Signal governance models.

Platform-level signal representation. GovernedSignal is the policy result
produced after evidence interpretation — it is NOT a replacement for
domain-specific evidence models (RuntimeEvidence, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SignalDisposition(StrEnum):
    """What should the platform do with this signal?"""

    FINDING = "finding"
    ADVISORY = "advisory"
    INFORMATIONAL = "informational"
    SUPPRESSED = "suppressed"


class SignalFamily(StrEnum):
    """Which evidence domain produced this signal?"""

    RUNTIME = "runtime"
    DEPENDENCY = "dependency"
    TEST = "test"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    BUILD = "build"
    OBSERVABILITY = "observability"
    CONFIGURATION = "configuration"
    PROCESS = "process"


@dataclass(frozen=True)
class GovernedSignal:
    """Platform-level governed signal.

    Produced by family-specific adapters after evidence interpretation.
    Consumed by analyzer, run-history, and reporter.

    Important:
        GovernedSignal is not a replacement for EvidenceItem or
        domain-specific IRs. It is the policy result produced after
        evidence interpretation.
    """

    signal_id: str
    family: SignalFamily
    kind: str
    disposition: SignalDisposition
    category: str
    severity: str
    confidence: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    title: str
    summary: str
    explanation: str
    metadata: dict[str, Any]


def make_signal_id(family: str, kind: str, evidence_ids: list[str]) -> str:
    """Deterministic signal ID from family, kind, and evidence IDs."""
    import hashlib

    payload = f"{family}:{kind}:{':'.join(sorted(evidence_ids))}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return f"SIG-{family.upper()}-{digest}"
