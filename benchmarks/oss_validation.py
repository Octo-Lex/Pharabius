"""OSS benchmark validation harness.

Provides safe snapshot extraction, pipeline execution, and bounded
validation against golden expectations for pinned public OSS repositories.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
import time
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_oss_manifest(benchmarks_root: Path) -> dict[str, Any]:
    """Load the OSS repos manifest (repos.yaml)."""
    manifest_path = benchmarks_root / "oss" / "repos.yaml"
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Safe tar extraction
# ---------------------------------------------------------------------------

def safe_extract_tar(tar: tarfile.TarFile, target: Path) -> None:
    """Extract tar archive safely.

    Rejects absolute paths and ``..`` traversal. Uses ``filter='data'``
    on Python 3.12+; falls back to manual member validation on older runtimes.
    """
    target.resolve().mkdir(parents=True, exist_ok=True)

    # Validate every member before extraction
    for member in tar.getmembers():
        if member.name.startswith("/") or ".." in member.name.split("/"):
            raise ValueError(f"Unsafe tar member: {member.name}")
        resolved = (target.resolve() / member.name).resolve()
        if not str(resolved).startswith(str(target.resolve())):
            raise ValueError(f"Traversal attempt: {member.name}")

    # Extract with data filter when available
    try:
        tar.extractall(target, filter="data")  # type: ignore[call-arg]
    except TypeError:
        tar.extractall(target)


def unpack_oss_snapshot(
    snapshot_path: Path,
    work_dir: Path,
    *,
    verify_sha256: str | None = None,
) -> Path:
    """Unpack a pinned OSS snapshot into a work directory.

    Returns the path to the extracted repository root (top-level directory
    inside the archive).
    """
    if verify_sha256:
        actual = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        if actual != verify_sha256:
            raise ValueError(
                f"SHA-256 mismatch for {snapshot_path.name}: "
                f"expected {verify_sha256}, got {actual}"
            )

    work_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(snapshot_path, "r:gz") as tar:
        safe_extract_tar(tar, work_dir)

    # Find the single top-level directory created by the archive
    top_dirs = [p for p in work_dir.iterdir() if p.is_dir()]
    if len(top_dirs) == 1:
        return top_dirs[0]

    # If multiple directories, return work_dir itself
    return work_dir


# ---------------------------------------------------------------------------
# Pipeline execution + metric collection
# ---------------------------------------------------------------------------

def run_oss_validation(repo_path: Path) -> dict[str, Any]:
    """Run execute_run() against an unpacked OSS snapshot and collect metrics.

    Returns a dict of validation metrics suitable for golden comparison.
    """
    from pharabius.core.run_metadata import execute_run

    t0 = time.monotonic()
    execute_run(repo_path)
    elapsed = time.monotonic() - t0

    workspace = repo_path / ".ai-debt"

    # Load debt register
    register_path = workspace / "debt-register.json"
    register = json.loads(register_path.read_text(encoding="utf-8")) if register_path.exists() else {}

    findings = register.get("findings", [])
    summary = register.get("summary", {})

    # Classify findings
    categories: dict[str, int] = {}
    severity_dist: dict[str, int] = {}
    structural_count = 0
    advisory_count = 0
    tech_debt_count = 0

    structural_categories = {"TD-BUILD", "TD-DOC", "TD-PROCESS"}

    for f in findings:
        cat = f.get("category", "UNKNOWN")
        categories[cat] = categories.get(cat, 0) + 1

        sev = f.get("severity", "Unknown")
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

        issue_type = f.get("issue_type", "technical_debt")
        if issue_type == "advisory":
            advisory_count += 1
        else:
            tech_debt_count += 1

        if cat in structural_categories:
            structural_count += 1

    # Evidence count
    evidence_path = workspace / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence_items = evidence.get("evidence", [])
    evidence_count = len(evidence_items) if isinstance(evidence_items, list) else 0

    # Work packages
    wp_path = workspace / "work-packages.json"
    wp_data = json.loads(wp_path.read_text(encoding="utf-8")) if wp_path.exists() else {}
    wp_count = len(wp_data.get("work_packages", []))

    # Output size
    total_bytes = sum(f.stat().st_size for f in workspace.rglob("*") if f.is_file())
    output_size_mb = round(total_bytes / (1024 * 1024), 2)

    return {
        "finding_count": len(findings),
        "technical_debt_count": tech_debt_count,
        "advisory_count": advisory_count,
        "categories": categories,
        "severity_distribution": severity_dist,
        "evidence_count": evidence_count,
        "work_package_count": wp_count,
        "structural_finding_count": structural_count,
        "runtime_seconds": round(elapsed, 2),
        "output_size_mb": output_size_mb,
        "critical": summary.get("critical", 0),
        "high": summary.get("high", 0),
        "medium": summary.get("medium", 0),
        "low": summary.get("low", 0),
    }


# ---------------------------------------------------------------------------
# Golden validation
# ---------------------------------------------------------------------------

def validate_against_oss_golden(
    result: dict[str, Any],
    golden: dict[str, Any],
) -> list[str]:
    """Return a list of validation failures against golden bounds.

    Golden uses ``max`` bounds for counts and categories. An empty list
    means all bounds are satisfied.
    """
    failures: list[str] = []

    # Finding count bound
    max_findings = golden.get("expected_findings_max", 100)
    if result["finding_count"] > max_findings:
        failures.append(
            f"finding_count={result['finding_count']} exceeds max={max_findings}"
        )

    # Technical debt bound
    max_td = golden.get("expected_technical_debt_max", 50)
    if result["technical_debt_count"] > max_td:
        failures.append(
            f"technical_debt_count={result['technical_debt_count']} "
            f"exceeds max={max_td}"
        )

    # Severity bounds
    max_critical = golden.get("expected_critical_max", 0)
    if result["critical"] > max_critical:
        failures.append(
            f"critical={result['critical']} exceeds max={max_critical}"
        )

    max_high = golden.get("expected_high_max", 5)
    if result["high"] > max_high:
        failures.append(
            f"high={result['high']} exceeds max={max_high}"
        )

    # Allowed categories
    allowed = golden.get("expected_categories_allowed")
    if allowed:
        unexpected = set(result["categories"]) - set(allowed)
        if unexpected:
            failures.append(
                f"unexpected categories: {sorted(unexpected)}"
            )

    # Output size
    max_mb = golden.get("expected_output_size_mb_max", 50)
    if result["output_size_mb"] > max_mb:
        failures.append(
            f"output_size_mb={result['output_size_mb']} exceeds max={max_mb}"
        )

    return failures
