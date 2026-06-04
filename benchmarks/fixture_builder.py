"""Programmatic benchmark fixture builder (v3.6.0).

Builds 8 deterministic synthetic repositories for validation:
  small-python-package, medium-python-service, small-node-package,
  medium-node-app, mixed-python-node, coverage-heavy,
  poor-hygiene, clean-baseline.

Each fixture targets specific validation concerns:
  - clean-baseline → validates near-zero false positives
  - poor-hygiene → validates detection sensitivity
  - coverage-heavy → validates multi-format coverage ingestion
  - medium-* → validates realistic mixed-signal detection
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class BenchmarkFixture:
    """Build synthetic benchmark repos programmatically."""

    def __init__(self, name: str, root: Path) -> None:
        self.name = name
        self.root = root / name
        self._ops: list[tuple[str, dict[str, Any]]] = []

    def add_file(self, rel_path: str, content: str) -> BenchmarkFixture:
        self._ops.append(("file", {"rel_path": rel_path, "content": content}))
        return self

    def add_python_file(self, rel_path: str, content: str) -> BenchmarkFixture:
        return self.add_file(rel_path, content)

    def add_js_file(self, rel_path: str, content: str) -> BenchmarkFixture:
        return self.add_file(rel_path, content)

    def add_pyproject(
        self, name: str = "example", deps: list[str] | None = None
    ) -> BenchmarkFixture:
        lines = ["[project]", f"name = '{name}'", "version = '1.0.0'", ""]
        if deps:
            lines.append("dependencies = [")
            for d in deps:
                lines.append(f'    "{d}",')
            lines.append("]")
        return self.add_file("pyproject.toml", "\n".join(lines))

    def add_requirements_txt(self, lines: list[str]) -> BenchmarkFixture:
        return self.add_file("requirements.txt", "\n".join(lines) + "\n")

    def add_package_json(
        self,
        deps: dict[str, str] | None = None,
        dev_deps: dict[str, str] | None = None,
    ) -> BenchmarkFixture:
        pkg: dict[str, Any] = {"name": "example", "version": "1.0.0"}
        if deps:
            pkg["dependencies"] = deps
        if dev_deps:
            pkg["devDependencies"] = dev_deps
        return self.add_file("package.json", json.dumps(pkg, indent=2))

    def add_coverage_json(self, pct: float) -> BenchmarkFixture:
        data = {
            "totals": {
                "percent_covered": pct,
                "covered_lines": int(pct),
                "num_statements": 100,
            }
        }
        return self.add_file("coverage.json", json.dumps(data, indent=2))

    def add_istanbul_coverage(self, metrics: dict[str, float]) -> BenchmarkFixture:
        total = {k: {"pct": v} for k, v in metrics.items()}
        return self.add_file(
            "coverage/coverage-summary.json", json.dumps({"total": total}, indent=2)
        )

    def add_lcov(self, lf: int, lh: int) -> BenchmarkFixture:
        return self.add_file("coverage/lcov.info", f"LF:{lf}\nLH:{lh}\n")

    def add_jacoco_xml(self, counters: list[dict[str, Any]]) -> BenchmarkFixture:
        lines = ['<?xml version="1.0" ?>', "<report>"]
        for c in counters:
            lines.append(
                f'  <counter type="{c["type"]}" missed="{c["missed"]}" covered="{c["covered"]}" />'
            )
        lines.append("</report>")
        return self.add_file("target/site/jacoco/jacoco.xml", "\n".join(lines))

    def add_runtime_pin(self, runtime: str, version: str) -> BenchmarkFixture:
        mapping = {"python": ".python-version", "node": ".nvmrc"}
        return self.add_file(mapping[runtime], version + "\n")

    def add_long_function(self, name: str = "long_func", lines: int = 100) -> BenchmarkFixture:
        body = "\n".join(["    x = 1"] * lines)
        return self.add_python_file(f"src/{name}.py", f"def {name}():\n{body}\n")

    def add_broad_exception(self, count: int = 5) -> BenchmarkFixture:
        blocks = []
        for i in range(count):
            blocks.append(f"try:\n    x{i} = do_stuff()\nexcept:\n    pass\n")
        return self.add_python_file("src/exceptions.py", "\n".join(blocks))

    def add_debt_markers(self, count: int = 10) -> BenchmarkFixture:
        lines = [f"# TODO: fix issue {i} before release" for i in range(count)]
        return self.add_python_file("src/debts.py", "\n".join(lines) + "\n")

    # ── v3.8.0 runtime fixture helpers ──────────────────────────────

    def add_tool_versions(self, entries: dict[str, str]) -> BenchmarkFixture:
        lines = [f"{tool} {ver}" for tool, ver in entries.items()]
        return self.add_file(".tool-versions", "\n".join(lines) + "\n")

    def add_ruby_version(self, version: str) -> BenchmarkFixture:
        return self.add_file(".ruby-version", version + "\n")

    def add_gemfile(self, ruby_version: str | None = None) -> BenchmarkFixture:
        lines = ['source "https://rubygems.org"']
        if ruby_version:
            lines.append(f'ruby "{ruby_version}"')
        return self.add_file("Gemfile", "\n".join(lines) + "\n")

    def add_java_version(self, version: str) -> BenchmarkFixture:
        return self.add_file(".java-version", version + "\n")

    def add_pom_xml(self, java_version: int | None = None) -> BenchmarkFixture:
        lines = ["<project>"]
        if java_version:
            lines.append(
                f"<properties><maven.compiler.release>{java_version}</maven.compiler.release></properties>"
            )
        lines.append("</project>")
        return self.add_file("pom.xml", "\n".join(lines))

    def add_gradle_build(self, java_version: int | None = None) -> BenchmarkFixture:
        if java_version:
            return self.add_file(
                "build.gradle", f"sourceCompatibility = JavaVersion.VERSION_{java_version}\n"
            )
        return self.add_file("build.gradle", "plugins { id 'java' }\n")

    def add_dockerfile(self, base_image: str) -> BenchmarkFixture:
        return self.add_file("Dockerfile", f"FROM {base_image}\n")

    def add_github_workflow(self, name: str, content: str) -> BenchmarkFixture:
        return self.add_file(f".github/workflows/{name}", content)

    def add_runtime_txt(self, version: str) -> BenchmarkFixture:
        return self.add_file("runtime.txt", f"python-{version}\n")

    def add_pyproject_toml(self, requires_python: str | None = None) -> BenchmarkFixture:
        lines = ["[project]", 'name = "example"', 'version = "1.0.0"']
        if requires_python:
            lines.append(f'requires-python = "{requires_python}"')
        return self.add_file("pyproject.toml", "\n".join(lines) + "\n")

    def build(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        for op, kwargs in self._ops:
            if op == "file":
                fpath = self.root / kwargs["rel_path"]
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(kwargs["content"], encoding="utf-8")
        return self.root


def build_all_fixtures(benchmarks_dir: Path) -> dict[str, Path]:
    """Build all 8 benchmark fixtures and return name→path mapping."""
    fixtures: dict[str, Path] = {}

    # 1. small-python-package
    fixtures["small-python-package"] = (
        BenchmarkFixture("small-python-package", benchmarks_dir)
        .add_pyproject(name="small-pkg", deps=["requests>=2.0"])
        .add_python_file("src/small_pkg/__init__.py", "# clean module\n")
        .add_python_file("src/small_pkg/main.py", "def hello():\n    print('hello')\n")
        .build()
    )

    # 2. medium-python-service
    fixtures["medium-python-service"] = (
        BenchmarkFixture("medium-python-service", benchmarks_dir)
        .add_requirements_txt(["flask>=2.0", "requests", "pytest==7.0.0"])
        .add_coverage_json(45.0)
        .add_python_file("src/service/__init__.py", "")
        .add_python_file("src/service/app.py", "from flask import Flask\napp = Flask(__name__)\n")
        .add_long_function("process_handler", 100)
        .add_broad_exception(4)
        .add_debt_markers(8)
        .build()
    )

    # 3. small-node-package
    fixtures["small-node-package"] = (
        BenchmarkFixture("small-node-package", benchmarks_dir)
        .add_package_json(deps={"lodash": "*", "express": "^4.17.1"})
        .add_js_file("src/index.js", "const _ = require('lodash');\nmodule.exports = {};\n")
        .build()
    )

    # 4. medium-node-app
    fixtures["medium-node-app"] = (
        BenchmarkFixture("medium-node-app", benchmarks_dir)
        .add_package_json(
            deps={"express": "*"},
            dev_deps={"jest": "^29.0.0", "typescript": "^5.0.0"},
        )
        .add_istanbul_coverage(
            {"lines": 55.0, "statements": 50.0, "functions": 70.0, "branches": 40.0}
        )
        .add_js_file("src/app.ts", "export function main(): void { console.log('hello'); }\n")
        .add_js_file(
            "src/utils.ts",
            "export function helper(): void {\n"
            "  try {\n"
            "    doWork();\n"
            "  } catch (e) {\n"
            "    // swallow\n"
            "  }\n"
            "}\n",
        )
        .build()
    )

    # 5. mixed-python-node
    fixtures["mixed-python-node"] = (
        BenchmarkFixture("mixed-python-node", benchmarks_dir)
        .add_pyproject(deps=["flask>=2.0"])
        .add_package_json(deps={"express": ">=4.0.0"})
        .add_python_file("backend/app.py", "from flask import Flask\napp = Flask(__name__)\n")
        .add_js_file("frontend/index.js", "const app = require('express');\n")
        .build()
    )

    # 6. coverage-heavy
    fixtures["coverage-heavy"] = (
        BenchmarkFixture("coverage-heavy", benchmarks_dir)
        .add_coverage_json(35.0)
        .add_istanbul_coverage({"lines": 40.0, "statements": 35.0})
        .add_lcov(200, 60)
        .add_jacoco_xml([{"type": "LINE", "missed": 150, "covered": 50}])
        .add_python_file("src/app.py", "def main():\n    pass\n")
        .build()
    )

    # 7. poor-hygiene
    fixtures["poor-hygiene"] = (
        BenchmarkFixture("poor-hygiene", benchmarks_dir)
        .add_requirements_txt(["requests", "flask", "numpy"])
        .add_package_json(deps={"express": "*", "lodash": "latest"})
        .add_python_file("src/main.py", "import requests\n\ndef fetch():\n    pass\n")
        .add_js_file("src/index.js", "const express = require('express');\n")
        .build()
    )

    # 8. clean-baseline
    fixtures["clean-baseline"] = (
        BenchmarkFixture("clean-baseline", benchmarks_dir)
        .add_requirements_txt(["flask==3.0.0", "requests==2.31.0"])
        .add_runtime_pin("python", "3.12.0")
        .add_coverage_json(92.0)
        .add_python_file(
            "src/app.py",
            "from flask import Flask\n\n"
            "app = Flask(__name__)\n\n"
            "def hello():\n    return 'Hello'\n",
        )
        .build()
    )

    return fixtures
