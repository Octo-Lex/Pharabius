# Wave 51 — v1.11.0 Final v1 Stabilization & Declaration

Goal: Declare the v1 product line stable by freezing the v1 artifact contract, command surface, safety boundaries, and compatibility commitments, while adding only final validation, documentation, and release-declaration artifacts.

Release target: `v1.11.0`  
Branch target: `roadmap/v1.11.0-final-v1-stabilization`  
Boundary: Stabilization and declaration only. No new product capability.

# W51-S05 — v1 Adoption and Upgrade Guide

Risk: Low  
Slice type: Documentation / adoption  
Artifact impact: Documentation only

## Scope

Create a v1 adoption and upgrade guide that helps teams adopt Pharabius v1.11.0, understand the stable workflow, upgrade from earlier v1.x versions, and use existing artifacts safely.

This slice is documentation-only.

## Goals

- Add a v1 adoption guide.
- Add upgrade notes for v1.5+ through v1.10.x users.
- Explain recommended command sequence.
- Explain artifact contract stability.
- Explain safety boundaries.
- Explain how to validate readiness.
- Explain how to use sample bundles.
- Explain when to use portfolio, ticket, export, and claims artifacts.
- Provide a go-live checklist.

## Patch Set

Expected files:

```text
docs/V1_ADOPTION_AND_UPGRADE_GUIDE.md       # new
docs/QUICKSTART.md                          # link/update
docs/ADOPTION_CHECKLIST.md                  # link/update
docs/README.md                              # link/update
README.md                                   # optional link only
```

Recommended guide structure:

```markdown
# Pharabius v1 Adoption and Upgrade Guide

## Who should use this guide
## Recommended adoption path
## Install and verify
## First run
## Golden path workflow
## Reading readiness results
## Using work packages and ticket drafts
## Using export bundles
## Using portfolio summaries
## Using operational claims and agent-handoff contracts
## Upgrading from earlier v1.x versions
## Go-live checklist
## Rollback and safe cleanup
```

Recommended upgrade notes:

| Source version | Guidance |
|---|---|
| v1.5.x | Review enhanced scoring and scoring calibration docs |
| v1.6.x | Review ticket draft workflow and completeness checks |
| v1.7.x | Review export bundle validation and tracker workflow docs |
| v1.8.x | Review portfolio command and local-only assumptions |
| v1.9.x | Review operational claims and agent-handoff safety docs |
| v1.10.x | Review readiness, doctor, packaging, and contract validation tools |

## Tests

Documentation-only. Optional link tests if available.

Recommended tests:

- Adoption guide exists.
- Docs index links to adoption guide.
- Guide mentions `ai-debt doctor`.
- Guide mentions `validate_golden_path.py`.
- Guide states no external API writes.
- Guide states no autonomous remediation.

## Targeted Verification

```bash
grep -R "ai-debt doctor" docs/V1_ADOPTION_AND_UPGRADE_GUIDE.md
grep -R "No external API writes" docs/V1_ADOPTION_AND_UPGRADE_GUIDE.md
grep -R "No autonomous remediation" docs/V1_ADOPTION_AND_UPGRADE_GUIDE.md
```

## Expected Behavior

A new team can use this guide to adopt the v1.11.0 stable line safely and understand how to upgrade from earlier v1.x releases.

## Acceptance Criteria

- `docs/V1_ADOPTION_AND_UPGRADE_GUIDE.md` exists.
- It includes install, first-run, golden path, readiness, and go-live guidance.
- It includes upgrade notes for prior v1.x capability groups.
- It links coherently from docs index and quickstart/adoption docs.
- It preserves safety boundaries.
- No runtime behavior changes are introduced.
- All 7 local gates pass.
## Guardrails

- Do not add new product capabilities.
- Do not add new CLI commands unless strictly diagnostic and explicitly approved; this wave should prefer scripts/docs/checks over command expansion.
- Do not change the v1 artifact contract except to document and freeze it.
- Do not break existing artifact paths, schema names, or command behavior.
- Do not mutate canonical artifacts outside normal command behavior.
- Do not change risk scoring behavior.
- Do not introduce dashboard, server, scheduler, database, remote crawling, or external APIs.
- Do not create external tracker issues or write to external systems.
- Do not authorize autonomous remediation or code modification.
- Treat this wave as a stability declaration and compatibility-hardening wave.

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

