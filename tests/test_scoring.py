"""Tests for v1.5.0 Enhanced Risk Scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.scoring import (
    FACTOR_SCALE,
    compute_centrality_signals,
    compute_change_frequency_signals,
    enhance_risk_breakdown,
    recalculate_risk_score,
)
from pharabius.schemas.config import (
    PharabiusConfig,
    RiskScoringConfig,
)

# ── Factor scale tests ────────────────────────────────────────────────


class TestFactorScale:
    def test_scale_values_match_existing_model(self) -> None:
        assert FACTOR_SCALE["Low"] == 1
        assert FACTOR_SCALE["Medium"] == 3
        assert FACTOR_SCALE["High"] == 5
        assert FACTOR_SCALE["Critical"] == 8

    def test_no_2_value(self) -> None:
        """Factor scale must NOT use 2 (old incorrect plan)."""
        assert 2 not in FACTOR_SCALE.values()


# ── Config schema tests ───────────────────────────────────────────────


class TestRiskScoringConfig:
    def test_default_disabled(self) -> None:
        rs = RiskScoringConfig()
        assert rs.enhanced is False
        assert rs.use_architecture_centrality is False
        assert rs.use_change_frequency is False

    def test_default_timeouts(self) -> None:
        rs = RiskScoringConfig()
        assert rs.git_timeout_seconds == 10
        assert rs.graph_timeout_seconds == 5

    def test_default_commits_cap(self) -> None:
        rs = RiskScoringConfig()
        assert rs.max_git_commits == 1000
        assert rs.max_git_paths == 5000

    def test_priority_bands_default(self) -> None:
        rs = RiskScoringConfig()
        assert rs.priority_bands.low == [0, 10]
        assert rs.priority_bands.medium == [11, 20]
        assert rs.priority_bands.high == [21, 35]
        assert rs.priority_bands.critical == [36, 100]

    def test_config_root_includes_risk_scoring(self) -> None:
        config = PharabiusConfig()
        assert hasattr(config, "risk_scoring")
        assert config.risk_scoring.enhanced is False

    def test_extra_keys_ignored(self) -> None:
        rs = RiskScoringConfig(unknown_key="value")
        assert rs.enhanced is False


# ── Centrality tests ──────────────────────────────────────────────────


class TestCentralitySignals:
    def test_no_graph_fallback(self, tmp_path: Path) -> None:
        signals = compute_centrality_signals(tmp_path, ["src/main.py"])
        assert len(signals) == 1
        assert signals[0].level == "Low"
        assert signals[0].value == FACTOR_SCALE["Low"]

    def test_empty_locations(self, tmp_path: Path) -> None:
        signals = compute_centrality_signals(tmp_path, [])
        assert len(signals) == 1  # fallback for empty
        assert signals[0].level == "Low"

    def test_with_graph_node_not_found(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".ai-debt"
        graph_dir.mkdir()
        graph = {
            "nodes": [{"id": "pkg.utils", "path": "pkg/utils.py"}],
            "edges": [],
        }
        (graph_dir / "architecture-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        signals = compute_centrality_signals(tmp_path, ["other/file.py"])
        assert signals[0].level == "Low"
        assert "not found" in signals[0].reason.lower()

    def test_high_fan_in(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".ai-debt"
        graph_dir.mkdir()
        nodes = [{"id": f"pkg.mod{i}", "path": f"pkg/mod{i}.py"} for i in range(10)]
        nodes.append({"id": "pkg.hub", "path": "pkg/hub.py"})
        edges = [{"source": f"pkg.mod{i}", "target": "pkg.hub"} for i in range(8)]
        graph = {"nodes": nodes, "edges": edges}
        (graph_dir / "architecture-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        signals = compute_centrality_signals(tmp_path, ["pkg/hub.py"])
        assert signals[0].level == "High"
        assert signals[0].value == FACTOR_SCALE["High"]
        assert "fan_in=8" in signals[0].reason

    def test_medium_fan_in(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".ai-debt"
        graph_dir.mkdir()
        nodes = [
            {"id": "pkg.a", "path": "pkg/a.py"},
            {"id": "pkg.b", "path": "pkg/b.py"},
            {"id": "pkg.c", "path": "pkg/c.py"},
            {"id": "pkg.d", "path": "pkg/d.py"},
            {"id": "pkg.e", "path": "pkg/e.py"},
        ]
        edges = [
            {"source": "pkg.a", "target": "pkg.c"},
            {"source": "pkg.b", "target": "pkg.c"},
            {"source": "pkg.d", "target": "pkg.c"},
        ]
        graph = {"nodes": nodes, "edges": edges}
        (graph_dir / "architecture-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        signals = compute_centrality_signals(tmp_path, ["pkg/c.py"])
        assert signals[0].level == "Medium"
        assert signals[0].value == FACTOR_SCALE["Medium"]

    def test_cycle_participation(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / ".ai-debt"
        graph_dir.mkdir()
        nodes = [
            {"id": "pkg.a", "path": "pkg/a.py"},
            {"id": "pkg.b", "path": "pkg/b.py"},
        ]
        edges = [
            {"source": "pkg.a", "target": "pkg.b"},
            {"source": "pkg.b", "target": "pkg.a"},
        ]
        sccs = [["pkg.a", "pkg.b"]]
        graph = {"nodes": nodes, "edges": edges, "strongly_connected_components": sccs}
        (graph_dir / "architecture-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        signals = compute_centrality_signals(tmp_path, ["pkg/a.py"])
        assert signals[0].level == "High"
        assert "cycle" in signals[0].reason.lower()


# ── Change frequency tests ────────────────────────────────────────────


class TestChangeFrequencySignals:
    def test_non_git_repo(self, tmp_path: Path) -> None:
        signals = compute_change_frequency_signals(tmp_path, ["src/main.py"])
        assert len(signals) == 1
        assert signals[0].level == "Low"
        assert signals[0].commit_count == 0
        assert "not a git" in signals[0].reason.lower()

    def test_empty_locations(self, tmp_path: Path) -> None:
        signals = compute_change_frequency_signals(tmp_path, [])
        assert len(signals) == 1
        assert signals[0].level == "Low"

    def test_real_git_repo(self, tmp_path: Path) -> None:
        """Test with an actual git repo (Pharabius if available)."""
        repo = Path(r"C:\Next-Era\Pharabius\pharabius")
        if not (repo / ".git").exists():
            pytest.skip("Pharabius repo not available")
        signals = compute_change_frequency_signals(repo, ["pyproject.toml"])
        assert len(signals) == 1
        assert signals[0].commit_count >= 0
        assert signals[0].level in ("Low", "Medium", "High")
        assert signals[0].value in FACTOR_SCALE.values()


# ── Integration tests ─────────────────────────────────────────────────


class TestEnhanceRiskBreakdown:
    def test_both_disabled(self, tmp_path: Path) -> None:
        result = enhance_risk_breakdown(
            tmp_path,
            ["src/main.py"],
            use_centrality=False,
            use_frequency=False,
        )
        assert result["architecture_centrality"]["value"] == FACTOR_SCALE["Low"]
        assert result["change_frequency"]["value"] == FACTOR_SCALE["Low"]

    def test_centrality_only(self, tmp_path: Path) -> None:
        result = enhance_risk_breakdown(
            tmp_path,
            ["src/main.py"],
            use_centrality=True,
            use_frequency=False,
        )
        assert "reason" in result["architecture_centrality"]
        assert result["change_frequency"]["value"] == FACTOR_SCALE["Low"]

    def test_provenance_fields(self, tmp_path: Path) -> None:
        result = enhance_risk_breakdown(
            tmp_path,
            ["src/main.py"],
            use_centrality=True,
            use_frequency=True,
        )
        for key in ["architecture_centrality", "change_frequency"]:
            assert "level" in result[key]
            assert "value" in result[key]
            assert "source" in result[key]
            assert "reason" in result[key]


class TestRecalculateRiskScore:
    def test_default_scores(self) -> None:
        template = {
            "technical_severity": 1,
            "architecture_centrality": 1,
            "blast_radius": 1,
            "change_frequency": 1,
            "test_gap": 0,
            "security_exposure": 0,
            "compliance_exposure": 0,
            "dependency_risk": 0,
            "operational_exposure": 0,
            "business_critical_proxy": 1,
            "remediation_simplicity": -1,
            "confidence_modifier": 0,
        }
        enhanced = {
            "architecture_centrality": {"value": 3, "level": "Medium"},
            "change_frequency": {"value": 5, "level": "High"},
        }
        score = recalculate_risk_score(template, enhanced)
        # 1+3+1+5+0+0+0+0+0+1-1+0 = 10
        # Wait: original was 1+1+1+1+0+0+0+0+0+1-1+0 = 4
        # With centrality=3, frequency=5: 1+3+1+5+0+0+0+0+0+1-1+0 = 10
        assert score == 10

    def test_high_centrality_high_frequency(self) -> None:
        template = {
            "technical_severity": 3,
            "architecture_centrality": 1,
            "blast_radius": 3,
            "change_frequency": 1,
            "test_gap": 0,
            "security_exposure": 5,
            "compliance_exposure": 0,
            "dependency_risk": 0,
            "operational_exposure": 0,
            "business_critical_proxy": 3,
            "remediation_simplicity": -1,
            "confidence_modifier": 0,
        }
        enhanced = {
            "architecture_centrality": {"value": 5, "level": "High"},
            "change_frequency": {"value": 5, "level": "High"},
        }
        score = recalculate_risk_score(template, enhanced)
        # 3+5+3+5+0+5+0+0+0+3-1+0 = 23
        assert score == 23


# ── Canonical immutability test ────────────────────────────────────────


class TestCanonicalImmutability:
    def test_default_scoring_unchanged(self, tmp_path: Path) -> None:
        """Default scoring must produce identical results to v1.4.0."""
        from pharabius.core.analyzer import RISK_SCORE_TEMPLATE, _score

        breakdown = dict(RISK_SCORE_TEMPLATE)
        score, priority = _score(breakdown)
        # v1.4.0 baseline: sum of defaults = 1+1+1+1+0+0+0+0+0+1-1+0 = 4
        # But actual findings have different breakdowns set by rules
        assert score == 4
        assert priority == "Low"


# ── Import contract test ──────────────────────────────────────────────


class TestImportContract:
    def test_scoring_imports_schemas_only(self) -> None:
        """scoring.py should only import stdlib + schemas, not cli or ai."""
        import inspect

        import pharabius.core.scoring as mod

        src = inspect.getsource(mod)
        assert "from pharabius.cli" not in src
        assert "from pharabius.ai" not in src
