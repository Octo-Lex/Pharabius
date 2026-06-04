from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pharabius.schemas.analysis_unit import AnalysisUnitStore
from pharabius.schemas.evidence import EvidenceItem, EvidenceStore
from pharabius.schemas.finding import DebtFinding, DebtRegister
from pharabius.schemas.repository import RepositoryProfile


@dataclass(frozen=True)
class ReportWriteResult:
    files_written: list[Path]


@dataclass(frozen=True)
class ReportContext:
    repository_root: Path
    profile: RepositoryProfile
    evidence_store: EvidenceStore
    debt_register: DebtRegister


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if isinstance(value, dict):
        return value

    return {}


def _load_profile(root: Path) -> RepositoryProfile:
    path = root / ".ai-debt" / "project-profile.json"
    data = _load_json(path)

    if not data:
        return RepositoryProfile.empty(root)

    return RepositoryProfile.model_validate(data)


def _load_evidence_store(root: Path) -> EvidenceStore:
    path = root / ".ai-debt" / "evidence.json"
    data = _load_json(path)

    if not data:
        return EvidenceStore(repository=str(root), evidence=[])

    return EvidenceStore.model_validate(data)


def _load_debt_register(root: Path) -> DebtRegister:
    path = root / ".ai-debt" / "debt-register.json"
    data = _load_json(path)

    if not data:
        return DebtRegister(project_name=root.name, repository=str(root))

    return DebtRegister.model_validate(data)


def _load_units_if_exists(root: Path) -> AnalysisUnitStore | None:
    """Load AnalysisUnitStore if file exists, else None."""
    path = root / ".ai-debt" / "analysis-units.json"
    if not path.exists():
        return None
    try:
        return AnalysisUnitStore.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _context(repository_root: Path) -> ReportContext:
    root = repository_root.resolve()

    return ReportContext(
        repository_root=root,
        profile=_load_profile(root),
        evidence_store=_load_evidence_store(root),
        debt_register=_load_debt_register(root),
    )


def _items_by_type(ctx: ReportContext, evidence_type: str) -> list[EvidenceItem]:
    return [item for item in ctx.evidence_store.evidence if item.type == evidence_type]


def _findings_by_category(ctx: ReportContext, category: str) -> list[DebtFinding]:
    return [finding for finding in ctx.debt_register.findings if finding.category == category]


def _findings_in_categories(
    ctx: ReportContext,
    categories: set[str],
) -> list[DebtFinding]:
    return [finding for finding in ctx.debt_register.findings if finding.category in categories]


def _bullet_list(values: list[str], empty: str = "None detected.") -> list[str]:
    if not values:
        return [f"- {empty}"]

    return [f"- `{value}`" for value in values]


def _unit_summary_table(units: Sequence[object], unit_type: str | None = None) -> list[str]:
    """Render a markdown table of analysis units."""
    filtered = units
    if unit_type:
        filtered = [u for u in units if getattr(u, "unit_type", "") == unit_type]
    if not filtered:
        return ["None detected."]
    lines = [
        "| ID | Name | Files | Evidence |",
        "|---|---|---:|---:|",
    ]
    for u in filtered:
        uid = getattr(u, "analysis_unit_id", "")
        name = getattr(u, "name", "")
        files = len(getattr(u, "files", []))
        evcount = len(getattr(u, "evidence_ids", []))
        lines.append(f"| `{uid}` | {name} | {files} | {evcount} |")
    return lines


def _units_by_type_section(units: Sequence[object]) -> list[str]:
    """Render a type-grouped analysis units summary."""
    if not units:
        return []
    lines: list[str] = []
    by_type: dict[str, list[object]] = {}
    for u in units:
        ut = getattr(u, "unit_type", "unknown")
        by_type.setdefault(ut, []).append(u)
    for ut in sorted(by_type):
        lines.append(f"### {ut.replace('_', ' ').title()}")
        lines.append("")
        for u in by_type[ut]:
            uid = getattr(u, "analysis_unit_id", "")
            name = getattr(u, "name", "")
            primary = getattr(u, "primary_files", [])
            primary_str = primary[0] if primary else "N/A"
            lines.append(f"- **{name}** (`{uid}`)")
            lines.append(f"  - Primary: `{primary_str}`")
            lines.append(f"  - Evidence: {len(getattr(u, 'evidence_ids', []))} items")
        lines.append("")
    return lines


def _evidence_table(items: list[EvidenceItem], limit: int = 20) -> list[str]:
    lines = [
        "| Evidence ID | Type | Location | Summary |",
        "|---|---|---|---|",
    ]

    if not items:
        lines.append("| N/A | N/A | N/A | No evidence detected. |")
        return lines

    for item in items[:limit]:
        location = item.location.file or "N/A"
        summary = item.summary.replace("\n", " ")
        lines.append(f"| `{item.evidence_id}` | `{item.type}` | `{location}` | {summary} |")

    if len(items) > limit:
        lines.append(
            f"| ... | ... | ... | {len(items) - limit} additional evidence items omitted. |"
        )

    return lines


def _finding_table(findings: list[DebtFinding]) -> list[str]:
    lines = [
        "| ID | Category | Priority | Score | Title | Evidence |",
        "|---|---|---|---:|---|---|",
    ]

    if not findings:
        lines.append("| N/A | N/A | N/A | 0 | No findings in this area. | N/A |")
        return lines

    for finding in findings:
        evidence = ", ".join(f"`{evidence_id}`" for evidence_id in finding.evidence_ids)
        lines.append(
            "| "
            f"`{finding.id}` | "
            f"`{finding.category}` | "
            f"{finding.priority} | "
            f"{finding.risk_score} | "
            f"{finding.title} | "
            f"{evidence} |"
        )

    return lines


def _evidence_type_counts(ctx: ReportContext) -> Counter[str]:
    return Counter(item.type for item in ctx.evidence_store.evidence)


def _risk_keyword_counts(items: list[EvidenceItem]) -> Counter[str]:
    counter: Counter[str] = Counter()

    for item in items:
        keywords = item.metadata.get("keywords", [])
        if not isinstance(keywords, list):
            continue

        for keyword in keywords:
            if isinstance(keyword, str):
                counter[keyword] += 1

    return counter


def render_architecture_map(ctx: ReportContext) -> str:
    import_items = _items_by_type(ctx, "imports_detected")
    deployment_items = _items_by_type(ctx, "deployment_file_detected")
    infrastructure_items = _items_by_type(ctx, "infrastructure_file_detected")
    architecture_findings = _findings_by_category(ctx, "TD-ARCH")

    lines = [
        "# Architecture Map",
        "",
        "## Repository Overview",
        "",
        f"- Project: `{ctx.profile.project_name}`",
        f"- Repository: `{ctx.repository_root}`",
        f"- Monorepo detected: `{ctx.profile.monorepo}`",
        f"- Analysis confidence: `{ctx.profile.analysis_confidence}`",
        "",
        "## Detected Languages",
        "",
        *_bullet_list(ctx.profile.detected_languages),
        "",
        "## Detected Frameworks",
        "",
        *_bullet_list(ctx.profile.detected_frameworks),
        "",
        "## Entry Points",
        "",
        *_bullet_list(ctx.profile.entry_points),
        "",
        "## Services or Packages",
        "",
        *_bullet_list(ctx.profile.services_or_packages),
        "",
        "## Architecture Evidence Summary",
        "",
        f"- Import evidence items: `{len(import_items)}`",
        f"- Deployment evidence items: `{len(deployment_items)}`",
        f"- Infrastructure evidence items: `{len(infrastructure_items)}`",
        "",
        "## Import Evidence",
        "",
        *_evidence_table(import_items, limit=25),
        "",
        "## Architecture Findings",
        "",
        *_finding_table(architecture_findings),
        "",
        "## Interpretation",
        "",
    ]

    if architecture_findings:
        lines.extend(
            [
                "Architecture risk is based on findings already present in the debt register.",
                "This report does not create additional architecture findings.",
            ]
        )
    else:
        lines.extend(
            [
                "No deterministic architecture debt findings were present in the debt register.",
                "This does not prove architectural health; it means the current analyzer did not",
                "produce supported `TD-ARCH` findings from the available evidence.",
            ]
        )

    # Analysis Units
    unit_store = _load_units_if_exists(ctx.repository_root)
    if unit_store is not None and unit_store.units:
        lines.extend(
            [
                "",
                "## Detected Analysis Units",
                "",
                *_units_by_type_section(unit_store.units),
            ]
        )

    lines.append("")
    return "\n".join(lines)


def render_dependency_health(ctx: ReportContext) -> str:
    manifest_items = _items_by_type(ctx, "manifest_detected")
    dependency_findings = _findings_by_category(ctx, "TD-DEP")

    lockfile_items = [
        item
        for item in manifest_items
        if "lockfile" in item.object or "lockfile" in item.raw_observation
    ]

    lines = [
        "# Dependency Health",
        "",
        "## Detected Package Managers",
        "",
        *_bullet_list(ctx.profile.package_managers),
        "",
        "## Detected Build Tools",
        "",
        *_bullet_list(ctx.profile.build_tools),
        "",
        "## Manifest Evidence",
        "",
        *_evidence_table(manifest_items, limit=30),
        "",
        "## Lockfile Evidence",
        "",
        *_evidence_table(lockfile_items, limit=30),
        "",
        "## Dependency Findings",
        "",
        *_finding_table(dependency_findings),
        "",
        "## Interpretation",
        "",
    ]

    if dependency_findings:
        lines.extend(
            [
                "Dependency risk is based on debt-register findings and manifest evidence.",
                "Validate package-manager policy before applying lockfile or upgrade changes.",
            ]
        )
    else:
        lines.extend(
            [
                "No deterministic dependency debt findings were present in the debt register.",
                (
                    "Dependency freshness and vulnerability status require "
                    "future scanner integration."
                ),
            ]
        )

    lines.append("")
    return "\n".join(lines)


def render_test_health(ctx: ReportContext) -> str:
    test_items = _items_by_type(ctx, "test_file_detected")
    test_script_items = [
        item for item in _items_by_type(ctx, "package_script_detected") if item.category == "test"
    ]
    test_findings = _findings_by_category(ctx, "TD-TEST")

    lines = [
        "# Test Health",
        "",
        "## Detected Test Frameworks",
        "",
        *_bullet_list(ctx.profile.test_frameworks),
        "",
        "## Detected Test Directories",
        "",
        *_bullet_list(ctx.profile.test_directories),
        "",
        "## Test File Evidence",
        "",
        *_evidence_table(test_items, limit=30),
        "",
        "## Test Script Evidence",
        "",
        *_evidence_table(test_script_items, limit=30),
        "",
        "## Test Findings",
        "",
        *_finding_table(test_findings),
        "",
        "## Interpretation",
        "",
    ]

    if test_findings:
        lines.extend(
            [
                "Test risk is based on debt-register findings and test-related evidence.",
                "Prioritize regression tests before broad remediation work.",
            ]
        )
    elif test_items or test_script_items or ctx.profile.test_frameworks:
        lines.extend(
            [
                "Test evidence was detected. This report does not assess coverage quality yet.",
                ("Future versions should ingest coverage reports and test execution results."),
            ]
        )
    else:
        lines.extend(
            [
                "No test evidence was detected by the current scanner.",
                "This should be validated with the Product Engineering Team.",
            ]
        )

    # Test suite analysis units
    unit_store = _load_units_if_exists(ctx.repository_root)
    if unit_store is not None:
        test_units = [u for u in unit_store.units if getattr(u, "unit_type", "") == "test_suite"]
        if test_units:
            lines.extend(
                [
                    "",
                    "## Test Suite Analysis Units",
                    "",
                    "| ID | Files | Evidence | Confidence |",
                    "|---|---:|---:|---|",
                ]
            )
            for u in test_units:
                uid = getattr(u, "analysis_unit_id", "")
                files = len(getattr(u, "files", []))
                evcount = len(getattr(u, "evidence_ids", []))
                conf = getattr(u, "confidence", "N/A")
                lines.append(f"| `{uid}` | {files} | {evcount} | {conf} |")

    lines.append("")
    return "\n".join(lines)


def render_security_exposure(ctx: ReportContext) -> str:
    risk_items = [
        item
        for item in ctx.evidence_store.evidence
        if item.type
        in {
            "risk_sensitive_path_detected",
            "risk_sensitive_keyword_detected",
        }
    ]

    security_findings = _findings_in_categories(
        ctx,
        {"TD-SEC", "TD-COMP", "TD-CONFIG"},
    )
    keyword_counts = _risk_keyword_counts(risk_items)

    lines = [
        "# Security and Compliance Exposure",
        "",
        "## Scope Note",
        "",
        "This report identifies repository evidence that may indicate sensitive areas.",
        "It does not prove vulnerabilities or compliance violations.",
        "",
        "## Risk-Sensitive Evidence",
        "",
        *_evidence_table(risk_items, limit=40),
        "",
        "## Keyword Signals",
        "",
    ]

    if keyword_counts:
        lines.extend(
            [
                "| Keyword | Evidence count |",
                "|---|---:|",
            ]
        )
        for keyword, count in keyword_counts.most_common(25):
            lines.append(f"| `{keyword}` | {count} |")
    else:
        lines.append("No risk-sensitive keyword signals detected.")

    lines.extend(
        [
            "",
            "## Security, Compliance, and Configuration Findings",
            "",
            *_finding_table(security_findings),
            "",
            "## Interpretation",
            "",
        ]
    )

    if security_findings:
        lines.extend(
            [
                "Security and compliance exposure is based on debt-register findings.",
                "All inferred impact should be validated with security and product owners.",
            ]
        )
    elif risk_items:
        lines.extend(
            [
                (
                    "Risk-sensitive signals exist, but no deterministic "
                    "security finding was created."
                ),
                ("This usually means the available evidence is not strong enough for a finding."),
            ]
        )
    else:
        lines.extend(
            [
                "No risk-sensitive evidence was detected by the current scanner.",
                "This does not replace security review or dependency vulnerability scanning.",
            ]
        )

    # Security-sensitive analysis units
    unit_store = _load_units_if_exists(ctx.repository_root)
    if unit_store is not None:
        sec_units = [
            u for u in unit_store.units if getattr(u, "unit_type", "") == "security_sensitive_area"
        ]
        if sec_units:
            lines.extend(
                [
                    "",
                    "## Security-Sensitive Analysis Units",
                    "",
                    "| ID | Tags | Files | Evidence |",
                    "|---|---|---:|---:|",
                ]
            )
            for u in sec_units:
                uid = getattr(u, "analysis_unit_id", "")
                tags = ", ".join(getattr(u, "trust_boundary_tags", []))
                files = len(getattr(u, "files", []))
                evcount = len(getattr(u, "evidence_ids", []))
                lines.append(f"| `{uid}` | {tags} | {files} | {evcount} |")

    lines.append("")
    return "\n".join(lines)


def render_business_risk_proxy(ctx: ReportContext) -> str:
    risk_items = [
        item
        for item in ctx.evidence_store.evidence
        if item.type
        in {
            "risk_sensitive_path_detected",
            "risk_sensitive_keyword_detected",
        }
    ]
    keyword_counts = _risk_keyword_counts(risk_items)
    high_priority_findings = [
        finding
        for finding in ctx.debt_register.findings
        if finding.priority in {"High", "Critical"}
    ]

    lines = [
        "# Business Risk Proxy",
        "",
        "## Scope Note",
        "",
        "Business impact in this report is inferred from repository evidence.",
        ("Validate all business-criticality assumptions with the Product Engineering Team."),
        "",
        "## Strongest Repository Signals",
        "",
    ]

    if keyword_counts:
        lines.extend(
            [
                "| Signal | Evidence count |",
                "|---|---:|",
            ]
        )
        for keyword, count in keyword_counts.most_common(20):
            lines.append(f"| `{keyword}` | {count} |")
    else:
        lines.append("No business-risk keyword signals were detected.")

    lines.extend(
        [
            "",
            "## Highest-Priority Findings",
            "",
            *_finding_table(high_priority_findings),
            "",
            "## Inferred Business-Risk Interpretation",
            "",
        ]
    )

    if high_priority_findings:
        lines.extend(
            [
                "The highest-priority findings should be reviewed first for planning impact.",
                ("The analyzer uses repository evidence only and does not know revenue, SLA,"),
                ("customer impact, incident history, or product roadmap commitments."),
            ]
        )
    elif ctx.debt_register.findings:
        lines.extend(
            [
                "Findings exist, but none are currently prioritized as High or Critical.",
                "Review Medium findings if they affect ownership, release, or onboarding.",
            ]
        )
    else:
        lines.extend(
            [
                "No deterministic debt findings were available for business-risk synthesis.",
                "This should be revisited after richer evidence sources are added.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def render_foundation_audit_report(ctx: ReportContext) -> str:
    counts = _evidence_type_counts(ctx)
    findings = ctx.debt_register.findings

    lines = [
        "# Foundation Technical Debt Audit Report",
        "",
        "## 1. Repository Overview",
        "",
        f"- Project: `{ctx.profile.project_name}`",
        f"- Repository: `{ctx.repository_root}`",
        f"- Branch: `{ctx.debt_register.branch or 'Unknown'}`",
        f"- Commit: `{ctx.debt_register.commit or 'Unknown'}`",
        f"- Analysis confidence: `{ctx.profile.analysis_confidence}`",
        "",
        "## 2. Analysis Method",
        "",
        "This report is generated from deterministic Pharabius artifacts:",
        "",
        "- `.ai-debt/project-profile.json`",
        "- `.ai-debt/evidence.json`",
        "- `.ai-debt/debt-register.json`",
        "",
        "No AI reasoning is required for this report generation step.",
        "",
        "## 3. Project Profile",
        "",
        "### Languages",
        "",
        *_bullet_list(ctx.profile.detected_languages),
        "",
        "### Frameworks",
        "",
        *_bullet_list(ctx.profile.detected_frameworks),
        "",
        "### Package Managers",
        "",
        *_bullet_list(ctx.profile.package_managers),
        "",
        "## 4. Evidence Summary",
        "",
        "| Evidence type | Count |",
        "|---|---:|",
    ]

    if counts:
        for evidence_type, count in counts.most_common():
            lines.append(f"| `{evidence_type}` | {count} |")
    else:
        lines.append("| N/A | 0 |")

    lines.extend(
        [
            "",
            "## 5. Debt Register Summary",
            "",
            "| Severity | Count |",
            "|---|---:|",
            f"| Critical | {ctx.debt_register.summary.critical} |",
            f"| High | {ctx.debt_register.summary.high} |",
            f"| Medium | {ctx.debt_register.summary.medium} |",
            f"| Low | {ctx.debt_register.summary.low} |",
            "",
            f"Total findings: **{ctx.debt_register.summary.total_findings}** "
            f"(technical debt: {ctx.debt_register.summary.technical_debt_count}, "
            f"advisories: {ctx.debt_register.summary.advisory_count})",
            "",
            "## 6. Top Findings",
            "",
            *_finding_table(findings[:10]),
        ]
    )

    # Advisory section (v3.7.0)
    advisories = [f for f in findings if f.issue_type == "advisory"]
    if advisories:
        lines.extend(
            [
                "",
                "## 6b. Advisory Signals",
                "",
                "> These are hygiene observations, not actionable debt.",
                "> They do not generate work packages or operational claims by default.",
                "",
                "| Category | Title | Severity | Risk Score |",
                "|---|---|---|---:|",
            ]
        )
        for a in advisories:
            lines.append(f"| {a.category} | {a.title[:80]} | {a.severity} | {a.risk_score} |")

    # Runtime reproducibility section (v3.9.0)
    runtime_evidence = [
        e for e in ctx.evidence_store.evidence if e.type == "runtime_version_signal"
    ]
    if runtime_evidence:
        runtime_by_signal: dict[str, list] = {}
        for re_ev in runtime_evidence:
            sig = re_ev.metadata.get("signal", "unknown")
            runtime_by_signal.setdefault(sig, []).append(re_ev)

        lines.extend(
            [
                "",
                "## 6c. Runtime Reproducibility",
                "",
            ]
        )

        if runtime_by_signal.get("runtime_version_conflict"):
            lines.append("**Conflicts detected.** See debt register for details.")
            lines.append("")

        pinned = runtime_by_signal.get("runtime_version_pinned", [])
        if pinned:
            lines.append("| Runtime | Source | Version | Constraint |")
            lines.append("|---|---|---|---|")
            for p in pinned:
                rt = p.metadata.get("runtime", "?")
                src = p.metadata.get("source_file", "?")
                ver = p.metadata.get("version", "?")
                ck = p.metadata.get("constraint_kind", "?")
                lines.append(f"| {rt} | {src} | {ver} | {ck} |")
            lines.append("")

        missing = runtime_by_signal.get("runtime_version_missing", [])
        if missing:
            runtimes = [m.metadata.get("runtime", "?") for m in missing]
            lines.append(f"**Missing pins:** {', '.join(runtimes)}")
            lines.append("")

    # Signal governance summary (v3.12.0)
    _add_signal_governance_section(lines, ctx)

    lines.extend(
        [
            "",
            "## 7. Architecture Summary",
            "",
            "See `architecture-map.md` for architecture and import evidence.",
            "",
            "## 8. Dependency Health",
            "",
            "See `dependency-health.md` for manifest, lockfile, and dependency findings.",
            "",
            "## 9. Test Health",
            "",
            "See `test-health.md` for test framework and test evidence.",
            "",
            "## 10. Security and Compliance Exposure",
            "",
            "See `security-exposure.md` for sensitive path and keyword evidence.",
            "",
            "## 11. Business-Risk Proxy",
            "",
            "See `business-risk-proxy.md` for inferred business-risk signals.",
            "",
            "## 12. Uncertainties and Limitations",
            "",
        ]
    )

    limitations = ctx.profile.limitations
    if limitations:
        lines.extend(_bullet_list(limitations, empty="No limitations recorded."))
    else:
        lines.append("- No profile limitations recorded.")

    # Analysis Units Summary (if available)
    unit_store = _load_units_if_exists(ctx.repository_root)
    if unit_store is not None and unit_store.units:
        lines.extend(
            [
                "",
                "## 13. Analysis Units Summary",
                "",
                f"Total analysis units: **{len(unit_store.units)}**",
                "",
                *_unit_summary_table(unit_store.units),
                "",
            ]
        )
        # Renumber remaining section
        lines.extend(
            [
                "## 14. Product Engineering Handoff",
                "",
                "Recommended next action:",
                "",
            ]
        )

    if findings:
        lines.extend(
            [
                "1. Review the debt register findings.",
                ("2. Validate inferred business impact with Product Engineering owners."),
                ("3. Use `ai-debt plan` to generate remediation roadmap and work packages."),
            ]
        )
    else:
        lines.extend(
            [
                "1. Validate that the repository evidence is complete.",
                "2. Add richer scanner integrations if deeper analysis is required.",
                ("3. Continue to `ai-debt plan` only if planning artifacts are needed."),
            ]
        )

    lines.append("")
    return "\n".join(lines)


def write_reports(repository_root: Path) -> ReportWriteResult:
    ctx = _context(repository_root)
    root = ctx.repository_root
    workspace = root / ".ai-debt"

    report_contents = {
        workspace / "architecture-map.md": render_architecture_map(ctx),
        workspace / "dependency-health.md": render_dependency_health(ctx),
        workspace / "test-health.md": render_test_health(ctx),
        workspace / "security-exposure.md": render_security_exposure(ctx),
        workspace / "business-risk-proxy.md": render_business_risk_proxy(ctx),
        workspace / "reports" / "foundation-audit-report.md": render_foundation_audit_report(ctx),
    }

    files_written: list[Path] = []

    for path, content in report_contents.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        files_written.append(path)

    return ReportWriteResult(files_written=files_written)


def _add_signal_governance_section(lines: list[str], ctx: ReportContext) -> None:
    """Add signal governance summary section to the foundation report (v3.13.0).

    Builds from GovernedSignal instances, not raw evidence heuristics.
    """
    from pharabius.core.constants import (
        EVIDENCE_RUNTIME_VERSION_SIGNAL,
        RUNTIME_SIGNAL_CONFLICT,
        RUNTIME_SIGNAL_MISSING,
    )
    from pharabius.core.signals.adapters import (
        build_ci_evidence_to_signal,
        build_missing_ci_to_signal,
        docs_evidence_to_signal,
        docs_missing_to_signal,
        process_missing_artifacts_to_signal,
        runtime_conflict_to_signal_from_evidence,
        runtime_missing_pin_to_signal_from_evidence,
        scan_test_coverage_evidence_to_signal,
        scan_test_coverage_gap_to_signal,
        scan_test_evidence_to_signal,
        scan_test_missing_to_signal,
        scan_test_risk_sensitive_without_tests_to_signal,
    )
    from pharabius.core.signals.summary import build_signal_summary

    signals = []

    # ── Runtime signals ──
    for ev in ctx.evidence_store.evidence:
        if ev.type != EVIDENCE_RUNTIME_VERSION_SIGNAL:
            continue
        signal_kind = ev.metadata.get("signal", "")
        if signal_kind == RUNTIME_SIGNAL_CONFLICT:
            signals.append(runtime_conflict_to_signal_from_evidence(ev))
        elif signal_kind == RUNTIME_SIGNAL_MISSING:
            signals.append(runtime_missing_pin_to_signal_from_evidence([ev]))
        # Informational runtime evidence not needed for report summary

    # ── Documentation signals ──
    docs_evidence = [
        e for e in ctx.evidence_store.evidence if e.type == "documentation_file_detected"
    ]
    for ev in docs_evidence:
        signals.append(docs_evidence_to_signal(ev))

    # Check for documentation advisory in findings
    doc_advisory = next(
        (
            f
            for f in ctx.debt_register.findings
            if f.category == "TD-DOC" and f.issue_type == "advisory"
        ),
        None,
    )
    if doc_advisory:
        signals.append(
            docs_missing_to_signal(
                evidence_ids=doc_advisory.evidence_ids[:1] if doc_advisory.evidence_ids else []
            )
        )

    # ── Build signals ──
    ci_evidence = [e for e in ctx.evidence_store.evidence if e.type == "deployment_file_detected"]
    for ev in ci_evidence:
        signals.append(build_ci_evidence_to_signal(ev))

    build_advisory = next(
        (
            f
            for f in ctx.debt_register.findings
            if f.category == "TD-BUILD" and f.issue_type == "advisory"
        ),
        None,
    )
    if build_advisory:
        signals.append(build_missing_ci_to_signal(evidence_ids=build_advisory.evidence_ids))

    # ── Process signals ──
    process_advisory = next(
        (
            f
            for f in ctx.debt_register.findings
            if f.category == "TD-PROCESS" and f.issue_type == "advisory"
        ),
        None,
    )
    if process_advisory:
        desc = process_advisory.description or ""
        missing = [
            t
            for t in ["CODEOWNERS", "CONTRIBUTING", "PULL_REQUEST_TEMPLATE"]
            if t.lower() in desc.lower()
        ]
        signals.append(
            process_missing_artifacts_to_signal(
                missing_artifacts=missing or ["unknown"],
                evidence_ids=process_advisory.evidence_ids,
            )
        )

    # ── Test signals ──
    test_evidence = [e for e in ctx.evidence_store.evidence if e.type == "test_file_detected"]
    for ev in test_evidence:
        signals.append(scan_test_evidence_to_signal(ev))

    coverage_types = {"coverage_report_detected", "coverage_metric_detected"}
    for ev in [e for e in ctx.evidence_store.evidence if e.type in coverage_types]:
        signals.append(scan_test_coverage_evidence_to_signal(ev))

    # Test-related findings from debt register
    test_findings = [
        f
        for f in ctx.debt_register.findings
        if f.category == "TD-TEST" and f.issue_type != "advisory"
    ]
    for f in test_findings:
        if "coverage" in (f.title or "").lower():
            signals.append(
                scan_test_coverage_gap_to_signal(
                    evidence_ids=f.evidence_ids,
                    low_count=f.evidence_ids.__len__(),
                )
            )
        else:
            signals.append(scan_test_missing_to_signal(evidence_ids=f.evidence_ids))

    # Risk-sensitive without tests
    risk_sensitive_finding = next(
        (
            f
            for f in ctx.debt_register.findings
            if f.category == "TD-SEC"
            and "test" in (f.title or "").lower()
            and f.issue_type != "advisory"
        ),
        None,
    )
    if risk_sensitive_finding:
        signals.append(
            scan_test_risk_sensitive_without_tests_to_signal(
                evidence_ids=risk_sensitive_finding.evidence_ids,
            )
        )

    if not signals:
        return

    # ── Build summary from signals ──
    summary = build_signal_summary(signals)

    # Count by family and disposition
    family_rows: dict[str, dict[str, int]] = {}
    for signal in signals:
        fam = signal.family.value
        disp = signal.disposition.value
        if fam not in family_rows:
            family_rows[fam] = {"finding": 0, "advisory": 0, "informational": 0, "suppressed": 0}
        family_rows[fam][disp] += 1

    lines.extend(
        [
            "",
            "## 6d. Signal Governance Summary",
            "",
            "| Family | Findings | Advisories | Informational | Suppressed |",
            "|---|---:|---:|---:|---:|",
        ]
    )

    for fam in sorted(family_rows.keys()):
        r = family_rows[fam]
        lines.append(
            f"| {fam.title()} | {r['finding']} | {r['advisory']} | {r['informational']} | {r['suppressed']} |"  # noqa: E501
        )

    lines.extend(
        [
            "",
            "> Findings are promoted into the technical debt register and may create work packages.",  # noqa: E501
            "> Advisories are reportable but do not create work packages.",
            "> Informational signals provide context and coverage visibility.",
            "> Suppressed signals are diagnostics-only and omitted from normal reports unless diagnostics are enabled.",  # noqa: E501
            "",
            "> Category describes the finding taxonomy (e.g., TD-DEP, TD-SEC).",
            "> Family describes the governance owner (e.g., dependency, security).",
            "> Category and family are not always identical: TD-COMP → SECURITY, TD-SEC → TEST.",
            "",
        ]
    )

    # ── Governance quality metrics (v3.23.0) ──
    from pharabius.core.signals.quality import build_governance_quality_metrics

    metrics = build_governance_quality_metrics(signals)

    lines.extend(
        [
            "",
            "## 6e. Governance Quality Metrics",
            "",
            f"| Metric | Value |",
            f"|---|---:|",
            f"| Total governed signals | {metrics.total_signals} |",
            f"| Finding evidence coverage | {metrics.finding_evidence_coverage:.0%} |",
            f"| Finding metadata coverage | {metrics.finding_metadata_coverage:.0%} |",
            f"| Advisory evidence/basis coverage | {metrics.advisory_evidence_coverage:.0%} |",
            f"| Informational evidence coverage | {metrics.informational_evidence_coverage:.0%} |",
            "",
        ]
    )

    # Disposition breakdown
    if metrics.by_disposition:
        lines.extend(
            [
                "| Disposition | Count |",
                "|---|---:|",
            ]
        )
        for disp, count in sorted(metrics.by_disposition.items()):
            lines.append(f"| {disp.title()} | {count} |")
        lines.append("")

    # Confidence breakdown
    if metrics.by_confidence:
        lines.extend(
            [
                "| Confidence | Count |",
                "|---|---:|",
            ]
        )
        for conf, count in sorted(metrics.by_confidence.items()):
            lines.append(f"| {conf} | {count} |")
        lines.append("")

    # Diagnostics
    if metrics.diagnostics:
        lines.extend(
            [
                "| Code | Severity | Message |",
                "|---|---|---|",
            ]
        )
        for d in metrics.diagnostics:
            lines.append(f"| {d.code} | {d.severity} | {d.message} |")
        lines.append("")

    lines.extend(
        [
            "> These metrics are descriptive only.",
            "> No quality gates are applied.",
            "> No signal is promoted or demoted by these metrics.",
            "",
        ]
    )

    # ── Governance quality trends (v3.24.0) ──
    # Compute trend from run-history if available
    try:
        from pharabius.core.run_history import _load_json, build_run_history_index
        from pharabius.core.signals.trends import (
            build_governance_trend_summary,
            format_count_delta,
            format_coverage_delta,
        )

        workspace = ctx.repository_root / ".ai-debt"
        index = build_run_history_index(workspace)
        runs = index.get("runs", [])

        # Load snapshots with governance_quality
        snapshots = []
        for r in reversed(runs):
            snap = _load_json(workspace / "runs" / f"{r.get('run_id', '')}-history-snapshot.json")
            if snap and snap.get("governance_quality") is not None:
                snapshots.insert(0, snap)  # maintain chronological order
                if len(snapshots) >= 2:
                    break

        trend = build_governance_trend_summary(snapshots)
    except Exception:
        trend = None

    if trend and trend.unavailable_reason is None:
        lines.extend(
            [
                "",
                "## 6f. Governance Quality Trends",
                "",
                "These trends compare governance quality metrics across recent runs. They are",
                "descriptive only; no quality gates, thresholds, or pass/fail rules are applied.",
                "",
                "| Metric | Previous | Current | Change |",
                "|---|---:|---:|---:|",
                f"| Total governed signals | {trend.signal_count_delta.previous or 0} | {trend.signal_count_delta.current} | {format_count_delta(trend.signal_count_delta)} |",  # noqa: E501
                f"| Finding evidence coverage | {(trend.finding_evidence_coverage_delta.previous or 1.0):.0%} | {trend.finding_evidence_coverage_delta.current:.0%} | {format_coverage_delta(trend.finding_evidence_coverage_delta)} |",  # noqa: E501
                f"| Advisory evidence/basis coverage | {(trend.advisory_evidence_coverage_delta.previous or 1.0):.0%} | {trend.advisory_evidence_coverage_delta.current:.0%} | {format_coverage_delta(trend.advisory_evidence_coverage_delta)} |",  # noqa: E501
                f"| Informational evidence coverage | {(trend.informational_evidence_coverage_delta.previous or 1.0):.0%} | {trend.informational_evidence_coverage_delta.current:.0%} | {format_coverage_delta(trend.informational_evidence_coverage_delta)} |",  # noqa: E501
                "",
            ]
        )

        # Family breakdown if deltas exist
        if trend.by_family_delta:
            lines.extend(
                [
                    "| Family | Signals (prev) | Signals (curr) | Change |",
                    "|---|---:|---:|---:|",
                ]
            )
            for fam, delta in sorted(trend.by_family_delta.items()):
                lines.append(
                    f"| {fam.title()} | {delta.previous or 0} | {delta.current} | {format_count_delta(delta)} |"  # noqa: E501
                )
            lines.append("")

        # Recurring diagnostics
        if trend.recurring_diagnostics:
            lines.extend(
                [
                    "| Diagnostic | Family | Runs | Latest severity |",
                    "|---|---|---:|---|",
                ]
            )
            for diag in trend.recurring_diagnostics:
                lines.append(
                    f"| {diag.code} | {diag.family or '-'} | {diag.occurrences} | {diag.latest_severity} |"  # noqa: E501
                )
            lines.append("")
    elif trend and trend.unavailable_reason:
        lines.extend(
            [
                "",
                "## 6f. Governance Quality Trends",
                "",
                f"{trend.unavailable_reason}",
                "",
            ]
        )
