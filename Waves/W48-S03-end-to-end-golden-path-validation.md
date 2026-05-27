# Wave 48 — v1.10.0 v1 Contract Consolidation & Release Candidate

Goal: Consolidate the v1 artifact contract, command surface, documentation, examples, validation scripts, and release readiness into a coherent v1.10 release candidate without adding a new product capability.

Release target: `v1.10.0`  
Branch target: `roadmap/v1.10.0-v1-contract-consolidation`  
Boundary: Consolidation, validation, documentation, and release-readiness only. No new product capability, no autonomous remediation, no external API writes.

# W48-S03 — End-to-End Golden Path Validation

Risk: Medium  
Slice type: Validation / integration hardening  
Artifact impact: Test fixtures and validation scripts only

## Scope

Add or strengthen an end-to-end golden path validation that exercises the full v1 command sequence and verifies expected artifacts are generated without violating safety boundaries.

This slice should validate the integrated product workflow rather than add new product behavior.

## Goals

- Define a deterministic golden-path fixture repository.
- Run the major Pharabius v1 workflow end to end.
- Verify required artifacts exist.
- Verify canonical artifacts are stable where expected.
- Verify sidecar artifacts are generated in expected locations.
- Verify no external APIs are called.
- Verify no source code mutation occurs.
- Verify artifact schemas parse.

## Patch Set

Expected files/modules:

```text
scripts/validate_golden_path.py              # new or expanded
tests/test_golden_path_validation.py         # new
tests/fixtures/golden_path_repo/             # fixture, if not already present
docs/VALIDATION.md                           # update
```

Recommended golden path:

```bash
ai-debt init
ai-debt profile
ai-debt scan
ai-debt graph
ai-debt analyze --no-ai
ai-debt review --init
ai-debt report
ai-debt plan
ai-debt tickets
ai-debt export
ai-debt portfolio --repo .
```

Optional if claims are generated through an existing command:

```bash
# verify claims artifacts after analyze/report/plan if applicable
ls .ai-debt/claims
ls .ai-debt/traceability
```

Required artifact assertions:

| Area | Artifacts |
|---|---|
| Core | profile, evidence, debt register |
| Graph | architecture graph |
| Reports | foundation report and domain reports |
| Planning | roadmap, work packages, handoff |
| Review | review sidecar |
| Tickets | ticket drafts/index/summary |
| Export bundles | manifest, tracker folders, summary |
| Portfolio | portfolio summary/index/rollup |
| Claims | operational claims, gaps/questions, confidence report, matrices |

## Tests

Add tests for:

- Golden path completes successfully.
- Required artifacts exist.
- JSON artifacts parse.
- Markdown artifacts are non-empty.
- Source files are not modified.
- No external API calls are attempted.
- Re-running validation is deterministic for stable inputs.
- Failures produce actionable diagnostics.

## Targeted Verification

```bash
pytest tests/test_golden_path_validation.py
python scripts/validate_golden_path.py
```

## Expected Behavior

Maintainers can run one validation script to verify the v1 product contract end to end before release.

Expected summary:

```text
Golden path validation: PASS
Commands run: N
Artifacts verified: N
Canonical mutation violations: 0
External API calls: 0
```

## Acceptance Criteria

- Golden path validation exists.
- It exercises the v1 workflow end to end.
- It verifies artifacts and safety boundaries.
- It produces actionable failure messages.
- It does not rely on network access.
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

