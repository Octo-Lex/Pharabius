"""Tests for GitHub Action metadata and safety (v2.0.1 S02)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTION_YML = REPO_ROOT / "action.yml"


def _load_action() -> dict:
    with open(ACTION_YML, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestActionMetadata:
    def test_action_yml_exists(self) -> None:
        assert ACTION_YML.exists()

    def test_action_yml_valid_yaml(self) -> None:
        data = _load_action()
        assert isinstance(data, dict)

    def test_has_required_fields(self) -> None:
        data = _load_action()
        assert "name" in data
        assert "description" in data
        assert "inputs" in data
        assert "runs" in data

    def test_composite_action(self) -> None:
        data = _load_action()
        assert data["runs"]["using"] == "composite"

    def test_inputs_have_descriptions(self) -> None:
        data = _load_action()
        for name, inp in data["inputs"].items():
            assert "description" in inp, f"Input {name} missing description"

    def test_inputs_have_defaults(self) -> None:
        data = _load_action()
        for name, inp in data["inputs"].items():
            assert "default" in inp, f"Input {name} missing default"

    def test_mode_input_exists(self) -> None:
        data = _load_action()
        assert "mode" in data["inputs"]
        assert data["inputs"]["mode"]["default"] == "strict"

    def test_generate_sarif_input_exists(self) -> None:
        data = _load_action()
        assert "generate-sarif" in data["inputs"]
        assert data["inputs"]["generate-sarif"]["default"] == "false"

    def test_output_dir_input_exists(self) -> None:
        data = _load_action()
        assert "output-dir" in data["inputs"]

    def test_pharabius_version_input_exists(self) -> None:
        data = _load_action()
        assert "pharabius-version" in data["inputs"]
        assert data["inputs"]["pharabius-version"]["default"] == "2.0.1"

    def test_install_step_uses_version_input(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        assert "pharabius==${{ inputs.pharabius-version }}" in content


class TestActionSafety:
    def test_no_upload_sarif_in_action(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        assert "upload-sarif" not in content
        assert "codeql-action" not in content

    def test_no_github_token_required(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        assert "GITHUB_TOKEN" not in content
        assert "token" not in content.lower() or "No token" in content

    def test_no_github_api_calls(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        assert "api.github.com" not in content
        assert "graphql" not in content.lower()
        assert "checks/create" not in content

    def test_no_pr_comments(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        assert "issues/create-comment" not in content
        assert "pulls/" not in content or "pull_request" not in content

    def test_no_issue_creation(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        assert "issues/create" not in content

    def test_description_mentions_local(self) -> None:
        data = _load_action()
        desc = data["description"].lower()
        assert "local" in desc or "no external" in desc

    def test_no_hardcoded_secrets(self) -> None:
        content = ACTION_YML.read_text(encoding="utf-8")
        for pattern in ["password", "secret", "api_key", "apikey"]:
            assert pattern not in content.lower()


class TestActionDocSafety:
    def test_doc_exists(self) -> None:
        assert (REPO_ROOT / "docs" / "GITHUB_ACTION.md").exists()

    def test_doc_local_only_statement(self) -> None:
        content = (REPO_ROOT / "docs" / "GITHUB_ACTION.md").read_text(encoding="utf-8")
        assert "local-only" in content.lower() or "local only" in content.lower()

    def test_doc_no_token_statement(self) -> None:
        content = (REPO_ROOT / "docs" / "GITHUB_ACTION.md").read_text(encoding="utf-8")
        assert "no github token" in content.lower() or "no token" in content.lower()

    def test_doc_upload_is_opt_in(self) -> None:
        content = (REPO_ROOT / "docs" / "GITHUB_ACTION.md").read_text(encoding="utf-8")
        # The SARIF upload step must be commented out or clearly opt-in
        lines = content.splitlines()
        for line in lines:
            if "upload-sarif" in line and "codeql" in line:
                assert line.strip().startswith("#") or "Optional" in line, (
                    f"SARIF upload must be opt-in: {line}"
                )
