"""GitHub Actions runtime evidence parser."""

from __future__ import annotations

from pathlib import Path

import yaml

from pharabius.core.io_helpers import read_text
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceType,
)
from pharabius.core.runtime.ecosystems import _make_id


_GH_SETUP_ACTIONS: dict[str, tuple[str, str]] = {
    "actions/setup-python": ("python-version", "Python"),
    "actions/setup-node": ("node-version", "Node.js"),
    "ruby/setup-ruby": ("ruby-version", "Ruby"),
    "actions/setup-java": ("java-version", "Java"),
    "actions/setup-go": ("go-version", "Go"),
    "actions/setup-dotnet": ("dotnet-version", ".NET"),
    "shivammathur/setup-php": ("php-version", "PHP"),
}


def detect_ci_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect runtime versions from GitHub Actions workflow files."""
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.exists():
        return []

    evidence: list[RuntimeEvidence] = []
    for wf_path in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        evidence.extend(_parse_workflow(root, wf_path))
    return evidence


def _parse_workflow(root: Path, wf_path: Path) -> list[RuntimeEvidence]:
    rel_path = str(wf_path.relative_to(root)).replace("\\", "/")
    text = read_text(wf_path)
    if not text:
        return []

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        # Malformed → unknown evidence
        return [RuntimeEvidence(
            runtime_evidence_id=_make_id("unknown", rel_path, "malformed", "unknown"),
            ecosystem=RuntimeEcosystem.PYTHON,  # placeholder
            runtime_name="unknown",
            constraint=RuntimeConstraint(kind=RuntimeConstraintKind.UNKNOWN, raw="malformed"),
            source_type=RuntimeSourceType.CI,
            source_path=rel_path,
            confidence=Confidence.LOW,
        )]

    if not isinstance(data, dict):
        return []

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return []

    evidence: list[RuntimeEvidence] = []
    for _job_name, job_data in jobs.items():
        if not isinstance(job_data, dict):
            continue
        steps = job_data.get("steps", [])
        if not isinstance(steps, list):
            continue

        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if not isinstance(uses, str):
                continue

            uses_base = uses.split("@")[0]
            action_info = _GH_SETUP_ACTIONS.get(uses_base)
            if not action_info:
                continue

            version_key, runtime = action_info
            with_data = step.get("with", {})
            if not isinstance(with_data, dict):
                continue

            version_val = with_data.get(version_key)
            if version_val is None:
                continue

            ecosystem = _runtime_to_ecosystem(runtime)

            # Matrix/env expression → unknown
            version_str = str(version_val)
            if "${{" in version_str:
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id(runtime, rel_path, uses_base, "matrix"),
                    ecosystem=ecosystem,
                    runtime_name=runtime,
                    constraint=RuntimeConstraint(kind=RuntimeConstraintKind.UNKNOWN, raw="matrix"),
                    source_type=RuntimeSourceType.CI,
                    source_path=rel_path,
                    source_detail=uses_base,
                    confidence=Confidence.LOW,
                ))
                continue

            # List of versions → one per version, all unknown
            if isinstance(version_val, list):
                for v in version_val:
                    v_str = str(v)
                    evidence.append(RuntimeEvidence(
                        runtime_evidence_id=_make_id(runtime, rel_path, f"{uses_base}[{v_str}]", v_str),
                        ecosystem=ecosystem,
                        runtime_name=runtime,
                        constraint=RuntimeConstraint(kind=RuntimeConstraintKind.UNKNOWN, raw=v_str),
                        source_type=RuntimeSourceType.CI,
                        source_path=rel_path,
                        source_detail=uses_base,
                        confidence=Confidence.LOW,
                        raw_version=v_str,
                    ))
                continue

            # Exact version from CI
            constraint = parse_constraint(runtime, version_str)
            evidence.append(RuntimeEvidence(
                runtime_evidence_id=_make_id(runtime, rel_path, uses_base, version_str),
                ecosystem=ecosystem,
                runtime_name=runtime,
                constraint=constraint,
                source_type=RuntimeSourceType.CI,
                source_path=rel_path,
                source_detail=uses_base,
                confidence=Confidence.MEDIUM,
                raw_version=version_str,
            ))

    return evidence


def _runtime_to_ecosystem(runtime: str) -> RuntimeEcosystem:
    mapping = {"Python": RuntimeEcosystem.PYTHON, "Node.js": RuntimeEcosystem.NODE,
               "Ruby": RuntimeEcosystem.RUBY, "Java": RuntimeEcosystem.JAVA,
               "Go": RuntimeEcosystem.GO, ".NET": RuntimeEcosystem.DOTNET,
               "PHP": RuntimeEcosystem.PHP}
    return mapping.get(runtime, RuntimeEcosystem.PYTHON)
