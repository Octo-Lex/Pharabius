"""Benchmark regression tests for v3.6.0.

Validates:
- 8 deterministic synthetic benchmark fixtures build correctly
- Golden snapshot bounds are met
- Finding quality rubric scores above targets
- Noise rates below targets
- Severity distribution within bounds
- Confidence honesty
- History snapshots enriched (v3.5.0)
- Run history summary present
- Report sections complete with heuristic disclaimers
- No large JSON blobs outside code blocks
- Golden snapshots don't assert volatile fields
- Calibration results schema is valid
- Two-run trend test validates v3.5.0 history layer
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from benchmarks.fixture_builder import BenchmarkFixture, build_all_fixtures
from benchmarks.rubric import (
    QUALITY_TARGETS,
    RUBRIC_CRITERIA,
    compute_fixture_quality,
    score_finding,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _run_pipeline(repo_root: Path) -> dict:
    """Run full pipeline and return key artifacts."""
    from pharabius.core.run_metadata import execute_run

    metadata = execute_run(repo_root)
    workspace = repo_root / ".ai-debt"

    register = _load_json(workspace / "debt-register.json")
    evidence = _load_json(workspace / "evidence.json")
    history_summary = _load_json(workspace / "reports" / "run-history-summary.json")

    return {
        "metadata": metadata,
        "workspace": workspace,
        "findings": register.get("findings", []),
        "evidence_items": evidence.get("evidence", []),
        "summary": register.get("summary", {}),
        "history_summary": history_summary,
    }


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


# ── S01: Fixture builder tests ────────────────────────────────────────


class TestFixtureBuilder:
    """Verify all 8 fixtures build correctly."""

    @pytest.fixture
    def fixtures(self, tmp_path: Path) -> dict[str, Path]:
        return build_all_fixtures(tmp_path)

    def test_fixture_builder_small_python(self, fixtures):
        assert "small-python-package" in fixtures
        assert (fixtures["small-python-package"] / "pyproject.toml").exists()

    def test_fixture_builder_medium_python(self, fixtures):
        assert "medium-python-service" in fixtures
        assert (fixtures["medium-python-service"] / "requirements.txt").exists()
        assert (fixtures["medium-python-service"] / "coverage.json").exists()

    def test_fixture_builder_small_node(self, fixtures):
        assert "small-node-package" in fixtures
        assert (fixtures["small-node-package"] / "package.json").exists()

    def test_fixture_builder_medium_node(self, fixtures):
        assert "medium-node-app" in fixtures
        assert (fixtures["medium-node-app"] / "package.json").exists()
        assert (fixtures["medium-node-app"] / "coverage" / "coverage-summary.json").exists()

    def test_fixture_builder_mixed(self, fixtures):
        assert "mixed-python-node" in fixtures
        assert (fixtures["mixed-python-node"] / "pyproject.toml").exists()
        assert (fixtures["mixed-python-node"] / "package.json").exists()

    def test_fixture_builder_coverage_heavy(self, fixtures):
        assert "coverage-heavy" in fixtures
        assert (fixtures["coverage-heavy"] / "coverage.json").exists()
        assert (fixtures["coverage-heavy"] / "coverage" / "lcov.info").exists()

    def test_fixture_builder_poor_hygiene(self, fixtures):
        assert "poor-hygiene" in fixtures
        assert (fixtures["poor-hygiene"] / "requirements.txt").exists()
        assert (fixtures["poor-hygiene"] / "package.json").exists()
        assert not (fixtures["poor-hygiene"] / ".python-version").exists()

    def test_fixture_builder_clean_baseline(self, fixtures):
        assert "clean-baseline" in fixtures
        assert (fixtures["clean-baseline"] / ".python-version").exists()
        assert (fixtures["clean-baseline"] / "coverage.json").exists()


# ── S02+S04: Golden bounds + threshold calibration ─────────────────────


class TestGoldenBounds:
    """Verify findings meet golden snapshot bounds."""

    @pytest.fixture
    def golden_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "benchmarks" / "golden"

    def _load_golden(self, golden_dir: Path, name: str) -> dict:
        path = golden_dir / f"{name}.json"
        if not path.exists():
            pytest.skip(f"Golden file missing: {name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_small_python_finding_count_in_bounds(self, tmp_path, golden_dir):
        fixtures = build_all_fixtures(tmp_path)
        result = _run_pipeline(fixtures["small-python-package"])
        golden = self._load_golden(golden_dir, "small-python-package")
        exp = golden["expected"]
        assert exp["finding_count_min"] <= len(result["findings"]) <= exp["finding_count_max"]

    def test_medium_python_categories_match(self, tmp_path, golden_dir):
        fixtures = build_all_fixtures(tmp_path)
        result = _run_pipeline(fixtures["medium-python-service"])
        golden = self._load_golden(golden_dir, "medium-python-service")
        actual_cats = set(str(f.get("category", "")) for f in result["findings"])
        for cat in golden["expected"]["categories"]:
            assert cat in actual_cats, f"Expected category {cat} not found"

    def test_poor_hygiene_finding_count_in_bounds(self, tmp_path, golden_dir):
        fixtures = build_all_fixtures(tmp_path)
        result = _run_pipeline(fixtures["poor-hygiene"])
        golden = self._load_golden(golden_dir, "poor-hygiene")
        exp = golden["expected"]
        assert exp["finding_count_min"] <= len(result["findings"]) <= exp["finding_count_max"]

    def test_clean_baseline_minimal_findings(self, tmp_path, golden_dir):
        fixtures = build_all_fixtures(tmp_path)
        result = _run_pipeline(fixtures["clean-baseline"])
        golden = self._load_golden(golden_dir, "clean-baseline")
        exp = golden["expected"]
        assert len(result["findings"]) <= exp["finding_count_max"]

    def test_coverage_heavy_coverage_evidence(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        result = _run_pipeline(fixtures["coverage-heavy"])
        cov_types = {"coverage_report_detected", "coverage_metric_detected"}
        actual_types = set(str(e.get("type", "")) for e in result["evidence_items"])
        assert actual_types & cov_types, "Expected coverage evidence not found"

    def test_medium_node_dep_signals(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        result = _run_pipeline(fixtures["medium-node-app"])
        dep_types = {"dependency_health_signal"}
        actual_types = set(str(e.get("type", "")) for e in result["evidence_items"])
        assert actual_types & dep_types, "Expected dependency signal not found"


# ── S03: Rubric quality ───────────────────────────────────────────────


class TestRubricQuality:
    """Verify finding quality meets targets."""

    def test_finding_quality_above_threshold(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        for name, repo_path in fixtures.items():
            result = _run_pipeline(repo_path)
            quality = compute_fixture_quality(result["findings"])
            target = QUALITY_TARGETS.get(name, {"min_quality": 0.5})
            assert quality["average_quality"] >= target["min_quality"], (
                f"{name}: quality {quality['average_quality']} < {target['min_quality']}"
            )

    def test_noise_rate_below_target(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        for name, repo_path in fixtures.items():
            result = _run_pipeline(repo_path)
            quality = compute_fixture_quality(result["findings"])
            target = QUALITY_TARGETS.get(name, {"max_noise": 0.25})
            assert quality["noise_rate"] <= target["max_noise"], (
                f"{name}: noise {quality['noise_rate']} > {target['max_noise']}"
            )


# ── S05: Severity calibration ─────────────────────────────────────────


class TestSeverityCalibration:
    """Verify severity distribution is within bounds."""

    def test_severity_distribution_in_bounds(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        for name, repo_path in fixtures.items():
            result = _run_pipeline(repo_path)
            findings = result["findings"]
            # Exclude advisories from severity distribution check (v3.7.0)
            debt_findings = [f for f in findings if f.get("issue_type") != "advisory"]
            dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for f in debt_findings:
                sev = str(f.get("severity", "Medium")).lower()
                if sev in dist:
                    dist[sev] += 1
            # No fixture should have >90% in a single severity (debt findings only)
            # Only enforce when there are >=3 debt findings to avoid small-sample noise
            total = max(len(debt_findings), 1)
            if len(debt_findings) < 3:
                continue
            for sev_name, count in dist.items():
                if count > 0:
                    assert count / total <= 0.9, (
                        f"{name}: {sev_name} is {count}/{total} = {count / total:.0%} (max 90%)"
                    )

    def test_confidence_honesty(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        for name, repo_path in fixtures.items():
            result = _run_pipeline(repo_path)
            issues = []
            for f in result["findings"]:
                if f.get("confidence") == "High":
                    ev_ids = f.get("evidence_ids") or []
                    ev = [e for e in result["evidence_items"] if e.get("evidence_id") in ev_ids]
                    if ev:
                        has_strong = any(
                            e.get("metadata", {}).get("observation_strength")
                            in ("direct", "derived")
                            for e in ev
                        )
                        if not has_strong:
                            issues.append(
                                f"{f.get('id')}: High confidence but no direct/derived evidence"
                            )
            # Allow up to 2 honesty issues per fixture
            assert len(issues) <= 2, f"{name}: {len(issues)} confidence issues: {issues[:3]}"


# ── S06: Report readability ───────────────────────────────────────────


class TestReportReadability:
    """Verify reports are readable and well-structured."""

    def test_report_sections_complete(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        repo_path = fixtures["medium-python-service"]
        _run_pipeline(repo_path)
        workspace = repo_path / ".ai-debt"

        md_files = [
            workspace / "debt-register.md",
            workspace / "reports" / "run-history-summary.md",
        ]
        for md_file in md_files:
            if not md_file.exists():
                continue
            text = md_file.read_text(encoding="utf-8")
            assert len(text) > 0, f"{md_file.name} is empty"

    def test_report_heuristic_disclaimers(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        repo_path = fixtures["medium-python-service"]
        _run_pipeline(repo_path)
        workspace = repo_path / ".ai-debt"
        md_path = workspace / "reports" / "run-history-summary.md"
        if md_path.exists():
            text = md_path.read_text(encoding="utf-8")
            assert "heuristic" in text.lower() or "not a scientific measure" in text.lower(), (
                "Run history summary missing heuristic disclaimer"
            )

    def test_report_no_large_json_blobs(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        repo_path = fixtures["medium-python-service"]
        _run_pipeline(repo_path)
        workspace = repo_path / ".ai-debt"
        md_path = workspace / "reports" / "run-history-summary.md"
        if not md_path.exists():
            pytest.skip("No run-history-summary.md")
        text = md_path.read_text(encoding="utf-8")
        issues = _check_no_large_json_outside_code_blocks(text)
        assert not issues, f"Large JSON outside code blocks: {issues[:3]}"


def _check_no_large_json_outside_code_blocks(markdown: str) -> list[str]:
    """Find large raw JSON blobs outside fenced code blocks."""
    issues = []
    in_fence = False
    for line in markdown.split("\n"):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        brace_count = line.count("{") + line.count("}")
        quoted_keys = line.count('":')
        if brace_count >= 3 and quoted_keys >= 2 and len(line) > 100:
            issues.append(f"Large JSON outside code block: {line[:80]}...")
    return issues


# ── S08: Calibration schema ───────────────────────────────────────────


class TestCalibrationSchema:
    """Verify calibration results file schema."""

    def test_calibration_results_schema(self):
        cal_path = (
            Path(__file__).resolve().parent.parent / "benchmarks" / "calibration-results.json"
        )
        if not cal_path.exists():
            pytest.skip("calibration-results.json not generated yet")
        data = json.loads(cal_path.read_text(encoding="utf-8"))
        required = [
            "schema_version",
            "generated_at",
            "fixtures_tested",
            "thresholds",
            "severity_distribution",
            "finding_quality_scores",
            "warnings",
        ]
        for key in required:
            assert key in data, f"Missing key: {key}"


# ── S09: Golden volatile fields ────────────────────────────────────────


class TestGoldenVolatileFields:
    """Verify golden snapshots don't assert on volatile fields."""

    def test_golden_snapshots_no_volatile_assertions(self):
        golden_dir = Path(__file__).resolve().parent.parent / "benchmarks" / "golden"
        if not golden_dir.exists():
            pytest.skip("Golden directory not found")
        for golden_file in golden_dir.glob("*.json"):
            data = json.loads(golden_file.read_text(encoding="utf-8"))
            volatile = data.get("volatile_fields_ignored", [])
            assert "generated_at" in volatile, (
                f"{golden_file.name}: missing generated_at in ignored"
            )
            assert "run_id" in volatile, f"{golden_file.name}: missing run_id in ignored"

    def test_golden_refresh_command_available(self):
        from benchmarks.generate_golden import generate_golden_snapshot

        assert callable(generate_golden_snapshot)


# ── v3.5.0 validation ─────────────────────────────────────────────────


class TestHistoryLayer:
    """Verify v3.5.0 history layer works under benchmark conditions."""

    def test_history_snapshot_enriched(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        repo_path = fixtures["medium-python-service"]
        result = _run_pipeline(repo_path)
        workspace = result["workspace"]

        snapshot_files = list((workspace / "runs").glob("*-history-snapshot.json"))
        assert len(snapshot_files) >= 1, "No history snapshot written"
        snapshot = json.loads(snapshot_files[0].read_text(encoding="utf-8"))
        assert snapshot.get("run_id"), "Snapshot missing run_id"
        assert "findings_by_category" in snapshot, "Snapshot missing findings_by_category"

    def test_run_history_summary_present(self, tmp_path):
        fixtures = build_all_fixtures(tmp_path)
        repo_path = fixtures["medium-python-service"]
        _run_pipeline(repo_path)
        workspace = repo_path / ".ai-debt"

        json_path = workspace / "reports" / "run-history-summary.json"
        md_path = workspace / "reports" / "run-history-summary.md"
        assert json_path.exists(), "run-history-summary.json missing"
        assert md_path.exists(), "run-history-summary.md missing"

    def test_two_run_history_trend_generated(self, tmp_path):
        """Run clean-baseline twice with modification in between.
        Assert trend status is not insufficient_data."""
        from pharabius.core.run_metadata import execute_run

        builder = BenchmarkFixture("trend-test", tmp_path)
        (
            builder.add_requirements_txt(["flask==3.0.0"])
            .add_runtime_pin("python", "3.12.0")
            .add_coverage_json(92.0)
            .add_python_file("src/app.py", "def hello():\n    return 'Hello'\n")
            .build()
        )
        execute_run(tmp_path / "trend-test")

        # Degrade: add unpinned deps
        (tmp_path / "trend-test" / "requirements.txt").write_text(
            "flask\nrequests\n", encoding="utf-8"
        )

        # Ensure different second-precision timestamp for run_id
        import time

        time.sleep(2)

        # Run 2
        execute_run(tmp_path / "trend-test")

        workspace = tmp_path / "trend-test" / ".ai-debt"
        summary = json.loads(
            (workspace / "reports" / "run-history-summary.json").read_text(encoding="utf-8")
        )

        assert summary["run_count"] == 2, f"Expected 2 runs, got {summary['run_count']}"
        assert summary["enriched_run_count"] == 2, (
            f"Expected 2 enriched, got {summary['enriched_run_count']}"
        )
        assert summary["confidence"] == "complete", (
            f"Expected complete, got {summary['confidence']}"
        )
        assert summary["overall_trajectory"] != "insufficient_data", (
            f"Expected non-insufficient trajectory, got {summary['overall_trajectory']}"
        )
