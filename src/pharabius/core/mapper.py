"""Analysis Unit mapper — groups evidence into engineering areas."""

from __future__ import annotations

import hashlib
from pathlib import Path

import typer

from pharabius.schemas.analysis_unit import AnalysisUnit, AnalysisUnitStore
from pharabius.schemas.evidence import EvidenceStore
from pharabius.schemas.repository import RepositoryProfile

# ---------------------------------------------------------------------------
# Unit types
# ---------------------------------------------------------------------------

UNIT_TYPE_PACKAGE = "package"
UNIT_TYPE_SERVICE = "service"
UNIT_TYPE_CLI = "cli"
UNIT_TYPE_TEST_SUITE = "test_suite"
UNIT_TYPE_CI_WORKFLOW = "ci_workflow"
UNIT_TYPE_INFRA_AREA = "infra_area"
UNIT_TYPE_CONFIG_SURFACE = "config_surface"
UNIT_TYPE_DOCUMENTATION_AREA = "documentation_area"
UNIT_TYPE_SECURITY_SENSITIVE_AREA = "security_sensitive_area"

# ---------------------------------------------------------------------------
# Service directory prefixes
# ---------------------------------------------------------------------------

SERVICE_PREFIXES: frozenset[str] = frozenset(
    {
        "apps",
        "services",
        "packages",
        "crates",
        "modules",
        "cmd",
    }
)

# ---------------------------------------------------------------------------
# Trust-boundary tag mapping
# ---------------------------------------------------------------------------

TRUST_BOUNDARY_TAGS: frozenset[str] = frozenset(
    {
        "auth",
        "authorization",
        "secrets",
        "filesystem",
        "database",
        "network",
        "external_api",
        "serialization",
        "concurrency",
        "user_input",
        "payment",
        "pii",
        "compliance",
        "deployment",
        "observability",
    }
)

_PATH_TAG_PARTS: dict[str, str] = {
    "auth": "auth",
    "login": "auth",
    "session": "auth",
    "token": "secrets",
    "secret": "secrets",
    "credential": "secrets",
    "password": "secrets",
    "api_key": "secrets",
    "payment": "payment",
    "billing": "payment",
    "stripe": "payment",
    "checkout": "payment",
    "database": "database",
    "migration": "database",
    "sql": "database",
    "prisma": "database",
    "user_input": "user_input",
    "upload": "user_input",
    "storage": "filesystem",
    "s3": "filesystem",
    "http": "network",
    "request": "network",
    "fetch": "network",
    "webhook": "external_api",
    "concurrent": "concurrency",
    "thread": "concurrency",
    "queue": "concurrency",
    "worker": "concurrency",
    "pii": "pii",
    "gdpr": "compliance",
    "hipaa": "compliance",
    "pci": "compliance",
    "sox": "compliance",
    "deploy": "deployment",
    "docker": "deployment",
    "k8s": "deployment",
    "kubernetes": "deployment",
    "terraform": "deployment",
    "helm": "deployment",
    "monitor": "observability",
    "metric": "observability",
    "trace": "observability",
    "telemetry": "observability",
}

# CI workflow paths
_CI_PATTERNS: tuple[str, ...] = (
    ".github/workflows/",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
)

# Infrastructure patterns (for matching evidence location files)
_INFRA_SUFFIXES: tuple[str, ...] = (
    ".tf",
    ".tfvars",
)
_INFRA_PREFIXES: tuple[str, ...] = (
    "k8s/",
    "kubernetes/",
    "helm/",
)

# Config file names (not manifests, not CI, not infra)
_CONFIG_FILENAMES: frozenset[str] = frozenset(
    {
        ".env.example",
        "tsconfig.json",
        "docker-compose.yaml",
        "docker-compose.yml",
        "compose.yaml",
        "compose.yml",
        "ruff.toml",
        ".flake8",
        "mypy.ini",
        "pytest.ini",
        "conftest.py",
    }
)

# Documentation filenames
_DOC_FILENAMES: frozenset[str] = frozenset(
    {
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "LICENSE",
    }
)

# Tool/cache directories to skip when building units
_TOOL_CACHE_DIRS: frozenset[str] = frozenset(
    {
        ".importlinter_cache",
        ".import_linter_cache",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        ".ai-debt",
        "dist",
        "build",
        "node_modules",
        ".eggs",
        ".tox",
        "htmlcov",
    }
)

# Low-signal directories: risk evidence here should NOT create security units
_LOW_SIGNAL_DIR_PREFIXES: frozenset[str] = frozenset(
    {
        "docs/",
        "tests/",
        "test/",
        "__tests__/",
        "e2e/",
        "spec/",
        ".github/",
    }
)

# Top-level source directories used for security grouping fallback
_SOURCE_TOP_DIRS: frozenset[str] = frozenset(
    {
        "src",
        "lib",
        "cmd",
        "pkg",
        "internal",
        "app",
        "web",
    }
)

# Confidence per unit type
_CONFIDENCE_BY_TYPE: dict[str, str] = {
    UNIT_TYPE_PACKAGE: "High",
    UNIT_TYPE_SERVICE: "Medium",
    UNIT_TYPE_CLI: "High",
    UNIT_TYPE_TEST_SUITE: "High",
    UNIT_TYPE_CI_WORKFLOW: "High",
    UNIT_TYPE_INFRA_AREA: "High",
    UNIT_TYPE_CONFIG_SURFACE: "Medium",
    UNIT_TYPE_DOCUMENTATION_AREA: "High",
    UNIT_TYPE_SECURITY_SENSITIVE_AREA: "Low",
}

# Limitations per unit type
_LIMITATIONS_BY_TYPE: dict[str, list[str]] = {
    UNIT_TYPE_PACKAGE: ["Package boundary inferred from manifest file location."],
    UNIT_TYPE_SERVICE: [
        "Service boundary inferred from directory convention "
        "(apps/, services/, packages/, crates/, modules/, cmd/)."
    ],
    UNIT_TYPE_CLI: ["CLI entry point inferred from file name or manifest scripts."],
    UNIT_TYPE_TEST_SUITE: ["Test suite boundary inferred from test directory/file patterns."],
    UNIT_TYPE_CI_WORKFLOW: ["CI workflow unit represents a single workflow file."],
    UNIT_TYPE_INFRA_AREA: ["Infrastructure area inferred from IaC file patterns."],
    UNIT_TYPE_CONFIG_SURFACE: [
        "Config surface boundary is approximate — config files may serve multiple areas."
    ],
    UNIT_TYPE_DOCUMENTATION_AREA: [
        "Documentation area inferred from docs/ directory or root doc files."
    ],
    UNIT_TYPE_SECURITY_SENSITIVE_AREA: [
        "Security-sensitive area inferred from path/keyword patterns. "
        "Does not represent verified security boundaries."
    ],
}


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def generate_analysis_unit_id(unit_type: str, root_path: str, primary_file: str) -> str:
    """Generate a stable deterministic analysis unit ID.

    Format: AU-{TYPE_UPPER}-{HEX8}
    """
    normalized_root = root_path.replace("\\", "/")
    while normalized_root.startswith("./"):
        normalized_root = normalized_root[2:]
    if not normalized_root:
        normalized_root = "."
    normalized_primary = primary_file.replace("\\", "/")
    while normalized_primary.startswith("./"):
        normalized_primary = normalized_primary[2:]
    raw = f"{unit_type}:{normalized_root}:{normalized_primary}"
    hex8 = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
    return f"AU-{unit_type.upper()}-{hex8}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(path: str) -> str:
    """Normalize a path to forward slashes."""
    result = path.replace("\\", "/")
    # Only strip leading ./  (not just .)
    while result.startswith("./"):
        result = result[2:]
    return result


def _parent_dir(file_path: str) -> str:
    """Get the parent directory of a file path, normalized."""
    p = Path(_normalize(file_path))
    parent = str(p.parent)
    if parent == ".":
        return "."
    return parent


def _path_starts_with(file_path: str, prefix: str) -> bool:
    """Check if file_path starts with prefix (both normalized)."""
    nf = _normalize(file_path)
    np_ = _normalize(prefix)
    if np_ == ".":
        return True
    return nf == np_ or nf.startswith(np_ + "/")


def _is_service_dir(file_path: str) -> str | None:
    """If file_path is under a service prefix, return the service root dir."""
    nf = _normalize(file_path)
    parts = nf.split("/")
    if len(parts) >= 2 and parts[0] in SERVICE_PREFIXES:
        return f"{parts[0]}/{parts[1]}"
    return None


def _trust_tags_from_path(file_path: str) -> list[str]:
    """Extract trust-boundary tags from a file path."""
    nf = _normalize(file_path).lower()
    tags: list[str] = []
    for part, tag in _PATH_TAG_PARTS.items():
        if part in nf and tag not in tags:
            tags.append(tag)
    return tags


def _is_ci_path(file_path: str) -> bool:
    """Check if a file path is a CI workflow file."""
    nf = _normalize(file_path)
    return any(nf.startswith(pattern) or nf == pattern for pattern in _CI_PATTERNS)


def _is_infra_path(file_path: str) -> bool:
    """Check if a file path is an infrastructure file."""
    nf = _normalize(file_path)
    for suffix in _INFRA_SUFFIXES:
        if nf.endswith(suffix):
            return True
    for prefix in _INFRA_PREFIXES:
        if nf.startswith(prefix):
            return True
    return nf in ("serverless.yml", "pulumi.yaml")


def _is_config_file(file_path: str) -> bool:
    """Check if a file is a config file (not manifest/CI/infra)."""
    nf = _normalize(file_path)
    name = Path(nf).name
    return name in _CONFIG_FILENAMES


def _is_doc_file(file_path: str) -> bool:
    """Check if a file is a documentation file."""
    nf = _normalize(file_path)
    name = Path(nf).name
    if name in _DOC_FILENAMES:
        return True
    return bool(nf.startswith("docs/"))


def _is_tool_cache_path(file_path: str) -> bool:
    """Check if a file path is inside a tool cache directory."""
    nf = _normalize(file_path)
    parts = nf.split("/")
    return any(part in _TOOL_CACHE_DIRS for part in parts)


def _is_low_signal_path(file_path: str) -> bool:
    """Check if a file path is inside a low-signal directory for security purposes."""
    nf = _normalize(file_path)
    for prefix in _LOW_SIGNAL_DIR_PREFIXES:
        if nf.startswith(prefix):
            return True
    # Also check if any path component is a tool cache dir
    return _is_tool_cache_path(file_path)


def _find_security_root(
    file_path: str,
    package_roots: set[str],
    service_roots: set[str],
) -> str:
    """Find nearest meaningful parent directory for a security-sensitive file.

    Hierarchy:
    1. Package root (directory with a manifest)
    2. Service root (under apps/, services/, etc.)
    3. Top-level source directory (src/, lib/, cmd/, etc.)
    4. Root (fallback)
    """
    nf = _normalize(file_path)
    parts = nf.split("/")

    # Check if under a package root
    for pr in sorted(package_roots, key=len, reverse=True):
        prn = _normalize(pr)
        if nf.startswith(prn + "/") or nf == prn:
            return pr

    # Check if under a service root
    for sr in sorted(service_roots, key=len, reverse=True):
        srn = _normalize(sr)
        if nf.startswith(srn + "/") or nf == srn:
            return sr

    # Check if under a top-level source directory
    if len(parts) >= 2 and parts[0] in _SOURCE_TOP_DIRS:
        return parts[0]

    # Fallback: root
    return "."


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------


def map_units(
    profile: RepositoryProfile,
    evidence_store: EvidenceStore,
) -> AnalysisUnitStore:
    """Map repository evidence into analysis units.

    Conservative first pass: produce fewer high-confidence units rather than
    many noisy ones.  Targets semantic anchors, not exhaustive modeling.
    """
    units: list[AnalysisUnit] = []
    repo_root = Path(profile.repository_root)

    # ---- 1. Package units ----
    units.extend(_map_package_units(evidence_store, repo_root))

    # ---- 2. Service units ----
    units.extend(_map_service_units(evidence_store, repo_root))

    # ---- 3. CLI units ----
    units.extend(_map_cli_units(profile, evidence_store, repo_root))

    # ---- 4. Test suite units ----
    units.extend(_map_test_suite_units(evidence_store, repo_root))

    # ---- 5. CI workflow units ----
    units.extend(_map_ci_workflow_units(evidence_store, repo_root))

    # ---- 6. Infra area units ----
    units.extend(_map_infra_area_units(evidence_store, repo_root))

    # ---- 7. Config surface units ----
    units.extend(_map_config_surface_units(evidence_store, repo_root))

    # ---- 8. Documentation area units ----
    units.extend(_map_documentation_area_units(evidence_store, repo_root))

    # ---- 9. Security-sensitive area units ----
    # Pass package and service roots for meaningful grouping
    package_roots = {u.root_path for u in units if u.unit_type == UNIT_TYPE_PACKAGE}
    service_roots = {u.root_path for u in units if u.unit_type == UNIT_TYPE_SERVICE}
    units.extend(
        _map_security_sensitive_units(evidence_store, repo_root, package_roots, service_roots)
    )

    # ---- Deduplicate units by ID ----
    seen_ids: set[str] = set()
    unique_units: list[AnalysisUnit] = []
    for u in units:
        if u.analysis_unit_id not in seen_ids:
            seen_ids.add(u.analysis_unit_id)
            unique_units.append(u)

    # ---- Attach evidence ----
    _attach_evidence(unique_units, evidence_store)

    # ---- Filter zero-evidence units ----
    unique_units = [u for u in unique_units if u.evidence_ids]

    return AnalysisUnitStore(
        repository=str(repo_root),
        units=unique_units,
    )


# ---------------------------------------------------------------------------
# Unit builders
# ---------------------------------------------------------------------------


def _map_package_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create one package unit per directory with a manifest."""
    manifest_dirs: dict[str, list[str]] = {}  # normalized dir -> [files]

    for item in evidence_store.evidence:
        if item.type != "manifest_detected":
            continue
        fp = item.location.file
        if not fp or _is_tool_cache_path(fp):
            continue
        d = _parent_dir(fp)
        manifest_dirs.setdefault(d, []).append(fp)

    units: list[AnalysisUnit] = []
    for dir_path, manifests in manifest_dirs.items():
        name = Path(dir_path).name if dir_path != "." else Path(repo_root).name
        primary = manifests[0]
        uid = generate_analysis_unit_id(UNIT_TYPE_PACKAGE, dir_path, primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_PACKAGE,
                name=name,
                root_path=dir_path,
                primary_files=sorted(set(manifests)),
                manifests=sorted(set(manifests)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_PACKAGE],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_PACKAGE]),
                metadata={"manifest_count": len(manifests)},
            )
        )
    return units


def _map_service_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create service units from directories under service prefixes."""
    service_dirs: dict[str, list[str]] = {}  # service root -> [manifests/main files]

    for item in evidence_store.evidence:
        fp = item.location.file
        if not fp or _is_tool_cache_path(fp):
            continue
        svc_root = _is_service_dir(fp)
        if svc_root is None:
            continue
        # Only if the service dir has a manifest or main entry
        name = Path(fp).name
        if (
            item.type == "manifest_detected"
            or name.startswith("main.")
            or name.startswith("index.")
        ):
            service_dirs.setdefault(svc_root, []).append(fp)

    units: list[AnalysisUnit] = []
    for svc_path, primary_files in service_dirs.items():
        # Pick the best primary: prefer manifest over main
        manifest = next(
            (
                f
                for f in primary_files
                if "manifest" in f
                or Path(f).name
                in (
                    "pyproject.toml",
                    "package.json",
                    "go.mod",
                    "Cargo.toml",
                    "pom.xml",
                    "build.gradle",
                    "composer.json",
                    "Gemfile",
                )
            ),
            primary_files[0],
        )
        uid = generate_analysis_unit_id(UNIT_TYPE_SERVICE, svc_path, manifest)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_SERVICE,
                name=Path(svc_path).name,
                root_path=svc_path,
                primary_files=[manifest],
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_SERVICE],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_SERVICE]),
            )
        )
    return units


def _map_cli_units(
    profile: RepositoryProfile,
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create CLI units from entry points and cli.* files."""
    cli_files: list[str] = []

    # Check evidence for cli.py or */cli.py
    for item in evidence_store.evidence:
        fp = item.location.file
        if not fp or _is_tool_cache_path(fp):
            continue
        name = Path(fp).name
        if name == "cli.py" or (name.startswith("cli.") and name.endswith(".py")):
            cli_files.append(fp)

    # Check profile entry points
    for ep in profile.entry_points:
        if "cli" in ep.lower():
            # Try to find the file in evidence
            for item in evidence_store.evidence:
                if ep in item.location.file:
                    fp = item.location.file
                    if fp not in cli_files:
                        cli_files.append(fp)
                    break

    # Check package_script_detected for CLI-like entries
    for item in evidence_store.evidence:
        if item.type == "package_script_detected":
            subj = item.subject.lower()
            if "cli" in subj or "ai-debt" in subj or "command" in subj:
                fp = item.location.file
                if fp and fp not in cli_files:
                    cli_files.append(fp)

    units: list[AnalysisUnit] = []
    for cli_file in sorted(set(cli_files)):
        d = _parent_dir(cli_file)
        name = Path(cli_file).stem + " CLI"
        uid = generate_analysis_unit_id(UNIT_TYPE_CLI, d, cli_file)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_CLI,
                name=name,
                root_path=d,
                primary_files=[cli_file],
                entry_points=[cli_file],
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_CLI],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_CLI]),
            )
        )
    return units


def _map_test_suite_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create test suite units from test directories."""
    test_dirs: dict[str, list[str]] = {}  # dir -> [test files]

    for item in evidence_store.evidence:
        if item.type != "test_file_detected":
            continue
        fp = item.location.file
        if not fp or _is_tool_cache_path(fp):
            continue
        # Use top-level test directory
        nf = _normalize(fp)
        parts = nf.split("/")
        # Find the first test-like directory
        test_dir = None
        for i, part in enumerate(parts):
            if part in ("tests", "test", "__tests__", "e2e", "spec"):
                test_dir = "/".join(parts[: i + 1])
                break
        if test_dir is None:
            test_dir = _parent_dir(fp)
        test_dirs.setdefault(test_dir, []).append(fp)

    units: list[AnalysisUnit] = []
    for test_dir, files in test_dirs.items():
        name = Path(test_dir).name if test_dir != "." else "root tests"
        # Primary: conftest.py or first test file
        primary = next(
            (f for f in files if Path(f).name == "conftest.py"),
            files[0],
        )
        uid = generate_analysis_unit_id(UNIT_TYPE_TEST_SUITE, test_dir, primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_TEST_SUITE,
                name=name,
                root_path=test_dir,
                primary_files=[primary],
                files=sorted(set(files)),
                related_tests=sorted(set(files)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_TEST_SUITE],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_TEST_SUITE]),
            )
        )
    return units


def _map_ci_workflow_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create CI workflow units from CI config files."""
    ci_files: list[str] = []

    for item in evidence_store.evidence:
        fp = item.location.file
        if not fp or _is_tool_cache_path(fp):
            continue
        if _is_ci_path(fp):
            ci_files.append(fp)

    units: list[AnalysisUnit] = []
    for ci_file in sorted(set(ci_files)):
        d = _parent_dir(ci_file)
        name = Path(ci_file).stem
        uid = generate_analysis_unit_id(UNIT_TYPE_CI_WORKFLOW, d, ci_file)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_CI_WORKFLOW,
                name=name,
                root_path=d,
                primary_files=[ci_file],
                deployment_files=[ci_file],
                trust_boundary_tags=["deployment"],
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_CI_WORKFLOW],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_CI_WORKFLOW]),
            )
        )
    return units


def _map_infra_area_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create infrastructure area units from IaC files."""
    infra_files: list[str] = []

    for item in evidence_store.evidence:
        if item.type == "infrastructure_file_detected":
            fp = item.location.file
            if fp and not _is_tool_cache_path(fp):
                infra_files.append(fp)
                continue
        # Also check deployment_file_detected for docker-compose, etc.
        if item.type == "deployment_file_detected":
            fp = item.location.file
            if fp and not _is_tool_cache_path(fp) and _is_infra_path(fp) and not _is_ci_path(fp):
                infra_files.append(fp)

    # Group by top-level directory
    infra_groups: dict[str, list[str]] = {}
    for fp in infra_files:
        nf = _normalize(fp)
        parts = nf.split("/")
        group = parts[0] if len(parts) > 1 else "."
        infra_groups.setdefault(group, []).append(fp)

    units: list[AnalysisUnit] = []
    for group_dir, files in infra_groups.items():
        primary = files[0]
        name = group_dir if group_dir != "." else "root infra"
        uid = generate_analysis_unit_id(UNIT_TYPE_INFRA_AREA, group_dir, primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_INFRA_AREA,
                name=name,
                root_path=group_dir,
                primary_files=[primary],
                infrastructure_files=sorted(set(files)),
                trust_boundary_tags=["deployment"],
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_INFRA_AREA],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_INFRA_AREA]),
            )
        )
    return units


def _map_config_surface_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create config surface units from config files."""
    config_files: list[str] = []

    for item in evidence_store.evidence:
        fp = item.location.file
        if not fp or _is_tool_cache_path(fp):
            continue
        if item.type == "configuration_file_detected" or _is_config_file(fp):
            # Skip files already claimed by CI/infra
            if _is_ci_path(fp) or _is_infra_path(fp):
                continue
            config_files.append(fp)

    if not config_files:
        return []

    # Group: root configs vs nested configs
    root_configs: list[str] = []
    nested_configs: dict[str, list[str]] = {}
    for fp in config_files:
        d = _parent_dir(fp)
        if d == ".":
            root_configs.append(fp)
        else:
            nested_configs.setdefault(d, []).append(fp)

    units: list[AnalysisUnit] = []
    if root_configs:
        primary = root_configs[0]
        uid = generate_analysis_unit_id(UNIT_TYPE_CONFIG_SURFACE, ".", primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_CONFIG_SURFACE,
                name="root config",
                root_path=".",
                primary_files=sorted(set(root_configs))[:3],
                related_configs=sorted(set(root_configs)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_CONFIG_SURFACE],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_CONFIG_SURFACE]),
            )
        )
    for d, files in nested_configs.items():
        primary = files[0]
        name = Path(d).name + " config"
        uid = generate_analysis_unit_id(UNIT_TYPE_CONFIG_SURFACE, d, primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_CONFIG_SURFACE,
                name=name,
                root_path=d,
                primary_files=[primary],
                related_configs=sorted(set(files)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_CONFIG_SURFACE],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_CONFIG_SURFACE]),
            )
        )
    return units


def _map_documentation_area_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
) -> list[AnalysisUnit]:
    """Create documentation area units from doc files."""
    root_docs: list[str] = []
    docs_dir_files: list[str] = []

    for item in evidence_store.evidence:
        if item.type == "documentation_file_detected":
            fp = item.location.file
            if not fp or _is_tool_cache_path(fp):
                continue
            d = _parent_dir(fp)
            if d == "docs" or _normalize(fp).startswith("docs/"):
                docs_dir_files.append(fp)
            elif d == "." or _is_doc_file(fp):
                root_docs.append(fp)

    units: list[AnalysisUnit] = []
    if docs_dir_files:
        primary = next(
            (f for f in docs_dir_files if Path(f).name == "index.md"),
            docs_dir_files[0],
        )
        uid = generate_analysis_unit_id(UNIT_TYPE_DOCUMENTATION_AREA, "docs", primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_DOCUMENTATION_AREA,
                name="docs",
                root_path="docs",
                primary_files=[primary],
                files=sorted(set(docs_dir_files)),
                related_docs=sorted(set(docs_dir_files)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_DOCUMENTATION_AREA],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_DOCUMENTATION_AREA]),
            )
        )
    if root_docs:
        primary = next(
            (f for f in root_docs if Path(f).name == "README.md"),
            root_docs[0],
        )
        uid = generate_analysis_unit_id(UNIT_TYPE_DOCUMENTATION_AREA, ".", primary)
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_DOCUMENTATION_AREA,
                name="root docs",
                root_path=".",
                primary_files=[primary],
                files=sorted(set(root_docs)),
                related_docs=sorted(set(root_docs)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_DOCUMENTATION_AREA],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_DOCUMENTATION_AREA]),
            )
        )
    return units


def _map_security_sensitive_units(
    evidence_store: EvidenceStore,
    repo_root: Path,
    package_roots: set[str],
    service_roots: set[str],
) -> list[AnalysisUnit]:
    """Create security-sensitive area units grouped by meaningful parent.

    Risk evidence under low-signal directories (docs/, tests/, cache dirs)
    is excluded from security unit creation.
    """
    risk_groups: dict[str, tuple[list[str], list[str]]] = {}  # root -> (files, tags)

    for item in evidence_store.evidence:
        if item.type not in (
            "risk_sensitive_path_detected",
            "risk_sensitive_keyword_detected",
        ):
            continue
        fp = item.location.file
        if not fp or _is_low_signal_path(fp):
            continue

        # Group by meaningful parent, not immediate directory
        sec_root = _find_security_root(fp, package_roots, service_roots)
        tags = _trust_tags_from_path(fp)
        # Also check item.subject for keywords
        if item.subject:
            subj_lower = item.subject.lower()
            for part, tag in _PATH_TAG_PARTS.items():
                if part in subj_lower and tag not in tags:
                    tags.append(tag)
        files, existing_tags = risk_groups.get(sec_root, ([], []))
        if fp not in files:
            files.append(fp)
        for t in tags:
            if t not in existing_tags:
                existing_tags.append(t)
        risk_groups[sec_root] = (files, existing_tags)

    units: list[AnalysisUnit] = []
    for dir_path, (files, tags) in risk_groups.items():
        primary = files[0]
        name = (Path(dir_path).name if dir_path != "." else "root") + " security"
        uid = generate_analysis_unit_id(
            UNIT_TYPE_SECURITY_SENSITIVE_AREA,
            dir_path,
            primary,
        )
        units.append(
            AnalysisUnit(
                analysis_unit_id=uid,
                unit_type=UNIT_TYPE_SECURITY_SENSITIVE_AREA,
                name=name,
                root_path=dir_path,
                primary_files=[primary],
                files=sorted(set(files)),
                trust_boundary_tags=sorted(set(tags)),
                confidence=_CONFIDENCE_BY_TYPE[UNIT_TYPE_SECURITY_SENSITIVE_AREA],
                limitations=list(_LIMITATIONS_BY_TYPE[UNIT_TYPE_SECURITY_SENSITIVE_AREA]),
            )
        )
    return units


# ---------------------------------------------------------------------------
# Evidence attachment (type-specific + territory-aware)
# ---------------------------------------------------------------------------

# Evidence types each unit_type may claim
# Narrow: package/service do NOT broadly claim file_detected
_UNIT_EVIDENCE_ALLOWLIST: dict[str, frozenset[str]] = {
    UNIT_TYPE_PACKAGE: frozenset(
        {
            "manifest_detected",
            "package_script_detected",
        }
    ),
    UNIT_TYPE_SERVICE: frozenset(
        {
            "manifest_detected",
            "package_script_detected",
        }
    ),
    UNIT_TYPE_CLI: frozenset(
        {
            "package_script_detected",
        }
    ),
    UNIT_TYPE_TEST_SUITE: frozenset(
        {
            "test_file_detected",
        }
    ),
    UNIT_TYPE_CI_WORKFLOW: frozenset(
        {
            "deployment_file_detected",
        }
    ),
    UNIT_TYPE_INFRA_AREA: frozenset(
        {
            "infrastructure_file_detected",
            "deployment_file_detected",
        }
    ),
    UNIT_TYPE_CONFIG_SURFACE: frozenset(
        {
            "configuration_file_detected",
        }
    ),
    UNIT_TYPE_DOCUMENTATION_AREA: frozenset(
        {
            "documentation_file_detected",
        }
    ),
    UNIT_TYPE_SECURITY_SENSITIVE_AREA: frozenset(
        {
            "risk_sensitive_path_detected",
            "risk_sensitive_keyword_detected",
        }
    ),
}


def _attach_evidence(
    units: list[AnalysisUnit],
    evidence_store: EvidenceStore,
) -> None:
    """Attach evidence IDs to units with type-specific + territory-aware assignment."""
    # Build set of nested unit root paths (non-package, non-root)
    nested_roots: set[str] = set()
    for u in units:
        nr = _normalize(u.root_path)
        if nr != "." and u.unit_type not in (UNIT_TYPE_PACKAGE,):
            nested_roots.add(nr)

    for unit in units:
        attached: list[str] = []
        unit_root = _normalize(unit.root_path)
        allowed = _UNIT_EVIDENCE_ALLOWLIST.get(unit.unit_type, frozenset())

        for item in evidence_store.evidence:
            fp = _normalize(item.location.file) if item.location.file else ""
            if not fp:
                continue

            if (
                _evidence_matches_unit(
                    fp,
                    item.type,
                    unit_root,
                    unit.unit_type,
                    nested_roots,
                    allowed,
                )
                and item.evidence_id not in attached
            ):
                attached.append(item.evidence_id)

        unit.evidence_ids = sorted(attached)


def _evidence_matches_unit(
    file_path: str,
    item_type: str,
    unit_root: str,
    unit_type: str,
    nested_roots: set[str],
    allowed_types: frozenset[str],
) -> bool:
    """Check if an evidence item belongs to a unit.

    Applies:
    1. Type allowlist: evidence type must be in the unit's allowed set
    2. Path territory: file must be under unit's root_path
    3. Root package exclusivity: root package skips nested territory
    """
    # 1. Type allowlist check
    if item_type not in allowed_types:
        return False

    # 2. Root package: only root-level evidence, not under nested territory
    if unit_root == "." and unit_type == UNIT_TYPE_PACKAGE:
        parent = str(Path(file_path).parent)
        if parent != ".":
            return False
        for nr in nested_roots:
            if file_path.startswith(nr + "/") or file_path.startswith(nr):
                return False
        return True

    # 3. Non-root units: path-prefix match
    if unit_root != ".":
        return file_path.startswith(unit_root + "/") or file_path == unit_root

    # 4. Root non-package units: only root-level evidence
    # (type allowlist already ensures we only get relevant evidence)
    parent = str(Path(file_path).parent)
    return parent == "."


# ---------------------------------------------------------------------------
# Public write function
# ---------------------------------------------------------------------------


def write_analysis_units(repository_root: Path) -> AnalysisUnitStore:
    """Load profile + evidence, map units, write analysis-units.json."""
    output_dir = repository_root / ".ai-debt"

    profile_path = output_dir / "project-profile.json"
    evidence_path = output_dir / "evidence.json"

    if not profile_path.exists():
        raise typer.BadParameter("project-profile.json not found. Run 'ai-debt profile' first.")
    if not evidence_path.exists():
        raise typer.BadParameter("evidence.json not found. Run 'ai-debt scan' first.")

    profile = RepositoryProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
    evidence_store = EvidenceStore.model_validate_json(evidence_path.read_text(encoding="utf-8"))

    unit_store = map_units(profile, evidence_store)

    output_file = output_dir / "analysis-units.json"
    output_file.write_text(
        unit_store.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    return unit_store
