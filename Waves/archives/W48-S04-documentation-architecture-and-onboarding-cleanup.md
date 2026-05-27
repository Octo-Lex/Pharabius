# Wave 48 — v1.10.0 v1 Contract Consolidation & Release Candidate

Goal: Consolidate the v1 artifact contract, command surface, documentation, examples, validation scripts, and release readiness into a coherent v1.10 release candidate without adding a new product capability.

Release target: `v1.10.0`  
Branch target: `roadmap/v1.10.0-v1-contract-consolidation`  
Boundary: Consolidation, validation, documentation, and release-readiness only. No new product capability, no autonomous remediation, no external API writes.

# W48-S04 — Documentation Architecture and Onboarding Cleanup

Risk: Low-medium  
Slice type: Documentation architecture / onboarding  
Artifact impact: Docs only, optionally doc link tests

## Scope

Reorganize and clarify the documentation structure so new users can understand Pharabius v1 from installation to full handoff workflow without reading every release note.

This slice should improve navigation, eliminate stale duplication, and link related concepts coherently.

## Goals

- Create or update a documentation index.
- Clarify the main user journey.
- Separate quickstart, reference, concepts, and advanced workflows.
- Link artifact contract, CLI reference, validation, ticket drafts, export bundles, portfolio, and operational claims docs.
- Add a v1 workflow overview.
- Add a “what Pharabius does not do” boundary section.
- Remove or correct stale references.

## Patch Set

Expected files:

```text
docs/README.md                               # documentation index
docs/QUICKSTART.md                           # update or create
docs/CLI.md                                  # link/update
docs/ARTIFACT_CONTRACT.md                    # link/update
docs/VALIDATION.md                           # link/update
docs/TICKET_DRAFTS.md                        # link/update
docs/EXPORT_BUNDLES.md                       # link/update
docs/PORTFOLIO.md                            # link/update
docs/OPERATIONAL_CLAIMS.md                   # link/update
README.md                                    # top-level docs links
tests/test_docs_navigation.py                # optional
```

Recommended docs taxonomy:

```text
Getting started
  - Quickstart
  - Command sequence
  - Output overview
Reference
  - CLI
  - Artifact contract
  - Schema map
Workflows
  - Review sidecar
  - Work packages
  - Ticket drafts
  - Export bundles
  - Portfolio summaries
  - Operational claims / agent handoff
Validation
  - Local gates
  - Golden path
  - Field validation
Boundaries
  - No remediation
  - No external API writes
  - No remote crawling
```

## Tests

Optional tests for:

- Docs index links to required docs.
- Required docs exist.
- Quickstart includes the canonical command sequence.
- Boundary language exists.
- No references to unsupported API-write behavior.

## Targeted Verification

```bash
grep -R "ai-debt init" docs/QUICKSTART.md docs/README.md
grep -R "does not" docs/README.md docs/QUICKSTART.md docs/OPERATIONAL_CLAIMS.md
pytest tests/test_docs_navigation.py || true
```

## Expected Behavior

A new user can start from the README, follow Quickstart, understand generated artifacts, and discover advanced workflows without reading historical release notes.

## Acceptance Criteria

- Docs index exists or is clearly updated.
- Quickstart is coherent and current.
- v1 workflow is documented end to end.
- Advanced workflow docs are linked.
- Safety boundaries are explicit.
- No runtime behavior changes.
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

