from __future__ import annotations

import json
import re
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

from pharabius.core.governance import effective_preset, load_governance
from pharabius.core.template_engine import (
    load_resolved_template,
    render_template,
)
from pharabius.schemas.finding import DebtFinding, DebtRegister
from pharabius.schemas.governance import GovernanceConfig
from pharabius.schemas.repository import RepositoryProfile
from pharabius.schemas.work_package import PlanResult, WorkPackage


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


def _load_debt_register(root: Path) -> DebtRegister:
    path = root / ".ai-debt" / "debt-register.json"
    data = _load_json(path)

    if not data:
        return DebtRegister(project_name=root.name, repository=str(root))

    return DebtRegister.model_validate(data)


def _load_profile(root: Path) -> RepositoryProfile:
    path = root / ".ai-debt" / "project-profile.json"
    data = _load_json(path)

    if not data:
        return RepositoryProfile.empty(root)

    return RepositoryProfile.model_validate(data)


def _slugify(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-")[:80] or "work-package"


def _sorted_findings(register: DebtRegister, top: int) -> list[DebtFinding]:
    return sorted(
        register.findings,
        key=lambda finding: finding.risk_score,
        reverse=True,
    )[:top]


def _roadmap_bucket(finding: DebtFinding) -> str:
    if finding.priority in {"Critical", "High"}:
        return "Immediate"
    if finding.priority == "Medium":
        return "Next"
    return "Later"


def _expected_risk_reduction(finding: DebtFinding) -> str:
    if finding.priority in {"Critical", "High"}:
        return "High"
    if finding.priority == "Medium":
        return "Medium"
    return "Low"


def _default_approach_for_category(finding: DebtFinding) -> list[str]:
    category = finding.category

    if category == "TD-DEP":
        return [
            "Confirm the intended dependency-management policy for this repository.",
            "Select the appropriate lockfile or deterministic install strategy.",
            "Update documentation and CI so dependency installation is reproducible.",
            "Run the full quality gate suite after dependency-management changes.",
        ]

    if category == "TD-TEST":
        return [
            "Identify the highest-risk entry points and workflows.",
            "Add a minimal automated test harness.",
            "Add regression tests around risk-sensitive behavior before refactoring.",
            "Run tests locally and in CI before accepting remediation work.",
        ]

    if category == "TD-BUILD":
        return [
            "Add or update CI workflow definitions.",
            (
                "Run formatting, linting, type checking, architecture checks, "
                "tests, and build validation."
            ),
            "Make the critical quality gates required before merge.",
            "Track CI duration and keep the default feedback loop under 10 minutes.",
        ]

    if category in {"TD-SEC", "TD-COMP"}:
        return [
            ("Validate the inferred sensitive areas with Product Engineering and security owners."),
            ("Add targeted regression and negative-path tests before changing sensitive behavior."),
            (
                "Document required approval boundaries for auth, data-handling, "
                "or compliance changes."
            ),
            "Run security review for any behavior-changing remediation.",
        ]

    if category == "TD-CONFIG":
        return [
            "Document the required configuration surface.",
            "Add sanitized examples for local and CI environments.",
            "Verify no real secrets or production credentials are committed.",
            "Confirm setup steps from a clean environment.",
        ]

    if category == "TD-DOC":
        return [
            "Document setup, test, build, and release workflows.",
            "Add architecture or ownership notes for maintainers.",
            "Validate documentation by following it in a clean environment.",
            "Keep documentation close to the repository contract.",
        ]

    return [
        "Review the finding and supporting evidence.",
        "Validate risk and ownership with Product Engineering.",
        "Add verification coverage before structural changes.",
        "Implement the smallest safe remediation slice.",
    ]


def _definition_of_done(finding: DebtFinding) -> list[str]:
    base = [
        f"Linked finding `{finding.id}` has been reviewed by the responsible owner.",
        "Recommended verification commands pass locally and in CI.",
        "Evidence and generated `.ai-debt/` artifacts are updated after remediation.",
    ]

    if finding.category == "TD-DEP":
        base.extend(
            [
                "Dependency installation is deterministic according to repository policy.",
                "Lockfile or documented lockfile exception is present.",
            ]
        )

    if finding.category == "TD-TEST":
        base.extend(
            [
                "Baseline tests cover the targeted remediation area.",
                "Regression tests are added for behavior that must not change.",
            ]
        )

    if finding.category in {"TD-SEC", "TD-COMP"}:
        base.extend(
            [
                "Security-sensitive behavior is reviewed before merge.",
                (
                    "No authentication, authorization, or data-handling "
                    "semantics change without approval."
                ),
            ]
        )

    return base


def _make_work_package(
    index: int,
    finding: DebtFinding,
) -> WorkPackage:
    package_id = f"WP-{index:03d}"

    affected_areas = finding.locations or ["Validate affected areas from linked evidence."]

    return WorkPackage(
        id=package_id,
        title=finding.title,
        linked_debt_items=[finding.id],
        objective=(
            f"Reduce risk from `{finding.id}` by addressing the supported "
            "technical debt without changing production behavior beyond the "
            "approved remediation scope."
        ),
        current_risk=finding.technical_impact,
        recommended_engineering_approach=_default_approach_for_category(finding),
        expected_affected_areas=affected_areas,
        preconditions=[
            "Review linked evidence IDs before implementation.",
            "Confirm ownership and remediation scope with Product Engineering.",
            "Avoid production behavior changes unless explicitly approved.",
        ],
        verification_recommendations=finding.verification_recommendations,
        risks_and_cautions=finding.risks_and_cautions,
        definition_of_done=_definition_of_done(finding),
        estimated_effort=finding.remediation_effort,
        expected_risk_reduction=_expected_risk_reduction(finding),
        suggested_owner_area=finding.suggested_owner_area or "Product Engineering",
    )


def _should_group(a: DebtFinding, b: DebtFinding) -> bool:
    """Conservative grouping policy for v3.1.0.

    Groups when ALL of:
    1. Same category
    2. Same suggested_owner_area
    3. Overlapping locations OR explicitly related via related_findings
    """
    if a.category != b.category:
        return False
    if (a.suggested_owner_area or "") != (b.suggested_owner_area or ""):
        return False

    # Location overlap
    a_locs = set(a.locations or [])
    b_locs = set(b.locations or [])
    if a_locs and b_locs and a_locs & b_locs:
        return True

    # Explicit related-findings link
    a_related = set(a.related_findings or [])
    b_related = set(b.related_findings or [])
    if b.id in a_related or a.id in b_related:
        return True

    return False


def _group_findings(findings: list[DebtFinding]) -> list[list[DebtFinding]]:
    """Group findings by conservative policy. Pre-sorted by risk_score descending."""
    sorted_findings = sorted(findings, key=lambda f: f.risk_score or 0, reverse=True)

    groups: list[list[DebtFinding]] = []
    assigned: set[str] = set()

    for finding in sorted_findings:
        if finding.id in assigned:
            continue
        group = [finding]
        assigned.add(finding.id)

        for other in sorted_findings:
            if other.id in assigned:
                continue
            if _should_group(finding, other):
                group.append(other)
                assigned.add(other.id)

        groups.append(group)

    return groups


def _make_grouped_work_package(index: int, group: list[DebtFinding]) -> WorkPackage:
    """Create a work package from grouped findings."""
    primary = group[0]  # Pre-sorted: highest risk_score first
    all_evidence = list(dict.fromkeys(
        eid for f in group for eid in f.evidence_ids
    ))
    all_locations = list(dict.fromkeys(
        loc for f in group for loc in (f.locations or [])
    ))

    return WorkPackage(
        id=f"WP-{index:03d}",
        title=(
            f"Address {len(group)} {primary.category} findings "
            f"in {primary.suggested_owner_area or 'affected areas'}"
        ),
        linked_debt_items=[f.id for f in group],
        objective=(
            f"Reduce risk from {len(group)} related {primary.category} findings "
            "by addressing the supported technical debt without changing "
            "production behavior beyond the approved remediation scope."
        ),
        current_risk=primary.technical_impact,
        recommended_engineering_approach=_default_approach_for_category(primary),
        expected_affected_areas=all_locations or ["Validate affected areas from linked evidence."],
        preconditions=[
            "Review all linked evidence IDs before implementation.",
            "Confirm ownership and remediation scope with Product Engineering.",
            "Avoid production behavior changes unless explicitly approved.",
        ],
        verification_recommendations=primary.verification_recommendations,
        risks_and_cautions=primary.risks_and_cautions,
        definition_of_done=[
            f"All {len(group)} linked findings have been reviewed by the responsible owner.",
            "Recommended verification commands pass locally and in CI.",
            "Evidence and generated `.ai-debt/` artifacts are updated after remediation.",
        ],
        estimated_effort=primary.remediation_effort,
        expected_risk_reduction=_expected_risk_reduction(primary),
        suggested_owner_area=primary.suggested_owner_area or "Product Engineering",
    )


def _generate_work_packages(
    findings: list[DebtFinding],
    max_work_packages: int,
) -> list[WorkPackage]:
    groups = _group_findings(findings)
    packages: list[WorkPackage] = []

    for index, group in enumerate(groups[:max_work_packages], start=1):
        if len(group) == 1:
            packages.append(_make_work_package(index, group[0]))
        else:
            packages.append(_make_grouped_work_package(index, group))

    return packages


def _render_work_package_template(
    template_text: str,
    package: WorkPackage,
    finding: DebtFinding,
) -> str:
    """Render work package using a template file."""
    linked = "\n".join(f"- `{item}`" for item in package.linked_debt_items)
    evidence = "\n".join(f"- `{eid}`" for eid in finding.evidence_ids)
    approach = "\n".join(
        f"{i}. {step}" for i, step in enumerate(package.recommended_engineering_approach, 1)
    )
    areas = "\n".join(f"- `{a}`" for a in package.expected_affected_areas)
    preconds = "\n".join(f"- {p}" for p in package.preconditions)
    verifications = "\n".join(f"- {v}" for v in package.verification_recommendations)
    cautions = "\n".join(f"- {c}" for c in package.risks_and_cautions)
    dod = "\n".join(f"- {d}" for d in package.definition_of_done)

    placeholders = {
        "package_id": package.id,
        "package_title": package.title,
        "package_status": package.status,
        "linked_findings": linked,
        "package_objective": package.objective,
        "evidence_list": evidence,
        "current_risk": package.current_risk,
        "recommended_approach": approach,
        "expected_affected_areas": areas,
        "preconditions": preconds,
        "verification_recommendations": verifications,
        "risks_and_cautions": cautions,
        "definition_of_done": dod,
        "estimated_effort": package.estimated_effort,
        "expected_risk_reduction": package.expected_risk_reduction,
        "suggested_owner_area": package.suggested_owner_area or "Product Engineering",
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return render_template(
            template_text,
            placeholders,
            artifact_name="work-package.md",
        )


def render_work_package_markdown(
    package: WorkPackage,
    finding: DebtFinding,
    *,
    repository_root: Path | None = None,
    governance: GovernanceConfig | None = None,
) -> str:
    # Try template override
    if repository_root is not None:
        gov = governance or GovernanceConfig()
        preset = effective_preset(gov)
        template_text = load_resolved_template(
            "work-package.md",
            repository_root,
            override_dir=gov.templates.override_dir,
            preset=preset,
        )
        if template_text is not None:
            return _render_work_package_template(
                template_text,
                package,
                finding,
            )

    # Built-in default rendering (v1.1 behavior)
    lines = [
        f"# Work Package: {package.id} {package.title}",
        "",
        "## Status",
        "",
        package.status,
        "",
        "## Linked Debt Items",
        "",
    ]

    for item in package.linked_debt_items:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "## Objective",
            "",
            package.objective,
            "",
            "## Evidence",
            "",
        ]
    )

    for evidence_id in finding.evidence_ids:
        lines.append(f"- `{evidence_id}`")

    lines.extend(
        [
            "",
            "## Current Risk",
            "",
            package.current_risk,
            "",
            "## Recommended Engineering Approach",
            "",
        ]
    )

    for index, step in enumerate(package.recommended_engineering_approach, start=1):
        lines.append(f"{index}. {step}")

    lines.extend(["", "## Expected Affected Areas", ""])

    for area in package.expected_affected_areas:
        lines.append(f"- `{area}`")

    lines.extend(["", "## Preconditions", ""])

    for precondition in package.preconditions:
        lines.append(f"- {precondition}")

    lines.extend(["", "## Verification Recommendations", ""])

    for recommendation in package.verification_recommendations:
        lines.append(f"- {recommendation}")

    lines.extend(["", "## Risks and Cautions", ""])

    for caution in package.risks_and_cautions:
        lines.append(f"- {caution}")

    lines.extend(["", "## Definition of Done", ""])

    for criterion in package.definition_of_done:
        lines.append(f"- {criterion}")

    lines.extend(
        [
            "",
            "## Estimated Effort",
            "",
            package.estimated_effort,
            "",
            "## Expected Risk Reduction",
            "",
            package.expected_risk_reduction,
            "",
            "## Suggested Owner Area",
            "",
            package.suggested_owner_area or "Product Engineering",
            "",
        ]
    )

    return "\n".join(lines)


def _render_roadmap_template(
    template_text: str,
    register: DebtRegister,
    packages: list[WorkPackage],
) -> str:
    """Render roadmap using a template file."""
    findings_by_id = {finding.id: finding for finding in register.findings}
    buckets: dict[str, list[DebtFinding]] = defaultdict(list)
    for package in packages:
        for debt_id in package.linked_debt_items:
            finding = findings_by_id.get(debt_id)
            if finding is not None:
                buckets[_roadmap_bucket(finding)].append(finding)

    summary = (
        f"- Total findings in debt register: `{register.summary.total_findings}`\n"
        f"- Work packages generated: `{len(packages)}`\n"
        "- Planning mode: `deterministic-no-ai`"
    )

    bucket_parts: list[str] = []
    for bucket_name in ("Immediate", "Next", "Later"):
        findings = buckets.get(bucket_name, [])
        if not findings:
            bucket_parts.append(
                f"## {bucket_name}\n\nNo work packages currently assigned to this bucket.\n"
            )
            continue
        lines = [
            f"## {bucket_name}\n",
            "| Priority | Debt ID | Title | Category | Score | Effort |",
            "|---|---|---|---|---:|---|",
        ]
        for f in findings:
            lines.append(
                "| "
                f"{f.priority} | "
                f"`{f.id}` | "
                f"{f.title} | "
                f"`{f.category}` | "
                f"{f.risk_score} | "
                f"{f.remediation_effort} |"
            )
        lines.append("")
        bucket_parts.append("\n".join(lines))

    wp_list_parts: list[str] = []
    if packages:
        for pkg in packages:
            slug = _slugify(pkg.title)
            wp_list_parts.append(f"- `{pkg.id}` — `work-packages/{pkg.id}-{slug}.md`")
    else:
        wp_list_parts.append("No work packages generated because no findings were available.")

    placeholders = {
        "summary_section": summary,
        "roadmap_buckets": "\n".join(bucket_parts),
        "work_package_list": "\n".join(wp_list_parts),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return render_template(
            template_text,
            placeholders,
            artifact_name="remediation-roadmap.md",
        )


def render_remediation_roadmap(
    register: DebtRegister,
    packages: list[WorkPackage],
    *,
    repository_root: Path | None = None,
    governance: GovernanceConfig | None = None,
) -> str:
    # Try template override
    if repository_root is not None:
        gov = governance or GovernanceConfig()
        preset = effective_preset(gov)
        template_text = load_resolved_template(
            "remediation-roadmap.md",
            repository_root,
            override_dir=gov.templates.override_dir,
            preset=preset,
        )
        if template_text is not None:
            return _render_roadmap_template(
                template_text,
                register,
                packages,
            )

    # Built-in default rendering (v1.1 behavior)
    findings_by_id = {finding.id: finding for finding in register.findings}
    buckets: dict[str, list[DebtFinding]] = defaultdict(list)

    for package in packages:
        for debt_id in package.linked_debt_items:
            finding = findings_by_id.get(debt_id)
            if finding is not None:
                buckets[_roadmap_bucket(finding)].append(finding)

    lines = [
        "# Remediation Roadmap",
        "",
        "## Summary",
        "",
        f"- Total findings in debt register: `{register.summary.total_findings}`",
        f"- Work packages generated: `{len(packages)}`",
        "- Planning mode: `deterministic-no-ai`",
        "",
        "## Prioritization Method",
        "",
        "Findings are sequenced by existing debt-register risk score and priority.",
        "This roadmap does not create new findings.",
        "",
    ]

    for bucket in ("Immediate", "Next", "Later"):
        lines.extend([f"## {bucket}", ""])

        findings = buckets.get(bucket, [])
        if not findings:
            lines.append("No work packages currently assigned to this bucket.")
            lines.append("")
            continue

        lines.extend(
            [
                "| Priority | Debt ID | Title | Category | Score | Effort |",
                "|---|---|---|---|---:|---|",
            ]
        )

        for finding in findings:
            lines.append(
                "| "
                f"{finding.priority} | "
                f"`{finding.id}` | "
                f"{finding.title} | "
                f"`{finding.category}` | "
                f"{finding.risk_score} | "
                f"{finding.remediation_effort} |"
            )

        lines.append("")

    lines.extend(
        [
            "## Deferred / Requires Decision",
            "",
            "The following items should be validated before implementation:",
            "",
            "- Whether inferred business impact matches Product Engineering priorities.",
            "- Whether remediation can be done without changing production behavior.",
            "- Whether security, compliance, or architecture approval is required.",
            "",
            "## Generated Work Packages",
            "",
        ]
    )

    if not packages:
        lines.append("No work packages generated because no findings were available.")
    else:
        for package in packages:
            slug = _slugify(package.title)
            lines.append(f"- `{package.id}` — `work-packages/{package.id}-{slug}.md`")

    lines.append("")
    return "\n".join(lines)


def _render_handoff_template(
    template_text: str,
    profile: RepositoryProfile,
    register: DebtRegister,
    packages: list[WorkPackage],
) -> str:
    """Render handoff summary using a template file."""
    findings = sorted(
        register.findings,
        key=lambda f: f.risk_score,
        reverse=True,
    )

    repo_section = (
        f"- Project: `{profile.project_name or register.project_name}`\n"
        f"- Repository: `{register.repository}`\n"
        f"- Branch: `{register.branch or 'Unknown'}`\n"
        f"- Commit: `{register.commit or 'Unknown'}`\n"
        "- Analysis mode: `deterministic-no-ai`"
    )

    if findings:
        top = findings[0]
        exec_summary = (
            f"Pharabius generated `{register.summary.total_findings}` "
            f"deterministic technical debt finding(s) and "
            f"`{len(packages)}` work package(s).\n\n"
            f"The top finding is `{top.id}` with priority `{top.priority}` "
            f"and risk score `{top.risk_score}`."
        )
    else:
        exec_summary = (
            "Pharabius did not generate deterministic technical debt findings "
            "from the available evidence.\n\n"
            "This does not prove the repository is debt-free; it means the "
            "current deterministic analyzer lacked sufficient evidence for "
            "supported findings."
        )

    table_header = (
        "| Priority | Debt ID | Title | Category | Score | Effort |\n|---|---|---|---:|---|---|"
    )
    if not findings:
        table_rows = "| N/A | N/A | No findings generated. | N/A | 0 | N/A |"
    else:
        rows = []
        for f in findings[:10]:
            rows.append(
                "| "
                f"{f.priority} | "
                f"`{f.id}` | "
                f"{f.title} | "
                f"`{f.category}` | "
                f"{f.risk_score} | "
                f"{f.remediation_effort} |"
            )
        table_rows = "\n".join(rows)
    top_risks = f"{table_header}\n{table_rows}"

    if packages:
        actions = "\n".join(
            f"{i}. Review `{p.id}` — {p.title}." for i, p in enumerate(packages[:3], 1)
        )
    else:
        actions = (
            "1. Validate that repository evidence is complete.\n"
            "2. Add richer scanner integrations if deeper analysis is required.\n"
            "3. Re-run `ai-debt analyze --no-ai` after new evidence is available."
        )

    pet_decisions = (
        "- Confirm whether inferred business impact matches product priorities.\n"
        "- Confirm ownership for each generated work package.\n"
        "- Confirm whether any remediation requires architecture, security, "
        "or compliance review."
    )

    cautions = (
        "- Pharabius v1 planning is evidence-backed but does not replace "
        "Product Engineering ownership.\n"
        "- Do not change public API behavior without explicit approval.\n"
        "- Do not change authentication, authorization, or data-handling "
        "semantics without review."
    )

    if profile.limitations:
        uncertainties = "\n".join(f"- {lim}" for lim in profile.limitations)
    else:
        uncertainties = (
            "- Production incident history is not available from repository-only evidence.\n"
            "- Runtime usage, revenue impact, and customer criticality are not available.\n"
            "- Coverage quality is not assessed unless coverage artifacts are added later."
        )

    artifacts = (
        "- `debt-register.md`\n"
        "- `remediation-roadmap.md`\n"
        "- `work-packages/`\n"
        "- `reports/foundation-audit-report.md`"
    )

    placeholders = {
        "repository_section": repo_section,
        "executive_summary": exec_summary,
        "top_risks_table": top_risks,
        "recommended_first_actions": actions,
        "pet_decisions": pet_decisions,
        "risks_and_cautions": cautions,
        "uncertainties": uncertainties,
        "generated_artifacts": artifacts,
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return render_template(
            template_text,
            placeholders,
            artifact_name="handoff-summary.md",
        )


def render_handoff_summary(
    profile: RepositoryProfile,
    register: DebtRegister,
    packages: list[WorkPackage],
    *,
    repository_root: Path | None = None,
    governance: GovernanceConfig | None = None,
) -> str:
    # Try template override
    if repository_root is not None:
        gov = governance or GovernanceConfig()
        preset = effective_preset(gov)
        template_text = load_resolved_template(
            "handoff-summary.md",
            repository_root,
            override_dir=gov.templates.override_dir,
            preset=preset,
        )
        if template_text is not None:
            return _render_handoff_template(
                template_text,
                profile,
                register,
                packages,
            )

    # Built-in default rendering (v1.1 behavior)
    findings = sorted(
        register.findings,
        key=lambda finding: finding.risk_score,
        reverse=True,
    )

    lines = [
        "# AI Technical Debt Handoff Summary",
        "",
        "## Repository",
        "",
        f"- Project: `{profile.project_name or register.project_name}`",
        f"- Repository: `{register.repository}`",
        f"- Branch: `{register.branch or 'Unknown'}`",
        f"- Commit: `{register.commit or 'Unknown'}`",
        "- Analysis mode: `deterministic-no-ai`",
        "",
        "## Executive Summary",
        "",
    ]

    if findings:
        top = findings[0]
        lines.extend(
            [
                (
                    f"Pharabius generated `{register.summary.total_findings}` "
                    f"deterministic technical debt finding(s) and "
                    f"`{len(packages)}` work package(s)."
                ),
                (
                    f"The top finding is `{top.id}` with priority `{top.priority}` "
                    f"and risk score `{top.risk_score}`."
                ),
            ]
        )
    else:
        lines.extend(
            [
                (
                    "Pharabius did not generate deterministic technical debt findings "
                    "from the available evidence."
                ),
                (
                    "This does not prove the repository is debt-free; it means the "
                    "current deterministic analyzer lacked sufficient evidence for "
                    "supported findings."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Top Risks",
            "",
            "| Priority | Debt ID | Title | Category | Score | Effort |",
            "|---|---|---|---:|---|---|",
        ]
    )

    if not findings:
        lines.append("| N/A | N/A | No findings generated. | N/A | 0 | N/A |")
    else:
        for finding in findings[:10]:
            lines.append(
                "| "
                f"{finding.priority} | "
                f"`{finding.id}` | "
                f"{finding.title} | "
                f"`{finding.category}` | "
                f"{finding.risk_score} | "
                f"{finding.remediation_effort} |"
            )

    lines.extend(["", "## Recommended First Actions", ""])

    if packages:
        for index, package in enumerate(packages[:3], start=1):
            lines.append(f"{index}. Review `{package.id}` — {package.title}.")
    else:
        lines.extend(
            [
                "1. Validate that repository evidence is complete.",
                "2. Add richer scanner integrations if deeper analysis is required.",
                "3. Re-run `ai-debt analyze --no-ai` after new evidence is available.",
            ]
        )

    lines.extend(
        [
            "",
            "## Remediation Roadmap",
            "",
            "See `remediation-roadmap.md`.",
            "",
            "## Product Engineering Decisions Needed",
            "",
            "- Confirm whether inferred business impact matches product priorities.",
            "- Confirm ownership for each generated work package.",
            (
                "- Confirm whether any remediation requires architecture, security, "
                "or compliance review."
            ),
            "",
            "## Risks and Cautions",
            "",
            (
                "- Pharabius v1 planning is evidence-backed but does not replace "
                "Product Engineering ownership."
            ),
            "- Do not change public API behavior without explicit approval.",
            (
                "- Do not change authentication, authorization, or data-handling "
                "semantics without review."
            ),
            "",
            "## Uncertainties and Missing Evidence",
            "",
        ]
    )

    if profile.limitations:
        for limitation in profile.limitations:
            lines.append(f"- {limitation}")
    else:
        lines.extend(
            [
                ("- Production incident history is not available from repository-only evidence."),
                ("- Runtime usage, revenue impact, and customer criticality are not available."),
                ("- Coverage quality is not assessed unless coverage artifacts are added later."),
            ]
        )

    lines.extend(
        [
            "",
            "## Generated Artifacts",
            "",
            "- `debt-register.md`",
            "- `remediation-roadmap.md`",
            "- `work-packages/`",
            "- `reports/foundation-audit-report.md`",
            "",
        ]
    )

    return "\n".join(lines)


def write_plan(
    repository_root: Path,
    *,
    top: int = 10,
    max_work_packages: int = 10,
) -> PlanResult:
    root = repository_root.resolve()
    workspace = root / ".ai-debt"
    work_packages_dir = workspace / "work-packages"

    # Load governance for template overrides
    governance = load_governance(root)

    profile = _load_profile(root)
    register = _load_debt_register(root)
    findings = _sorted_findings(register, top=top)
    packages = _generate_work_packages(findings, max_work_packages=max_work_packages)

    work_packages_dir.mkdir(parents=True, exist_ok=True)

    for stale_path in work_packages_dir.glob("WP-*.md"):
        stale_path.unlink()

    work_package_paths: list[Path] = []
    findings_by_id = {finding.id: finding for finding in findings}

    for package in packages:
        # Collect evidence IDs from ALL linked findings
        all_wp_evidence: list[str] = []
        primary_finding = None
        for debt_id in package.linked_debt_items:
            finding = findings_by_id.get(debt_id)
            if finding is not None:
                if primary_finding is None:
                    primary_finding = finding
                all_wp_evidence.extend(eid for eid in finding.evidence_ids if eid not in all_wp_evidence)

        # Fall back to first linked finding if none found by ID
        if primary_finding is None:
            debt_id = package.linked_debt_items[0]
            primary_finding = findings_by_id.get(debt_id)
            if primary_finding is None:
                continue

        slug = _slugify(package.title)
        path = work_packages_dir / f"{package.id}-{slug}.md"
        path.write_text(
            render_work_package_markdown(
                package,
                primary_finding,
                repository_root=root,
                governance=governance,
            ),
            encoding="utf-8",
        )
        work_package_paths.append(path)

    roadmap_path = workspace / "remediation-roadmap.md"
    handoff_path = workspace / "handoff-summary.md"

    roadmap_path.write_text(
        render_remediation_roadmap(
            register,
            packages,
            repository_root=root,
            governance=governance,
        ),
        encoding="utf-8",
    )
    handoff_path.write_text(
        render_handoff_summary(
            profile,
            register,
            packages,
            repository_root=root,
            governance=governance,
        ),
        encoding="utf-8",
    )

    return PlanResult(
        remediation_roadmap_path=str(roadmap_path),
        handoff_summary_path=str(handoff_path),
        work_package_paths=[str(path) for path in work_package_paths],
        work_packages=packages,
    )
