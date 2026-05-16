from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.scanner import scan_repository, write_evidence_store


def _evidence_types(store: object) -> set[str]:
    evidence = store.evidence
    return {item.type for item in evidence}


def test_scan_repository_collects_core_evidence(tmp_path: Path) -> None:
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "infra").mkdir()

    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "build": "vite build",
                    "test": "jest",
                    "start": "node src/index.js",
                },
                "dependencies": {
                    "express": "^4.0.0",
                },
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "src" / "index.js").write_text(
        "const express = require('express');\nconst session = require('./auth/session');\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "auth" / "session.js").write_text(
        "const token = process.env.JWT_SECRET;\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "app.test.js").write_text(
        "test('works', () => {});\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM node:20\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\n",
        encoding="utf-8",
    )
    (tmp_path / "infra" / "main.tf").write_text(
        'resource "aws_s3_bucket" "example" {}\n',
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text(
        "JWT_SECRET=example\n",
        encoding="utf-8",
    )

    store = scan_repository(tmp_path)
    types = _evidence_types(store)

    assert "repository_summary" in types
    assert "file_detected" in types
    assert "manifest_detected" in types
    assert "configuration_file_detected" in types
    assert "test_file_detected" in types
    assert "documentation_file_detected" in types
    assert "deployment_file_detected" in types
    assert "infrastructure_file_detected" in types
    assert "risk_sensitive_path_detected" in types
    assert "risk_sensitive_keyword_detected" in types
    assert "imports_detected" in types
    assert "package_script_detected" in types

    evidence_ids = [item.evidence_id for item in store.evidence]
    assert evidence_ids[0] == "EVD-000001"
    assert len(evidence_ids) == len(set(evidence_ids))


def test_write_evidence_store_writes_evidence_json(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "main.py").write_text(
        "import json\nprint('hello')\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi\npytest\n",
        encoding="utf-8",
    )

    store = write_evidence_store(tmp_path)

    output_path = tmp_path / ".ai-debt" / "evidence.json"
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert written["schema_version"] == "1.0"
    assert written["repository"] == str(tmp_path.resolve())
    assert len(written["evidence"]) == len(store.evidence)
    assert written["evidence"][0]["evidence_id"] == "EVD-000001"


def test_scan_repository_excludes_generated_and_dependency_directories(
    tmp_path: Path,
) -> None:
    (tmp_path / "node_modules" / "example").mkdir(parents=True)
    (tmp_path / ".ai-debt").mkdir()
    (tmp_path / "src").mkdir()

    (tmp_path / "node_modules" / "example" / "index.js").write_text(
        "module.exports = true;\n",
        encoding="utf-8",
    )
    (tmp_path / ".ai-debt" / "evidence.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "src" / "index.py").write_text(
        "print('included')\n",
        encoding="utf-8",
    )

    store = scan_repository(tmp_path)

    files = {item.location.file for item in store.evidence if item.type == "file_detected"}

    assert "src/index.py" in files
    assert "node_modules/example/index.js" not in files
    assert ".ai-debt/evidence.json" not in files


def test_nested_node_modules_excluded(tmp_path: Path) -> None:
    """node_modules at nested depth is excluded."""
    nested = tmp_path / "apps" / "web" / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    (nested / "index.js").write_text("module.exports = true;\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

    store = scan_repository(tmp_path)
    files = {item.location.file for item in store.evidence if item.type == "file_detected"}

    assert "src/main.py" in files
    assert "apps/web/node_modules/pkg/index.js" not in files


def test_nested_target_excluded(tmp_path: Path) -> None:
    """target at nested depth is excluded."""
    nested = tmp_path / "crates" / "foo" / "target" / "debug"
    nested.mkdir(parents=True)
    (nested / "foo.bin").write_bytes(b"\x00")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}\n", encoding="utf-8")

    store = scan_repository(tmp_path)
    files = {item.location.file for item in store.evidence if item.type == "file_detected"}

    assert "src/main.rs" in files
    assert "crates/foo/target/debug/foo.bin" not in files


def test_nested_mypy_cache_excluded(tmp_path: Path) -> None:
    """ ".mypy_cache at nested depth is excluded."""
    nested = tmp_path / "services" / "api" / ".mypy_cache" / "3.11"
    nested.mkdir(parents=True)
    (nested / "data.json").write_text("{}", encoding="utf-8")
    (tmp_path / "services" / "api").mkdir(exist_ok=True)
    (tmp_path / "services" / "api" / "main.py").write_text("print('hello')\n", encoding="utf-8")

    store = scan_repository(tmp_path)
    files = {item.location.file for item in store.evidence if item.type == "file_detected"}

    assert "services/api/main.py" in files
    assert "services/api/.mypy_cache/3.11/data.json" not in files


def test_nested_ruff_cache_excluded(tmp_path: Path) -> None:
    """ ".ruff_cache at nested depth is excluded."""
    nested = tmp_path / "pkg" / ".ruff_cache"
    nested.mkdir(parents=True)
    (nested / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "main.py").write_text("print('hello')\n", encoding="utf-8")

    store = scan_repository(tmp_path)
    files = {item.location.file for item in store.evidence if item.type == "file_detected"}

    assert "pkg/main.py" in files
    assert "pkg/.ruff_cache/__init__.py" not in files


def test_go_test_file_detected(tmp_path: Path) -> None:
    """Go *_test.go produces test_file_detected evidence."""
    (tmp_path / "handler_test.go").write_text(
        'package main\nimport "testing"\nfunc TestHandler(t *testing.T) {}\n',
        encoding="utf-8",
    )

    store = scan_repository(tmp_path)
    test_files = [
        item
        for item in store.evidence
        if item.type == "test_file_detected" and item.location.file == "handler_test.go"
    ]

    assert test_files, "Expected test_file_detected evidence for handler_test.go"
