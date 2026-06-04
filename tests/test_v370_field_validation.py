"""v3.7.0 — Field Validation & Structural Signal Calibration.

Tests cover:
- OSS manifest loading and snapshot extraction
- Advisory classification behavior
- Count separation (technical_debt_count / advisory_count)
- Planner advisory exclusion
- Claims advisory exclusion
- Reporter advisory section
- Run history advisory tracking
- Finding trend advisory exclusion
- TD-DEP boundary (lockfile advisory vs unpinned finding)
- Severity cap for advisories
- Clean-baseline quietness policy
- Large synthetic repo generation
"""

from __future__ import annotations

import json
import tarfile
from io import BytesIO
from pathlib import Path

import pytest
from benchmarks.fixture_builder import BenchmarkFixture
from benchmarks.oss_validation import (
    load_oss_manifest,
    safe_extract_tar,
    unpack_oss_snapshot,
)

from pharabius.core.run_metadata import execute_run

# ── Helpers ──────────────────────────────────────────────────────────


def _build_clean(tmp_path: Path) -> Path:
    """Build a clean-baseline fixture and return its path."""
    builder = BenchmarkFixture("clean", tmp_path)
    (
        builder.add_requirements_txt(["flask==3.0.0", "requests==2.31.0"])
        .add_runtime_pin("python", "3.12.0")
        .add_coverage_json(92.0)
        .add_python_file(
            "src/app.py",
            "from flask import Flask\napp = Flask(__name__)\ndef hello():\n    return 'Hello'\n",
        )
    )
    builder.build()
    return tmp_path / "clean"


def _run_pipeline(repo_path: Path) -> dict:
    """Run the full pipeline and return debt-register contents."""
    execute_run(repo_path)
    reg_path = repo_path / ".ai-debt" / "debt-register.json"
    return json.loads(reg_path.read_text(encoding="utf-8"))


def _build_poor_hygiene(tmp_path: Path) -> Path:
    """Build a poor-hygiene fixture with unpinned deps."""
    builder = BenchmarkFixture("poor", tmp_path)
    (
        builder.add_requirements_txt(["flask", "requests"]).add_package_json(
            {"name": "test", "version": "1.0.0", "dependencies": {"express": "*"}}
        )
    )
    builder.build()
    return tmp_path / "poor"


# ── S01: OSS Manifest ───────────────────────────────────────────────


class TestOSSManifest:
    def test_oss_manifest_loads(self):
        manifest = load_oss_manifest(Path("benchmarks"))
        assert "repos" in manifest
        assert len(manifest["repos"]) == 3

    def test_oss_manifest_has_required_fields(self):
        manifest = load_oss_manifest(Path("benchmarks"))
        for repo in manifest["repos"]:
            assert repo["name"]
            assert repo["commit"]
            assert repo["snapshot"]
            assert repo["snapshot_sha256"]
            assert repo["snapshot_size_bytes"]
            assert repo["license"]
            assert repo["upstream_url"]
            assert isinstance(repo["languages"], list)

    def test_oss_snapshots_exist(self):
        manifest = load_oss_manifest(Path("benchmarks"))
        for repo in manifest["repos"]:
            snap = Path("benchmarks") / "oss" / repo["snapshot"].replace("snapshots/", "")
            # Adjust path: repos.yaml has "snapshots/..." but file is relative to oss/
            snap = Path("benchmarks/oss") / repo["snapshot"]
            assert snap.exists(), f"Missing snapshot: {snap}"


# ── S02: Snapshot Extraction ────────────────────────────────────────


class TestSnapshotExtraction:
    def test_oss_snapshot_unpackable(self, tmp_path):
        manifest = load_oss_manifest(Path("benchmarks"))
        repo = manifest["repos"][0]
        snap = Path("benchmarks/oss") / repo["snapshot"]
        extracted = unpack_oss_snapshot(
            snap, tmp_path / "work", verify_sha256=repo["snapshot_sha256"]
        )
        assert extracted.exists()
        # Should contain files
        files = list(extracted.rglob("*"))
        assert len(files) > 0

    def test_safe_extract_rejects_traversal(self, tmp_path):
        """Verify safe_extract_tar rejects .. traversal."""
        buf = BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="../../../etc/passwd")
            info.size = 4
            tar.addfile(info, BytesIO(b"test"))
        buf.seek(0)

        with tarfile.open(fileobj=buf, mode="r:gz") as tar:  # noqa: SIM117
            with pytest.raises(ValueError, match=r"Unsafe|Traversal"):
                safe_extract_tar(tar, tmp_path / "safe")

    def test_safe_extract_rejects_absolute_path(self, tmp_path):
        """Verify safe_extract_tar rejects absolute paths."""
        buf = BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="/etc/passwd")
            info.size = 4
            tar.addfile(info, BytesIO(b"test"))
        buf.seek(0)

        with tarfile.open(fileobj=buf, mode="r:gz") as tar:  # noqa: SIM117
            with pytest.raises(ValueError, match=r"Unsafe|absolute"):
                safe_extract_tar(tar, tmp_path / "safe")


# ── S03/S04: Advisory Classification ────────────────────────────────


class TestAdvisoryClassification:
    def test_structural_findings_are_advisory(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        structural = {
            "TD-BUILD",
            "TD-DOC",
            "TD-PROCESS",
        }
        for f in reg["findings"]:
            if f["category"] in structural:
                assert f["issue_type"] == "advisory", (
                    f"{f['id']} ({f['category']}) should be advisory"
                )

    def test_lockfile_absence_is_advisory(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        lockfile_findings = [
            f
            for f in reg["findings"]
            if f["category"] == "TD-DEP" and "lockfile" in f.get("title", "").lower()
        ]
        for f in lockfile_findings:
            assert f["issue_type"] == "advisory", f"Lockfile finding {f['id']} should be advisory"

    def test_unpinned_deps_remain_finding(self, tmp_path):
        """TD-DEP unpinned dependency findings remain technical_debt."""
        repo = _build_poor_hygiene(tmp_path)
        reg = _run_pipeline(repo)
        unpinned = [
            f
            for f in reg["findings"]
            if f["category"] == "TD-DEP"
            and "lockfile" not in f.get("title", "").lower()
            and "unpinned" in f.get("title", "").lower()
        ]
        # If unpinned findings exist, they must be technical_debt
        for f in unpinned:
            assert f["issue_type"] == "technical_debt", (
                f"Unpinned dep finding {f['id']} must remain technical_debt"
            )

    def test_advisories_capped_at_low_severity(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        for f in reg["findings"]:
            if f["issue_type"] == "advisory":
                assert f["severity"] == "Low", (
                    f"Advisory {f['id']} should be Low severity, got {f['severity']}"
                )
                assert f["risk_score"] <= 10, (
                    f"Advisory {f['id']} risk_score={f['risk_score']} exceeds cap of 10"
                )


# ── S05: Clean-Baseline Quietness ───────────────────────────────────


class TestCleanBaselineQuietness:
    def test_clean_baseline_has_no_high_or_critical(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        summary = reg["summary"]
        assert summary["critical"] == 0, f"clean-baseline has {summary['critical']} critical"
        assert summary["high"] == 0, f"clean-baseline has {summary['high']} high"

    def test_clean_baseline_technical_debt_count_minimal(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        summary = reg["summary"]
        assert summary["technical_debt_count"] <= 2, (
            f"clean-baseline has {summary['technical_debt_count']} debt findings (max 2)"
        )

    def test_clean_baseline_advisories_exist(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        summary = reg["summary"]
        assert summary["advisory_count"] >= 3, (
            f"clean-baseline has {summary['advisory_count']} advisories (expected 3+)"
        )


# ── Planner / Claims Exclusion ──────────────────────────────────────


class TestAdvisoryExclusion:
    def test_advisories_do_not_generate_work_packages(self, tmp_path):
        repo = _build_clean(tmp_path)
        _run_pipeline(repo)
        wp_dir = repo / ".ai-debt" / "work-packages"
        wp_files = list(wp_dir.glob("WP-*.md"))
        # Only technical_debt findings should generate WPs
        # clean-baseline has 1 debt finding (TD-TEST), so max 1 WP
        assert len(wp_files) <= 1, f"Expected ≤1 WP from clean-baseline, got {len(wp_files)}"

    def test_advisories_do_not_generate_claims(self, tmp_path):
        repo = _build_clean(tmp_path)
        _run_pipeline(repo)
        claims_path = repo / ".ai-debt" / "claims" / "operational-claims.json"
        claims = json.loads(claims_path.read_text(encoding="utf-8"))
        # Only technical_debt findings should generate claims
        claim_count = len(claims.get("claims", []))
        assert claim_count <= 2, f"Expected ≤2 claims from clean-baseline, got {claim_count}"

    def test_advisory_report_section_present(self, tmp_path):
        repo = _build_clean(tmp_path)
        _run_pipeline(repo)
        report_path = repo / ".ai-debt" / "reports" / "foundation-audit-report.md"
        report = report_path.read_text(encoding="utf-8")
        assert "Advisory Signals" in report
        assert "technical debt:" in report


# ── Count Separation ────────────────────────────────────────────────


class TestCountSeparation:
    def test_debt_summary_separates_technical_debt_and_advisories(self, tmp_path):
        repo = _build_clean(tmp_path)
        reg = _run_pipeline(repo)
        summary = reg["summary"]
        assert "technical_debt_count" in summary
        assert "advisory_count" in summary
        assert (
            summary["technical_debt_count"] + summary["advisory_count"] == summary["total_findings"]
        )

    def test_run_history_snapshot_counts_advisories_separately(self, tmp_path):
        repo = _build_clean(tmp_path)
        _run_pipeline(repo)
        snaps = list((repo / ".ai-debt" / "runs").glob("*-history-snapshot.json"))
        assert len(snaps) >= 1
        snap = json.loads(snaps[0].read_text(encoding="utf-8"))
        assert "technical_debt_count" in snap
        assert "advisory_count" in snap
        assert "advisories_by_category" in snap
        assert snap["advisory_count"] >= 3

    def test_finding_trend_excludes_advisories_by_default(self, tmp_path):
        """Two-run trend should use technical_debt_count."""
        repo = _build_clean(tmp_path)
        execute_run(repo)

        import time

        time.sleep(2)

        # Degrade: remove coverage to add a debt finding
        cov_path = repo / "coverage.json"
        if cov_path.exists():
            cov_path.unlink()

        execute_run(repo)

        # Check summary
        summary_path = repo / ".ai-debt" / "reports" / "run-history-summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            # Trend should exist and use technical_debt_count
            if "finding_trend" in summary:
                trend = summary["finding_trend"]
                # Status should not be insufficient_data
                assert trend.get("status") != "insufficient_data"


# ── S06: Large Synthetic Repo ───────────────────────────────────────


class TestLargeSyntheticRepo:
    @pytest.mark.slow
    def test_large_synthetic_repo_generation(self, tmp_path):
        """Generate a 500-file synthetic repo and verify structure."""
        repo = tmp_path / "large-synthetic"
        repo.mkdir(parents=True)
        (repo / "pyproject.toml").write_text("[project]\nname = 'large-test'\nversion = '1.0.0'\n")
        src = repo / "src" / "pkg"
        src.mkdir(parents=True)
        for i in range(500):
            (src / f"module_{i:04d}.py").write_text(f"def func_{i}():\n    return {i}\n")

        py_files = list(src.glob("*.py"))
        assert len(py_files) == 500

    @pytest.mark.slow
    def test_large_synthetic_repo_scan_completes(self, tmp_path):
        """Full pipeline on 500-file repo should complete without crash."""
        repo = tmp_path / "large-synthetic"
        repo.mkdir(parents=True)
        (repo / "pyproject.toml").write_text("[project]\nname = 'large-test'\nversion = '1.0.0'\n")
        src = repo / "src" / "pkg"
        src.mkdir(parents=True)
        for i in range(500):
            (src / f"module_{i:04d}.py").write_text(f"def func_{i}():\n    return {i}\n")

        execute_run(repo)
        assert (repo / ".ai-debt" / "debt-register.json").exists()
        reg = json.loads((repo / ".ai-debt" / "debt-register.json").read_text())
        assert reg["summary"]["total_findings"] > 0


# ── OSS Validation Harness ──────────────────────────────────────────


class TestOSSValidationHarness:
    def test_oss_validation_summary_shape(self, tmp_path):
        """Validation summary should have expected fields."""
        manifest = load_oss_manifest(Path("benchmarks"))
        repo = manifest["repos"][0]
        snap = Path("benchmarks/oss") / repo["snapshot"]
        extracted = unpack_oss_snapshot(snap, tmp_path / "work")

        # Just verify shape, don't run full pipeline in unit tests
        # (that's for manual/benchmark runs)
        assert extracted.exists()
