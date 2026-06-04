from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.analyzer import analyze_evidence, write_debt_register
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.scanner import write_evidence_store


def _finding_categories(register: object) -> set[str]:
    findings = register.findings  # type: ignore[attr-defined]
    return {finding.category for finding in findings}


def test_analyze_evidence_generates_supported_findings(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^4.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "src" / "auth" / "session.js").write_text(
        "const token = process.env.JWT_SECRET;\n",
        encoding="utf-8",
    )

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    categories = _finding_categories(register)

    assert "TD-TEST" in categories
    assert "TD-SEC" in categories
    assert "TD-BUILD" in categories
    assert "TD-DEP" in categories

    for finding in register.findings:
        assert finding.evidence_ids
        assert finding.risk_score > 0
        assert finding.priority in {"Low", "Medium", "High", "Critical"}


def test_write_debt_register_writes_json_and_markdown(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "main.py").write_text(
        "print('hello')\n",
        encoding="utf-8",
    )

    write_evidence_store(tmp_path)
    register = write_debt_register(tmp_path)

    json_output = tmp_path / ".ai-debt" / "debt-register.json"
    markdown_output = tmp_path / ".ai-debt" / "debt-register.md"

    written = json.loads(json_output.read_text(encoding="utf-8"))
    markdown = markdown_output.read_text(encoding="utf-8")

    assert json_output.exists()
    assert markdown_output.exists()
    assert written["schema_version"] == "1.0"
    assert written["summary"]["total_findings"] == register.summary.total_findings
    assert "# Technical Debt Register" in markdown


def test_analyze_evidence_does_not_create_findings_without_evidence(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    register = analyze_evidence(tmp_path)

    assert register.summary.total_findings == 0
    assert register.findings == []


def test_analyze_evidence_avoids_missing_ci_when_ci_exists(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Example\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_example.py").write_text(
        "def test_example():\n    assert True\n",
        encoding="utf-8",
    )

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    categories = _finding_categories(register)

    assert "TD-BUILD" not in categories


def _td_dep_findings(register: object) -> list:
    return [f for f in register.findings if f.category == "TD-DEP"]  # type: ignore[attr-defined]


def test_node_lockfile_present_no_dep_finding(tmp_path: Path) -> None:
    """package.json + package-lock.json -> no TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    # v3.3.0: Missing runtime pin now generates TD-DEP too
    dep_findings = _td_dep_findings(register)
    non_runtime = [f for f in dep_findings if "runtime" not in f.title.lower()]
    assert non_runtime == []


def test_python_manifest_missing_lockfile_produces_dep(tmp_path: Path) -> None:
    """pyproject.toml without lock -> TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 1
    assert "Python" in dep_findings[0].title


def test_multi_ecosystem_only_missing_flagged(tmp_path: Path) -> None:
    """package.json+lock and pyproject.toml without lock -> only Python TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 1
    assert "Python" in dep_findings[0].title
    assert "Node" not in dep_findings[0].title


def test_nested_manifest_missing_lock(tmp_path: Path) -> None:
    """services/api/pyproject.toml without lock in same root -> TD-DEP."""
    initialize_workspace(tmp_path)
    svc = tmp_path / "services" / "api"
    svc.mkdir(parents=True)
    (svc / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 1
    assert "Python" in dep_findings[0].title


def test_nested_manifest_with_same_root_lock_no_dep(tmp_path: Path) -> None:
    """services/api/pyproject.toml + services/api/uv.lock -> no TD-DEP."""
    initialize_workspace(tmp_path)
    svc = tmp_path / "services" / "api"
    svc.mkdir(parents=True)
    (svc / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (svc / "uv.lock").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_nested_manifest_root_lock_still_produces_dep(tmp_path: Path) -> None:
    """services/api/pyproject.toml + root uv.lock -> TD-DEP (different root)."""
    initialize_workspace(tmp_path)
    svc = tmp_path / "services" / "api"
    svc.mkdir(parents=True)
    (svc / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 1
    assert "Python" in dep_findings[0].title


def test_nested_manifest_different_service_lock_still_dep(tmp_path: Path) -> None:
    """services/api/pyproject.toml + services/worker/uv.lock -> TD-DEP."""
    initialize_workspace(tmp_path)
    api = tmp_path / "services" / "api"
    worker = tmp_path / "services" / "worker"
    api.mkdir(parents=True)
    worker.mkdir(parents=True)
    (api / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (worker / "uv.lock").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 1


def test_bun_lock_satisfies_node(tmp_path: Path) -> None:
    """package.json + bun.lock -> no TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bun.lock").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_bun_lockb_satisfies_node(tmp_path: Path) -> None:
    """package.json + bun.lockb -> no TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bun.lockb").write_bytes(b"\x00\x01")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_rust_cargo_no_lock_cautious(tmp_path: Path) -> None:
    """Cargo.toml without Cargo.lock -> cautious TD-DEP (Medium, not High)."""
    initialize_workspace(tmp_path)
    (tmp_path / "Cargo.toml").write_text('[package]\nname="x"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.rs").write_text("#[test]\nfn test() {}\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 1
    f = dep_findings[0]
    assert f.severity == "Low"  # Advisory: capped at Low (v3.7.0)
    assert f.issue_type == "advisory"
    assert f.confidence == "Medium"
    assert "Rust" in f.title
    # Rust caution in description, risks_and_cautions, and verification
    assert "library" in f.description.lower()
    assert any("library" in c.lower() for c in f.risks_and_cautions)
    assert any("library" in v.lower() for v in f.verification_recommendations)


def test_python_dual_manifests_grouped_as_one_dep(tmp_path: Path) -> None:
    """pyproject.toml + requirements.txt in same root -> one Python TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep_findings = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep_findings) == 2  # v3.2.0: no-lockfile + unpinned deps
    lockfile_f = next(
        (
            f
            for f in dep_findings
            if "lockfile" in f.title.lower() or "lockfile" in f.description.lower()
        ),
        dep_findings[0],
    )
    assert "Python" in lockfile_f.title
    # Both manifest evidence IDs included
    assert len(lockfile_f.evidence_ids) >= 2


def test_root_manifest_with_root_lock_no_dep(tmp_path: Path) -> None:
    """Root pyproject.toml + root uv.lock -> no TD-DEP."""
    initialize_workspace(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


# --- Step 7.5: Node workspace lockfile policy tests ---


def _bootstrap_repo(tmp_path: Path) -> None:
    """Create minimal CI/docs/tests infrastructure to suppress non-DEP findings."""
    initialize_workspace(tmp_path)
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test(): pass\n", encoding="utf-8")


def test_workspace_root_pkgjson_plus_root_lock_no_dep(tmp_path: Path) -> None:
    """Root package.json + root package-lock.json -> no TD-DEP."""
    _bootstrap_repo(tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_nested_plus_root_workspaces_plus_root_lock(tmp_path: Path) -> None:
    """Nested package.json + root package.json workspaces + root lock -> no TD-DEP."""
    _bootstrap_repo(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"workspaces": ["apps/*"]}), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_nested_plus_pnpm_workspace_plus_root_lock(tmp_path: Path) -> None:
    """Nested package.json + pnpm-workspace.yaml + root pnpm-lock -> no TD-DEP."""
    _bootstrap_repo(tmp_path)
    ui = tmp_path / "packages" / "ui"
    ui.mkdir(parents=True)
    (ui / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n", encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_nested_plus_turbo_plus_root_yarn(tmp_path: Path) -> None:
    """Nested package.json + turbo.json + root yarn.lock -> no TD-DEP."""
    _bootstrap_repo(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "turbo.json").write_text("{}", encoding="utf-8")
    (tmp_path / "yarn.lock").write_text("", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_nested_no_marker_plus_root_lock_still_dep(tmp_path: Path) -> None:
    """Nested package.json + no workspace marker + root lock -> TD-DEP."""
    _bootstrap_repo(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    # Root lockfile but NO workspace marker
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep) == 1
    assert "Node" in dep[0].title


def test_workspace_nested_same_root_lock_no_dep(tmp_path: Path) -> None:
    """Nested package.json + same-root lockfile -> no TD-DEP even without workspace."""
    _bootstrap_repo(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    (web / "package-lock.json").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_root_bun_lock_no_dep(tmp_path: Path) -> None:
    """Root package.json + bun.lock -> no TD-DEP."""
    _bootstrap_repo(tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bun.lock").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_nested_plus_root_workspaces_plus_bun_lockb(tmp_path: Path) -> None:
    """Nested package.json + root workspaces + bun.lockb -> no TD-DEP."""
    _bootstrap_repo(tmp_path)
    ui = tmp_path / "packages" / "ui"
    ui.mkdir(parents=True)
    (ui / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps({"workspaces": ["packages/*"]}), encoding="utf-8"
    )
    (tmp_path / "bun.lockb").write_bytes(b"\x00\x01")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    assert [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()] == []


def test_workspace_python_nested_unaffected_by_node_workspace(tmp_path: Path) -> None:
    """services/api/pyproject.toml + root uv.lock -> TD-DEP even with Node workspace."""
    _bootstrap_repo(tmp_path)
    api = tmp_path / "services" / "api"
    api.mkdir(parents=True)
    (api / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("{}", encoding="utf-8")
    # Add a Node workspace alongside — must not affect Python
    (tmp_path / "package.json").write_text(json.dumps({"workspaces": ["apps/*"]}), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep) == 1
    assert "Python" in dep[0].title


def test_workspace_node_satisfied_python_missing_only_python_dep(tmp_path: Path) -> None:
    """Node workspace satisfied + Python missing lockfile -> only Python TD-DEP."""
    _bootstrap_repo(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"workspaces": ["apps/*"]}), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    # Python manifest without lock
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep) == 1
    assert "Python" in dep[0].title


def test_workspace_nested_pkgjson_workspaces_not_root(tmp_path: Path) -> None:
    """apps/web/package.json with workspaces + root lock -> still TD-DEP."""
    _bootstrap_repo(tmp_path)
    web = tmp_path / "apps" / "web"
    web.mkdir(parents=True)
    (web / "package.json").write_text(json.dumps({"workspaces": ["packages/*"]}), encoding="utf-8")
    # Root lockfile but NO root workspace marker
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")

    write_evidence_store(tmp_path)
    register = analyze_evidence(tmp_path)

    dep = [f for f in _td_dep_findings(register) if "runtime" not in f.title.lower()]
    assert len(dep) == 1
    assert "Node" in dep[0].title
