"""Tests for v0.3.2 field-validation bug fixes.

Covers:
- .NET manifest suffix detection (BUG-001)
- .sln solution evidence
- Maven POM classification (BUG-002, FP-001, FP-002)
- Terraform lockfile detection (FN-006)
- Risk keyword CI/deployment context narrowing (FP-003)
- Profiler .NET detection
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.analyzer import _classify_pom_role, analyze_evidence
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.mapper import map_units
from pharabius.core.profiler import profile_repository
from pharabius.core.scanner import (
    _is_ci_or_deployment_path,
    scan_repository,
    write_evidence_store,
)
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation

# ── Helpers ──────────────────────────────────────────────────────────


def _setup_repo(tmp_path: Path) -> None:
    """Initialize .ai-debt workspace."""
    initialize_workspace(tmp_path)


def _full_pipeline(tmp_path: Path) -> None:
    """Run init + scan + analyze (writes to disk)."""
    _setup_repo(tmp_path)
    write_evidence_store(tmp_path)
    analyze_evidence(tmp_path)


# ── Task 1: .NET Manifest Detection ──────────────────────────────────


class TestDotNetManifestSuffix:
    def test_csproj_manifest_detected(self, tmp_path: Path) -> None:
        (tmp_path / "Api.csproj").write_text("<Project></Project>", encoding="utf-8")
        store = scan_repository(tmp_path)
        manifest = [e for e in store.evidence if e.type == "manifest_detected"]
        assert any(
            e.metadata and e.metadata.get("manifest_type") == "dotnet_manifest" for e in manifest
        )

    def test_fsproj_manifest_detected(self, tmp_path: Path) -> None:
        (tmp_path / "App.fsproj").write_text("<Project></Project>", encoding="utf-8")
        store = scan_repository(tmp_path)
        manifest = [e for e in store.evidence if e.type == "manifest_detected"]
        assert any(
            e.metadata and e.metadata.get("manifest_type") == "dotnet_manifest" for e in manifest
        )

    def test_vbproj_manifest_detected(self, tmp_path: Path) -> None:
        (tmp_path / "Legacy.vbproj").write_text("<Project></Project>", encoding="utf-8")
        store = scan_repository(tmp_path)
        manifest = [e for e in store.evidence if e.type == "manifest_detected"]
        assert any(
            e.metadata and e.metadata.get("manifest_type") == "dotnet_manifest" for e in manifest
        )

    def test_packages_lockjson_detected(self, tmp_path: Path) -> None:
        (tmp_path / "packages.lock.json").write_text("{}", encoding="utf-8")
        store = scan_repository(tmp_path)
        manifest = [e for e in store.evidence if e.type == "manifest_detected"]
        assert any(e.object and "lockfile" in e.object for e in manifest)


class TestDotNetSolutionFile:
    def test_sln_solution_file_detected(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.sln").write_text(
            "Microsoft Visual Studio Solution File", encoding="utf-8"
        )
        store = scan_repository(tmp_path)
        types = [e.type for e in store.evidence]
        assert "solution_file_detected" in types

    def test_sln_not_manifest_detected(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.sln").write_text(
            "Microsoft Visual Studio Solution File", encoding="utf-8"
        )
        store = scan_repository(tmp_path)
        sln_manifests = [
            e
            for e in store.evidence
            if e.type == "manifest_detected" and e.location.file == "MyApp.sln"
        ]
        assert len(sln_manifests) == 0

    def test_sln_no_dep_finding(self, tmp_path: Path) -> None:
        """Only .sln — no TD-DEP finding."""
        (tmp_path / "MyApp.sln").write_text(
            "Microsoft Visual Studio Solution File", encoding="utf-8"
        )
        _full_pipeline(tmp_path)
        reg = analyze_evidence(tmp_path)
        dep = [f for f in reg.findings if f.category == "TD-DEP" and f.issue_type != "advisory"]
        assert len(dep) == 0


class TestDotNetAnalyzer:
    def test_csproj_without_lockfile(self, tmp_path: Path) -> None:
        """Single .csproj without packages.lock.json produces TD-DEP (advisory)."""
        (tmp_path / "Api.csproj").write_text("<Project></Project>", encoding="utf-8")
        _full_pipeline(tmp_path)
        dep = [f for f in analyze_evidence(tmp_path).findings if f.category == "TD-DEP"]
        assert len(dep) >= 1
        assert any(".NET" in f.title for f in dep)

    def test_csproj_with_lockfile(self, tmp_path: Path) -> None:
        """Single .csproj with same-root packages.lock.json does NOT produce TD-DEP."""
        (tmp_path / "Api.csproj").write_text("<Project></Project>", encoding="utf-8")
        (tmp_path / "packages.lock.json").write_text("{}", encoding="utf-8")
        _full_pipeline(tmp_path)
        dep = [
            f
            for f in analyze_evidence(tmp_path).findings
            if f.category == "TD-DEP" and f.issue_type != "advisory"
        ]
        assert len(dep) == 0

    def test_nested_csproj_root_lockfile_unsatisfied(self, tmp_path: Path) -> None:
        """Nested .csproj + root packages.lock.json still produces TD-DEP (advisory)."""
        (tmp_path / "src" / "Api").mkdir(parents=True)
        (tmp_path / "src" / "Api" / "Api.csproj").write_text(
            "<Project></Project>", encoding="utf-8"
        )
        (tmp_path / "packages.lock.json").write_text("{}", encoding="utf-8")
        _full_pipeline(tmp_path)
        dep = [f for f in analyze_evidence(tmp_path).findings if f.category == "TD-DEP"]
        assert len(dep) >= 1

    def test_nested_csproj_same_root_lockfile(self, tmp_path: Path) -> None:
        """Nested .csproj + same-root packages.lock.json does NOT produce TD-DEP."""
        (tmp_path / "src" / "Api").mkdir(parents=True)
        (tmp_path / "src" / "Api" / "Api.csproj").write_text(
            "<Project></Project>", encoding="utf-8"
        )
        (tmp_path / "src" / "Api" / "packages.lock.json").write_text("{}", encoding="utf-8")
        _full_pipeline(tmp_path)
        dep = [
            f
            for f in analyze_evidence(tmp_path).findings
            if f.category == "TD-DEP" and f.issue_type != "advisory"
        ]
        assert len(dep) == 0


# ── Task 2: Maven POM Classification ─────────────────────────────────


class TestMavenPomClassification:
    def test_parent_pom_no_dep_finding(self, tmp_path: Path) -> None:
        """Root POM with <packaging>pom</packaging> and <modules> → no TD-DEP."""
        (tmp_path / "pom.xml").write_text(
            "<project><packaging>pom</packaging><modules><module>api</module></modules></project>",
            encoding="utf-8",
        )
        _full_pipeline(tmp_path)
        dep = [
            f
            for f in analyze_evidence(tmp_path).findings
            if f.category == "TD-DEP" and f.issue_type != "advisory"
        ]
        assert len(dep) == 0

    def test_parent_pom_whitespace_tolerant(self, tmp_path: Path) -> None:
        """POM with whitespace around tags → correctly classified as parent."""
        (tmp_path / "pom.xml").write_text(
            "<project>\n  <packaging> pom </packaging>\n"
            "  <modules><module>api</module></modules>\n</project>",
            encoding="utf-8",
        )
        item = EvidenceItem(
            evidence_id="EVD-001",
            type="manifest_detected",
            category="deps",
            location=EvidenceLocation(file="pom.xml"),
            summary="test",
        )
        role = _classify_pom_role(item, tmp_path)
        assert role == "parent"

    def test_spring_boot_app_dep_finding(self, tmp_path: Path) -> None:
        """Spring Boot service POM without reproducibility → TD-DEP."""
        (tmp_path / "api-service").mkdir()
        (tmp_path / "api-service" / "pom.xml").write_text(
            "<project><dependencies>"
            "<dependency>spring-boot-starter-web</dependency>"
            "</dependencies></project>",
            encoding="utf-8",
        )
        _full_pipeline(tmp_path)
        dep = [f for f in analyze_evidence(tmp_path).findings if f.category == "TD-DEP"]
        # v3.7.0: lockfile absence is advisory; v3.8.0: Java missing runtime also advisory
        # The Java lockfile absence should still be TD-DEP (advisory)
        assert len(dep) >= 1
        assert any("Java" in f.title for f in dep)

    def test_library_pom_no_dep_finding(self, tmp_path: Path) -> None:
        """Common-lib POM without application signals → no TD-DEP."""
        (tmp_path / "common-lib").mkdir()
        (tmp_path / "common-lib" / "pom.xml").write_text(
            "<project><artifactId>common-lib</artifactId></project>",
            encoding="utf-8",
        )
        _full_pipeline(tmp_path)
        dep = [
            f
            for f in analyze_evidence(tmp_path).findings
            if f.category == "TD-DEP" and f.issue_type != "advisory"
        ]
        assert len(dep) == 0

    def test_maven_with_reproducibility_no_finding(self, tmp_path: Path) -> None:
        """Application POM with mvnw in same root → no TD-DEP."""
        (tmp_path / "api-service").mkdir()
        (tmp_path / "api-service" / "pom.xml").write_text(
            "<project><dependencies>"
            "<dependency>spring-boot-starter-web</dependency>"
            "</dependencies></project>",
            encoding="utf-8",
        )
        (tmp_path / "api-service" / "mvnw").write_text("#!/bin/sh", encoding="utf-8")
        _full_pipeline(tmp_path)
        dep = [
            f
            for f in analyze_evidence(tmp_path).findings
            if f.category == "TD-DEP" and f.issue_type != "advisory"
        ]
        assert len(dep) == 0

    def test_multi_module_one_dep_finding(self, tmp_path: Path) -> None:
        """3 modules (parent + app + lib) → exactly 1 TD-DEP (app only)."""
        (tmp_path / "pom.xml").write_text(
            "<project><packaging>pom</packaging>"
            "<modules><module>api-service</module>"
            "<module>common-lib</module></modules></project>",
            encoding="utf-8",
        )
        (tmp_path / "api-service").mkdir()
        (tmp_path / "api-service" / "pom.xml").write_text(
            "<project><dependencies>"
            "<dependency>spring-boot-starter-web</dependency>"
            "</dependencies></project>",
            encoding="utf-8",
        )
        (tmp_path / "common-lib").mkdir()
        (tmp_path / "common-lib" / "pom.xml").write_text(
            "<project><artifactId>common-lib</artifactId></project>",
            encoding="utf-8",
        )
        _full_pipeline(tmp_path)
        dep = [f for f in analyze_evidence(tmp_path).findings if f.category == "TD-DEP"]
        # v3.7.0: lockfile absence is advisory; expect at least 1 TD-DEP (advisory)
        # for the api-service application POM without lockfile
        assert len(dep) >= 1
        assert any("api-service" in loc for f in dep for loc in f.locations)

    def test_unreadable_pom_no_dep_finding(self, tmp_path: Path) -> None:
        """POM that cannot be read → unknown → no TD-DEP."""
        item = EvidenceItem(
            evidence_id="EVD-001",
            type="manifest_detected",
            category="deps",
            location=EvidenceLocation(file="nonexistent/pom.xml"),
            summary="test",
        )
        role = _classify_pom_role(item, tmp_path)
        assert role == "unknown"


# ── Task 3: Terraform Lockfile ───────────────────────────────────────


class TestTerraformLockfile:
    def test_terraform_lockfile_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".terraform.lock.hcl").write_text(
            'provider "registry.terraform.io/hashicorp/aws" {}',
            encoding="utf-8",
        )
        store = scan_repository(tmp_path)
        types = [e.type for e in store.evidence]
        assert "lockfile_detected" in types

    def test_terraform_no_dep_finding(self, tmp_path: Path) -> None:
        """.tf files without .terraform.lock.hcl do NOT produce TD-DEP in v0.3.2."""
        (tmp_path / "main.tf").write_text('resource "aws_vpc" "main" {}', encoding="utf-8")
        _full_pipeline(tmp_path)
        dep = [
            f
            for f in analyze_evidence(tmp_path).findings
            if f.category == "TD-DEP" and f.issue_type != "advisory"
        ]
        assert len(dep) == 0


# ── Task 4: Risk Keyword CI/Deployment Context ───────────────────────


class TestRiskKeywordCIExclusion:
    def test_ci_path_detection_github(self) -> None:
        assert _is_ci_or_deployment_path(Path(".github/workflows/ci.yml"), Path("/tmp/repo"))
        assert _is_ci_or_deployment_path(Path(".github/workflows/deploy.yml"), Path("/tmp/repo"))

    def test_ci_path_rejects_source(self) -> None:
        assert not _is_ci_or_deployment_path(Path("src/payments/checkout.py"), Path("/tmp/repo"))
        assert not _is_ci_or_deployment_path(Path("src/auth/login.py"), Path("/tmp/repo"))

    def test_ci_checkout_no_risk_signal(self, tmp_path: Path) -> None:
        """CI workflow with actions/checkout → no risk_sensitive_keyword_detected."""
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "steps:\n  - uses: actions/checkout@v4\n  - run: npm test",
            encoding="utf-8",
        )
        store = scan_repository(tmp_path)
        risk_kw = [e for e in store.evidence if e.type == "risk_sensitive_keyword_detected"]
        assert not any("checkout" in (e.raw_observation or "") for e in risk_kw)

    def test_ci_deploy_no_risk_signal(self, tmp_path: Path) -> None:
        """CI workflow with deploy → no risk_sensitive_keyword_detected."""
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "deploy.yml").write_text(
            "name: Deploy\nsteps:\n  - run: deploy production",
            encoding="utf-8",
        )
        store = scan_repository(tmp_path)
        risk_kw = [e for e in store.evidence if e.type == "risk_sensitive_keyword_detected"]
        assert not any("deploy" in (e.raw_observation or "") for e in risk_kw)

    def test_ci_auth_still_risk(self, tmp_path: Path) -> None:
        """CI workflow with 'password' in content → still risk signal."""
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "env:\n  DB_PASSWORD: secret\n", encoding="utf-8"
        )
        store = scan_repository(tmp_path)
        risk_kw = [e for e in store.evidence if e.type == "risk_sensitive_keyword_detected"]
        assert any("password" in (e.raw_observation or "") for e in risk_kw)

    def test_payment_checkout_still_risk(self, tmp_path: Path) -> None:
        """Payment file with 'checkout' → still risk signal."""
        (tmp_path / "src" / "payments").mkdir(parents=True)
        (tmp_path / "src" / "payments" / "checkout.py").write_text(
            "class CheckoutService:\n    pass", encoding="utf-8"
        )
        store = scan_repository(tmp_path)
        risk_path = [e for e in store.evidence if e.type == "risk_sensitive_path_detected"]
        assert any("checkout" in (e.raw_observation or "") for e in risk_path)

    def test_auth_keyword_still_risk(self, tmp_path: Path) -> None:
        """File with 'auth' in path → risk_sensitive_path_detected."""
        (tmp_path / "src" / "auth").mkdir(parents=True)
        (tmp_path / "src" / "auth" / "login.py").write_text(
            "def authenticate(): pass", encoding="utf-8"
        )
        store = scan_repository(tmp_path)
        risk_path = [e for e in store.evidence if e.type == "risk_sensitive_path_detected"]
        assert len(risk_path) > 0

    def test_ci_workflow_no_sec_finding(self, tmp_path: Path) -> None:
        """CI workflow with actions/checkout + no tests → no TD-SEC."""
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
            "steps:\n  - uses: actions/checkout@v4\n  - run: npm test",
            encoding="utf-8",
        )
        _full_pipeline(tmp_path)
        sec = [f for f in analyze_evidence(tmp_path).findings if f.category == "TD-SEC"]
        assert len(sec) == 0


# ── Task 5: Profiler .NET Detection ──────────────────────────────────


class TestProfilerDotNet:
    def test_profiler_detects_nuget_from_csproj(self, tmp_path: Path) -> None:
        (tmp_path / "Api.csproj").write_text("<Project></Project>", encoding="utf-8")
        profile = profile_repository(tmp_path)
        assert "nuget" in profile.package_managers

    def test_profiler_detects_nuget_from_fsproj(self, tmp_path: Path) -> None:
        (tmp_path / "App.fsproj").write_text("<Project></Project>", encoding="utf-8")
        profile = profile_repository(tmp_path)
        assert "nuget" in profile.package_managers

    def test_profiler_sln_build_tool(self, tmp_path: Path) -> None:
        (tmp_path / "MyApp.sln").write_text(
            "Microsoft Visual Studio Solution File", encoding="utf-8"
        )
        profile = profile_repository(tmp_path)
        assert "Visual Studio" in profile.build_tools


# ── Task 5: Mapper .sln Check ────────────────────────────────────────


class TestMapperSlnNoPackageUnit:
    def test_sln_no_package_unit(self, tmp_path: Path) -> None:
        """.sln should not create a package analysis unit."""
        (tmp_path / "MyApp.sln").write_text(
            "Microsoft Visual Studio Solution File", encoding="utf-8"
        )
        (tmp_path / "Api.csproj").write_text("<Project></Project>", encoding="utf-8")
        store = scan_repository(tmp_path)
        profile = profile_repository(tmp_path)
        unit_store = map_units(profile, store)
        package_units = [u for u in unit_store.units if u.unit_type == "package"]
        sln_units = [u for u in package_units if any("sln" in f for f in u.files)]
        assert len(sln_units) == 0
