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
