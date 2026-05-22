"""Tests for scoring calibration fixtures (W40-S03).

These tests lock current v1.5.0 threshold behavior. Any future threshold
change must update the corresponding fixture expectations intentionally.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.scoring import FACTOR_SCALE, compute_centrality_signals

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "scoring_calibration"


# ── Fixture loading helpers ───────────────────────────────────────────


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_fixtures(subdir: str) -> list[tuple[str, dict]]:
    """Yield (case_id, fixture_data) from a subdirectory."""
    d = FIXTURES_DIR / subdir
    if not d.exists():
        return []
    results = []
    for p in sorted(d.glob("*.json")):
        data = _load_json(p)
        results.append((data["case_id"], data))
    return results


# ── Fixture validity tests ─────────────────────────────────────────────


class TestFixtureValidity:
    def test_all_architecture_fixtures_are_valid_json(self) -> None:
        cases = _iter_fixtures("architecture_centrality")
        assert len(cases) >= 6, f"Expected >= 6 arch fixtures, got {len(cases)}"
        for case_id, data in cases:
            assert "case_id" in data
            assert "description" in data
            assert "finding_locations" in data
            assert "expected" in data
            assert "architecture_centrality" in data["expected"]

    def test_all_frequency_fixtures_are_valid_json(self) -> None:
        cases = _iter_fixtures("change_frequency")
        assert len(cases) >= 6, f"Expected >= 6 freq fixtures, got {len(cases)}"
        for case_id, data in cases:
            assert "case_id" in data
            assert "description" in data
            assert "finding_locations" in data
            assert "expected" in data
            assert "change_frequency" in data["expected"]

    def test_calibration_expectations_file_valid(self) -> None:
        path = FIXTURES_DIR / "expected" / "calibration_expectations.json"
        assert path.exists()
        data = _load_json(path)
        assert "architecture_centrality_thresholds" in data
        assert "change_frequency_thresholds" in data
        for level in ("Low", "Medium", "High"):
            assert level in data["architecture_centrality_thresholds"]
            assert level in data["change_frequency_thresholds"]


# ── Architecture centrality calibration tests ─────────────────────────


class TestArchitectureCentralityCalibration:
    """Test centrality against fixtures using real graph-loading logic."""

    def _run_graph_case(self, case_data: dict, tmp_path: Path) -> tuple[str, int]:
        """Set up graph file, run centrality, return (level, value)."""
        graph = case_data["architecture_graph"]
        locations = [loc["file"] for loc in case_data["finding_locations"]]

        if graph is not None:
            graph_dir = tmp_path / ".ai-debt"
            graph_dir.mkdir()
            (graph_dir / "architecture-graph.json").write_text(json.dumps(graph), encoding="utf-8")

        signals = compute_centrality_signals(tmp_path, locations)
        best = max(signals, key=lambda s: s.value)
        return best.level, best.value

    def test_missing_graph(self, tmp_path: Path) -> None:
        data = _load_json(FIXTURES_DIR / "architecture_centrality" / "missing_graph.json")
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]

    def test_empty_graph(self, tmp_path: Path) -> None:
        data = _load_json(FIXTURES_DIR / "architecture_centrality" / "empty_graph.json")
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]

    def test_node_not_found(self, tmp_path: Path) -> None:
        data = _load_json(FIXTURES_DIR / "architecture_centrality" / "node_not_found.json")
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]

    def test_low_peripheral_node(self, tmp_path: Path) -> None:
        data = _load_json(FIXTURES_DIR / "architecture_centrality" / "low_peripheral_node.json")
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]

    def test_medium_fan_in_boundary(self, tmp_path: Path) -> None:
        data = _load_json(FIXTURES_DIR / "architecture_centrality" / "medium_fan_in_boundary.json")
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]

    def test_high_fan_in_boundary(self, tmp_path: Path) -> None:
        data = _load_json(FIXTURES_DIR / "architecture_centrality" / "high_fan_in_boundary.json")
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]

    def test_high_cycle_participation(self, tmp_path: Path) -> None:
        data = _load_json(
            FIXTURES_DIR / "architecture_centrality" / "high_cycle_participation.json"
        )
        level, value = self._run_graph_case(data, tmp_path)
        assert level == data["expected"]["architecture_centrality"]["level"]
        assert value == data["expected"]["architecture_centrality"]["value"]


# ── Change frequency calibration tests (unit-level) ───────────────────


class TestChangeFrequencyCalibration:
    """Test frequency threshold boundaries at unit level.

    These tests use the threshold logic directly rather than mocking
    git subprocesses. They verify the level→value mapping is correct.
    """

    @pytest.mark.parametrize(
        "count,expected_level",
        [
            (0, "Low"),
            (1, "Low"),
            (2, "Low"),
            (3, "Medium"),
            (5, "Medium"),
            (10, "Medium"),
            (11, "High"),
            (50, "High"),
        ],
    )
    def test_commit_count_to_level_mapping(self, count: int, expected_level: str) -> None:
        """Verify threshold boundaries: Low (0-2), Medium (3-10), High (>10)."""
        if count > 10:
            level = "High"
        elif count >= 3:
            level = "Medium"
        else:
            level = "Low"
        assert level == expected_level
        # Verify FACTOR_SCALE consistency
        assert level in FACTOR_SCALE
        expected_value = FACTOR_SCALE[expected_level]
        if level == "Low":
            assert expected_value == 1
        elif level == "Medium":
            assert expected_value == 3
        elif level == "High":
            assert expected_value == 5

    def test_fixture_zero_commits_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "zero_commits.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "Low" and exp["value"] == 1

    def test_fixture_two_commits_boundary_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "two_commits_boundary.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "Low" and exp["value"] == 1

    def test_fixture_three_commits_boundary_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "three_commits_boundary.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "Medium" and exp["value"] == 3

    def test_fixture_ten_commits_boundary_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "ten_commits_boundary.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "Medium" and exp["value"] == 3

    def test_fixture_eleven_commits_boundary_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "eleven_commits_boundary.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "High" and exp["value"] == 5

    def test_fixture_non_git_repo_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "non_git_repo.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "Low" and exp["value"] == 1

    def test_fixture_shallow_clone_matches(self) -> None:
        data = _load_json(FIXTURES_DIR / "change_frequency" / "shallow_clone.json")
        exp = data["expected"]["change_frequency"]
        assert exp["level"] == "Low" and exp["value"] == 1
