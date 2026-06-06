"""Workflow lifecycle governance.

Defines explicit lifecycle states for findings and work packages,
allowed transitions between states, and validation logic.

Design rules:
- Status enums preserve compatibility with existing persisted values.
- Transition validation is pure — no write operations.
- lifecycle-history.json is optional and append-only.
- Inferred lifecycle state is report-only unless explicitly persisted.
- No auto-promotion. No auto-approval. No historical artifact mutation.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# S01 — Finding Lifecycle
# ---------------------------------------------------------------------------


class FindingStatus(enum.StrEnum):
    """Explicit lifecycle states for findings.

    Preserves compatibility with existing status values:
    - "Detected" maps to DETECTED (default in DebtFinding)
    - Review decision statuses map through compatibility table
    """

    DETECTED = "Detected"
    ACKNOWLEDGED = "Acknowledged"
    IN_PROGRESS = "In Progress"
    REMEDIATED = "Remediated"
    VERIFIED = "Verified"
    DEFERRED = "Deferred"
    WONT_FIX = "Won't Fix"


# Compatibility mapping: existing free-text values → FindingStatus
FINDING_STATUS_ALIASES: dict[str, FindingStatus] = {
    # Exact matches (DebtFinding default)
    "Detected": FindingStatus.DETECTED,
    "detected": FindingStatus.DETECTED,
    # Review decision status → lifecycle mapping (report-only inference)
    "accepted": FindingStatus.ACKNOWLEDGED,
    "risk-accepted": FindingStatus.WONT_FIX,
    "rejected": FindingStatus.WONT_FIX,
    "deferred": FindingStatus.DEFERRED,
    "needs-investigation": FindingStatus.ACKNOWLEDGED,
    "duplicate": FindingStatus.WONT_FIX,
    "already-fixed": FindingStatus.REMEDIATED,
    # Verification result status → lifecycle mapping (report-only inference)
    "still_detected": FindingStatus.DETECTED,
    "likely_remediated": FindingStatus.REMEDIATED,
    "evidence_missing": FindingStatus.DETECTED,
    "partially_supported": FindingStatus.DETECTED,
    "stale": FindingStatus.DETECTED,
    "uncertain": FindingStatus.DETECTED,
}

# Allowed transitions: from → set of allowed to
FINDING_TRANSITIONS: dict[FindingStatus, set[FindingStatus]] = {
    FindingStatus.DETECTED: {
        FindingStatus.ACKNOWLEDGED,
        FindingStatus.DEFERRED,
    },
    FindingStatus.ACKNOWLEDGED: {
        FindingStatus.IN_PROGRESS,
        FindingStatus.DEFERRED,
        FindingStatus.WONT_FIX,
    },
    FindingStatus.IN_PROGRESS: {
        FindingStatus.REMEDIATED,
        FindingStatus.WONT_FIX,
        FindingStatus.DEFERRED,
    },
    FindingStatus.DEFERRED: {
        FindingStatus.ACKNOWLEDGED,
    },
    FindingStatus.REMEDIATED: {
        FindingStatus.VERIFIED,
        FindingStatus.DETECTED,  # Regression
    },
    FindingStatus.WONT_FIX: {
        FindingStatus.ACKNOWLEDGED,  # Reopen
    },
    FindingStatus.VERIFIED: {
        FindingStatus.DETECTED,  # Regression
    },
}


# ---------------------------------------------------------------------------
# S02 — Work Package Lifecycle
# ---------------------------------------------------------------------------


class WorkPackageStatus(enum.StrEnum):
    """Explicit lifecycle states for work packages.

    Preserves compatibility with existing status values:
    - "Ready for Product Engineering review" → READY
    - "Ready for review" → READY (test shorthand)
    """

    DRAFT = "Draft"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    VERIFIED = "Verified"
    DEFERRED = "Deferred"
    BLOCKED = "Blocked"


# Compatibility mapping: existing free-text values → WorkPackageStatus
WORK_PACKAGE_STATUS_ALIASES: dict[str, WorkPackageStatus] = {
    # Default from WorkPackage schema
    "Ready for Product Engineering review": WorkPackageStatus.READY,
    "Ready for review": WorkPackageStatus.READY,
    "Ready for PET review": WorkPackageStatus.READY,
    "Ready": WorkPackageStatus.READY,
    # Verification results
    "needs_review": WorkPackageStatus.READY,
    "valid": WorkPackageStatus.VERIFIED,
    "stale": WorkPackageStatus.BLOCKED,
    "orphaned": WorkPackageStatus.BLOCKED,
    # Common free-text values
    "draft": WorkPackageStatus.DRAFT,
    "in_progress": WorkPackageStatus.IN_PROGRESS,
    "completed": WorkPackageStatus.COMPLETED,
    "deferred": WorkPackageStatus.DEFERRED,
    "blocked": WorkPackageStatus.BLOCKED,
}

# Allowed transitions: from → set of allowed to
WORK_PACKAGE_TRANSITIONS: dict[WorkPackageStatus, set[WorkPackageStatus]] = {
    WorkPackageStatus.DRAFT: {
        WorkPackageStatus.READY,
        WorkPackageStatus.DEFERRED,
    },
    WorkPackageStatus.READY: {
        WorkPackageStatus.IN_PROGRESS,
        WorkPackageStatus.DEFERRED,
    },
    WorkPackageStatus.IN_PROGRESS: {
        WorkPackageStatus.COMPLETED,
        WorkPackageStatus.BLOCKED,
        WorkPackageStatus.DEFERRED,
    },
    WorkPackageStatus.COMPLETED: {
        WorkPackageStatus.VERIFIED,
    },
    WorkPackageStatus.DEFERRED: {
        WorkPackageStatus.READY,
    },
    WorkPackageStatus.BLOCKED: {
        WorkPackageStatus.IN_PROGRESS,
        WorkPackageStatus.DEFERRED,
    },
    WorkPackageStatus.VERIFIED: set(),  # Terminal state
}


# ---------------------------------------------------------------------------
# S03 — Transition Validation (pure, no writes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionResult:
    """Result of a lifecycle transition validation.

    Attributes:
        valid: Whether the transition is allowed.
        from_status: The source status (normalized).
        to_status: The target status (normalized).
        allowed_targets: All statuses reachable from from_status.
        reason: Human-readable reason if invalid.
    """

    valid: bool
    from_status: str
    to_status: str
    allowed_targets: tuple[str, ...]
    reason: str = ""


def resolve_finding_status(raw_status: str) -> FindingStatus | None:
    """Resolve a raw status string to a FindingStatus.

    Returns None if the status cannot be mapped.
    """
    # Try direct enum match first
    try:
        return FindingStatus(raw_status)
    except ValueError:
        pass
    # Try alias match
    return FINDING_STATUS_ALIASES.get(raw_status)


def resolve_work_package_status(raw_status: str) -> WorkPackageStatus | None:
    """Resolve a raw status string to a WorkPackageStatus.

    Returns None if the status cannot be mapped.
    """
    try:
        return WorkPackageStatus(raw_status)
    except ValueError:
        pass
    return WORK_PACKAGE_STATUS_ALIASES.get(raw_status)


def validate_finding_transition(
    from_status: str,
    to_status: str,
) -> TransitionResult:
    """Validate a finding lifecycle transition.

    Pure function — no write operations.

    Args:
        from_status: Current status (raw string, will be resolved).
        to_status: Target status (raw string, will be resolved).

    Returns:
        TransitionResult with validity, reason, and allowed targets.
    """
    from_resolved = resolve_finding_status(from_status)
    to_resolved = resolve_finding_status(to_status)

    if from_resolved is None:
        return TransitionResult(
            valid=False,
            from_status=from_status,
            to_status=to_status,
            allowed_targets=(),
            reason=f"Unknown finding status: {from_status!r}",
        )

    if to_resolved is None:
        return TransitionResult(
            valid=False,
            from_status=from_status,
            to_status=to_status,
            allowed_targets=tuple(t.value for t in FINDING_TRANSITIONS.get(from_resolved, set())),
            reason=f"Unknown finding status: {to_status!r}",
        )

    allowed = FINDING_TRANSITIONS.get(from_resolved, set())
    allowed_values = tuple(sorted(t.value for t in allowed))

    if to_resolved in allowed:
        return TransitionResult(
            valid=True,
            from_status=from_resolved.value,
            to_status=to_resolved.value,
            allowed_targets=allowed_values,
        )

    return TransitionResult(
        valid=False,
        from_status=from_resolved.value,
        to_status=to_resolved.value,
        allowed_targets=allowed_values,
        reason=(
            f"Transition {from_resolved.value!r} → {to_resolved.value!r} is not allowed. "
            f"Allowed: {', '.join(allowed_values) or 'none (terminal state)'}"
        ),
    )


def validate_work_package_transition(
    from_status: str,
    to_status: str,
) -> TransitionResult:
    """Validate a work package lifecycle transition.

    Pure function — no write operations.

    Args:
        from_status: Current status (raw string, will be resolved).
        to_status: Target status (raw string, will be resolved).

    Returns:
        TransitionResult with validity, reason, and allowed targets.
    """
    from_resolved = resolve_work_package_status(from_status)
    to_resolved = resolve_work_package_status(to_status)

    if from_resolved is None:
        return TransitionResult(
            valid=False,
            from_status=from_status,
            to_status=to_status,
            allowed_targets=(),
            reason=f"Unknown work package status: {from_status!r}",
        )

    if to_resolved is None:
        return TransitionResult(
            valid=False,
            from_status=from_status,
            to_status=to_status,
            allowed_targets=tuple(
                t.value for t in WORK_PACKAGE_TRANSITIONS.get(from_resolved, set())
            ),
            reason=f"Unknown work package status: {to_status!r}",
        )

    allowed = WORK_PACKAGE_TRANSITIONS.get(from_resolved, set())
    allowed_values = tuple(sorted(t.value for t in allowed))

    if to_resolved in allowed:
        return TransitionResult(
            valid=True,
            from_status=from_resolved.value,
            to_status=to_resolved.value,
            allowed_targets=allowed_values,
        )

    return TransitionResult(
        valid=False,
        from_status=from_resolved.value,
        to_status=to_status,
        allowed_targets=allowed_values,
        reason=(
            f"Transition {from_resolved.value!r} → {to_resolved.value!r} is not allowed. "
            f"Allowed: {', '.join(allowed_values) or 'none (terminal state)'}"
        ),
    )


def get_allowed_finding_transitions(status: str) -> tuple[str, ...]:
    """Get allowed next statuses for a finding."""
    resolved = resolve_finding_status(status)
    if resolved is None:
        return ()
    allowed = FINDING_TRANSITIONS.get(resolved, set())
    return tuple(sorted(t.value for t in allowed))


def get_allowed_work_package_transitions(status: str) -> tuple[str, ...]:
    """Get allowed next statuses for a work package."""
    resolved = resolve_work_package_status(status)
    if resolved is None:
        return ()
    allowed = WORK_PACKAGE_TRANSITIONS.get(resolved, set())
    return tuple(sorted(t.value for t in allowed))


# ---------------------------------------------------------------------------
# S05 — Report-only inference from review decisions / verification
# ---------------------------------------------------------------------------


def infer_finding_status_from_context(
    finding_status: str,
    review_decision_status: str | None = None,
    verification_status: str | None = None,
) -> str:
    """Infer lifecycle status from existing context (report-only).

    Does NOT persist any state. Returns the most advanced status
    based on available context. Used for reporting and display only.

    Args:
        finding_status: Current status from DebtFinding.
        review_decision_status: Status from ReviewDecision (if any).
        verification_status: Status from VerificationResult (if any).

    Returns:
        Inferred FindingStatus value as string.
    """
    candidates: list[FindingStatus] = []

    # Base status from finding
    base = resolve_finding_status(finding_status)
    if base is not None:
        candidates.append(base)

    # Review decision → lifecycle mapping
    if review_decision_status:
        mapped = FINDING_STATUS_ALIASES.get(review_decision_status)
        if mapped is not None:
            candidates.append(mapped)

    # Verification result → lifecycle mapping
    if verification_status:
        mapped = FINDING_STATUS_ALIASES.get(verification_status)
        if mapped is not None:
            candidates.append(mapped)

    if not candidates:
        return FindingStatus.DETECTED.value

    # Use the most advanced status (highest in lifecycle order)
    lifecycle_order = [
        FindingStatus.DETECTED,
        FindingStatus.DEFERRED,
        FindingStatus.ACKNOWLEDGED,
        FindingStatus.IN_PROGRESS,
        FindingStatus.WONT_FIX,
        FindingStatus.REMEDIATED,
        FindingStatus.VERIFIED,
    ]
    best_idx = -1
    best = candidates[0]
    for c in candidates:
        try:
            idx = lifecycle_order.index(c)
        except ValueError:
            idx = -1
        if idx > best_idx:
            best_idx = idx
            best = c

    return best.value
