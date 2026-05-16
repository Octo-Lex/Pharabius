from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pharabius.core.exclusions import EXCLUDED_DIR_NAMES, is_excluded_path
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".kts",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".hpp",
    ".scala",
}


TEXT_EXTENSIONS = SOURCE_EXTENSIONS | {
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".xml",
    ".md",
    ".txt",
    ".ini",
    ".cfg",
    ".env",
}


MANIFEST_FILES = {
    "package.json": "node_manifest",
    "package-lock.json": "node_lockfile",
    "yarn.lock": "node_lockfile",
    "pnpm-lock.yaml": "node_lockfile",
    "bun.lock": "node_lockfile",
    "bun.lockb": "node_lockfile",
    "pnpm-workspace.yaml": "node_workspace",
    "turbo.json": "node_workspace",
    "nx.json": "node_workspace",
    "lerna.json": "node_workspace",
    "rush.json": "node_workspace",
    "requirements.txt": "python_manifest",
    "pyproject.toml": "python_manifest",
    "poetry.lock": "python_lockfile",
    "uv.lock": "python_lockfile",
    "Pipfile": "python_manifest",
    "Pipfile.lock": "python_lockfile",
    "pom.xml": "java_manifest",
    "build.gradle": "java_manifest",
    "build.gradle.kts": "java_manifest",
    "settings.gradle": "java_workspace",
    "settings.gradle.kts": "java_workspace",
    "go.mod": "go_manifest",
    "go.sum": "go_lockfile",
    "Cargo.toml": "rust_manifest",
    "Cargo.lock": "rust_lockfile",
    "composer.json": "php_manifest",
    "composer.lock": "php_lockfile",
    "Gemfile": "ruby_manifest",
    "Gemfile.lock": "ruby_lockfile",
    "Package.swift": "swift_manifest",
}


CONFIG_FILES = {
    ".env",
    ".env.example",
    ".env.local",
    ".editorconfig",
    ".gitignore",
    ".dockerignore",
    "tsconfig.json",
    "jsconfig.json",
    "eslint.config.js",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    ".prettierrc",
    ".prettierrc.json",
    "ruff.toml",
    "mypy.ini",
    "pytest.ini",
    "tox.ini",
    "pyproject.toml",
    "setup.cfg",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}


RISK_KEYWORDS = {
    "auth",
    "authentication",
    "authorization",
    "permission",
    "role",
    "session",
    "token",
    "jwt",
    "oauth",
    "saml",
    "password",
    "secret",
    "credential",
    "payment",
    "billing",
    "invoice",
    "checkout",
    "subscription",
    "order",
    "transaction",
    "refund",
    "settlement",
    "pii",
    "personal",
    "customer",
    "patient",
    "financial",
    "audit",
    "retention",
    "encryption",
    "consent",
    "gdpr",
    "hipaa",
    "pci",
    "deploy",
    "release",
    "migration",
    "rollback",
    "incident",
    "alert",
    "monitoring",
    "logging",
    "tracing",
}


IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
    re.compile(r"^\s*from\s+([\w.]+)\s+import\s+", re.MULTILINE),
    re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    re.compile(r"^\s*const\s+.*?=\s+require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE),
]


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_excluded(path: Path, root: Path) -> bool:
    return is_excluded_path(path, root)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []

    for path in root.rglob("*"):
        if path.is_dir():
            continue

        if _is_excluded(path, root):
            continue

        files.append(path)

    return sorted(files)


def _read_text(path: Path, max_chars: int = 100_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if isinstance(value, dict):
        return value

    return {}


def _is_test_path(path: Path, root: Path) -> bool:
    parts = {part.lower() for part in path.relative_to(root).parts}
    name = path.name.lower()

    is_in_test_dir = bool(
        parts
        & {
            "test",
            "tests",
            "__tests__",
            "spec",
            "specs",
            "e2e",
            "integration-tests",
            "unit-tests",
        }
    )

    is_test_file = any(
        name.endswith(suffix)
        for suffix in (
            ".test.py",
            ".test.ts",
            ".test.tsx",
            ".test.js",
            ".test.jsx",
            ".spec.ts",
            ".spec.tsx",
            ".spec.js",
            ".spec.jsx",
        )
    ) or name.endswith("_test.go")

    return is_in_test_dir or is_test_file


def _is_documentation_file(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    name = path.name.lower()

    if name.startswith("readme"):
        return True

    if name in {"changelog.md", "contributing.md", "architecture.md", "adr.md"}:
        return True

    return bool(parts and parts[0].lower() in {"docs", "documentation", "adr", "adrs"})


def _is_deployment_file(path: Path, root: Path) -> bool:
    relative = _relative(path, root)
    name = path.name.lower()

    if name in {
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "procfile",
        "fly.toml",
        "render.yaml",
        "app.yaml",
    }:
        return True

    if relative.startswith(".github/workflows/"):
        return True

    if relative.startswith(".gitlab-ci"):
        return True

    return name in {"jenkinsfile", "bitbucket-pipelines.yml", "azure-pipelines.yml"}


def _is_infrastructure_file(path: Path, root: Path) -> bool:
    relative = _relative(path, root)
    name = path.name.lower()

    if path.suffix == ".tf":
        return True

    if "k8s" in relative.lower() or "kubernetes" in relative.lower():
        return path.suffix in {".yaml", ".yml", ".json"}

    if "helm" in relative.lower():
        return path.suffix in {".yaml", ".yml", ".tpl"}

    return name in {"serverless.yml", "serverless.yaml", "pulumi.yaml", "pulumi.yml"}


def _risk_keywords_for_path(path: Path, root: Path) -> list[str]:
    relative = _relative(path, root).lower()
    normalized = relative.replace("\\", "/").replace("-", "_").replace(".", "_")

    return sorted(keyword for keyword in RISK_KEYWORDS if keyword in normalized)


def _risk_keywords_for_text(text: str) -> list[str]:
    lowered = text.lower()

    return sorted(keyword for keyword in RISK_KEYWORDS if keyword in lowered)


def _extract_imports(path: Path) -> list[str]:
    if path.suffix not in SOURCE_EXTENSIONS:
        return []

    text = _read_text(path)
    if not text:
        return []

    imports: set[str] = set()

    for pattern in IMPORT_PATTERNS:
        for match in pattern.finditer(text):
            imported = match.group(1).strip()
            if imported:
                imports.add(imported)

    return sorted(imports)


def _package_json_scripts(path: Path) -> dict[str, str]:
    if path.name != "package.json":
        return {}

    package_json = _read_json(path)
    scripts = package_json.get("scripts")

    if not isinstance(scripts, dict):
        return {}

    result: dict[str, str] = {}

    for name, command in scripts.items():
        if isinstance(name, str) and isinstance(command, str):
            result[name] = command

    return result


def _git_value(root: Path, command: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *command],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


class EvidenceBuilder:
    def __init__(self) -> None:
        self._counter = 0
        self.items: list[EvidenceItem] = []

    def add(
        self,
        *,
        type_: str,
        category: str,
        summary: str,
        location_file: str = "",
        line_start: int | None = None,
        line_end: int | None = None,
        subject: str = "",
        object_: str = "",
        raw_observation: str = "",
        confidence: str = "Medium",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._counter += 1

        item = EvidenceItem(
            evidence_id=f"EVD-{self._counter:06d}",
            type=type_,
            category=category,
            location=EvidenceLocation(
                file=location_file,
                line_start=line_start,
                line_end=line_end,
            ),
            subject=subject,
            object=object_,
            summary=summary,
            raw_observation=raw_observation,
            confidence=confidence,
            metadata=metadata or {},
        )

        self.items.append(item)


def scan_repository(repository_root: Path) -> EvidenceStore:
    root = repository_root.resolve()
    files = _iter_files(root)

    builder = EvidenceBuilder()

    builder.add(
        type_="repository_summary",
        category="repository",
        summary=f"Repository scan discovered {len(files)} files after exclusions.",
        subject=root.name,
        raw_observation=str(root),
        confidence="High",
        metadata={
            "excluded_directories": sorted(EXCLUDED_DIR_NAMES),
            "file_count": len(files),
        },
    )

    branch = _git_value(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _git_value(root, ["rev-parse", "HEAD"])

    if branch:
        builder.add(
            type_="git_branch",
            category="repository_metadata",
            summary=f"Current git branch is {branch}.",
            subject="git_branch",
            object_=branch,
            raw_observation=branch,
            confidence="High",
        )

    if commit:
        builder.add(
            type_="git_commit",
            category="repository_metadata",
            summary=f"Current git commit is {commit}.",
            subject="git_commit",
            object_=commit,
            raw_observation=commit,
            confidence="High",
        )

    for file_path in files:
        relative = _relative(file_path, root)

        builder.add(
            type_="file_detected",
            category="file_tree",
            summary=f"File detected: {relative}",
            location_file=relative,
            subject=relative,
            raw_observation=relative,
            confidence="High",
            metadata={
                "suffix": file_path.suffix,
                "size_bytes": file_path.stat().st_size,
            },
        )

        if file_path.name in MANIFEST_FILES:
            builder.add(
                type_="manifest_detected",
                category="dependencies",
                summary=f"Dependency or package manifest detected: {relative}",
                location_file=relative,
                subject=relative,
                object_=MANIFEST_FILES[file_path.name],
                raw_observation=file_path.name,
                confidence="High",
                metadata={"manifest_type": MANIFEST_FILES[file_path.name]},
            )

        # Root package.json workspaces: only at repository root
        if file_path.name == "package.json" and relative == "package.json":
            pkg_data = _read_json(file_path)
            workspaces = pkg_data.get("workspaces")
            if workspaces and isinstance(workspaces, (list, dict)):
                builder.add(
                    type_="manifest_detected",
                    category="dependencies",
                    summary=f"Node.js workspace manifest detected: {relative}",
                    location_file=relative,
                    subject=relative,
                    object_="node_workspace",
                    raw_observation="package.json workspaces",
                    confidence="High",
                    metadata={"workspace_type": "package.json"},
                )

        if file_path.name in CONFIG_FILES or file_path.suffix in {".env"}:
            builder.add(
                type_="configuration_file_detected",
                category="configuration",
                summary=f"Configuration file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_test_path(file_path, root):
            builder.add(
                type_="test_file_detected",
                category="test",
                summary=f"Test-related file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_documentation_file(file_path, root):
            builder.add(
                type_="documentation_file_detected",
                category="documentation",
                summary=f"Documentation file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_deployment_file(file_path, root):
            builder.add(
                type_="deployment_file_detected",
                category="operations",
                summary=f"Deployment or CI/CD file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_infrastructure_file(file_path, root):
            builder.add(
                type_="infrastructure_file_detected",
                category="operations",
                summary=f"Infrastructure-as-code file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        path_keywords = _risk_keywords_for_path(file_path, root)
        if path_keywords:
            builder.add(
                type_="risk_sensitive_path_detected",
                category="risk_signal",
                summary=f"Risk-sensitive path detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="Medium",
                metadata={"keywords": path_keywords},
            )

        if file_path.suffix in TEXT_EXTENSIONS or file_path.name in MANIFEST_FILES:
            text = _read_text(file_path)
            text_keywords = _risk_keywords_for_text(text)

            if text_keywords:
                builder.add(
                    type_="risk_sensitive_keyword_detected",
                    category="risk_signal",
                    summary=f"Risk-sensitive keyword detected in {relative}",
                    location_file=relative,
                    subject=relative,
                    raw_observation=", ".join(text_keywords),
                    confidence="Medium",
                    metadata={"keywords": text_keywords[:50]},
                )

        imports = _extract_imports(file_path)
        if imports:
            builder.add(
                type_="imports_detected",
                category="code_structure",
                summary=f"Import statements detected in {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=", ".join(imports),
                confidence="Medium",
                metadata={"imports": imports[:200]},
            )

        scripts = _package_json_scripts(file_path)
        if scripts:
            for script_name, command in scripts.items():
                script_category = "build"
                if "test" in script_name.lower():
                    script_category = "test"
                elif script_name.lower() in {"start", "dev", "serve"}:
                    script_category = "runtime"

                builder.add(
                    type_="package_script_detected",
                    category=script_category,
                    summary=f"Package script detected: {script_name}",
                    location_file=relative,
                    subject=script_name,
                    object_=command,
                    raw_observation=command,
                    confidence="High",
                    metadata={"script_name": script_name, "command": command},
                )

    return EvidenceStore(repository=str(root), evidence=builder.items)


def write_evidence_store(repository_root: Path) -> EvidenceStore:
    store = scan_repository(repository_root)
    output_path = repository_root.resolve() / ".ai-debt" / "evidence.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(store.model_dump_json(indent=2) + "\n", encoding="utf-8")

    return store
