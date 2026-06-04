"""Governance surface inventory — test-only, NOT a runtime registry.

Machine-checkable inventory of all 10 governed signal families,
their adapters, analyzer functions, dispositions, and categories.

This is used by the v3.21.0 governance audit tests to prove completeness
and consistency. It must not be imported by production code.
"""

from __future__ import annotations

from pharabius.core.signals.models import SignalDisposition, SignalFamily


# ═══════════════════════════════════════════════════════════════════════
# Family inventory
# ═══════════════════════════════════════════════════════════════════════

GOVERNED_FAMILY_INVENTORY: dict[str, dict] = {
    "runtime": {
        "family": SignalFamily.RUNTIME,
        "adapter_module": "pharabius.core.signals.adapters",
        "adapters": [
            "runtime_conflict_to_signal",
            "runtime_missing_pin_to_signal",
            "runtime_evidence_to_signal",
            "runtime_conflict_to_signal_from_evidence",
            "runtime_missing_pin_to_signal_from_evidence",
        ],
        "analyzer_functions": [
            "_analyze_runtime_conflicts",
            "_analyze_missing_pin",
            "_analyze_runtimes",
        ],
        "dispositions": {SignalDisposition.FINDING, SignalDisposition.ADVISORY, SignalDisposition.INFORMATIONAL},
        "categories": {"TD-DEP"},  # Runtime findings use TD-DEP category
        "evidence_caps": {},
    },
    "documentation": {
        "family": SignalFamily.DOCUMENTATION,
        "adapter_module": "pharabius.core.signals.adapters",
        "adapters": [
            "docs_missing_to_signal",
            "docs_evidence_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_missing_docs",
        ],
        "dispositions": {SignalDisposition.ADVISORY, SignalDisposition.INFORMATIONAL},
        "categories": {"TD-DOC"},
        "evidence_caps": {},
    },
    "build": {
        "family": SignalFamily.BUILD,
        "adapter_module": "pharabius.core.signals.adapters",
        "adapters": [
            "build_missing_ci_to_signal",
            "build_ci_evidence_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_missing_ci_cd",
        ],
        "dispositions": {SignalDisposition.ADVISORY, SignalDisposition.INFORMATIONAL},
        "categories": {"TD-BUILD"},
        "evidence_caps": {},
    },
    "process": {
        "family": SignalFamily.PROCESS,
        "adapter_module": "pharabius.core.signals.adapters",
        "adapters": [
            "process_missing_artifacts_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_missing_process_artifacts",
        ],
        "dispositions": {SignalDisposition.ADVISORY},
        "categories": {"TD-PROCESS"},
        "evidence_caps": {},
    },
    "test": {
        "family": SignalFamily.TEST,
        "adapter_module": "pharabius.core.signals.adapters",
        "adapters": [
            "scan_test_missing_to_signal",
            "scan_test_risk_sensitive_without_tests_to_signal",
            "scan_test_coverage_gap_to_signal",
            "scan_test_evidence_to_signal",
            "scan_test_coverage_evidence_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_missing_tests",
            "_analyze_risk_sensitive_without_tests",
            "_analyze_low_coverage",
        ],
        "dispositions": {SignalDisposition.FINDING, SignalDisposition.INFORMATIONAL},
        "categories": {"TD-SEC"},  # TD-SEC for risk-sensitive-without-tests — known exception
        "evidence_caps": {},
    },
    "dependency": {
        "family": SignalFamily.DEPENDENCY,
        "adapter_module": "pharabius.core.signals.dependency_adapters",
        "adapters": [
            "dependency_manifest_detected_to_signal",
            "dependency_missing_lockfile_to_signal",
            "dependency_manifest_without_lockfile_to_signal",
            "dependency_unpinned_to_signal",
            "dependency_lockfile_conflict_to_signal",
            "dependency_orphan_lockfile_to_signal",
            "dependency_parse_failure_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_dependency_signals",
            "_emit_lockfile_finding",
        ],
        "dispositions": {SignalDisposition.FINDING, SignalDisposition.ADVISORY, SignalDisposition.INFORMATIONAL},
        "categories": {"TD-DEP"},
        "evidence_caps": {},
    },
    "security": {
        "family": SignalFamily.SECURITY,
        "adapter_module": "pharabius.core.signals.security_adapters",
        "adapters": [
            "security_compliance_exposure_to_signal",
            "security_sensitive_path_to_signal",
            "security_sensitive_keyword_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_compliance_keywords",
        ],
        "dispositions": {SignalDisposition.FINDING, SignalDisposition.INFORMATIONAL},
        "categories": {"TD-COMP"},  # TD-COMP for compliance exposure — governed under SECURITY
        "evidence_caps": {},
    },
    "architecture": {
        "family": SignalFamily.ARCHITECTURE,
        "adapter_module": "pharabius.core.signals.architecture_adapters",
        "adapters": [
            "architecture_cycle_to_signal",
            "architecture_boundary_violation_to_signal",
        ],
        "analyzer_functions": [
            "_add_architecture_findings",
        ],
        "dispositions": {SignalDisposition.FINDING},
        "categories": {"TD-ARCH"},
        "evidence_caps": {"cycle": 20, "boundary_violation": 20},
    },
    "configuration": {
        "family": SignalFamily.CONFIGURATION,
        "adapter_module": "pharabius.core.signals.configuration_adapters",
        "adapters": [
            "configuration_env_without_example_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_env_without_example",
        ],
        "dispositions": {SignalDisposition.FINDING},
        "categories": {"TD-CONFIG"},
        "evidence_caps": {},
    },
    "observability": {
        "family": SignalFamily.OBSERVABILITY,
        "adapter_module": "pharabius.core.signals.observability_adapters",
        "adapters": [
            "observability_missing_to_signal",
        ],
        "analyzer_functions": [
            "_analyze_missing_observability",
        ],
        "dispositions": {SignalDisposition.FINDING},
        "categories": {"TD-OBS"},
        "evidence_caps": {"missing_observability": 5},
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Category-to-family mapping (including known exceptions)
# ═══════════════════════════════════════════════════════════════════════

CATEGORY_FAMILY_EXPECTATIONS: dict[str, tuple[SignalFamily, str]] = {
    # Direct mappings
    "TD-RUNTIME": (SignalFamily.RUNTIME, "runtime findings"),
    "TD-DOC": (SignalFamily.DOCUMENTATION, "documentation advisories"),
    "TD-BUILD": (SignalFamily.BUILD, "build advisories"),
    "TD-PROCESS": (SignalFamily.PROCESS, "process advisories"),
    "TD-DEP": (SignalFamily.DEPENDENCY, "dependency findings"),
    "TD-ARCH": (SignalFamily.ARCHITECTURE, "architecture findings"),
    "TD-CONFIG": (SignalFamily.CONFIGURATION, "configuration findings"),
    "TD-OBS": (SignalFamily.OBSERVABILITY, "observability findings"),
    # Known exceptions — category does not match family directly
    "TD-COMP": (SignalFamily.SECURITY, "compliance exposure governed under SECURITY family"),
    "TD-SEC": (SignalFamily.TEST, "risk-sensitive-without-tests governed under TEST family"),
}


# ═══════════════════════════════════════════════════════════════════════
# Metadata minimum contract
# ═══════════════════════════════════════════════════════════════════════

FAMILY_METADATA_REQUIRED_KEYS: dict[SignalFamily, set[str]] = {
    # Uniform families — adapters share a common metadata schema
    SignalFamily.ARCHITECTURE: {"spec_kind"},
    SignalFamily.CONFIGURATION: {"spec_kind"},
    SignalFamily.OBSERVABILITY: {"spec_kind"},
    # Diverse families — multiple adapter kinds with different schemas
    # No universal required keys for these families
    SignalFamily.RUNTIME: set(),
    SignalFamily.DEPENDENCY: set(),
    SignalFamily.SECURITY: set(),
    SignalFamily.TEST: set(),
    SignalFamily.DOCUMENTATION: set(),
    SignalFamily.BUILD: set(),
    SignalFamily.PROCESS: set(),
}
