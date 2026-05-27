"""Tests for Analysis Unit mapper."""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.mapper import (
    UNIT_TYPE_CI_WORKFLOW,
    UNIT_TYPE_CONFIG_SURFACE,
    UNIT_TYPE_DOCUMENTATION_AREA,
    UNIT_TYPE_INFRA_AREA,
    UNIT_TYPE_PACKAGE,
    UNIT_TYPE_SECURITY_SENSITIVE_AREA,
    UNIT_TYPE_SERVICE,
    UNIT_TYPE_TEST_SUITE,
    generate_analysis_unit_id,
    map_units,
    write_analysis_units,
)
from pharabius.schemas.analysis_unit import AnalysisUnit, AnalysisUnitStore
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore
from pharabius.schemas.repository import RepositoryProfile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(
    evidence_id: str,
    type_: str,
    category: str = "test",
    file: str = "test.py",
    subject: str = "",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        type=type_,
        category=category,
        location=EvidenceLocation(file=file),
        subject=subject,
        summary=f"{type_}: {file}",
    )


def _minimal_profile(repo_root: Path = Path("/tmp/repo")) -> RepositoryProfile:
    return RepositoryProfile(
        repository_root=str(repo_root),
        project_name="test-repo",
    )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestAnalysisUnitSchema:
    def test_analysis_unit_validates(self) -> None:
        unit = AnalysisUnit(
            analysis_unit_id="AU-PACKAGE-ABC12345",
            unit_type="package",
            name="test",
            root_path=".",
        )
        assert unit.analysis_unit_id == "AU-PACKAGE-ABC12345"
        assert unit.confidence == "Medium"
        assert unit.files == []
        assert unit.evidence_ids == []

    def test_analysis_unit_store_validates(self) -> None:
        store = AnalysisUnitStore(
            repository="/tmp/repo",
            units=[
                AnalysisUnit(
                    analysis_unit_id="AU-PACKAGE-ABC12345",
                    unit_type="package",
                    name="test",
                    root_path=".",
                ),
            ],
        )
        assert len(store.units) == 1
        assert store.schema_version == "1.0"

    def test_analysis_unit_id_format(self) -> None:
        uid = generate_analysis_unit_id("package", ".", "pyproject.toml")
        assert uid.startswith("AU-PACKAGE-")
        assert len(uid) == len("AU-PACKAGE-") + 8

    def test_analysis_unit_default_fields(self) -> None:
        unit = AnalysisUnit(
            analysis_unit_id="AU-PACKAGE-ABC12345",
            unit_type="package",
            name="test",
            root_path=".",
        )
        assert isinstance(unit.files, list)
        assert isinstance(unit.metadata, dict)
        assert isinstance(unit.trust_boundary_tags, list)

    def test_analysis_unit_confidence_string_values(self) -> None:
        for conf in ("High", "Medium", "Low"):
            unit = AnalysisUnit(
                analysis_unit_id="AU-PACKAGE-ABC12345",
                unit_type="package",
                name="test",
                root_path=".",
                confidence=conf,
            )
            assert unit.confidence == conf


# ---------------------------------------------------------------------------
# Deterministic ID tests
# ---------------------------------------------------------------------------


class TestDeterministicIds:
    def test_same_inputs_same_id(self) -> None:
        id1 = generate_analysis_unit_id("package", ".", "pyproject.toml")
        id2 = generate_analysis_unit_id("package", ".", "pyproject.toml")
        assert id1 == id2

    def test_different_inputs_different_id(self) -> None:
        id1 = generate_analysis_unit_id("package", ".", "pyproject.toml")
        id2 = generate_analysis_unit_id("package", "src", "pyproject.toml")
        assert id1 != id2

    def test_different_type_different_id(self) -> None:
        id1 = generate_analysis_unit_id("package", ".", "pyproject.toml")
        id2 = generate_analysis_unit_id("service", ".", "pyproject.toml")
        assert id1 != id2

    def test_deterministic_ids_across_runs(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
            ]
        )
        store1 = map_units(profile, evidence)
        store2 = map_units(profile, evidence)
        ids1 = sorted(u.analysis_unit_id for u in store1.units)
        ids2 = sorted(u.analysis_unit_id for u in store2.units)
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# Package unit tests
# ---------------------------------------------------------------------------


class TestPackageUnits:
    def test_pyproject_toml_creates_package_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
            ]
        )
        store = map_units(profile, evidence)
        packages = [u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE]
        assert len(packages) == 1
        assert packages[0].name == "repo"  # root dir name from Path("/tmp/repo")
        assert packages[0].root_path == "."

    def test_package_json_creates_package_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "package.json"),
            ]
        )
        store = map_units(profile, evidence)
        packages = [u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE]
        assert len(packages) == 1

    def test_go_mod_creates_package_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "go.mod"),
            ]
        )
        store = map_units(profile, evidence)
        packages = [u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE]
        assert len(packages) == 1

    def test_cargo_toml_creates_package_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "Cargo.toml"),
            ]
        )
        store = map_units(profile, evidence)
        packages = [u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE]
        assert len(packages) == 1

    def test_multiple_manifests_same_dir_one_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence(
                    "EVD-000002", "manifest_detected", "dependencies", "requirements.txt"
                ),
            ]
        )
        store = map_units(profile, evidence)
        packages = [u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE]
        assert len(packages) == 1

    def test_nested_package_creates_separate_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence(
                    "EVD-000002",
                    "manifest_detected",
                    "dependencies",
                    "libs/sub/package.json",
                ),
            ]
        )
        store = map_units(profile, evidence)
        packages = [u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE]
        assert len(packages) == 2


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


class TestServiceUnits:
    def test_services_dir_creates_service_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "manifest_detected",
                    "dependencies",
                    "services/api/pyproject.toml",
                ),
            ]
        )
        store = map_units(profile, evidence)
        services = [u for u in store.units if u.unit_type == UNIT_TYPE_SERVICE]
        assert len(services) == 1
        assert services[0].root_path == "services/api"

    def test_no_service_without_manifest(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "file_detected",
                    "file_tree",
                    "services/api/handler.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        services = [u for u in store.units if u.unit_type == UNIT_TYPE_SERVICE]
        assert len(services) == 0


# ---------------------------------------------------------------------------
# Test suite unit tests
# ---------------------------------------------------------------------------


class TestTestSuiteUnits:
    def test_tests_dir_creates_test_suite_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "test_file_detected",
                    "test",
                    "tests/test_main.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        suites = [u for u in store.units if u.unit_type == UNIT_TYPE_TEST_SUITE]
        assert len(suites) == 1
        assert suites[0].root_path == "tests"

    def test_nested_test_dirs_separate_units(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "test_file_detected",
                    "test",
                    "tests/unit/test_a.py",
                ),
                _make_evidence(
                    "EVD-000002",
                    "test_file_detected",
                    "test",
                    "tests/integration/test_b.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        suites = [u for u in store.units if u.unit_type == UNIT_TYPE_TEST_SUITE]
        # Both should be under "tests" top-level dir
        assert len(suites) == 1
        assert suites[0].root_path == "tests"


# ---------------------------------------------------------------------------
# CI workflow unit tests
# ---------------------------------------------------------------------------


class TestCIWorkflowUnits:
    def test_github_workflow_creates_ci_workflow_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "deployment_file_detected",
                    "operations",
                    ".github/workflows/ci.yml",
                ),
            ]
        )
        store = map_units(profile, evidence)
        ci = [u for u in store.units if u.unit_type == UNIT_TYPE_CI_WORKFLOW]
        assert len(ci) == 1
        assert "deployment" in ci[0].trust_boundary_tags


# ---------------------------------------------------------------------------
# Infra area unit tests
# ---------------------------------------------------------------------------


class TestInfraAreaUnits:
    def test_terraform_file_creates_infra_area_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "infrastructure_file_detected",
                    "operations",
                    "infra/main.tf",
                ),
            ]
        )
        store = map_units(profile, evidence)
        infra = [u for u in store.units if u.unit_type == UNIT_TYPE_INFRA_AREA]
        assert len(infra) == 1


# ---------------------------------------------------------------------------
# Documentation area unit tests
# ---------------------------------------------------------------------------


class TestDocumentationAreaUnits:
    def test_readme_creates_documentation_area_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "documentation_file_detected",
                    "documentation",
                    "README.md",
                ),
            ]
        )
        store = map_units(profile, evidence)
        docs = [u for u in store.units if u.unit_type == UNIT_TYPE_DOCUMENTATION_AREA]
        assert len(docs) == 1

    def test_docs_dir_creates_documentation_area_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "documentation_file_detected",
                    "documentation",
                    "docs/guide.md",
                ),
            ]
        )
        store = map_units(profile, evidence)
        docs = [u for u in store.units if u.unit_type == UNIT_TYPE_DOCUMENTATION_AREA]
        assert len(docs) == 1
        assert docs[0].root_path == "docs"


# ---------------------------------------------------------------------------
# Security-sensitive area unit tests
# ---------------------------------------------------------------------------


class TestSecuritySensitiveUnits:
    def test_auth_path_creates_security_unit_with_tags(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "risk_sensitive_path_detected",
                    "risk_signal",
                    "src/auth/session.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        sec = [u for u in store.units if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA]
        assert len(sec) == 1
        assert "auth" in sec[0].trust_boundary_tags

    def test_trust_boundary_tags_from_evidence(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "risk_sensitive_keyword_detected",
                    "risk_signal",
                    "src/api/handler.py",
                    subject="payment",
                ),
            ]
        )
        store = map_units(profile, evidence)
        sec = [u for u in store.units if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA]
        assert len(sec) == 1
        assert "payment" in sec[0].trust_boundary_tags


# ---------------------------------------------------------------------------
# Evidence attachment tests
# ---------------------------------------------------------------------------


class TestEvidenceAttachment:
    def test_units_include_evidence_ids(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence("EVD-000002", "test_file_detected", "test", "tests/test_a.py"),
            ]
        )
        store = map_units(profile, evidence)
        all_eids: list[str] = []
        for u in store.units:
            all_eids.extend(u.evidence_ids)
        # At least some evidence should be attached
        assert len(all_eids) > 0

    def test_root_package_does_not_absorb_tests_evidence(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence("EVD-000002", "test_file_detected", "test", "tests/test_a.py"),
            ]
        )
        store = map_units(profile, evidence)
        root_pkg = next(
            (u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE and u.root_path == "."),
            None,
        )
        assert root_pkg is not None
        # Root package should NOT have test evidence
        assert "EVD-000002" not in root_pkg.evidence_ids

    def test_root_package_does_not_absorb_services_evidence(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence(
                    "EVD-000002",
                    "manifest_detected",
                    "dependencies",
                    "services/api/pyproject.toml",
                ),
            ]
        )
        store = map_units(profile, evidence)
        root_pkg = next(
            (u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE and u.root_path == "."),
            None,
        )
        assert root_pkg is not None
        assert "EVD-000002" not in root_pkg.evidence_ids

    def test_nested_service_evidence_attaches_to_service_unit(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-000001",
                    "manifest_detected",
                    "dependencies",
                    "services/api/pyproject.toml",
                ),
                _make_evidence(
                    "EVD-000002",
                    "file_detected",
                    "file_tree",
                    "services/api/handler.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        svc = next(
            (u for u in store.units if u.unit_type == UNIT_TYPE_SERVICE),
            None,
        )
        assert svc is not None
        # Service should have its own evidence
        assert "EVD-000001" in svc.evidence_ids


# ---------------------------------------------------------------------------
# Confidence tests
# ---------------------------------------------------------------------------


class TestConfidenceValues:
    def test_confidence_values_by_type(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence("EVD-000002", "test_file_detected", "test", "tests/test_a.py"),
                _make_evidence(
                    "EVD-000003",
                    "deployment_file_detected",
                    "operations",
                    ".github/workflows/ci.yml",
                ),
                _make_evidence(
                    "EVD-000004",
                    "risk_sensitive_path_detected",
                    "risk_signal",
                    "src/auth/login.py",
                ),
            ]
        )
        store = map_units(profile, evidence)

        high_confidence_types = {
            UNIT_TYPE_PACKAGE,
            UNIT_TYPE_TEST_SUITE,
            UNIT_TYPE_CI_WORKFLOW,
        }
        for u in store.units:
            if u.unit_type in high_confidence_types:
                assert u.confidence == "High"
            elif u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA:
                assert u.confidence == "Low"


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_idempotency_same_unit_count(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence("EVD-000002", "test_file_detected", "test", "tests/test_a.py"),
            ]
        )
        store1 = map_units(profile, evidence)
        store2 = map_units(profile, evidence)
        assert len(store1.units) == len(store2.units)

    def test_idempotency_same_unit_ids(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence("EVD-000002", "test_file_detected", "test", "tests/test_a.py"),
            ]
        )
        store1 = map_units(profile, evidence)
        store2 = map_units(profile, evidence)
        ids1 = sorted(u.analysis_unit_id for u in store1.units)
        ids2 = sorted(u.analysis_unit_id for u in store2.units)
        assert ids1 == ids2

    def test_idempotency_same_json_except_timestamp(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
            ]
        )
        store1 = map_units(profile, evidence)
        store2 = map_units(profile, evidence)
        # Compare units ignoring generated_at
        for u1, u2 in zip(store1.units, store2.units, strict=False):
            assert u1.analysis_unit_id == u2.analysis_unit_id
            assert u1.unit_type == u2.unit_type
            assert u1.name == u2.name
            assert u1.root_path == u2.root_path
            assert u1.evidence_ids == u2.evidence_ids


# ---------------------------------------------------------------------------
# No duplicate units test
# ---------------------------------------------------------------------------


class TestNoDuplicates:
    def test_no_duplicate_units(self) -> None:
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence("EVD-000002", "manifest_detected", "dependencies", "pyproject.toml"),
            ]
        )
        store = map_units(profile, evidence)
        ids = [u.analysis_unit_id for u in store.units]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# write_analysis_units tests
# ---------------------------------------------------------------------------


class TestWriteAnalysisUnits:
    def test_write_analysis_units_creates_file(self, tmp_path: Path) -> None:
        # Create profile + evidence files
        profile = _minimal_profile(tmp_path)
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "project-profile.json").write_text(profile.model_dump_json(), encoding="utf-8")
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-000001", "manifest_detected", "dependencies", "pyproject.toml"),
            ]
        )
        (ai_debt / "evidence.json").write_text(evidence.model_dump_json(), encoding="utf-8")

        store = write_analysis_units(tmp_path)
        output = ai_debt / "analysis-units.json"
        assert output.exists()
        assert len(store.units) >= 1

    def test_write_fails_without_profile(self, tmp_path: Path) -> None:
        import click

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        evidence = EvidenceStore()
        (ai_debt / "evidence.json").write_text(evidence.model_dump_json(), encoding="utf-8")

        with pytest.raises((SystemExit, Exception)):
            write_analysis_units(tmp_path)

    def test_write_fails_without_evidence(self, tmp_path: Path) -> None:
        import click

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        profile = _minimal_profile(tmp_path)
        (ai_debt / "project-profile.json").write_text(profile.model_dump_json(), encoding="utf-8")

        with pytest.raises((SystemExit, Exception)):
            write_analysis_units(tmp_path)


# ---------------------------------------------------------------------------
# Step 8.2 regression tests - P0: Root over-attachment
# ---------------------------------------------------------------------------


class TestRootAttachmentFix:
    def test_root_package_does_not_attach_doc_evidence(self) -> None:
        """Root package unit must not attach documentation evidence."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence(
                    "EVD-002", "documentation_file_detected", "documentation", "README.md"
                ),
            ]
        )
        store = map_units(profile, evidence)
        root_pkg = next(
            u for u in store.units if u.unit_type == UNIT_TYPE_PACKAGE and u.root_path == "."
        )
        assert "EVD-002" not in root_pkg.evidence_ids

    def test_root_doc_does_not_attach_manifest_evidence(self) -> None:
        """Root documentation unit must not attach manifest evidence."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence(
                    "EVD-002", "documentation_file_detected", "documentation", "README.md"
                ),
            ]
        )
        store = map_units(profile, evidence)
        root_doc = next(
            (
                u
                for u in store.units
                if u.unit_type == UNIT_TYPE_DOCUMENTATION_AREA and u.root_path == "."
            ),
            None,
        )
        if root_doc:
            assert "EVD-001" not in root_doc.evidence_ids

    def test_root_config_does_not_attach_doc_evidence(self) -> None:
        """Root config surface unit must not attach documentation evidence."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001", "configuration_file_detected", "configuration", "ruff.toml"
                ),
                _make_evidence(
                    "EVD-002", "documentation_file_detected", "documentation", "README.md"
                ),
            ]
        )
        store = map_units(profile, evidence)
        root_cfg = next(
            (
                u
                for u in store.units
                if u.unit_type == UNIT_TYPE_CONFIG_SURFACE and u.root_path == "."
            ),
            None,
        )
        if root_cfg:
            assert "EVD-002" not in root_cfg.evidence_ids

    def test_root_security_does_not_attach_manifest_evidence(self) -> None:
        """Root security unit must not attach manifest evidence."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-001", "manifest_detected", "dependencies", "pyproject.toml"),
                _make_evidence(
                    "EVD-002", "risk_sensitive_path_detected", "risk_signal", "src/auth/login.py"
                ),
            ]
        )
        store = map_units(profile, evidence)
        root_sec = next(
            (
                u
                for u in store.units
                if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA and u.root_path == "."
            ),
            None,
        )
        if root_sec:
            assert "EVD-001" not in root_sec.evidence_ids


# ---------------------------------------------------------------------------
# Step 8.2 regression tests - P1: Security grouping
# ---------------------------------------------------------------------------


class TestSecurityGrouping:
    def test_service_auth_groups_under_service_root(self) -> None:
        """Risk files under services/api/auth should group under services/api."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001", "manifest_detected", "dependencies", "services/api/pyproject.toml"
                ),
                _make_evidence(
                    "EVD-002",
                    "risk_sensitive_path_detected",
                    "risk_signal",
                    "services/api/auth/session.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        sec_units = [u for u in store.units if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA]
        assert len(sec_units) <= 1
        if sec_units:
            normalized_root = sec_units[0].root_path.replace("\\", "/")
            assert normalized_root in ("services/api", ".")

    def test_no_security_unit_for_tests_dir(self) -> None:
        """Risk evidence under tests/ should not create security units."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001",
                    "risk_sensitive_keyword_detected",
                    "risk_signal",
                    "tests/test_auth.py",
                    subject="token",
                ),
            ]
        )
        store = map_units(profile, evidence)
        sec_units = [u for u in store.units if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA]
        assert len(sec_units) == 0

    def test_no_security_unit_for_docs_dir(self) -> None:
        """Risk evidence under docs/ should not create security units."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001",
                    "risk_sensitive_keyword_detected",
                    "risk_signal",
                    "docs/security-guide.md",
                    subject="auth",
                ),
            ]
        )
        store = map_units(profile, evidence)
        sec_units = [u for u in store.units if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA]
        assert len(sec_units) == 0

    def test_multiple_risk_files_under_service_aggregate(self) -> None:
        """Multiple risk files under the same service root create one security unit."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001", "manifest_detected", "dependencies", "services/api/pyproject.toml"
                ),
                _make_evidence(
                    "EVD-002",
                    "risk_sensitive_path_detected",
                    "risk_signal",
                    "services/api/auth/session.py",
                ),
                _make_evidence(
                    "EVD-003",
                    "risk_sensitive_path_detected",
                    "risk_signal",
                    "services/api/billing/charge.py",
                ),
            ]
        )
        store = map_units(profile, evidence)
        sec_units = [u for u in store.units if u.unit_type == UNIT_TYPE_SECURITY_SENSITIVE_AREA]
        assert len(sec_units) <= 1


# ---------------------------------------------------------------------------
# Step 8.2 regression tests - P2: Cache noise
# ---------------------------------------------------------------------------


class TestCacheNoise:
    def test_importlinter_cache_no_config_unit(self) -> None:
        """.importlinter_cache files should not produce config_surface units."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001",
                    "configuration_file_detected",
                    "configuration",
                    ".importlinter_cache/foo.json",
                ),
            ]
        )
        store = map_units(profile, evidence)
        cfg_units = [u for u in store.units if u.unit_type == UNIT_TYPE_CONFIG_SURFACE]
        assert len(cfg_units) == 0

    def test_import_linter_cache_no_config_unit(self) -> None:
        """.import_linter_cache files should not produce config_surface units."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence(
                    "EVD-001",
                    "configuration_file_detected",
                    "configuration",
                    ".import_linter_cache/foo.json",
                ),
            ]
        )
        store = map_units(profile, evidence)
        cfg_units = [u for u in store.units if u.unit_type == UNIT_TYPE_CONFIG_SURFACE]
        assert len(cfg_units) == 0


# ---------------------------------------------------------------------------
# Step 8.2 regression tests - P3: Zero evidence filtering
# ---------------------------------------------------------------------------


class TestZeroEvidenceFiltering:
    def test_zero_evidence_units_removed(self) -> None:
        """Units with zero evidence IDs should be filtered out."""
        profile = _minimal_profile()
        evidence = EvidenceStore(
            evidence=[
                _make_evidence("EVD-001", "manifest_detected", "dependencies", "pyproject.toml"),
            ]
        )
        store = map_units(profile, evidence)
        for u in store.units:
            assert len(u.evidence_ids) > 0
