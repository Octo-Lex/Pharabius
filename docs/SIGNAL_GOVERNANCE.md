# Signal Governance

## Signal lifecycle

```text
Evidence → Domain signal → Governed signal → Disposition → Output behavior
```

Every piece of evidence Pharabius collects flows through a domain-specific layer
(runtime, dependency, test, etc.) into a governed signal with a deterministic
disposition. The disposition controls what the platform does with the signal.

## Dispositions

| Disposition     | Debt register? | Work package? | Reportable? | Run-history count? |
|-----------------|:-:|:-:|:-:|:-:|
| `FINDING`       | Yes | Yes | Yes | Yes |
| `ADVISORY`      | No | No | Yes | Yes |
| `INFORMATIONAL` | No | No | Optional/summary | Yes |
| `SUPPRESSED`    | No | No | Usually no | Yes (diagnostics) |

## Promotion rules

- `should_create_finding(signal)` → True only for `FINDING` disposition
- `should_create_advisory(signal)` → True only for `ADVISORY` disposition
- `should_create_work_package(signal)` → True only for `FINDING` disposition
- `is_reportable(signal)` → True for `FINDING` and `ADVISORY` (actionable/advisory reportability, not summary visibility)
- `is_informational(signal)` → True only for `INFORMATIONAL`

**Explicit disposition branching only.** No catch-all fallback. The analyzer
uses:

```python
if should_create_finding(signal):
    create_technical_debt_finding(signal)
elif should_create_advisory(signal):
    create_advisory(signal)
elif is_informational(signal):
    record_signal_only(signal)
elif signal.disposition == SignalDisposition.SUPPRESSED:
    record_diagnostic_only(signal)
```

## Work-package rules

Only `FINDING` disposition creates work packages. Advisories, informational
signals, and suppressed signals never generate work packages. This protects
the advisory/finding boundary established in v3.7.0 and hardened in v3.12.0.

## Category vs. Family

Category describes the finding taxonomy (e.g., `TD-ARCH`, `TD-DEP`).
Family describes the governance owner (e.g., Architecture, Dependency).
They are usually aligned, but not always identical.

### Family boundary reference

| Case | Governed family | Category | Why |
|---|---|---|---|
| Runtime version conflict | Runtime | TD-DEP | Runtime/toolchain reproducibility |
| Missing pin / unpinned runtime | Runtime | TD-DEP | Toolchain pinning hygiene |
| Runtime evidence detected | Runtime | TD-DEP | Evidence visibility (INFORMATIONAL) |
| Missing docs | Documentation | TD-DOC | Documentation coverage |
| Missing CI | Build | TD-BUILD | CI/CD quality |
| CODEOWNERS / CONTRIBUTING | Process | TD-PROCESS | Engineering process artifacts |
| Missing tests | Test | TD-TEST | Test-health debt |
| Risk-sensitive code without tests | Test | TD-SEC | Security-sensitive area lacking tests, governed as test health |
| Compliance keywords | Security | TD-COMP | Security/compliance exposure indicator |
| Sensitive path detected | Security | risk_signal | Path-based risk context (INFORMATIONAL) |
| Dependency unpinned / lockfile conflict | Dependency | TD-DEP | Dependency-management condition |
| Architecture cycle / boundary violation | Architecture | TD-ARCH | Graph-derived architecture risk |
| `.env` without `.env.example` | Configuration | TD-CONFIG | Configuration hygiene |
| Deployment without observability evidence | Observability | TD-OBS | Repository-local operational visibility gap |

### Known category/family exceptions

| Category | Family | Rationale |
|---|---|---|
| TD-COMP | SECURITY | Compliance exposure governed under Security family |
| TD-SEC | TEST | Risk-sensitive-without-tests governed under Test family |

All other categories map directly to their family.

## Signal examples

| Disposition | Example | Reviewer interpretation |
|---|---|---|
| FINDING | Architecture cycle | Actionable technical debt; work-package eligible |
| FINDING | Missing tests | Work-package eligible |
| FINDING | `.env` without `.env.example` | Configuration hygiene finding |
| ADVISORY | Missing documentation | Reportable caution; not a work package |
| ADVISORY | Missing lockfile | Reproducibility caution |
| INFORMATIONAL | Test file detected | Coverage/context signal; not remediation |
| INFORMATIONAL | Runtime evidence detected | Evidence visibility |
| SUPPRESSED | Diagnostic-only skipped signal | Hidden unless diagnostics enabled |

## Runtime as reference implementation

Runtime is the first signal family to use governed signals. The adapter layer
in `src/pharabius/core/signals/adapters.py` converts:

- `RuntimeConflictGroup` → `GovernedSignal(disposition=FINDING)`
- Missing pin evidence → `GovernedSignal(disposition=ADVISORY)`
- `RuntimeEvidence` → `GovernedSignal(disposition=INFORMATIONAL)`

Runtime keeps its internal IR (`RuntimeEvidence`, `RuntimeConflictGroup`,
`RuntimeSourceGrade`). The adapter is a thin translation layer.

## GovernedSignal model

```python
@dataclass(frozen=True)
class GovernedSignal:
    signal_id: str          # Deterministic: SIG-{FAMILY}-{hash}
    family: SignalFamily    # runtime, dependency, test, security, etc.
    kind: str               # Conflict kind, evidence kind, etc.
    disposition: SignalDisposition
    category: str           # TD-DEP, TD-ARCH, etc.
    severity: str
    confidence: str
    evidence_ids: list[str]
    source_signal_ids: list[str]
    title: str
    summary: str
    explanation: str
    metadata: dict[str, Any]  # Family-specific data preserved
```

## Non-goals (v3.12.0)

- No configurable governance policy engine
- No migration of all analyzer families (only runtime)
- No persistent SignalStore (signals reconstructed from existing evidence)
- No security/dependency/architecture policy rewrite
- No risk-score redesign

## v3.13.0 — Additional reference families

Documentation and build/CI signals adopted as governed signal families:
- `docs_missing_to_signal()` → `DOCUMENTATION` / `ADVISORY`
- `docs_evidence_to_signal()` → `DOCUMENTATION` / `INFORMATIONAL`
- `build_missing_ci_to_signal()` → `BUILD` / `ADVISORY`
- `build_ci_evidence_to_signal()` → `BUILD` / `INFORMATIONAL`
- `process_missing_artifacts_to_signal()` → `PROCESS` / `ADVISORY`

The `PROCESS` family covers CODEOWNERS, CONTRIBUTING, and PR template
observations. It is distinct from `BUILD` — process artifacts are governance,
not CI/CD quality.

## v3.14.0 — Test health signals

Test health signals adopted as governed signal family:
- `scan_test_missing_to_signal()` → `TEST` / `FINDING` (no tests = actionable debt)
- `scan_test_risk_sensitive_without_tests_to_signal()` → `TEST` / `FINDING` (security/compliance risk)
- `scan_test_coverage_gap_to_signal()` → `TEST` / `FINDING` (low coverage = actionable debt)
- `scan_test_evidence_to_signal()` → `TEST` / `INFORMATIONAL` (test file detected)
- `scan_test_coverage_evidence_to_signal()` → `TEST` / `INFORMATIONAL` (coverage report detected)

Test findings are distinct from documentation/build/process advisories.
Missing tests, risk-sensitive areas without tests, and low coverage are all
actionable technical debt — they create work packages and register in the
tech debt summary. Test file and coverage report evidence are informational.

Signal summary is now signal-driven: built from `GovernedSignal` instances
via `build_signal_summary()`, not from raw evidence type heuristics.

Runtime, documentation, build, and process families all appear in the
signal governance report section.

## v3.15.0 — Governance Hardening

Enforcement layer for all migrated families:

- **Invariant registry** (`invariants.py`): 8 named platform rules (INV_001–INV_008)
- **Signal validation** (`validation.py`): `validate_governed_signal()` checks completeness, traceability, and invariant compliance
- **Signal diagnostics** (`validation.py`): `diagnose_signal()` returns structured `SignalDiagnostic` instances
- **Output behavior** (`policy.py`): `output_behavior()` maps dispositions to complete behavior profiles
- **SUPPRESSED summary handling**: Excluded from normal summaries; included only with `include_diagnostics=True`

### Invariant reference

| Code | Rule | Severity |
|------|------|----------|
| INV_001 | FINDING is the only source of technical debt findings | critical |
| INV_002 | ADVISORY never creates work packages | critical |
| INV_003 | INFORMATIONAL signals are non-actionable | critical |
| INV_004 | SUPPRESSED signals are diagnostics-only | critical |
| INV_005 | Signal IDs are deterministic (SIG-{FAMILY}-{hex12}) | warning |
| INV_006 | FINDING signals must include evidence_ids | critical |
| INV_007 | Migrated analyzers use signal policy helpers | critical |
| INV_008 | Signal summaries count governed signal instances | warning |

### Signal family migration checklist

- [ ] Adapter returns `GovernedSignal`
- [ ] Signal IDs are deterministic
- [ ] Disposition is explicit
- [ ] Analyzer uses signal policy helpers
- [ ] Findings only from `FINDING`
- [ ] Advisories only from `ADVISORY`
- [ ] Work packages only from `FINDING`
- [ ] Informational signals are summary-only
- [ ] Summary is built from `GovernedSignal`
- [ ] Contract tests cover the migrated family
- [ ] `validate_governed_signal()` passes for all adapter outputs

## Non-goals (v3.13.0)

- No security signal migration
- No architecture signal migration
- No dependency vulnerability migration
- No configurable policy engine
- No persistent SignalStore
- No frontend governance dashboard
- No risk-score rewrite
- No remediation automation

## v3.16.0 — Dependency health signals

Dependency health signals adopted as governed signal family:
- `dependency_unpinned_to_signal()` → `DEPENDENCY` / `FINDING` (unpinned deps = actionable debt)
- `dependency_lockfile_conflict_to_signal()` → `DEPENDENCY` / `FINDING` (conflicting lockfiles)
- `dependency_missing_lockfile_to_signal()` → `DEPENDENCY` / `ADVISORY` (missing lockfile)
- `dependency_manifest_without_lockfile_to_signal()` → `DEPENDENCY` / `ADVISORY` (Poetry/Pipfile without lockfile)
- `dependency_orphan_lockfile_to_signal()` → `DEPENDENCY` / `ADVISORY` (lockfile without manifest)
- `dependency_parse_failure_to_signal()` → `DEPENDENCY` / `ADVISORY` (parse error limits coverage)
- `dependency_manifest_detected_to_signal()` → `DEPENDENCY` / `INFORMATIONAL` (manifest detected)

This is an **adoption release**, not a dependency-feature release. Existing dependency
findings, advisories, and observations produce identical output. No new vulnerability
scanning, SBOM, license, freshness, or remediation capabilities.

### Family boundary

Runtime and dependency signals both touch manifests and lockfiles but answer
different questions:
- Runtime signals: *what runtime/toolchain is selected?* (e.g., `package.json engines.node`)
- Dependency signals: *what dependency-management condition exists?* (e.g., `package.json dependencies`)

These are counted separately in signal summaries. No double-counting.

### Migrated families after v3.16.0

| Family | Findings | Advisories | Informational |
|--------|:--------:|:----------:|:-------------:|
| Runtime | ✅ | ✅ | ✅ |
| Documentation | — | ✅ | ✅ |
| Build | — | ✅ | ✅ |
| Process | — | ✅ | — |
| Test | ✅ | — | ✅ |
| Dependency | ✅ | ✅ | ✅ |

### Non-goals (v3.16.0)

- No vulnerability scanning
- No SBOM generation
- No package-version freshness lookup
- No license compliance analysis
- No dependency graph centrality scoring
- No dependency remediation planning changes

## v3.17.0 — Security exposure signals

Security exposure signals adopted as governed signal family:
- `security_compliance_exposure_to_signal()` → `SECURITY` / `FINDING` (compliance keyword exposure)
- `security_sensitive_path_to_signal()` → `SECURITY` / `INFORMATIONAL` (risk-sensitive path, summary-only)
- `security_sensitive_keyword_to_signal()` → `SECURITY` / `INFORMATIONAL` (risk-sensitive keyword, summary-only)

This is an **adoption release**, not a security-feature release. Existing compliance
findings produce identical output. No vulnerability, CVE, exploitability, SAST, DAST,
taint analysis, or secret validation capabilities are added.

Compliance exposure findings are governed under `SignalFamily.SECURITY` in v3.17.0
because the migrated analyzer represents security/compliance exposure indicators,
while preserving `category="TD-COMP"`.

### Family boundary

Security exposure and test-health signals both touch risk-sensitive evidence
but answer different questions:
- Security signals: *what security/compliance exposure indicators exist?* (e.g., PII/GDPR/HIPAA keywords)
- Test signals: *are risk-sensitive areas tested?* (e.g., risk-sensitive paths without test evidence)

`_analyze_risk_sensitive_without_tests` stays under `SignalFamily.TEST` (governed since v3.14.0).
Informational security path/keyword signals are summary-only and non-actionable.

### Migrated families after v3.17.0

| Family | Findings | Advisories | Informational |
|--------|:--------:|:----------:|:-------------:|
| Runtime | ✅ | ✅ | ✅ |
| Documentation | — | ✅ | ✅ |
| Build | — | ✅ | ✅ |
| Process | — | ✅ | — |
| Test | ✅ | — | ✅ |
| Dependency | ✅ | ✅ | ✅ |
| Security | ✅ | — | ✅ |

### Non-goals (v3.17.0)

- No vulnerability scanning
- No CVE lookup
- No exploitability claims
- No SAST/DAST/taint analysis
- No secret validation against external services
- No credential verification
- No compliance certification claims
- No new detection logic

## v3.18.0 — Architecture risk signals

Architecture risk signals adopted as governed signal family:
- `architecture_cycle_to_signal()` → `ARCHITECTURE` / `FINDING` (circular dependencies)
- `architecture_boundary_violation_to_signal()` → `ARCHITECTURE` / `FINDING` (layer violations)

This is an **adoption release**, not an architecture-feature release. All cycle and
boundary-violation findings produce identical output. No new high-coupling,
unresolved-import, external-import, graph analysis, or policy expansion.

Architecture signals are graph-derived repository-local indicators. They do not
introduce new architecture scoring, coupling findings, or graph schema changes.

### Family boundary

`architecture_analyzer.py` produces `ArchFindingSpec` with a `kind` field
(`"cycle"` or `"boundary_violation"`). Governance routing uses `spec.kind`,
not title text. Unknown spec kinds fall back to direct builder path.

v3.18.0 emits FINDING only for architecture — no informational architecture signals.

### Migrated families after v3.18.0

| Family | Findings | Advisories | Informational |
|--------|:--------:|:----------:|:-------------:|
| Runtime | ✅ | ✅ | ✅ |
| Documentation | — | ✅ | ✅ |
| Build | — | ✅ | ✅ |
| Process | — | ✅ | — |
| Test | ✅ | — | ✅ |
| Dependency | ✅ | ✅ | ✅ |
| Security | ✅ | — | ✅ |
| Architecture | ✅ | — | — |

### Non-goals (v3.18.0)

- No new architecture graph analysis
- No high-coupling findings
- No unresolved-import findings
- No external-import findings
- No architecture policy expansion
- No graph schema redesign
- No frontend graph UI

## v3.19.0 — Configuration & environment signals

Configuration/environment signals adopted as governed signal family:
- `configuration_env_without_example_to_signal()` → `CONFIGURATION` / `FINDING` (missing env example)

This is an **adoption release**, not a configuration-feature release. All TD-CONFIG
findings produce identical output. No new secret scanning, credential validation,
config hardening, or policy-as-code behavior.

Configuration signals are environment/configuration hygiene indicators. They are
NOT security signals. They do not perform secret validation, credential verification,
or security claims.

### Family boundary

`_analyze_env_without_example()` is the only TD-CONFIG producer. It triggers when
`.env` or `.env.local` is present but `.env.example` is absent.

v3.19.0 emits FINDING only for configuration — no advisory or informational
configuration signals.

`.env.example` alone is a skip/no-signal condition.

### Migrated families after v3.19.0

| Family | Findings | Advisories | Informational |
|--------|:--------:|:----------:|:-------------:|
| Runtime | ✅ | ✅ | ✅ |
| Documentation | — | ✅ | ✅ |
| Build | — | ✅ | ✅ |
| Process | — | ✅ | — |
| Test | ✅ | — | ✅ |
| Dependency | ✅ | ✅ | ✅ |
| Security | ✅ | — | ✅ |
| Architecture | ✅ | — | — |
| Configuration | ✅ | — | — |

### Non-goals (v3.19.0)

- No new secret scanning
- No credential validation
- No config hardening engine
- No policy-as-code engine
- No environment-variable risk scoring
- No new security finding
- No security reclassification
- No build/deployment reclassification
- No reporter section regrouping

## v3.20.0 — Observability signals

Observability signals adopted as governed signal family:
- `observability_missing_to_signal()` → `OBSERVABILITY` / `FINDING` (missing deployment observability)

This is an **adoption release**, not an observability-feature release. All TD-OBS
findings produce identical output. No new telemetry, monitoring, health-check,
SLO/SLA, maturity, or production-readiness capabilities.

**v3.20.0 completes first-pass signal governance adoption across all 10 families.**

### Family boundary

`_analyze_missing_observability()` fires when deployment/infrastructure evidence
exists and no `risk_sensitive_keyword_detected` items match the observability keyword
set (`logging`, `monitoring`, `tracing`, `alert`, `metrics`).

v3.20.0 does NOT add new keyword scanning or reinterpret keyword evidence.

CI-only deployment evidence (`.github/workflows/`, `.gitlab-ci`) is excluded.

v3.20.0 emits FINDING only for observability — no advisory or informational
observability signals.

### Migrated families after v3.20.0 (COMPLETE)

| Family | Findings | Advisories | Informational |
|--------|:--------:|:----------:|:-------------:|
| Runtime | ✅ | ✅ | ✅ |
| Documentation | — | ✅ | ✅ |
| Build | — | ✅ | ✅ |
| Process | — | ✅ | — |
| Test | ✅ | — | ✅ |
| Dependency | ✅ | ✅ | ✅ |
| Security | ✅ | — | ✅ |
| Architecture | ✅ | — | — |
| Configuration | ✅ | — | — |
| Observability | ✅ | — | — |

### Non-goals (v3.20.0)

- No new observability scanner
- No runtime telemetry collection
- No external monitoring integrations
- No OpenTelemetry expansion
- No SLO/SLA analysis
- No operational maturity scoring
- No production-readiness certification
- No build/config/security reclassification

## v3.21.0 — Governance completion audit

Cross-family consistency audit across all 10 governed families:
- Disposition behavior verified uniform across all families
- Evidence traceability verified for all FINDING-emitting families
- Summary/report consistency verified
- Family boundary regression matrix covers 10 known overlap cases
- Metadata minimum contract for uniform families
- Static analyzer audit: no unlisted direct-promotion paths

See `docs/SIGNAL_GOVERNANCE_AUDIT.md` for the complete audit results.

## Governance quality metrics (v3.23.0)

Governance quality metrics are **read-only descriptive analytics**. They measure
signal coverage, disposition mix, confidence distribution, and evidence
traceability.

They do **not**:
- create findings
- create advisories
- create work packages
- promote or demote signals
- enforce quality gates
- change `output_behavior()`
- fail a run

Coverage ratios use 1.0 when no signals of that disposition exist, meaning
"no uncovered signals observed," not "coverage proven."

Diagnostic codes:

| Code | Meaning | Severity |
|---|---|---|
| GQM-001 | Finding signal lacks evidence IDs | warning |
| GQM-002 | Advisory signal lacks evidence IDs or metadata basis | info |
| GQM-003 | Informational signal lacks evidence IDs | info |
| GQM-004 | Signal metadata empty | info |
| GQM-005 | Unexpected severity/confidence label | warning |

## Governance quality trends (v3.24.0)

Governance quality trends compare read-only governance metrics across runs.
They describe changes in signal mix, confidence, evidence coverage, and
diagnostics recurrence.

They do **not**:
- create findings
- create advisories
- create work packages
- apply gates or thresholds
- promote or demote signals
- score governance health
- characterize trends as healthy/unhealthy, compliant/noncompliant, passing/failing

Trend selection uses the latest two snapshots containing `governance_quality`,
not merely the latest two runs. Older snapshots without `governance_quality`
are skipped, not backfilled.

Coverage deltas render as percentage points (pp), not raw decimals.

## Governance analytics export (v3.25.0)

Governance analytics are exportable in stable machine-readable formats:

- `.ai-debt/exports/governance-summary.json` — full export with schema versioning
- `.ai-debt/exports/governance-summary.jsonl` — single-line JSON for streaming consumers

Export fields:

| Field | Description |
|---|---|
| `schema_version` | Export schema version (currently "1.0") |
| `export_type` | Always "governance_analytics" |
| `run_id` | Run identifier |
| `generated_at` | ISO 8601 timestamp |
| `signal_summary` | Signal counts by family/disposition |
| `governance_quality` | Coverage metrics and GQM diagnostics |
| `governance_trends` | Historical deltas and recurring diagnostics |
| `diagnostics` | Current GQM diagnostics |
| `recurring_diagnostics` | Diagnostics appearing in ≥ 2 comparable runs |
| `metadata` | Export metadata (families_governed, source) |

The export is descriptive only. It does not apply quality gates, change findings,
create work packages, or enforce policy.

Forbidden field names: pass, fail, score, grade, compliant, noncompliant, healthy, unhealthy.

## Governance contract

The complete v3 governance contract is documented in [GOVERNANCE_CONTRACT.md](GOVERNANCE_CONTRACT.md).

- `schema_version` remains `"1.0"` for additive changes.
- Breaking changes (field removal or rename) require a schema version increment and CHANGELOG migration note.
- v3.26.0 freezes the current v3 governance surface at 10 families and 29 adapters.
- Future major versions may add families/adapters with explicit contract migration notes.
