"""Tests for portfolio risk/category rollups (W45-S03)."""

from __future__ import annotations

from pharabius.core.portfolio import (
    compute_category_rollup,
    compute_risk_rollup,
    top_risk_repositories,
)
from pharabius.schemas.portfolio import PortfolioRepositoryEntry


def _entry(
    repo_id: str,
    total: int = 0,
    priorities: dict[str, int] | None = None,
    categories: list[str] | None = None,
) -> PortfolioRepositoryEntry:
    return PortfolioRepositoryEntry(
        repository_id=repo_id,
        project_name=repo_id,
        repository_path=f"/repos/{repo_id}",
        total_findings=total,
        priority_counts=priorities or {},
        top_categories=categories or [],
        highest_priority=max((p for p, c in (priorities or {}).items() if c > 0), default=None),
    )


class TestRiskRollup:
    def test_aggregates_priorities(self) -> None:
        entries = [
            _entry("a", total=5, priorities={"High": 3, "Low": 2}),
            _entry("b", total=3, priorities={"Critical": 1, "Medium": 2}),
        ]
        rollup = compute_risk_rollup(entries)
        assert rollup.total_repositories == 2
        assert rollup.total_findings == 8
        assert rollup.priority_counts == {"High": 3, "Low": 2, "Critical": 1, "Medium": 2}
        assert rollup.highest_priority == "Critical"

    def test_empty_entries(self) -> None:
        rollup = compute_risk_rollup([])
        assert rollup.total_repositories == 0
        assert rollup.total_findings == 0
        assert rollup.highest_priority is None

    def test_no_priorities(self) -> None:
        entries = [_entry("x", total=0)]
        rollup = compute_risk_rollup(entries)
        assert rollup.priority_counts == {}


class TestCategoryRollup:
    def test_aggregates_categories(self) -> None:
        entries = [
            _entry("a", categories=["TD-ARCH", "TD-DEP"]),
            _entry("b", categories=["TD-ARCH", "TD-TEST"]),
        ]
        rollup = compute_category_rollup(entries)
        assert rollup.category_counts["TD-ARCH"] == 2
        assert rollup.category_counts["TD-DEP"] == 1
        assert rollup.category_counts["TD-TEST"] == 1

    def test_top_categories_ordered(self) -> None:
        entries = [
            _entry("a", categories=["TD-ARCH", "TD-ARCH", "TD-DEP"]),
            _entry("b", categories=["TD-TEST"]),
        ]
        rollup = compute_category_rollup(entries)
        # TD-ARCH count=2, TD-DEP=1, TD-TEST=1; sorted by count desc, name asc
        assert rollup.top_categories[0] == "TD-ARCH"

    def test_empty_entries(self) -> None:
        rollup = compute_category_rollup([])
        assert rollup.category_counts == {}
        assert rollup.top_categories == []


class TestTopRiskRepositories:
    def test_ordering_by_risk(self) -> None:
        entries = [
            _entry("low", total=1, priorities={"Low": 1}),
            _entry("crit", total=1, priorities={"Critical": 1}),
            _entry("high", total=1, priorities={"High": 1}),
        ]
        result = top_risk_repositories(entries)
        assert result[0] == "crit"
        assert result[1] == "high"
        assert result[2] == "low"

    def test_limit(self) -> None:
        entries = [_entry(f"r{i}", total=i) for i in range(20)]
        result = top_risk_repositories(entries, limit=5)
        assert len(result) == 5

    def test_same_risk_uses_id(self) -> None:
        entries = [
            _entry("beta", total=1, priorities={"High": 1}),
            _entry("alpha", total=1, priorities={"High": 1}),
        ]
        result = top_risk_repositories(entries)
        assert result[0] == "alpha"

    def test_empty(self) -> None:
        result = top_risk_repositories([])
        assert result == []
