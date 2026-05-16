from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.core.exclusions import EXCLUDED_DIR_NAMES, is_excluded_path
from pharabius.schemas.repository import RepositoryProfile

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".scala": "Scala",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".tf": "Terraform",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".xml": "XML",
}


PACKAGE_MANAGER_FILES = {
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "pnpm-workspace.yaml": "pnpm",
    "requirements.txt": "pip",
    "pyproject.toml": "python",
    "poetry.lock": "poetry",
    "uv.lock": "uv",
    "Pipfile": "pipenv",
    "Pipfile.lock": "pipenv",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "settings.gradle": "gradle",
    "settings.gradle.kts": "gradle",
    "go.mod": "go",
    "Cargo.toml": "cargo",
    "composer.json": "composer",
    "Gemfile": "bundler",
    "Package.swift": "swift-package-manager",
}


BUILD_TOOL_FILES = {
    "vite.config.js": "Vite",
    "vite.config.ts": "Vite",
    "webpack.config.js": "Webpack",
    "webpack.config.ts": "Webpack",
    "rollup.config.js": "Rollup",
    "rollup.config.ts": "Rollup",
    "turbo.json": "Turborepo",
    "nx.json": "Nx",
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "Makefile": "Make",
    "justfile": "Just",
    "Taskfile.yml": "Task",
    "Taskfile.yaml": "Task",
}


CONFIG_FILE_NAMES = {
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


FRAMEWORK_PACKAGES = {
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "express": "Express",
    "fastify": "Fastify",
    "koa": "Koa",
    "@nestjs/core": "NestJS",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "spring-boot": "Spring Boot",
    "rails": "Ruby on Rails",
    "laravel/framework": "Laravel",
}


TEST_FRAMEWORK_PACKAGES = {
    "jest": "Jest",
    "vitest": "Vitest",
    "mocha": "Mocha",
    "jasmine": "Jasmine",
    "cypress": "Cypress",
    "playwright": "Playwright",
    "@playwright/test": "Playwright",
    "pytest": "pytest",
    "unittest": "unittest",
    "rspec": "RSpec",
    "junit": "JUnit",
}


COMMON_ENTRY_POINTS = {
    "main.py",
    "app.py",
    "manage.py",
    "server.py",
    "src/main.py",
    "src/app.py",
    "src/index.py",
    "index.js",
    "server.js",
    "app.js",
    "main.js",
    "src/index.js",
    "src/server.js",
    "src/app.js",
    "index.ts",
    "server.ts",
    "app.ts",
    "main.ts",
    "src/index.ts",
    "src/server.ts",
    "src/app.ts",
    "src/main.ts",
    "cmd/main.go",
    "main.go",
    "src/main.rs",
    "Program.cs",
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

    return files


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _read_text_sample(path: Path, max_chars: int = 50_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _detect_from_package_json(
    package_json_path: Path,
    root: Path,
    detected_frameworks: set[str],
    test_frameworks: set[str],
    build_tools: set[str],
    entry_points: set[str],
    services_or_packages: set[str],
) -> bool:
    package_json = _read_json(package_json_path)
    if not package_json:
        return False

    dependencies: dict[str, Any] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        value = package_json.get(key)
        if isinstance(value, dict):
            dependencies.update(value)

    dependency_names = set(dependencies.keys())

    for package_name, framework_name in FRAMEWORK_PACKAGES.items():
        if package_name in dependency_names:
            detected_frameworks.add(framework_name)

    for package_name, framework_name in TEST_FRAMEWORK_PACKAGES.items():
        if package_name in dependency_names:
            test_frameworks.add(framework_name)

    for package_name, tool_name in {
        "vite": "Vite",
        "webpack": "Webpack",
        "rollup": "Rollup",
        "turbo": "Turborepo",
        "nx": "Nx",
        "typescript": "TypeScript Compiler",
    }.items():
        if package_name in dependency_names:
            build_tools.add(tool_name)

    main_value = package_json.get("main")
    if isinstance(main_value, str):
        main_path = package_json_path.parent / main_value
        if main_path.exists():
            entry_points.add(_relative(main_path, root))

    workspaces = package_json.get("workspaces")
    if isinstance(workspaces, list):
        for workspace in workspaces:
            if isinstance(workspace, str):
                services_or_packages.add(workspace)

    if isinstance(workspaces, dict):
        packages = workspaces.get("packages")
        if isinstance(packages, list):
            for workspace in packages:
                if isinstance(workspace, str):
                    services_or_packages.add(workspace)

    return bool(workspaces)


def _detect_python_frameworks_from_text(
    text: str,
    detected_frameworks: set[str],
    test_frameworks: set[str],
) -> None:
    lowered = text.lower()

    python_framework_markers = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
    }

    for marker, framework_name in python_framework_markers.items():
        if marker in lowered:
            detected_frameworks.add(framework_name)

    if "pytest" in lowered:
        test_frameworks.add("pytest")

    if "unittest" in lowered:
        test_frameworks.add("unittest")


def _is_documentation_file(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    name = path.name.lower()

    if name.startswith("readme"):
        return True

    if name in {"changelog.md", "contributing.md", "architecture.md", "adr.md"}:
        return True

    return bool(
        relative_parts and relative_parts[0].lower() in {"docs", "documentation", "adr", "adrs"}
    )


def _is_test_directory(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    lowered_parts = {part.lower() for part in relative_parts}

    return bool(
        lowered_parts
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

    if ".terraform" in relative:
        return True

    if "k8s" in relative.lower() or "kubernetes" in relative.lower():
        return path.suffix in {".yaml", ".yml", ".json"}

    if "helm" in relative.lower():
        return path.suffix in {".yaml", ".yml", ".tpl"}

    return name in {"serverless.yml", "serverless.yaml", "pulumi.yaml", "pulumi.yml"}


def _has_risk_keyword(path: Path, root: Path) -> bool:
    relative = _relative(path, root).lower()
    tokens = relative.replace("\\", "/").replace("-", "_").replace(".", "_").split("/")
    joined = "_".join(tokens)

    return any(keyword in joined for keyword in RISK_KEYWORDS)


def _detect_monorepo_markers(files: list[Path], root: Path) -> bool:
    names = {_relative(path, root) for path in files}

    if {
        "pnpm-workspace.yaml",
        "lerna.json",
        "nx.json",
        "turbo.json",
        "rush.json",
    } & names:
        return True

    for folder_name in ("apps", "packages", "services"):
        candidate = root / folder_name
        if candidate.exists() and candidate.is_dir():
            return True

    return False


def _detect_services_or_packages(root: Path) -> set[str]:
    services_or_packages: set[str] = set()

    for folder_name in ("apps", "packages", "services"):
        folder = root / folder_name
        if not folder.exists() or not folder.is_dir():
            continue

        for child in folder.iterdir():
            if child.is_dir() and child.name not in EXCLUDED_DIR_NAMES:
                services_or_packages.add(_relative(child, root))

    return services_or_packages


def profile_repository(repository_root: Path) -> RepositoryProfile:
    root = repository_root.resolve()
    files = _iter_files(root)

    detected_languages: set[str] = set()
    detected_frameworks: set[str] = set()
    package_managers: set[str] = set()
    build_tools: set[str] = set()
    test_frameworks: set[str] = set()
    entry_points: set[str] = set()
    deployment_files: set[str] = set()
    infrastructure_files: set[str] = set()
    documentation_files: set[str] = set()
    test_directories: set[str] = set()
    configuration_files: set[str] = set()
    risk_sensitive_areas: set[str] = set()
    services_or_packages: set[str] = _detect_services_or_packages(root)

    monorepo = _detect_monorepo_markers(files, root)

    for file_path in files:
        relative = _relative(file_path, root)
        name = file_path.name

        if file_path.suffix in LANGUAGE_BY_EXTENSION:
            detected_languages.add(LANGUAGE_BY_EXTENSION[file_path.suffix])

        if name == "Dockerfile":
            detected_languages.add("Dockerfile")

        if name in PACKAGE_MANAGER_FILES:
            package_managers.add(PACKAGE_MANAGER_FILES[name])

        if name in BUILD_TOOL_FILES:
            build_tools.add(BUILD_TOOL_FILES[name])

        if relative in COMMON_ENTRY_POINTS:
            entry_points.add(relative)

        if name in CONFIG_FILE_NAMES:
            configuration_files.add(relative)

        if _is_documentation_file(file_path, root):
            documentation_files.add(relative)

        if _is_test_directory(file_path, root):
            parts = file_path.relative_to(root).parts
            for index, part in enumerate(parts):
                if part.lower() in {
                    "test",
                    "tests",
                    "__tests__",
                    "spec",
                    "specs",
                    "e2e",
                    "integration-tests",
                    "unit-tests",
                }:
                    test_directories.add("/".join(parts[: index + 1]))
                    break

        if _is_deployment_file(file_path, root):
            deployment_files.add(relative)

        if _is_infrastructure_file(file_path, root):
            infrastructure_files.add(relative)

        if _has_risk_keyword(file_path, root):
            risk_sensitive_areas.add(relative)

        if name == "package.json":
            package_monorepo = _detect_from_package_json(
                package_json_path=file_path,
                root=root,
                detected_frameworks=detected_frameworks,
                test_frameworks=test_frameworks,
                build_tools=build_tools,
                entry_points=entry_points,
                services_or_packages=services_or_packages,
            )
            monorepo = monorepo or package_monorepo

        if name in {"requirements.txt", "pyproject.toml", "Pipfile"}:
            _detect_python_frameworks_from_text(
                text=_read_text_sample(file_path),
                detected_frameworks=detected_frameworks,
                test_frameworks=test_frameworks,
            )

    if not test_frameworks:
        for file_path in files:
            lowered = file_path.name.lower()
            if lowered.startswith("test_") or lowered.endswith("_test.py"):
                test_frameworks.add("pytest")
            if lowered.endswith("_test.go"):
                test_frameworks.add("Go testing")
            if lowered.endswith(".test.ts") or lowered.endswith(".test.js"):
                test_frameworks.add("Jest/Vitest")
            if lowered.endswith(".spec.ts") or lowered.endswith(".spec.js"):
                test_frameworks.add("Jest/Vitest")

    if detected_languages and package_managers:
        confidence = "High"
    elif detected_languages:
        confidence = "Medium"
    else:
        confidence = "Low"

    limitations: list[str] = []
    if not detected_languages:
        limitations.append("No source languages detected from known file extensions.")
    if not package_managers:
        limitations.append("No package manager or dependency manifest detected.")
    if not test_directories and not test_frameworks:
        limitations.append("No test framework or test directory detected.")
    if not documentation_files:
        limitations.append("No documentation files detected.")

    return RepositoryProfile(
        project_name=root.name,
        repository_root=str(root),
        detected_languages=sorted(detected_languages),
        detected_frameworks=sorted(detected_frameworks),
        package_managers=sorted(package_managers),
        build_tools=sorted(build_tools),
        test_frameworks=sorted(test_frameworks),
        entry_points=sorted(entry_points),
        deployment_files=sorted(deployment_files),
        infrastructure_files=sorted(infrastructure_files),
        documentation_files=sorted(documentation_files),
        test_directories=sorted(test_directories),
        configuration_files=sorted(configuration_files),
        risk_sensitive_areas=sorted(risk_sensitive_areas)[:100],
        monorepo=monorepo,
        services_or_packages=sorted(services_or_packages),
        analysis_confidence=confidence,
        limitations=limitations,
    )


def write_repository_profile(repository_root: Path) -> RepositoryProfile:
    profile = profile_repository(repository_root)
    output_path = repository_root.resolve() / ".ai-debt" / "project-profile.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(profile.model_dump_json(indent=2) + "\n", encoding="utf-8")

    return profile
