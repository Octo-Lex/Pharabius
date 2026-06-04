# Signal Governance Completion Audit

## Scope

This document records the v3.21.0 governance completion audit across all 10 governed signal families. The audit verifies disposition behavior, evidence traceability, summary/report consistency, family boundaries, and metadata preservation.

## Governed families

All 10 `SignalFamily` enum values are governed:

| Family | Since | Adapters | Dispositions | Categories |
|---|---|:---:|---|---|
| Runtime | v3.14.0 | 5 | FINDING, ADVISORY, INFORMATIONAL | TD-RUNTIME |
| Documentation | v3.14.0 | 2 | ADVISORY, INFORMATIONAL | TD-DOC |
| Build | v3.14.0 | 2 | ADVISORY, INFORMATIONAL | TD-BUILD |
| Process | v3.14.0 | 1 | ADVISORY | TD-PROCESS |
| Test | v3.14.0 | 5 | FINDING, INFORMATIONAL | TD-SEC |
| Dependency | v3.16.0 | 7 | FINDING, ADVISORY, INFORMATIONAL | TD-DEP |
| Security | v3.17.0 | 3 | FINDING, INFORMATIONAL | TD-COMP |
| Architecture | v3.18.0 | 2 | FINDING | TD-ARCH |
| Configuration | v3.19.0 | 1 | FINDING | TD-CONFIG |
| Observability | v3.20.0 | 1 | FINDING | TD-OBS |

**Total: 29 adapters across 10 families.**

## Disposition behavior

Uniform across all families via `output_behavior()`:

| Disposition | Finding | Advisory | Work Package | Report Detail | Summary | Diagnostics |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| FINDING | ✅ | — | ✅ | ✅ | ✅ | — |
| ADVISORY | — | ✅ | — | ✅ | ✅ | — |
| INFORMATIONAL | — | — | — | — | ✅ | — |
| SUPPRESSED | — | — | — | — | — | ✅ |

Cross-family consistency verified: Runtime FINDING ≡ Test FINDING ≡ Dependency FINDING ≡ Security FINDING ≡ Architecture FINDING ≡ Configuration FINDING ≡ Observability FINDING.

## Evidence traceability

Every FINDING signal carries evidence_ids. Verified for all 7 FINDING-emitting families.

Family-specific evidence behavior:
- Architecture: cycle and boundary-violation findings capped at 20 per type
- Observability: deployment/infra evidence capped at 5
- Dependency: manifest/lockfile context preserved in metadata

## Category-to-family mapping

Known exceptions where category does not directly match family name:

| Category | Family | Rationale |
|---|---|---|
| TD-COMP | SECURITY | Compliance exposure governed under Security family |
| TD-SEC | TEST | Risk-sensitive-without-tests governed under Test family |

All other categories map directly to their family.

## Summary/report consistency

Signal summaries count governed signal instances via `build_signal_summary()`, not raw evidence heuristics. This is the INV_008 invariant.

Verified:
- Summary total = sum of family counts
- Summary by_family matches actual signal instances
- SUPPRESSED excluded from normal summary
- SUPPRESSED included only when diagnostics enabled

## Family boundary matrix

| Overlap | Boundary | Verified |
|---|---|---|
| `package.json` engines.node | Runtime, not Dependency | ✅ |
| `.env` with token-like keys | Configuration, not new Security | ✅ |
| CI workflow with monitoring step | Build, not Observability | ✅ |
| Deployment without observability | Observability, not Build | ✅ |
| Risk-sensitive code without tests | Test, not Security | ✅ |
| Compliance keywords | Security (TD-COMP) | ✅ |
| Architecture graph cycles | Architecture only | ✅ |
| Dockerfile runtime tags | Runtime, not Build | ✅ |
| Lockfile conflict | Dependency, not Runtime | ✅ |
| CODEOWNERS / CONTRIBUTING | Process, not Documentation | ✅ |

## Metadata expectations

Per-family required metadata keys (only for uniform adapter schemas):

| Family | Required Keys |
|---|---|
| Architecture | `spec_kind` |
| Configuration | `spec_kind` |
| Observability | `spec_kind` |

Diverse families (runtime, dependency, test, security, documentation, build, process) have multiple adapter kinds with different schemas — no universal required keys.

## Named invariants

8 platform invariants enforced:

| Code | Title |
|---|---|
| INV_001 | FINDING disposition is the only source of technical debt findings |
| INV_002 | ADVISORY disposition never creates work packages |
| INV_003 | INFORMATIONAL signals are non-actionable |
| INV_004 | SUPPRESSED signals are diagnostics-only |
| INV_005 | Signal IDs are deterministic |
| INV_006 | FINDING signals must include evidence IDs |
| INV_007 | Migrated analyzers use signal policy helpers |
| INV_008 | Signal summaries count governed signal instances |

## Non-goals

- No new signal family
- No new analyzer migration
- No new detection logic
- No configurable policy engine
- No persistent SignalStore
- No governance dashboard
- No analytics layer

## Future work

- Cross-family invariants (e.g., no signal in two families, evidence deduplication)
- Governance analytics layer
- v4.0 configurable policy engine
- Dashboard for governance surface visibility
