from __future__ import annotations

import dataclasses
import json
from collections import Counter
from pathlib import Path

from pharabius.schemas.evidence import EvidenceItem, EvidenceStore
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary


@dataclasses.dataclass(frozen=True)
class _EcosystemDef:
    name: str
    manifest_names: frozenset[str]
    lockfile_names: frozenset[str]
    rust_library_exempt: bool = False


_ECOSYSTEMS = (
    _EcosystemDef(
        "Node.js",
        frozenset({"package.json"}),
        frozenset({"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"}),
    ),
    _EcosystemDef(
        "Python",
        frozenset({"pyproject.toml", "requirements.txt", "Pipfile"}),
        frozenset({"poetry.lock", "uv.lock", "Pipfile.lock"}),
    ),
    _EcosystemDef(
        "Java",
        frozenset({"pom.xml", "build.gradle", "build.gradle.kts"}),
        frozenset({"gradle.lockfile", "mvnw", "gradlew"}),
    ),
    _EcosystemDef(
        "Go",
        frozenset({"go.mod"}),
        frozenset({"go.sum"}),
    ),
    _EcosystemDef(
        "Rust",
        frozenset({"Cargo.toml"}),
        frozenset({"Cargo.lock"}),
        rust_library_exempt=True,
    ),
    _EcosystemDef(
        "PHP",
        frozenset({"composer.json"}),
        frozenset({"composer.lock"}),
    ),
    _EcosystemDef(
        "Ruby",
        frozenset({"Gemfile"}),
        frozenset({"Gemfile.lock"}),
    ),
)


RISK_SCORE_TEMPLATE = {
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


def _priority_for_score(score: int) -> str:
    if score >= 36:
        return "Critical"
    if score >= 21:
        return "High"
    if score >= 11:
        return "Medium"
    return "Low"


def _severity_for_priority(priority: str) -> str:
    if priority == "Critical":
        return "Critical"
    if priority == "High":
        return "High"
    if priority == "Medium":
        return "Medium"
    return "Low"


def _score(breakdown: dict[str, int]) -> tuple[int, str]:
    total = sum(breakdown.values())
    return total, _priority_for_score(total)


def _load_evidence_store(repository_root: Path) -> EvidenceStore:
    path = repository_root.resolve() / ".ai-debt" / "evidence.json"

    if not path.exists():
        return EvidenceStore(repository=str(repository_root.resolve()), evidence=[])

    data = json.loads(path.read_text(encoding="utf-8"))
    return EvidenceStore.model_validate(data)


def _load_project_name(repository_root: Path) -> str:
    path = repository_root.resolve() / ".ai-debt" / "project-profile.json"

    if not path.exists():
        return repository_root.resolve().name

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return repository_root.resolve().name

    project_name = data.get("project_name")
    if isinstance(project_name, str) and project_name:
        return project_name

    return repository_root.resolve().name


def _evidence_by_type(store: EvidenceStore, evidence_type: str) -> list[EvidenceItem]:
    return [item for item in store.evidence if item.type == evidence_type]


def _first_evidence_id(store: EvidenceStore) -> list[str]:
    if not store.evidence:
        return []
    return [store.evidence[0].evidence_id]


def _evidence_ids(items: list[EvidenceItem], limit: int = 20) -> list[str]:
    return [item.evidence_id for item in items[:limit]]


def _locations(items: list[EvidenceItem], limit: int = 20) -> list[str]:
    locations: list[str] = []

    for item in items[:limit]:
        if item.location.file:
            locations.append(item.location.file)

    return sorted(set(locations))


def _manifest_files(store: EvidenceStore) -> set[str]:
    return {
        item.location.file
        for item in _evidence_by_type(store, "manifest_detected")
        if item.location.file
    }


def _file_names(store: EvidenceStore) -> set[str]:
    return {
        Path(item.location.file).name
        for item in _evidence_by_type(store, "file_detected")
        if item.location.file
    }


def _package_root(manifest_path: str) -> str:
    """Return the normalized package root directory for a manifest path.

    Root manifests (e.g. 'pyproject.toml') yield '.'.
    Nested manifests (e.g. 'services/api/pyproject.toml') yield 'services/api'.
    """
    parent = Path(manifest_path).parent.as_posix()
    return parent if parent else "."


def _lockfile_basenames_in_root(
    store: EvidenceStore,
    package_root: str,
    lockfile_names: frozenset[str],
) -> set[str]:
    """Return lockfile basenames found in the same package root directory."""
    result: list[str] = []
    for item in _evidence_by_type(store, "file_detected"):
        if not item.location.file:
            continue
        item_root = _package_root(item.location.file)
        if item_root != package_root:
            continue
        basename = Path(item.location.file).name
        if basename in lockfile_names:
            result.append(basename)
    return set(result)


def _manifest_evidence_for_ecosystem(
    store: EvidenceStore,
    ecosystem: _EcosystemDef,
) -> list[EvidenceItem]:
    """Return manifest evidence items matching this ecosystem's manifest names."""
    return [
        item
        for item in _evidence_by_type(store, "manifest_detected")
        if item.location.file and Path(item.location.file).name in ecosystem.manifest_names
    ]


_NODE_LOCKFILE_NAMES = frozenset(
    {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"}
)


def _root_node_workspace_evidence_exists(store: EvidenceStore) -> bool:
    """True if any node_workspace manifest evidence exists at any depth."""
    return any(
        item.type == "manifest_detected" and item.object == "node_workspace"
        for item in store.evidence
    )


def _root_node_lockfile_exists(store: EvidenceStore) -> bool:
    """True if a Node lockfile exists in the repository root."""
    return bool(_lockfile_basenames_in_root(store, ".", _NODE_LOCKFILE_NAMES))


def _is_nested_manifest(location: str) -> bool:
    """True if the manifest is in a subdirectory (not at repository root)."""
    return _package_root(location) != "."


def _deployment_locations(store: EvidenceStore) -> set[str]:
    return {
        item.location.file
        for item in _evidence_by_type(store, "deployment_file_detected")
        if item.location.file
    }


def _has_ci_cd(store: EvidenceStore) -> bool:
    locations = _deployment_locations(store)

    return any(
        location.startswith(".github/workflows/")
        or location.startswith(".gitlab-ci")
        or Path(location).name.lower()
        in {
            "jenkinsfile",
            "bitbucket-pipelines.yml",
            "azure-pipelines.yml",
        }
        for location in locations
    )


def _has_tests(store: EvidenceStore) -> bool:
    if _evidence_by_type(store, "test_file_detected"):
        return True

    package_scripts = _evidence_by_type(store, "package_script_detected")
    return any(item.category == "test" for item in package_scripts)


def _has_docs(store: EvidenceStore) -> bool:
    return bool(_evidence_by_type(store, "documentation_file_detected"))


def _risk_signal_items(store: EvidenceStore) -> list[EvidenceItem]:
    return [
        item
        for item in store.evidence
        if item.type
        in {
            "risk_sensitive_path_detected",
            "risk_sensitive_keyword_detected",
        }
    ]


def _git_value(store: EvidenceStore, evidence_type: str) -> str:
    for item in store.evidence:
        if item.type == evidence_type and item.object:
            return item.object

    return ""


class FindingBuilder:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self.findings: list[DebtFinding] = []

    def add(
        self,
        *,
        category: str,
        title: str,
        description: str,
        evidence_ids: list[str],
        locations: list[str],
        technical_impact: str,
        business_impact: str,
        risk_breakdown: dict[str, int],
        remediation_effort: str,
        recommended_action: str,
        verification_recommendations: list[str],
        risks_and_cautions: list[str],
        confidence: str = "Medium",
        suggested_owner_area: str = "",
    ) -> None:
        if not evidence_ids:
            return

        self._counters[category] += 1
        raw_score, priority = _score(risk_breakdown)

        self.findings.append(
            DebtFinding(
                id=f"{category}-{self._counters[category]:03d}",
                category=category,
                title=title,
                description=description,
                severity=_severity_for_priority(priority),
                confidence=confidence,
                locations=locations,
                evidence_ids=evidence_ids,
                technical_impact=technical_impact,
                business_impact=business_impact,
                risk_score=raw_score,
                priority=priority,
                risk_breakdown=risk_breakdown,
                remediation_effort=remediation_effort,
                recommended_action=recommended_action,
                verification_recommendations=verification_recommendations,
                risks_and_cautions=risks_and_cautions,
                suggested_owner_area=suggested_owner_area,
            )
        )


def _analyze_missing_tests(store: EvidenceStore, builder: FindingBuilder) -> None:
    if _has_tests(store):
        return

    risk_items = _risk_signal_items(store)
    supporting_evidence = risk_items or store.evidence[:1]

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 5,
        "blast_radius": 3,
        "test_gap": 8,
        "security_exposure": 3 if risk_items else 0,
        "compliance_exposure": 3 if risk_items else 0,
        "business_critical_proxy": 3 if risk_items else 1,
        "remediation_simplicity": -2,
    }

    builder.add(
        category="TD-TEST",
        title="No test evidence detected",
        description=(
            "The repository scan did not detect test files or package test scripts. "
            "This increases regression risk and weakens confidence in future remediation work."
        ),
        evidence_ids=_evidence_ids(supporting_evidence),
        locations=_locations(supporting_evidence),
        technical_impact=(
            "Without detectable tests, changes to existing behavior are harder to verify and "
            "technical debt remediation becomes riskier."
        ),
        business_impact=(
            "Regression risk is inferred from repository evidence. Validate critical workflows "
            "with the Product Engineering Team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Add a minimal test harness and prioritize tests around entry points, risk-sensitive "
            "areas, and behavior that must remain stable during remediation."
        ),
        verification_recommendations=[
            "Add at least one automated test suite recognized by the project stack.",
            "Run the test suite in CI.",
            "Add regression tests before refactoring risk-sensitive code paths.",
        ],
        risks_and_cautions=[
            "Do not begin broad refactoring until baseline regression coverage exists.",
            "Mark untested critical workflows as Product Engineering validation items.",
        ],
        suggested_owner_area="Quality Engineering / Product Engineering",
    )


def _analyze_risk_sensitive_without_tests(store: EvidenceStore, builder: FindingBuilder) -> None:
    risk_items = _risk_signal_items(store)

    if not risk_items or _has_tests(store):
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 5,
        "blast_radius": 5,
        "test_gap": 8,
        "security_exposure": 6,
        "compliance_exposure": 3,
        "business_critical_proxy": 5,
        "remediation_simplicity": -1,
        "confidence_modifier": 1,
    }

    builder.add(
        category="TD-SEC",
        title="Risk-sensitive areas detected without test evidence",
        description=(
            "The repository contains security, compliance, operational, or business-sensitive "
            "signals, but the scan did not detect automated test evidence."
        ),
        evidence_ids=_evidence_ids(risk_items),
        locations=_locations(risk_items),
        technical_impact=(
            "Risk-sensitive paths without detectable tests increase the probability of unsafe "
            "behavioral changes during maintenance or remediation."
        ),
        business_impact=(
            "Potential business impact is inferred from path names and keywords such as auth, "
            "token, billing, customer, audit, deployment, or monitoring."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Create targeted regression and negative-path tests for the risk-sensitive areas "
            "before changing related logic."
        ),
        verification_recommendations=[
            (
                "Add tests covering successful and failing "
                "authorization/security paths where applicable."
            ),
            ("Add regression tests for business-critical or operationally sensitive behavior."),
            "Request Product Engineering review of inferred critical areas.",
        ],
        risks_and_cautions=[
            "Keyword evidence is a risk signal, not proof of a vulnerability.",
            (
                "Do not change authentication, authorization, or "
                "data-handling semantics without review."
            ),
        ],
        confidence="Medium",
        suggested_owner_area="Security / Product Engineering",
    )


def _analyze_missing_ci(store: EvidenceStore, builder: FindingBuilder) -> None:
    if _has_ci_cd(store):
        return

    manifests = _evidence_by_type(store, "manifest_detected")
    supporting_evidence = manifests or store.evidence[:1]

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "blast_radius": 3,
        "test_gap": 2,
        "operational_exposure": 5,
        "business_critical_proxy": 3,
        "remediation_simplicity": -2,
    }

    builder.add(
        category="TD-BUILD",
        title="No CI/CD workflow evidence detected",
        description=(
            "The repository scan did not detect common CI/CD workflow files such as GitHub "
            "Actions, GitLab CI, Jenkins, Bitbucket Pipelines, or Azure Pipelines."
        ),
        evidence_ids=_evidence_ids(supporting_evidence),
        locations=_locations(supporting_evidence),
        technical_impact=(
            "Without automated quality gates, formatting, linting, type checking, tests, and "
            "architecture checks may not be enforced consistently before merge."
        ),
        business_impact=(
            "Delivery risk is inferred from missing CI/CD evidence. Validate release process "
            "with the Product Engineering Team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Small",
        recommended_action=(
            "Add a minimal CI workflow that runs formatting checks, linting, type checking, "
            "architecture boundary checks, tests, and package build validation."
        ),
        verification_recommendations=[
            "Run CI on pull requests.",
            "Block merges when quality gates fail.",
            "Track CI duration and keep the default feedback loop under 10 minutes.",
        ],
        risks_and_cautions=[
            "Do not add slow or flaky checks directly to the required path without stabilization.",
        ],
        suggested_owner_area="Platform / DevOps",
    )


def _analyze_missing_docs(store: EvidenceStore, builder: FindingBuilder) -> None:
    if _has_docs(store):
        return

    supporting_evidence = store.evidence[:1]

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "blast_radius": 3,
        "business_critical_proxy": 1,
        "remediation_simplicity": -2,
    }

    builder.add(
        category="TD-DOC",
        title="No documentation evidence detected",
        description=(
            "The repository scan did not detect common documentation files such as README, "
            "docs, ADRs, changelog, or contributing guidance."
        ),
        evidence_ids=_evidence_ids(supporting_evidence),
        locations=_locations(supporting_evidence),
        technical_impact=(
            "Missing documentation increases onboarding cost and makes architectural intent, "
            "setup steps, and operational procedures harder to verify."
        ),
        business_impact=(
            "Maintainability and onboarding impact is inferred from missing documentation evidence."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Small",
        recommended_action=(
            "Add a README with setup, test, build, architecture overview, and ownership notes. "
            "Add ADRs for important architectural decisions."
        ),
        verification_recommendations=[
            "Confirm a new contributor can set up and test the project using documented steps.",
            "Add links to generated `.ai-debt/` reports where useful.",
        ],
        risks_and_cautions=[
            "Avoid writing aspirational documentation that does not match the repository behavior.",
        ],
        suggested_owner_area="Product Engineering",
    )


def _analyze_missing_lockfile(store: EvidenceStore, builder: FindingBuilder) -> None:
    """Check each ecosystem/package-root independently for missing lockfiles.

    Generates one TD-DEP finding per (ecosystem, package_root) pair that is
    missing expected lockfile evidence. Manifests for the same ecosystem in
    the same package root are grouped into a single finding.
    """
    for ecosystem in _ECOSYSTEMS:
        manifest_items = _manifest_evidence_for_ecosystem(store, ecosystem)
        if not manifest_items:
            continue

        # Group manifest evidence by package root
        roots: dict[str, list[EvidenceItem]] = {}
        for item in manifest_items:
            root = _package_root(item.location.file)
            roots.setdefault(root, []).append(item)

        for root, items_in_root in roots.items():
            found = _lockfile_basenames_in_root(store, root, ecosystem.lockfile_names)
            if found:
                continue

            # Node workspace satisfaction: nested packages covered by root lockfile
            if (
                ecosystem.name == "Node.js"
                and root != "."
                and _root_node_workspace_evidence_exists(store)
                and _root_node_lockfile_exists(store)
            ):
                continue

            # One finding per (ecosystem, package_root)
            _emit_lockfile_finding(
                builder,
                ecosystem=ecosystem,
                manifest_items=items_in_root,
                package_root=root,
            )

    # .NET special case: manifests identified by path suffix
    dotnet_items = [
        item
        for item in _evidence_by_type(store, "manifest_detected")
        if item.location.file
        and (item.location.file.endswith(".csproj") or item.location.file.endswith(".sln"))
    ]
    if dotnet_items:
        dotnet_lockfile_names = frozenset({"packages.lock.json"})
        roots: dict[str, list[EvidenceItem]] = {}  # type: ignore[no-redef]
        for item in dotnet_items:
            root = _package_root(item.location.file)
            roots.setdefault(root, []).append(item)
        for root, items_in_root in roots.items():
            found = _lockfile_basenames_in_root(store, root, dotnet_lockfile_names)
            if found:
                continue
            _emit_lockfile_finding(
                builder,
                ecosystem=_EcosystemDef(".NET", frozenset(), dotnet_lockfile_names),
                manifest_items=items_in_root,
                package_root=root,
            )


def _emit_lockfile_finding(
    builder: FindingBuilder,
    *,
    ecosystem: _EcosystemDef,
    manifest_items: list[EvidenceItem],
    package_root: str,
) -> None:
    evidence_ids = _evidence_ids(manifest_items)
    locations = _locations(manifest_items)

    root_label = "repository root" if package_root == "." else package_root

    is_java = ecosystem.name == "Java"
    reproducibility_term = "dependency reproducibility evidence" if is_java else "lockfile evidence"

    is_rust = ecosystem.rust_library_exempt

    title = f"{ecosystem.name} dependency manifest detected without {reproducibility_term}"

    description = (
        f"The repository contains {ecosystem.name} dependency manifest(s) in "
        f"{root_label}, but the scan did not detect corresponding "
        f"{reproducibility_term} for that package root."
    )
    if is_rust:
        description += (
            " Rust library crates may intentionally omit Cargo.lock. "
            "Validate repository policy before acting on this finding."
        )

    technical_impact = (
        f"Missing {reproducibility_term} may reduce dependency reproducibility "
        f"across local, CI, and deployment environments."
    )

    confidence = "Medium" if is_rust else "High"

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "dependency_risk": 5,
        "operational_exposure": 3,
        "business_critical_proxy": 3,
        "remediation_simplicity": -2,
    }

    risks_and_cautions: list[str] = [
        "Some library repositories intentionally avoid committed "
        "lockfiles; validate project policy.",
    ]
    if is_rust:
        risks_and_cautions.append(
            "Rust library crates (as opposed to binary crates) conventionally "
            "do not commit Cargo.lock. Confirm whether this is a library "
            "before generating a lockfile."
        )

    verification: list[str] = [
        f"Generate or confirm the appropriate lockfile for {ecosystem.name}.",
        "Run dependency installation in a clean environment.",
        "Ensure CI uses deterministic dependency installation where supported.",
    ]
    if is_rust:
        verification.append(
            "Check whether this crate is published as a library; if so, "
            "omitting Cargo.lock may be intentional and this finding can be dismissed."
        )

    recommended_action = (
        f"Adopt the {ecosystem.name}-appropriate lockfile strategy and document "
        f"whether applications or libraries are expected to commit lockfiles."
    )
    if is_rust:
        recommended_action += (
            " For binary crates, run `cargo generate-lockfile` and commit the resulting Cargo.lock."
        )

    builder.add(
        category="TD-DEP",
        title=title,
        description=description,
        evidence_ids=evidence_ids,
        locations=locations,
        technical_impact=technical_impact,
        business_impact=(
            "Release and environment reproducibility risk is inferred "
            "from dependency manifest evidence."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Small",
        recommended_action=recommended_action,
        verification_recommendations=verification,
        risks_and_cautions=risks_and_cautions,
        confidence=confidence,
        suggested_owner_area="Product Engineering / Platform",
    )


def _analyze_env_without_example(store: EvidenceStore, builder: FindingBuilder) -> None:
    config_items = _evidence_by_type(store, "configuration_file_detected")
    config_locations = {item.location.file for item in config_items}

    has_env = ".env" in config_locations or ".env.local" in config_locations
    has_example = ".env.example" in config_locations

    if not has_env or has_example:
        return

    env_items = [item for item in config_items if item.location.file in {".env", ".env.local"}]

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "security_exposure": 3,
        "operational_exposure": 3,
        "business_critical_proxy": 3,
        "remediation_simplicity": -2,
    }

    builder.add(
        category="TD-CONFIG",
        title="Environment configuration detected without example file",
        description=(
            "An environment configuration file was detected, but no `.env.example` file was found."
        ),
        evidence_ids=_evidence_ids(env_items),
        locations=_locations(env_items),
        technical_impact=(
            "Missing environment examples make setup, onboarding, and environment parity harder "
            "to verify."
        ),
        business_impact=(
            "Operational setup risk is inferred from environment configuration evidence."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Small",
        recommended_action=(
            "Add a sanitized `.env.example` documenting required variables without secrets."
        ),
        verification_recommendations=[
            "Verify `.env.example` contains no real secrets.",
            "Confirm local setup works from documented environment variables.",
        ],
        risks_and_cautions=[
            "Never commit real credentials or production secrets.",
        ],
        suggested_owner_area="Platform / Product Engineering",
    )


def _summarize(findings: list[DebtFinding]) -> DebtRegisterSummary:
    severity_counts = Counter(finding.severity.lower() for finding in findings)
    category_counts = Counter(finding.category for finding in findings)

    return DebtRegisterSummary(
        total_findings=len(findings),
        critical=severity_counts["critical"],
        high=severity_counts["high"],
        medium=severity_counts["medium"],
        low=severity_counts["low"],
        top_categories=[category for category, _ in category_counts.most_common(5)],
    )


def analyze_evidence(repository_root: Path) -> DebtRegister:
    root = repository_root.resolve()
    store = _load_evidence_store(root)

    builder = FindingBuilder()

    _analyze_missing_tests(store, builder)
    _analyze_risk_sensitive_without_tests(store, builder)
    _analyze_missing_ci(store, builder)
    _analyze_missing_docs(store, builder)
    _analyze_missing_lockfile(store, builder)
    _analyze_env_without_example(store, builder)

    findings = sorted(
        builder.findings,
        key=lambda finding: finding.risk_score,
        reverse=True,
    )

    return DebtRegister(
        project_name=_load_project_name(root),
        repository=str(root),
        commit=_git_value(store, "git_commit"),
        branch=_git_value(store, "git_branch"),
        summary=_summarize(findings),
        findings=findings,
    )


def render_debt_register_markdown(register: DebtRegister) -> str:
    lines: list[str] = [
        "# Technical Debt Register",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|---|---:|",
        f"| Critical | {register.summary.critical} |",
        f"| High | {register.summary.high} |",
        f"| Medium | {register.summary.medium} |",
        f"| Low | {register.summary.low} |",
        "",
        f"Total findings: **{register.summary.total_findings}**",
        "",
        "## Findings",
        "",
    ]

    if not register.findings:
        lines.extend(
            [
                "No deterministic technical debt findings were generated.",
                "",
                (
                    "This does not prove the repository has no technical debt. "
                    "It means the current deterministic analyzer did not find "
                    "enough evidence to create supported findings."
                ),
                "",
            ]
        )
        return "\n".join(lines)

    for finding in register.findings:
        locations = ", ".join(f"`{location}`" for location in finding.locations) or "N/A"
        evidence = ", ".join(f"`{evidence_id}`" for evidence_id in finding.evidence_ids)

        lines.extend(
            [
                f"### {finding.id}: {finding.title}",
                "",
                f"- Category: `{finding.category}`",
                f"- Severity: {finding.severity}",
                f"- Confidence: {finding.confidence}",
                f"- Risk score: {finding.risk_score}",
                f"- Priority: {finding.priority}",
                f"- Locations: {locations}",
                f"- Evidence: {evidence}",
                f"- Technical impact: {finding.technical_impact}",
                f"- Business impact: {finding.business_impact}",
                f"- Business impact basis: {finding.business_impact_basis}",
                f"- Recommended action: {finding.recommended_action}",
                "",
                "**Verification recommendations:**",
                "",
            ]
        )

        for recommendation in finding.verification_recommendations:
            lines.append(f"- {recommendation}")

        lines.extend(["", "**Risks and cautions:**", ""])

        for caution in finding.risks_and_cautions:
            lines.append(f"- {caution}")

        lines.append("")

    return "\n".join(lines)


def write_debt_register(repository_root: Path) -> DebtRegister:
    root = repository_root.resolve()
    register = analyze_evidence(root)

    json_output_path = root / ".ai-debt" / "debt-register.json"
    markdown_output_path = root / ".ai-debt" / "debt-register.md"

    json_output_path.parent.mkdir(parents=True, exist_ok=True)

    json_output_path.write_text(
        register.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_output_path.write_text(
        render_debt_register_markdown(register),
        encoding="utf-8",
    )

    return register
