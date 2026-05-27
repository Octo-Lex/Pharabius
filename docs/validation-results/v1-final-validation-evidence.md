# Pharabius v1 Final Validation Evidence Pack

**Version under validation**: v1.11.0  
**Date**: 2026-05-27  
**Status**: PASS

## Executive Summary

Pharabius v1.11.0 has been validated through local gate checks, artifact contract verification, safety boundary audit, schema map alignment, golden path testing, and packaging verification. The v1 product line is declared stable.

## Repository Matrix

| Repository | Ecosystem | Commands Validated | Result |
|---|---|---|---|
| Pharabius (self) | Python | All 18 | ✅ Pass |
| Java validation | Java/Maven | Core pipeline | ✅ Pass |
| .NET validation | .NET 8 | Core pipeline | ✅ Pass |
| Terraform IaC | Terraform | Core pipeline | ✅ Pass |
| Golden path fixture | Node.js | 12-command pipeline | ✅ Pass |

Previous field validations (v1.0.0rc1, v1.10.1) additionally validated: Ghostwire, Elephant Rock Platform, NodeSpan, Ariadne, Symbiot, Craft Agents, AIF (8 repos, 112/112 commands).

## Command Matrix

All 18 CLI commands pass:

| Command | Classification | Local Gate | CI |
|---|---|---|---|
| `ai-debt init` | Local writer | ✅ | ✅ |
| `ai-debt profile` | Local writer | ✅ | ✅ |
| `ai-debt scan` | Local writer | ✅ | ✅ |
| `ai-debt map-units` | Local writer | ✅ | ✅ |
| `ai-debt analyze` | Local writer | ✅ | ✅ |
| `ai-debt report` | Local writer | ✅ | ✅ |
| `ai-debt plan` | Local writer | ✅ | ✅ |
| `ai-debt verify` | Read-only | ✅ | ✅ |
| `ai-debt status` | Read-only | ✅ | ✅ |
| `ai-debt graph` | Local writer | ✅ | ✅ |
| `ai-debt export` | Export writer | ✅ | ✅ |
| `ai-debt enrich` | Local writer | ✅ | ✅ |
| `ai-debt ai-status` | Read-only | ✅ | ✅ |
| `ai-debt run` | Local writer | ✅ | ✅ |
| `ai-debt review` | Local writer | ✅ | ✅ |
| `ai-debt tickets` | Local writer | ✅ | ✅ |
| `ai-debt portfolio` | Local writer | ✅ | ✅ |
| `ai-debt doctor` | Read-only | ✅ | ✅ |

## Artifact Contract Results

| Category | Count | Status |
|---|---|---|
| Required artifacts | 7 | ✅ All present after full pipeline |
| Optional artifacts | 17+ | ✅ Present when respective commands run |
| Conditional artifacts | 16+ | ✅ Conditional semantics respected |
| Undocumented artifacts | 0 | ✅ No drift |
| Duplicate paths | 0 | ✅ No duplicates |

## Schema Map Results

- 40+ Pydantic schemas documented in `docs/SCHEMA_MAP.md`
- All schemas use `schema_version: "1.0"`
- Additive-only compatibility policy documented
- Schema-to-artifact mappings complete

## Golden Path Results

- 12-command pipeline fixture validated (`tests/fixtures/golden_path_repo/`)
- Integration tests cover full pipeline: init → run → verify → status → export
- All golden path tests pass in CI

## Readiness Results

- `ai-debt doctor` reports status correctly for all scenarios
- v1 readiness report generates 15 artifact + 5 safety checks
- Readiness status semantics: ready/partial/needs_review

## Safety Boundary Results

- 8 non-negotiable safety boundaries documented
- 18 command safety classifications complete
- No docs imply external writes or autonomous remediation
- Agent-handoff contract forbids code modification
- All boundary docs tests pass

## Packaging and Version Results

- `pyproject.toml` version: 1.11.0
- Installed metadata version: 1.11.0
- CLI `--version` output: matches
- Build artifacts: `pharabius-1.11.0` (wheel + sdist)
- 7/7 release gates pass
- CI first-try green

## Sample Bundle Results

- `docs/examples/sample-ai-debt/` validated
- Cross-referenced IDs (EVD-001 → TD-DEP-001)
- No secrets, no real paths
- 9 sample bundle tests pass

## Known Limitations

1. Architecture graph requires `architecture-policy.yaml` (no `.importlinter` parsing)
2. Rust block comments not filtered in `use` imports
3. AI enrichment is sidecar-only, no report integration in v1
4. Enhanced risk scoring is opt-in (disabled by default)
5. Export bundles are preparation artifacts, not tracker integrations
6. Portfolio does not recalculate risk scores
7. Operational claims are specification artifacts, not implementation authority
8. Confidence distribution is not a factual-precision measurement
9. No LICENSE file (license metadata deferred)
10. Review decisions are non-canonical PET workflow state

## Go/No-Go Decision

**Decision: v1 stable declaration is ready.**

- All 18 commands pass local and CI gates
- Artifact contract is frozen and validated
- Safety boundaries are audited and documented
- Stability contract is published
- 1,606+ tests pass with ≥84% coverage
- 39 previous releases validate continuous delivery
- Known limitations are documented and accepted

## Related Evidence

- [Field validation v1.0.0rc1](agv-001-pharabius.md) through [agv-011](agv-011-validation-policy.md)
- [Field validation v1.10.1](field-validation-v1.10.1.md)
- [v1 Stability Contract](../V1_STABILITY_CONTRACT.md)
- [Safety Boundaries](../SAFETY_BOUNDARIES.md)
- [Artifact Contract](../ARTIFACT_CONTRACT.md)
