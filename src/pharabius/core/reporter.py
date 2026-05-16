from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
            f"Total findings: **{ctx.debt_register.summary.total_findings}**",
            "",
            "## 6. Top Findings",
            "",
            *_finding_table(findings[:10]),
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

    lines.extend(
        [
            "",
            "## 13. Product Engineering Handoff",
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
