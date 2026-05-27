"""Tests for GitHub Action configuration (W53-S05)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestActionYaml:
    def test_action_yml_exists(self) -> None:
        assert (REPO_ROOT / "action.yml").exists()

    def test_action_yml_valid_yaml(self) -> None:
        with open(REPO_ROOT / "action.yml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_action_has_required_fields(self) -> None:
        with open(REPO_ROOT / "action.yml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "name" in data
        assert "description" in data
        assert "inputs" in data
        assert "runs" in data

    def test_action_inputs_documented(self) -> None:
        with open(REPO_ROOT / "action.yml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for input_name, input_def in data["inputs"].items():
            assert "description" in input_def, f"Input {input_name} missing description"

    def test_action_inputs_have_defaults(self) -> None:
        with open(REPO_ROOT / "action.yml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        required_inputs = {"command", "max-critical", "max-high", "max-total", "fail-on-gate"}
        for name in required_inputs:
            assert name in data["inputs"], f"Missing input: {name}"
            assert "default" in data["inputs"][name], f"Missing default for: {name}"

    def test_no_hardcoded_secrets(self) -> None:
        content = (REPO_ROOT / "action.yml").read_text(encoding="utf-8")
        for pattern in ["password", "secret", "token", "api_key", "apikey"]:
            assert pattern not in content.lower(), f"Found potential secret: {pattern}"

    def test_no_network_dependency(self) -> None:
        content = (REPO_ROOT / "action.yml").read_text(encoding="utf-8")
        assert "curl" not in content
        assert "wget" not in content
        assert "http://" not in content
        assert "https://" not in content or "github.com" in content

    def test_composite_action(self) -> None:
        with open(REPO_ROOT / "action.yml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["runs"]["using"] == "composite"


class TestExampleWorkflow:
    def test_example_workflow_exists(self) -> None:
        assert (REPO_ROOT / ".github" / "workflows" / "pharabius-example.yml").exists()

    def test_example_workflow_valid_yaml(self) -> None:
        with open(
            REPO_ROOT / ".github" / "workflows" / "pharabius-example.yml",
            encoding="utf-8",
        ) as f:
            data = yaml.safe_load(f)
        assert "jobs" in data

    def test_example_workflow_uses_action(self) -> None:
        content = (REPO_ROOT / ".github" / "workflows" / "pharabius-example.yml").read_text(
            encoding="utf-8"
        )
        assert "Pharabius" in content


class TestGithubActionDoc:
    def test_doc_exists(self) -> None:
        assert (REPO_ROOT / "docs" / "GITHUB_ACTION.md").exists()

    def test_doc_has_quickstart(self) -> None:
        content = (REPO_ROOT / "docs" / "GITHUB_ACTION.md").read_text(encoding="utf-8")
        assert "Quick Start" in content
        assert "Elephant-Rock-Lab/Pharabius" in content
