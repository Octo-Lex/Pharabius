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
