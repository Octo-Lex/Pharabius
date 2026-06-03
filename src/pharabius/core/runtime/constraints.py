"""Runtime version normalization and constraint parsing.

Centralizes all version comparison logic. Consumed by parsers and conflict detection.
"""

from __future__ import annotations

import re

from pharabius.core.runtime.models import (
    RuntimeConstraint,
    RuntimeConstraintKind,
)


def normalize_runtime_version(runtime: str, raw: str) -> tuple[str | None, str]:
    """Normalize a runtime version string.

    Returns (normalized_version, constraint_kind_string).
    """
    constraint = parse_constraint(runtime, raw)
    return constraint.value, constraint.kind.value


def parse_constraint(runtime: str, raw: str) -> RuntimeConstraint:
    """Parse a raw version string into a RuntimeConstraint."""
    raw_stripped = raw.strip()
    if not raw_stripped or raw_stripped in ("*", "latest"):
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            raw=raw_stripped,
        )

    # Range patterns: >=X.Y, ~> X.Y, ^X.Y, X.Y.x, X.Y.*, <=X.Y
    if re.match(r"^[><~^]", raw_stripped) or ".x" in raw_stripped.lower() or ".*" in raw_stripped:
        return _parse_range(runtime, raw_stripped)

    # Strip common prefixes
    cleaned = re.sub(
        r"^(python-|ruby-|v|temurin-|adoptopenjdk-|corretto-)",
        "", raw_stripped, flags=re.IGNORECASE,
    )

    # Extract version number
    match = re.match(r"(\d+)(?:\.(\d+))?", cleaned)
    if not match:
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.UNKNOWN,
            raw=raw_stripped,
        )

    major = match.group(1)
    minor = match.group(2)

    if runtime == "Node.js":
        return RuntimeConstraint(kind=RuntimeConstraintKind.EXACT, value=major, raw=raw_stripped)
    elif runtime == "Java":
        return RuntimeConstraint(kind=RuntimeConstraintKind.EXACT, value=major, raw=raw_stripped)
    elif runtime in ("Python", "Ruby"):
        if minor is not None:
            return RuntimeConstraint(
                kind=RuntimeConstraintKind.EXACT,
                value=f"{major}.{minor}",
                raw=raw_stripped,
            )
        return RuntimeConstraint(kind=RuntimeConstraintKind.EXACT, value=major, raw=raw_stripped)
    else:
        if minor is not None:
            return RuntimeConstraint(
                kind=RuntimeConstraintKind.EXACT,
                value=f"{major}.{minor}",
                raw=raw_stripped,
            )
        return RuntimeConstraint(kind=RuntimeConstraintKind.EXACT, value=major, raw=raw_stripped)


def _parse_range(runtime: str, raw: str) -> RuntimeConstraint:
    """Parse a range constraint into a RuntimeConstraint."""
    # >=X.Y
    m = re.match(r">=?\s*(\d+)(?:\.(\d+))?", raw)
    if m:
        major, minor = m.group(1), m.group(2)
        lb = f"{major}.{minor}" if minor else major
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            lower_bound=lb,
            raw=raw,
        )

    # ~> X.Y (Ruby pessimistic)
    m = re.match(r"~>\s*(\d+)\.(\d+)", raw)
    if m:
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            lower_bound=f"{m.group(1)}.{m.group(2)}",
            raw=raw,
        )

    # ^X.Y
    m = re.match(r"\^\s*(\d+)(?:\.(\d+))?", raw)
    if m:
        major, minor = m.group(1), m.group(2)
        lb = f"{major}.{minor}" if minor else major
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            lower_bound=lb,
            raw=raw,
        )

    # X.Y.x — >=X.Y, <(X+1).0
    m = re.match(r"(\d+)\.(\d+)\.x", raw, re.IGNORECASE)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            lower_bound=f"{major}.{minor}",
            upper_bound=f"{major + 1}.0",
            raw=raw,
        )

    # X.x — >=X, <(X+1)
    m = re.match(r"(\d+)\.x", raw, re.IGNORECASE)
    if m:
        major = int(m.group(1))
        return RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            lower_bound=str(major),
            upper_bound=str(major + 1),
            raw=raw,
        )

    return RuntimeConstraint(kind=RuntimeConstraintKind.RANGE, raw=raw)


def range_excludes_exact(
    constraint: RuntimeConstraint,
    exact_value: str,
) -> bool:
    """Check if a range constraint clearly excludes an exact version.

    Only handles simple cases. Returns True if conflict is definite.
    """
    if constraint.lower_bound is None:
        return False

    range_major = _extract_major(constraint.lower_bound)
    exact_major = _extract_major(exact_value)
    if range_major is None or exact_major is None:
        return False

    # If upper bound exists and exact is >= upper bound → conflict
    if constraint.upper_bound is not None:
        upper_major = _extract_major(constraint.upper_bound)
        if upper_major is not None and exact_major >= upper_major:
            return True

    # If range requires >=X and exact is < X → conflict
    if exact_major < range_major:
        return True

    # Same major: compare minor if available
    if exact_major == range_major:
        range_minor = _extract_minor(constraint.lower_bound)
        exact_minor = _extract_minor(exact_value)
        if range_minor is not None and exact_minor is not None:
            if exact_minor < range_minor:
                return True

    return False


def _extract_major(version: str) -> int | None:
    m = re.match(r"(\d+)", version)
    return int(m.group(1)) if m else None


def _extract_minor(version: str) -> int | None:
    m = re.match(r"\d+\.(\d+)", version)
    return int(m.group(1)) if m else None


def ranges_are_disjoint(
    constraint_a: RuntimeConstraint,
    constraint_b: RuntimeConstraint,
) -> bool:
    """Check if two ranges are definitely disjoint.

    Conservative: only returns True when both ranges have enough
    normalized bounds to prove no intersection.
    """
    # Need at least lower_bound on one and upper_bound on the other
    if constraint_a.lower_bound and constraint_b.upper_bound:
        lb_a = _extract_major(constraint_a.lower_bound)
        ub_b = _extract_major(constraint_b.upper_bound)
        lb_a_minor = _extract_minor(constraint_a.lower_bound)
        ub_b_minor = _extract_minor(constraint_b.upper_bound)
        if lb_a is not None and ub_b is not None:
            # a >= X, b < Y where X >= Y → disjoint
            # Note: >=X and <Y are disjoint if X >= Y
            if lb_a > ub_b:
                return True
            if lb_a == ub_b:
                # Same major — check minor
                if lb_a_minor is not None and ub_b_minor is not None and lb_a_minor >= ub_b_minor:
                    return True
                elif lb_a_minor is None and ub_b_minor is None:
                    # >=X and <X are disjoint (X not included in <X)
                    return True

    if constraint_b.lower_bound and constraint_a.upper_bound:
        lb_b = _extract_major(constraint_b.lower_bound)
        ub_a = _extract_major(constraint_a.upper_bound)
        lb_b_minor = _extract_minor(constraint_b.lower_bound)
        ub_a_minor = _extract_minor(constraint_a.upper_bound)
        if lb_b is not None and ub_a is not None:
            if lb_b > ub_a:
                return True
            if lb_b == ub_a:
                if lb_b_minor is not None and ub_a_minor is not None and lb_b_minor >= ub_a_minor:
                    return True
                elif lb_b_minor is None and ub_a_minor is None:
                    return True

    return False
