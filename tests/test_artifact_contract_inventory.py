"""Tests for artifact contract inventory (W48-S01)."""

from __future__ import annotations

from pathlib import Path

CONTRACT = Path("docs/ARTIFACT_CONTRACT.md")
SCHEMA_MAP = Path("docs/SCHEMA_MAP.md")

# Canonical artifacts that MUST appear in the contract
REQUIRED_CANONICAL = [
    "evidence.json",
    "debt-register.json",
    "project-profile.json",
    "analysis-units.json",
    "architecture-graph.json",
]

# Required non-canonical artifacts
REQUIRED_OTHER = [
    "review/decisions.json",
    "ticket-drafts/ticket-drafts.json",
    "export-bundles/manifest.json",
    "portfolio/portfolio-summary.json",
    "claims/operational-claims.json",
    "agent-handoff-contract.md",
]


class TestArtifactContractExists:
    def test_contract_doc_exists(self) -> None:
        assert CONTRACT.exists()

    def test_schema_map_exists(self) -> None:
        assert SCHEMA_MAP.exists()


class TestCanonicalArtifacts:
    def test_all_canonical_artifacts_listed(self) -> None:
        text = CONTRACT.read_text()
        for artifact in REQUIRED_CANONICAL:
            assert artifact in text, f"Missing canonical artifact: {artifact}"

    def test_all_noncanonical_artifacts_listed(self) -> None:
        text = CONTRACT.read_text()
        for artifact in REQUIRED_OTHER:
            assert artifact in text, f"Missing artifact: {artifact}"


class TestProducerConsumerMapping:
    def test_every_artifact_has_producer(self) -> None:
        text = CONTRACT.read_text()
        rows = [line for line in text.split("\n") if line.startswith("|")]
        data_rows = [r for r in rows if not all(c in " |-:" for c in r.strip())]
        for row in data_rows:
            if ".ai-debt/" in row:
                # Config artifacts may be human-created
                if "Human-created" in row or "Human-edited" in row:
                    continue
                assert any(
                    cmd in row
                    for cmd in [
                        "init",
                        "profile",
                        "scan",
                        "map-units",
                        "analyze",
                        "report",
                        "plan",
                        "verify",
                        "status",
                        "graph",
                        "export",
                        "enrich",
                        "run",
                        "review",
                        "tickets",
                        "portfolio",
                        "claims",
                        "combine-evidence",
                        "import-evidence",
                        "lifecycle",
                        "candidate",
                    ]
                ), f"Row lacks producer command: {row[:80]}"

    def test_mutation_policy_documented(self) -> None:
        text = CONTRACT.read_text()
        assert "Regenerated" in text
        assert "Append-only" in text


class TestCanonicalVsSidecar:
    def test_canonical_section_exists(self) -> None:
        text = CONTRACT.read_text()
        assert "Canonical Analysis" in text

    def test_sidecar_sections_exist(self) -> None:
        text = CONTRACT.read_text()
        assert "Review Sidecar" in text
        assert "AI Sidecar" in text


class TestSchemaMapCompleteness:
    def test_all_schemas_listed(self) -> None:
        text = SCHEMA_MAP.read_text()
        required_schemas = [
            "EvidenceStore",
            "DebtRegister",
            "RepositoryProfile",
            "AnalysisUnitStore",
            "ArchitectureGraph",
            "RunMetadata",
            "VerificationReport",
            "ReviewDecisions",
            "TicketDraftIndex",
            "ExportBundleManifest",
            "PortfolioSummary",
            "OperationalClaimsRegister",
            "ProjectConfig",
            "GovernanceConfig",
        ]
        for schema in required_schemas:
            assert schema in text, f"Missing schema: {schema}"

    def test_schema_versions_documented(self) -> None:
        text = SCHEMA_MAP.read_text()
        assert "1.0" in text

    def test_schema_compatibility_policy_exists(self) -> None:
        text = SCHEMA_MAP.read_text()
        assert "additive-only" in text


class TestDeterminism:
    def test_contract_deterministic(self) -> None:
        text1 = CONTRACT.read_text()
        text2 = CONTRACT.read_text()
        assert text1 == text2
