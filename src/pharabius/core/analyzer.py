from __future__ import annotations

import dataclasses
import json
import re
from collections import Counter
from pathlib import Path

from pharabius.core.architecture_analyzer import (
    analyze_architecture_graph as _analyze_architecture_graph,
)
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


# Risk scoring template matching blueprint §12.1.
#
# All 12 factors are present. Two factors default to Low (1) and are not
# overridden by any rule:
#   - architecture_centrality: requires import graph wiring (deferred)
#   - change_frequency: requires git history analysis (deferred)
# Both defaulting to 1 is conservative — no score inflation.
# Full alignment with blueprint §12 requires v0.11.0+ work.
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


def _classify_pom_role(manifest_item: EvidenceItem, root: Path) -> str:
    """Classify a pom.xml as 'parent', 'application', 'library', or 'unknown'.

    Uses whitespace-tolerant regex matching. No XML parser dependency.
    Falls back to 'unknown' on any read error.
    """
    pom_path = root / manifest_item.location.file
    try:
        text = pom_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "unknown"

    # Parent/aggregator: <packaging>pom</packaging> and <modules>
    has_pom_packaging = bool(re.search(r"<\s*packaging\s*>\s*pom\s*<\s*/packaging\s*>", text))
    has_modules = bool(re.search(r"<\s*modules?\s*>", text))
    if has_pom_packaging and has_modules:
        return "parent"

    # Application signals
    app_signals = [
        r"spring-boot-maven-plugin",
        r"spring-boot-starter-web",
        r"spring-boot-starter-actuator",
        r"<\s*mainClass\s*>",
        r"maven-shade-plugin",
        r"maven-assembly-plugin",
    ]
    if any(re.search(sig, text, re.IGNORECASE) for sig in app_signals):
        return "application"

    return "library"


def _analyze_missing_lockfile(
    store: EvidenceStore,
    builder: FindingBuilder,
    *,
    repository_root: Path,
) -> None:
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

            # Java: skip parent/aggregator and library POMs
            if ecosystem.name == "Java":
                classified = []
                for item in items_in_root:
                    role = _classify_pom_role(item, repository_root)
                    if role in ("parent", "library", "unknown"):
                        continue
                    classified.append(item)
                if not classified:
                    continue
                items_in_root = classified

            # One finding per (ecosystem, package_root)
            _emit_lockfile_finding(
                builder,
                ecosystem=ecosystem,
                manifest_items=items_in_root,
                package_root=root,
            )

    # .NET: manifests identified by metadata manifest_type
    dotnet_items = [
        item
        for item in _evidence_by_type(store, "manifest_detected")
        if item.metadata and item.metadata.get("manifest_type") == "dotnet_manifest"
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


# ── TD-CODE: Code-level debt ───────────────────────────────────────────────


def _analyze_large_files(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-CODE: Flag very large source files as code-level debt.

    Conservative threshold: files > 1000 lines detected as evidence.
    Only applies to source files (not generated, config, or lockfiles).
    """
    LARGE_FILE_THRESHOLD = 1000
    source_extensions = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
    }

    large_items: list[EvidenceItem] = []
    for item in store.evidence:
        if item.type != "file_detected" or not item.location.file:
            continue
        ext = Path(item.location.file).suffix.lower()
        if ext not in source_extensions:
            continue
        # Check raw_observation for line count hint
        obs = item.raw_observation.lower()
        if "lines" not in obs:
            continue
        # Extract line count from observation if present
        import re as _re

        match = _re.search(r"(\d+)\s*lines?", obs)
        if match and int(match.group(1)) > LARGE_FILE_THRESHOLD:
            large_items.append(item)

    if not large_items:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 5,
        "blast_radius": 3,
        "test_gap": 2,
        "remediation_simplicity": -1,
    }

    builder.add(
        category="TD-CODE",
        title="Very large source files detected",
        description=(
            f"{len(large_items)} source file(s) exceed {LARGE_FILE_THRESHOLD} lines. "
            "Large files increase cognitive load, review difficulty, and merge conflict risk."
        ),
        evidence_ids=_evidence_ids(large_items),
        locations=_locations(large_items),
        technical_impact=(
            "Files exceeding 1000 lines are harder to understand, test, and refactor. "
            "They often indicate mixed responsibilities or insufficient decomposition."
        ),
        business_impact=(
            "Maintenance cost is inferred from file size evidence. "
            "Validate impact with the Product Engineering Team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Consider decomposing large files into focused modules. "
            "Prioritize files with the most change activity."
        ),
        verification_recommendations=[
            "Verify decomposition does not change public API behavior.",
            "Run existing tests after refactoring.",
        ],
        risks_and_cautions=[
            "Some large files are legitimate (generated code, data tables). Review before acting.",
        ],
        confidence="Low",
        suggested_owner_area="Product Engineering",
    )


def _analyze_debt_markers(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-CODE: Flag TODO/FIXME/HACK debt markers in source evidence.

    Only counts markers in source code evidence, not in config or CI files.
    Requires multiple markers to avoid noise from single-line annotations.
    """
    DEBT_MARKERS = {"todo", "fixme", "hack", "xxx"}
    MIN_MARKERS = 5

    marker_items: list[EvidenceItem] = []
    for item in store.evidence:
        if item.type != "risk_sensitive_keyword_detected":
            continue
        keyword = item.raw_observation.lower().strip()
        if keyword in DEBT_MARKERS:
            marker_items.append(item)

    if len(marker_items) < MIN_MARKERS:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "blast_radius": 2,
        "confidence_modifier": -1,
        "remediation_simplicity": -2,
    }

    builder.add(
        category="TD-CODE",
        title=f"Accumulated debt markers ({len(marker_items)} TODO/FIXME/HACK)",
        description=(
            f"{len(marker_items)} debt marker(s) (TODO, FIXME, HACK, XXX) detected in source code. "
            "Accumulated debt markers indicate deferred maintenance that may compound over time."
        ),
        evidence_ids=_evidence_ids(marker_items),
        locations=_locations(marker_items),
        technical_impact=(
            "Debt markers represent known but unaddressed issues. "
            "High density suggests areas where technical debt is accumulating."
        ),
        business_impact=(
            "Maintenance burden is inferred from debt marker density. "
            "Validate with the Product Engineering Team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Small",
        recommended_action=(
            "Review and triage debt markers. Resolve or convert to tracked issues."
        ),
        verification_recommendations=[
            "Verify marker removal does not lose intent.",
            "Create issues for legitimate deferred work.",
        ],
        risks_and_cautions=[
            "Not all debt markers indicate real debt. Some are planning notes.",
        ],
        confidence="Low",
        suggested_owner_area="Product Engineering",
    )


# ── TD-COMP: Compliance debt ────────────────────────────────────────────────


def _analyze_compliance_keywords(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-COMP: Flag potential compliance-sensitive areas without supporting controls.

    Detects compliance-related keywords (PII, GDPR, HIPAA, PCI, audit, retention)
    in application/domain source code. Creates a finding only when compliance-sensitive
    evidence exists in application code — NOT in scanner logic, test fixtures, docs,
    or keyword-list definitions.
    Does NOT claim legal non-compliance.
    """
    COMPLIANCE_KEYWORDS = {"pii", "gdpr", "hipaa", "pci", "retention", "patient"}

    # Paths that indicate tooling/infrastructure rather than application logic
    NOISE_PATH_SEGMENTS = {
        "tests/",
        "test_",
        "_test.",
        "docs/",
        "templates/",
        "scanner.py",
        "analyzer.py",
        "validator.py",
        "enricher.py",
        "mock_provider.py",
        "test_taxonomy",
    }

    comp_items: list[EvidenceItem] = []
    for item in store.evidence:
        if item.type != "risk_sensitive_keyword_detected":
            continue
        keyword = item.raw_observation.lower().strip()
        if keyword not in COMPLIANCE_KEYWORDS:
            continue
        # Skip evidence from tooling/test/docs paths
        if item.location.file:
            file_lower = item.location.file.lower().replace("\\", "/")
            if any(seg in file_lower for seg in NOISE_PATH_SEGMENTS):
                continue
        comp_items.append(item)

    if not comp_items:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "security_exposure": 3,
        "compliance_exposure": 6,
        "blast_radius": 3,
        "business_critical_proxy": 5,
        "remediation_simplicity": -1,
    }

    builder.add(
        category="TD-COMP",
        title="Potential compliance exposure detected",
        description=(
            f"Compliance-related keywords detected in {len(comp_items)} location(s). "
            "Areas handling PII, healthcare, financial, or regulatory data may require "
            "additional controls, audit logging, or policy documentation."
        ),
        evidence_ids=_evidence_ids(comp_items),
        locations=_locations(comp_items),
        technical_impact=(
            "Compliance-sensitive code areas may lack explicit data handling policies, "
            "audit trails, or retention controls. "
            "This is a potential exposure, not a confirmed violation."
        ),
        business_impact=(
            "Compliance impact is inferred from keyword evidence. "
            "Validate with legal/compliance teams before acting."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Review compliance-sensitive code areas for data handling policies, "
            "audit logging, and retention controls. Document compliance requirements."
        ),
        verification_recommendations=[
            "Verify data handling policies exist for sensitive areas.",
            "Confirm audit logging covers compliance-relevant operations.",
            "Review with legal/compliance team.",
        ],
        risks_and_cautions=[
            "This is a potential exposure based on keyword evidence, "
            "not a confirmed compliance gap.",
            "Do not assume legal non-compliance without legal review.",
        ],
        confidence="Low",
        suggested_owner_area="Product Engineering / Compliance",
    )


# ── TD-OPS: Operational / DevOps debt ───────────────────────────────────────


def _analyze_deployment_without_healthchecks(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-OPS: Flag deployment files without healthcheck/rollback indicators.

    Checks deployment and infrastructure evidence for missing operational
    safety cues. Only triggers when actual deployment/service artifacts
    exist (Dockerfile, k8s, terraform, docker-compose), NOT for CI-only
    workflows (GitHub Actions, GitLab CI) unless accompanied by deployment
    artifacts.
    """
    deploy_items = _evidence_by_type(store, "deployment_file_detected")
    infra_items = _evidence_by_type(store, "infrastructure_file_detected")

    if not deploy_items and not infra_items:
        return

    # Separate CI-only workflows from actual deployment artifacts
    CI_PREFIXES = (".github/workflows/", ".gitlab-ci")
    ci_items = [
        item
        for item in deploy_items
        if item.location.file
        and item.location.file.lower().replace("\\", "/").startswith(CI_PREFIXES)
    ]
    # Actual deployment artifacts: Dockerfile, compose, k8s, terraform, etc.
    deploy_artifacts = [item for item in deploy_items if item not in ci_items]

    # If only CI workflows exist (no actual deployment artifacts),
    # do not flag for missing healthcheck — CI != deployment.
    if not deploy_artifacts and not infra_items:
        return

    all_ops = deploy_artifacts + infra_items
    # Also include CI items for rollback check (CI deploy steps may have rollback)
    all_for_check = all_ops + ci_items

    # Check for healthcheck/rollback evidence in observations
    has_healthcheck = any(
        "healthcheck" in item.raw_observation.lower()
        or "health_check" in item.raw_observation.lower()
        or "readiness" in item.raw_observation.lower()
        for item in all_for_check
    )
    has_rollback = any("rollback" in item.raw_observation.lower() for item in all_for_check)

    if has_healthcheck and has_rollback:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "operational_exposure": 5,
        "blast_radius": 3,
        "business_critical_proxy": 3,
        "remediation_simplicity": -2,
    }

    missing = []
    if not has_healthcheck:
        missing.append("healthcheck/readiness probes")
    if not has_rollback:
        missing.append("rollback indicators")

    builder.add(
        category="TD-OPS",
        title=f"Deployment files missing {', '.join(missing)}",
        description=(
            f"Deployment/infrastructure files detected without clear "
            f"{', '.join(missing)}. Operational safety may be insufficient."
        ),
        evidence_ids=_evidence_ids(all_ops[:5]),
        locations=_locations(all_ops[:5]),
        technical_impact=(
            "Missing operational safety cues can lead to longer incident recovery times "
            "and higher risk during deployments."
        ),
        business_impact=(
            "Operational risk is inferred from deployment evidence. "
            "Validate with the Platform/SRE team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Add healthcheck/readiness probes and rollback strategies to deployment configurations."
        ),
        verification_recommendations=[
            "Verify healthcheck endpoints work in staging.",
            "Test rollback procedure.",
        ],
        risks_and_cautions=[
            "Some deployment tools provide healthchecking outside configuration files.",
        ],
        confidence="Medium",
        suggested_owner_area="Platform / SRE",
    )


# ── TD-DATA: Data debt ─────────────────────────────────────────────────────


def _analyze_data_migration_risk(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-DATA: Flag migration files without rollback/down evidence.

    Detects database migration artifacts and checks for rollback support.
    Conservative: only triggers when actual migration files exist in recognized
    migration directory structures. Does NOT match "schema" in general paths
    (e.g., Pydantic schema definitions, JSON schema validators).
    """
    # Match migration files in recognized migration directory structures
    MIGRATION_DIR_PATTERNS = {
        "migrations/",
        "migrate/",
        "db/migrate/",
        "alembic/",
        "alembic/versions/",
        "prisma/migrations/",
        "supabase/migrations/",
        "flyway/",
        "liquibase/",
        "src/main/resources/db/",
    }
    ROLLBACK_INDICATORS = {"rollback", "down", "revert", "reverse"}

    migration_items: list[EvidenceItem] = []
    for item in store.evidence:
        if item.type not in {"file_detected", "infrastructure_file_detected"}:
            continue
        if not item.location.file:
            continue
        file_path = item.location.file.lower().replace("\\", "/")
        name = Path(item.location.file).name.lower()
        # Exclude docs, tests, and tool paths
        if "/tests/" in file_path or file_path.startswith("tests/"):
            continue
        if "/docs/" in file_path or file_path.startswith("docs/"):
            continue
        # Match files in recognized migration directories
        in_migration_dir = any(p in file_path for p in MIGRATION_DIR_PATTERNS)
        # Also match files with migration-related names
        # (e.g. V001__create_users.sql, 001_initial.py)
        has_migration_name = "migration" in name or "migrate" in name
        if not (in_migration_dir or has_migration_name):
            continue
        migration_items.append(item)

    if not migration_items:
        return

    # Check for rollback evidence
    has_rollback = any(
        any(ind in item.raw_observation.lower() for ind in ROLLBACK_INDICATORS)
        for item in migration_items
    )
    if has_rollback:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 5,
        "blast_radius": 5,
        "operational_exposure": 3,
        "remediation_simplicity": -1,
    }

    builder.add(
        category="TD-DATA",
        title="Schema migrations without rollback evidence",
        description=(
            f"{len(migration_items)} migration/schema file(s) detected without "
            "rollback or down-migration indicators. This increases risk during "
            "schema changes."
        ),
        evidence_ids=_evidence_ids(migration_items[:10]),
        locations=_locations(migration_items[:10]),
        technical_impact=(
            "Migrations without rollback paths make it harder to safely revert schema changes "
            "if issues are discovered after deployment."
        ),
        business_impact=(
            "Data integrity risk is inferred from migration evidence. "
            "Validate with the Product Engineering Team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Add down-migrations or rollback scripts for all schema changes. "
            "Test rollback in staging before production deployment."
        ),
        verification_recommendations=[
            "Verify each migration has a corresponding rollback.",
            "Test rollback procedure in staging.",
        ],
        risks_and_cautions=[
            "Some migration frameworks handle rollback outside files.",
            "Do not infer data loss risk without production evidence.",
        ],
        confidence="Low",
        suggested_owner_area="Product Engineering / Data",
    )


# ── TD-PERF: Performance debt ───────────────────────────────────────────────


def _analyze_performance_patterns(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-PERF: Flag potential performance debt indicators.

    Detects synchronous/blocking patterns in evidence near risk-sensitive areas.
    Conservative: only triggers when both risk-sensitive keywords and
    operational evidence coexist. Does NOT claim measured performance impact.
    """
    # Look for risk-sensitive keywords that suggest hot paths
    risk_items = _risk_signal_items(store)
    if not risk_items:
        return

    # Only flag if there's evidence of synchronous patterns
    # This is intentionally conservative
    sync_keywords = {"sync", "synchronous", "blocking", "block"}
    sync_items: list[EvidenceItem] = []
    for item in store.evidence:
        if item.type != "risk_sensitive_keyword_detected":
            continue
        keyword = item.raw_observation.lower().strip()
        if keyword in sync_keywords:
            sync_items.append(item)

    if not sync_items:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "blast_radius": 3,
        "business_critical_proxy": 3,
        "remediation_simplicity": -1,
    }

    builder.add(
        category="TD-PERF",
        title="Potential synchronous/blocking patterns near sensitive areas",
        description=(
            "Synchronous or blocking patterns detected near risk-sensitive code areas. "
            "This is a potential performance concern, not a measured bottleneck."
        ),
        evidence_ids=_evidence_ids(sync_items[:5]),
        locations=_locations(sync_items[:5]),
        technical_impact=(
            "Synchronous patterns in critical paths can limit throughput and scalability. "
            "This is inferred from evidence, not measured."
        ),
        business_impact=(
            "Performance impact is inferred from code pattern evidence. "
            "Validate with performance testing before acting."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Profile the identified areas under realistic load. "
            "Consider async alternatives if profiling confirms bottlenecks."
        ),
        verification_recommendations=[
            "Run performance profiling before making changes.",
            "Compare before/after metrics after optimization.",
        ],
        risks_and_cautions=[
            "Not all synchronous patterns are performance problems.",
            "Do not optimize without measurement.",
        ],
        confidence="Low",
        suggested_owner_area="Product Engineering",
    )


# ── TD-OBS: Observability debt ──────────────────────────────────────────────


def _analyze_missing_observability(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-OBS: Flag services/entrypoints with no logging or monitoring evidence.

    Only triggers when deployment/service evidence exists but no
    observability keywords are found. Conservative to avoid noise on
    libraries or simple projects.
    """
    OBS_KEYWORDS = {"logging", "monitoring", "tracing", "alert", "metrics"}

    # Need deployment/infra evidence to be relevant
    deploy_items = _evidence_by_type(store, "deployment_file_detected")
    infra_items = _evidence_by_type(store, "infrastructure_file_detected")
    if not deploy_items and not infra_items:
        return

    # Filter out CI-only workflows (same logic as TD-OPS)
    CI_PREFIXES = (".github/workflows/", ".gitlab-ci")
    deploy_artifacts = [
        item
        for item in deploy_items
        if item.location.file
        and not item.location.file.lower().replace("\\", "/").startswith(CI_PREFIXES)
    ]
    if not deploy_artifacts and not infra_items:
        return

    # Check if any observability keywords exist
    obs_items: list[EvidenceItem] = []
    for item in store.evidence:
        if item.type != "risk_sensitive_keyword_detected":
            continue
        keyword = item.raw_observation.lower().strip()
        if keyword in OBS_KEYWORDS:
            obs_items.append(item)

    if obs_items:
        return

    ops_evidence = (deploy_artifacts + infra_items)[:5]

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 3,
        "operational_exposure": 5,
        "blast_radius": 3,
        "business_critical_proxy": 3,
        "remediation_simplicity": -2,
    }

    builder.add(
        category="TD-OBS",
        title="Deployment without observability evidence",
        description=(
            "Deployment/infrastructure files detected but no logging, monitoring, "
            "tracing, or alerting keywords found. Operational visibility may be insufficient."
        ),
        evidence_ids=_evidence_ids(ops_evidence),
        locations=_locations(ops_evidence),
        technical_impact=(
            "Without observability, incidents are harder to detect, diagnose, and resolve. "
            "This is inferred from missing evidence, not confirmed absence."
        ),
        business_impact=(
            "Operational risk is inferred from deployment evidence. "
            "Validate with the SRE/Platform team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Medium",
        recommended_action=(
            "Add structured logging, health metrics, and alerting to deployment configurations. "
            "Consider distributed tracing for service-oriented architectures."
        ),
        verification_recommendations=[
            "Verify logging covers critical operations.",
            "Confirm alerts fire for known failure modes.",
        ],
        risks_and_cautions=[
            "Observability may exist outside repository files (managed services, SaaS tools).",
        ],
        confidence="Low",
        suggested_owner_area="Platform / SRE",
    )


# ── TD-PROCESS: Repository process debt ─────────────────────────────────────


def _analyze_missing_process_artifacts(store: EvidenceStore, builder: FindingBuilder) -> None:
    """TD-PROCESS: Flag missing repository process artifacts.

    Checks for CODEOWNERS, CONTRIBUTING, PR templates, and release checklists.
    Only triggers when multiple process artifacts are absent AND the repository
    has substantive source evidence (not just summary/empty evidence).
    """
    PROCESS_FILES = {
        "CODEOWNERS",
        "CONTRIBUTING.md",
        "CONTRIBUTING.rst",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/pull_request_template.md",
        "docs/CONTRIBUTING.md",
    }

    # Guard: only run when there's substantive file evidence
    source_extensions = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
    }
    has_source_files = any(
        item.type == "file_detected"
        and item.location.file
        and Path(item.location.file).suffix.lower() in source_extensions
        for item in store.evidence
    )
    if not has_source_files:
        return

    file_names = _file_names(store)
    all_file_paths = {
        item.location.file
        for item in store.evidence
        if item.type == "file_detected" and item.location.file
    }

    # Check which process files exist
    missing: list[str] = []
    for pf in PROCESS_FILES:
        if pf not in file_names and pf not in all_file_paths:
            missing.append(pf)

    # Only flag if multiple artifacts are missing
    if len(missing) < 3:
        return

    breakdown = {
        **RISK_SCORE_TEMPLATE,
        "technical_severity": 1,
        "blast_radius": 2,
        "business_critical_proxy": 1,
        "remediation_simplicity": -2,
        "confidence_modifier": -1,
    }

    builder.add(
        category="TD-PROCESS",
        title="Missing repository process artifacts",
        description=(
            f"{len(missing)} process artifact(s) missing: "
            f"{', '.join(missing[:5])}. "
            "These artifacts support code review quality, onboarding, and release governance."
        ),
        evidence_ids=_first_evidence_id(store),
        locations=[],
        technical_impact=(
            "Missing process artifacts weaken code review, onboarding, and release governance. "
            "Impact depends on team size and repository criticality."
        ),
        business_impact=(
            "Process maturity is inferred from missing artifacts. "
            "Validate with the Product Engineering Team."
        ),
        risk_breakdown=breakdown,
        remediation_effort="Small",
        recommended_action=(
            "Add CODEOWNERS for ownership tracking, CONTRIBUTING.md for onboarding, "
            "and PR templates for review consistency."
        ),
        verification_recommendations=[
            "Verify process artifacts match actual team practices.",
            "Review with team leads.",
        ],
        risks_and_cautions=[
            "Small or personal projects may not need all process artifacts.",
            "Missing files do not prove missing processes.",
        ],
        confidence="Low",
        suggested_owner_area="Product Engineering",
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


def _add_architecture_findings(
    repository_root: Path,
    builder: FindingBuilder,
) -> None:
    """Convert architecture graph specs into DebtFinding entries."""

    specs = _analyze_architecture_graph(repository_root)
    for spec in specs:
        builder.add(
            category=spec.category,
            title=spec.title,
            description=spec.description,
            evidence_ids=spec.evidence_ids,
            locations=spec.locations,
            technical_impact=spec.technical_impact,
            business_impact=spec.business_impact,
            risk_breakdown=spec.risk_breakdown,
            remediation_effort=spec.remediation_effort,
            recommended_action=spec.recommended_action,
            verification_recommendations=spec.verification_recommendations,
            risks_and_cautions=spec.risks_and_cautions,
            confidence=spec.confidence,
            suggested_owner_area=spec.suggested_owner_area,
        )


def analyze_evidence(repository_root: Path) -> DebtRegister:
    root = repository_root.resolve()
    store = _load_evidence_store(root)

    builder = FindingBuilder()

    _analyze_missing_tests(store, builder)
    _analyze_risk_sensitive_without_tests(store, builder)
    _analyze_missing_ci(store, builder)
    _analyze_missing_docs(store, builder)
    _analyze_missing_lockfile(store, builder, repository_root=repository_root)
    _analyze_env_without_example(store, builder)

    # Taxonomy closure (v0.10.0)
    _analyze_large_files(store, builder)
    _analyze_debt_markers(store, builder)
    _analyze_compliance_keywords(store, builder)
    _analyze_deployment_without_healthchecks(store, builder)
    _analyze_data_migration_risk(store, builder)
    _analyze_performance_patterns(store, builder)
    _analyze_missing_observability(store, builder)
    _analyze_missing_process_artifacts(store, builder)

    # Architecture graph analysis (TD-ARCH findings)
    _add_architecture_findings(repository_root, builder)

    findings = sorted(
        builder.findings,
        key=lambda finding: finding.risk_score,
        reverse=True,
    )

    # Attach analysis unit IDs if available
    unit_store = _load_analysis_units_if_exists(root)
    if unit_store is not None:
        for finding in findings:
            _attach_units_to_finding(finding, unit_store)

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


def _load_analysis_units_if_exists(root: Path) -> object | None:
    """Load AnalysisUnitStore if analysis-units.json exists, else None."""
    path = root / ".ai-debt" / "analysis-units.json"
    if not path.exists():
        return None
    try:
        from pharabius.schemas.analysis_unit import AnalysisUnitStore

        return AnalysisUnitStore.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _attach_units_to_finding(finding: DebtFinding, unit_store: object) -> None:
    """Attach analysis unit IDs to a finding based on evidence overlap."""
    unit_ids: list[str] = []
    for unit in getattr(unit_store, "units", []):
        unit_eids = getattr(unit, "evidence_ids", [])
        for eid in finding.evidence_ids:
            if eid in unit_eids:
                unit_ids.append(getattr(unit, "analysis_unit_id", ""))
                break
    finding.analysis_unit_ids = sorted(set(unit_ids))


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
