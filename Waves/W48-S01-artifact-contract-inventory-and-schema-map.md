# Wave 48 — v1.10.0 v1 Contract Consolidation & Release Candidate

Goal: Consolidate the v1 artifact contract, command surface, documentation, examples, validation scripts, and release readiness into a coherent v1.10 release candidate without adding a new product capability.

Release target: `v1.10.0`  
Branch target: `roadmap/v1.10.0-v1-contract-consolidation`  
Boundary: Consolidation, validation, documentation, and release-readiness only. No new product capability, no autonomous remediation, no external API writes.

# W48-S01 — Artifact Contract Inventory and Schema Map

Risk: Medium  
Slice type: Contract inventory / schema documentation  
Artifact impact: Documentation and validation sidecar only

## Scope

Create a comprehensive inventory of the v1 artifact contract and map every major artifact to its schema, producer command, consumer command, stability level, mutation behavior, and validation coverage.

This slice consolidates the artifact surface accumulated through v1.0–v1.9.1. It should not change artifact behavior.

## Goals

- Create a single artifact contract inventory.
- Map canonical artifacts, sidecar artifacts, reports, and derived outputs.
- Identify artifact producers and consumers.
- Identify schema ownership and schema versions.
- Identify which artifacts are canonical versus derived.
- Identify which artifacts are mutable, append-only, regenerated, or read-only.
- Identify validation coverage per artifact.
- Highlight undocumented or weakly documented artifacts.

## Patch Set

Expected files/modules:

```text
docs/ARTIFACT_CONTRACT.md                    # new or consolidated
docs/SCHEMA_MAP.md                           # new
src/pharabius/core/artifact_contract.py       # optional, if machine-readable inventory is useful
tests/test_artifact_contract_inventory.py     # new
```

Recommended artifact categories:

| Category | Examples |
|---|---|
| Canonical analysis | `evidence.json`, `debt-register.json`, `project-profile.json` |
| Human-readable canonical mirrors | `debt-register.md` |
| Reports | architecture, dependency, test, security, business-risk, foundation audit |
| Planning | remediation roadmap, work packages, handoff summary |
| Review | PET review sidecar |
| Scoring | scoring delta, scoring preview, scoring evidence pack |
| Tickets | ticket drafts, ticket summary |
| Export bundles | tracker export bundles, manifest, summary |
| Portfolio | portfolio summary, repository index, validation rollup |
| Operational claims | claims, gaps, questions, confidence report, traceability matrices, agent-handoff contract |
| Run metadata | run files, version metadata |

Recommended inventory fields:

```yaml
artifact: .ai-debt/debt-register.json
category: canonical_analysis
schema: DebtRegister
schema_version: "1.0"
producer: ai-debt analyze
consumers:
  - ai-debt report
  - ai-debt plan
  - ai-debt tickets
  - ai-debt portfolio
mutation_policy: regenerated_by_producer
stability: stable
validation: covered
notes: canonical finding source
```

## Tests

Add tests for:

- Inventory contains required v1 canonical artifacts.
- Every listed artifact has a producer.
- Every listed artifact has a mutation policy.
- Every listed artifact has a stability classification.
- Schema-backed artifacts name their schema or explicitly state `unstructured_markdown`.
- Inventory is deterministic if generated from code.
- Docs mention canonical versus sidecar distinction.

## Targeted Verification

```bash
pytest tests/test_artifact_contract_inventory.py
grep -R "debt-register.json" docs/ARTIFACT_CONTRACT.md docs/SCHEMA_MAP.md
grep -R "agent-handoff-contract" docs/ARTIFACT_CONTRACT.md docs/SCHEMA_MAP.md
```

## Expected Behavior

Users and maintainers can answer:

- Which artifacts are part of the v1 contract?
- Which command produces each artifact?
- Which artifacts are canonical versus sidecar?
- Which schemas govern each artifact?
- Which artifacts are safe to regenerate?

## Acceptance Criteria

- Artifact contract inventory exists.
- Schema map exists.
- Canonical and sidecar artifacts are clearly separated.
- Producer and consumer relationships are documented.
- Mutation behavior is documented.
- No artifact behavior changes.
- No scoring behavior changes.
- All 7 local gates pass.
## Guardrails

- Do not add a new product capability.
- Do not modify production/source code under analysis.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call external APIs.
- Do not add a server, dashboard, scheduler, queue, remote crawler, or database.
- Do not change risk scoring behavior.
- Do not mutate canonical analysis artifacts except where explicitly regenerating validation outputs in controlled tests.
- Do not weaken the no-remediation boundary.
- Treat this wave as a v1 contract consolidation and release-candidate hardening wave.

## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.

