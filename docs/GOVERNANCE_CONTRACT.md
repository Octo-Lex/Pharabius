# Governance Contract (v3)

> **Stability:** This document describes the v3 governance contract as of v3.26.0.
> Future major versions may add families, adapters, or surfaces with explicit contract migration notes.

## Purpose

The governance contract defines the stable surfaces of Pharabius signal governance.
It is documentation and test reference only — not a runtime registry or policy engine.

## Stable Surfaces

### GovernedSignal

The core signal model. Frozen dataclass.

| Field | Type | Description |
|---|---|---|
| `signal_id` | `str` | Deterministic signal identifier |
| `family` | `SignalFamily` | Governance owner domain |
| `kind` | `str` | Signal kind within family (stable routing key) |
| `disposition` | `SignalDisposition` | Output classification |
| `category` | `str` | Finding taxonomy (e.g., TD-DEP, TD-SEC) |
| `severity` | `str` | Severity level (Critical, High, Medium, Low) |
| `confidence` | `str` | Confidence level |
| `evidence_ids` | `list[str]` | Linked evidence identifiers |
| `source_signal_ids` | `list[str]` | Upstream signal identifiers |
| `title` | `str` | Human-readable title |
| `summary` | `str` | Signal summary |
| `explanation` | `str` | Signal explanation |
| `metadata` | `dict` | Additional structured data |

### SignalDisposition

Four disposition values with explicit semantics:

| Disposition | Semantics |
|---|---|
| `FINDING` | Promoted into the technical debt register; may create work packages |
| `ADVISORY` | Reportable but does not create work packages |
| `INFORMATIONAL` | Provides context and coverage visibility; non-actionable |
| `SUPPRESSED` | Diagnostics-only; omitted from normal reports |

### SignalFamily

v3.26.0 freezes the current v3 governance surface at **10 families**.

| Family | Value | Description |
|---|---|---|
| RUNTIME | `runtime` | Runtime version signals |
| DEPENDENCY | `dependency` | Dependency health signals |
| TEST | `test` | Test gap and coverage signals |
| SECURITY | `security` | Security exposure signals |
| ARCHITECTURE | `architecture` | Architecture risk signals |
| DOCUMENTATION | `documentation` | Documentation debt signals |
| BUILD | `build` | Build/CI gap signals |
| OBSERVABILITY | `observability` | Observability gap signals |
| CONFIGURATION | `configuration` | Configuration hygiene signals |
| PROCESS | `process` | Process artifact signals |

Future major versions may add families with explicit contract migration notes.

### Family/Category Exceptions

Category and family are not always identical:

| Category | Family | Reason |
|---|---|---|
| TD-COMP | SECURITY | Compliance exposure governed under Security family |
| TD-SEC | TEST | Risk-sensitive-without-tests governed under Test family |

### Adapters

v3.26.0 freezes the current v3 governance surface at **29 adapters** across 10 families.

| Module | Count | Families |
|---|---|---|
| `adapters.py` | 15 | runtime (5), documentation (2), build (2), process (1), test (5) |
| `dependency_adapters.py` | 7 | dependency |
| `security_adapters.py` | 3 | security |
| `architecture_adapters.py` | 2 | architecture |
| `configuration_adapters.py` | 1 | configuration |
| `observability_adapters.py` | 1 | observability |

### Invariants

Eight named invariants (INV_001–INV_008):

| Code | Invariant |
|---|---|
| INV_001 | FINDING disposition only creates findings |
| INV_002 | ADVISORY never creates work packages |
| INV_003 | INFORMATIONAL is non-actionable |
| INV_004 | SUPPRESSED is diagnostics-only |
| INV_005 | Signal IDs are deterministic |
| INV_006 | Promoted findings have evidence |
| INV_007 | Migrated analyzers use policy helpers |
| INV_008 | Summary counts governed signal instances |

### SignalSummary

Shape produced by `build_signal_summary()`:

| Field | Type |
|---|---|
| `total` | `int` |
| `by_family` | `dict[str, int]` |
| `by_disposition` | `dict[str, int]` |

### GovernanceQualityMetrics

Shape produced by `build_governance_quality_metrics()`:

| Field | Type |
|---|---|
| `total_signals` | `int` |
| `by_family` | `dict[str, int]` |
| `by_disposition` | `dict[str, int]` |
| `by_severity` | `dict[str, int]` |
| `by_confidence` | `dict[str, int]` |
| `finding_evidence_coverage` | `float` (1.0 when denominator is 0) |
| `finding_metadata_coverage` | `float` (1.0 when denominator is 0) |
| `advisory_evidence_coverage` | `float` (1.0 when denominator is 0) |
| `informational_evidence_coverage` | `float` (1.0 when denominator is 0) |
| `diagnostics` | `list[GovernanceQualityDiagnostic]` |

#### GQM Diagnostic Codes

| Code | Description | Severity |
|---|---|---|
| GQM-001 | Finding without evidence | warning |
| GQM-002 | Advisory without evidence or metadata basis | info |
| GQM-003 | Informational without evidence | info |
| GQM-004 | Finding with empty metadata | info |
| GQM-005 | Unexpected severity/confidence label | warning |

Diagnostics are NOT findings, NOT advisories, NOT work packages.
They do not change signal dispositions or output behavior.

### GovernanceTrendSummary

Shape produced by `build_governance_trend_summary()`:

| Field | Type |
|---|---|
| `runs_compared` | `int` |
| `current_run_id` | `str \| None` |
| `previous_run_id` | `str \| None` |
| `signal_count_delta` | `GovernanceMetricDelta` |
| `finding_evidence_coverage_delta` | `GovernanceMetricDelta` |
| `advisory_evidence_coverage_delta` | `GovernanceMetricDelta` |
| `informational_evidence_coverage_delta` | `GovernanceMetricDelta` |
| `by_disposition_delta` | `dict[str, GovernanceMetricDelta]` |
| `by_family_delta` | `dict[str, GovernanceMetricDelta]` |
| `by_confidence_delta` | `dict[str, GovernanceMetricDelta]` |
| `recurring_diagnostics` | `list[GovernanceDiagnosticTrend]` |
| `unavailable_reason` | `str \| None` |

Trend selection uses the latest two snapshots containing `governance_quality`,
not merely the latest two runs. Coverage deltas render as percentage points.

### Governance Export Schema v1.0

Produced by `build_governance_export()`:

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Currently `"1.0"` |
| `export_type` | `str` | Always `"governance_analytics"` |
| `tool_version` | `str` | Pharabius package version |
| `run_id` | `str \| None` | Run identifier |
| `generated_at` | `str` | ISO 8601 timestamp |
| `signal_summary` | `dict \| null` | Signal counts |
| `governance_quality` | `dict \| null` | Quality metrics and diagnostics |
| `governance_trends` | `dict \| null` | Trend deltas and recurrence |
| `diagnostics` | `list` | Current GQM diagnostics |
| `recurring_diagnostics` | `list` | Diagnostics in ≥ 2 comparable runs |
| `metadata` | `dict` | Export metadata |

#### Schema Version Escalation Rule

- `schema_version` remains `"1.0"` for additive changes (new fields added).
- Breaking changes (field removal or rename) require a schema version increment
  and a CHANGELOG migration note.

#### Forbidden Export Field Names

These field names are forbidden in generated export payloads:

`pass`, `fail`, `score`, `grade`, `compliant`, `noncompliant`, `healthy`, `unhealthy`

## Compatibility Rules

1. **Existing fields are not removed.**
2. **Existing fields are not renamed.**
3. **New fields are additive only.**
4. **Schema version changes require a changelog note.**
5. **No policy/gate fields are introduced.**

## Non-Policy Boundaries

The v3 governance contract is explicitly non-enforcing:

- No quality gates
- No pass/fail thresholds
- No health scores
- No policy decisions
- No signal promotion or demotion based on metrics
- No risk-score changes from governance
- No work-package changes from governance
- No analyzer changes from governance
- No new signal detection from governance
- No dashboard behavior
- No runtime telemetry collection

Governance analytics describe; they do not prescribe.

## Non-Goals Until v4

- Configurable policy engine
- Governance dashboard
- Quality gate enforcement
- CI failure behavior
- External integrations
- Persistent SignalStore
- Remediation automation
- Signal promotion/demotion logic
