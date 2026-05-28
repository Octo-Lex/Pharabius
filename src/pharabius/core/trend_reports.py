"""Trend report rendering (v2.1.0 S05).

Generates focused Markdown reports from TrendSummary.
All reports include honest limitations and do not imply causality.
"""

from __future__ import annotations

from pharabius.schemas.trend import TrendSummary


def render_risk_trends_md(summary: TrendSummary) -> str:
    """Render risk-focused trend report."""
    lines = ["# Risk Trends\n"]

    if len(summary.points) < 2:
        lines.append("**Status:** Insufficient data for risk trend analysis.\n")
        lines.append("At least 2 runs required.\n")
        return "\n".join(lines)

    baseline = summary.points[0]
    latest = summary.points[-1]

    lines.append(f"**Trajectory:** {summary.trajectory}\n")
    lines.append("## Severity Movement\n")
    lines.append("| Severity | Baseline | Latest | Delta |")
    lines.append("|----------|----------|--------|-------|")

    for sev in ["critical", "high", "medium", "low"]:
        b_val = getattr(baseline, sev)
        l_val = getattr(latest, sev)
        d = l_val - b_val
        sign = "+" if d > 0 else ""
        lines.append(f"| {sev.capitalize()} | {b_val} | {l_val} | {sign}{d} |")

    total_d = latest.total_findings - baseline.total_findings
    sign = "+" if total_d > 0 else ""
    lines.append(
        f"| **Total** | {baseline.total_findings} | {latest.total_findings} | {sign}{total_d} |"
    )
    lines.append("")

    lines.append("## Important\n")
    lines.append(
        "This report is based on available Pharabius run artifacts, "
        "not a scientific measure of engineering quality.\n"
    )

    return "\n".join(lines)


def render_category_trends_md(summary: TrendSummary) -> str:
    """Render category trend report.

    Only includes data when historical category data is available.
    Otherwise reports insufficient_data honestly.
    """
    lines = ["# Category Trends\n"]

    has_data = any(p.category_data_available for p in summary.points)
    if not has_data:
        lines.append("**Status:** Insufficient data for category trend analysis.\n")
        lines.append(
            "Run metadata does not store per-run category breakdowns. "
            "Category trends require historical debt-register snapshots "
            "which are not currently archived.\n"
        )
        return "\n".join(lines)

    # Only reached when category data is actually available
    baseline = summary.points[0]
    latest = summary.points[-1]

    if baseline.category_counts and latest.category_counts:
        all_cats = sorted(set(baseline.category_counts) | set(latest.category_counts))
        lines.append("| Category | Baseline | Latest | Delta |")
        lines.append("|----------|----------|--------|-------|")
        for cat in all_cats:
            b_val = baseline.category_counts.get(cat, 0)
            l_val = latest.category_counts.get(cat, 0)
            d = l_val - b_val
            sign = "+" if d > 0 else ""
            lines.append(f"| {cat} | {b_val} | {l_val} | {sign}{d} |")
        lines.append("")

    lines.append("## Important\n")
    lines.append(
        "This report is based on available Pharabius run artifacts, "
        "not a scientific measure of engineering quality.\n"
    )
    return "\n".join(lines)


def render_gate_trends_md(summary: TrendSummary) -> str:
    """Render gate result trend report."""
    lines = ["# Quality Gate Trends\n"]

    if not summary.points:
        lines.append("**Status:** No run data available.\n")
        return "\n".join(lines)

    lines.append("| Run | Date | Gate Result | Critical | High | Total |")
    lines.append("|-----|------|-------------|----------|------|-------|")

    for p in summary.points:
        gate_display: str = p.gate_result
        if p.gate_approximated:
            gate_display += "*"
        lines.append(
            f"| {p.run_id} | {p.timestamp[:10]} | {gate_display} "
            f"| {p.critical} | {p.high} | {p.total_findings} |"
        )
    lines.append("")

    approx_count = sum(1 for p in summary.points if p.gate_approximated)
    if approx_count > 0:
        lines.append(
            f"\\* Gate result approximated from severity counts "
            f"({approx_count}/{len(summary.points)} runs). "
            "Actual gate thresholds may differ.\n"
        )

    lines.append("## Important\n")
    lines.append(
        "This report is based on available Pharabius run artifacts, "
        "not a scientific measure of engineering quality.\n"
    )
    return "\n".join(lines)
