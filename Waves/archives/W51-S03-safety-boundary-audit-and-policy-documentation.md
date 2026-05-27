# Wave 51 — v1.11.0 Final v1 Stabilization & Declaration

Goal: Declare the v1 product line stable by freezing the v1 artifact contract, command surface, safety boundaries, and compatibility commitments, while adding only final validation, documentation, and release-declaration artifacts.

Release target: `v1.11.0`  
Branch target: `roadmap/v1.11.0-final-v1-stabilization`  
Boundary: Stabilization and declaration only. No new product capability.

# W51-S03 — Safety Boundary Audit and Policy Documentation

Risk: Medium  
Slice type: Safety audit / documentation / validation  
Artifact impact: Documentation and optional validation report only

## Scope

Perform a final v1 safety-boundary audit and document the boundaries that Pharabius commits to for the v1 product line.

This slice should verify that current commands and docs do not imply or perform autonomous remediation, external writes, source-code modification, credential use, tracker API writes, dashboard/server behavior, or remote crawling.

## Goals

- Document v1 safety boundaries in a dedicated policy file.
- Audit CLI commands for boundary classification.
- Audit docs for ambiguous language.
- Add validation tests or scripts for forbidden phrases/claims where practical.
- Ensure agent-handoff language does not authorize code modification.
- Ensure ticket/export language does not imply issue creation.
- Ensure portfolio language does not imply remote crawling.

## Patch Set

Expected files:

```text
docs/SAFETY_BOUNDARIES.md                 # new
docs/V1_STABILITY_CONTRACT.md             # link/update
docs/CLI.md                               # safety classification update if needed
docs/README.md                            # link/update
tests/test_safety_boundary_docs.py         # optional/new
scripts/validate_safety_boundaries.py      # optional if useful
```

Recommended policy sections:

```markdown
# Pharabius v1 Safety Boundaries

## No production code modification
## No autonomous remediation
## No external API writes
## No issue creation
## No remote repository crawling
## No dashboard/server/database requirement
## No risk acceptance decisions
## Human ownership model
## Command safety classifications
## Agent-handoff limitations
```

Recommended command safety classifications:

| Class | Meaning |
|---|---|
| Read-only diagnostic | No writes except console output |
| Repository-local artifact writer | Writes only under `.ai-debt/` |
| Export artifact writer | Writes local export files only |
| Validation script | Reads artifacts and reports status |
| Forbidden in v1 | External writes, remediation, code changes |

Recommended audit checks:

- `ai-debt doctor` is read-only.
- `ai-debt tickets` writes local ticket drafts only.
- export bundles do not create external issues.
- portfolio command does not crawl remote repos.
- agent-handoff contract forbids autonomous code modification.
- docs do not promise remediation or external sync.

## Tests

Add tests for:

- Safety boundaries doc exists.
- Docs contain required forbidden-action statements.
- CLI reference includes safety classification for all commands.
- Agent-handoff docs include forbidden actions.
- Export bundle docs state no API writes.
- Portfolio docs state no remote crawling.
- Ticket docs state local drafts only.

## Targeted Verification

```bash
pytest tests/test_safety_boundary_docs.py || true
python scripts/validate_safety_boundaries.py || true
grep -R "No autonomous remediation" docs
```

## Expected Behavior

Maintainers and users have a single authoritative safety-boundary document for v1.

## Acceptance Criteria

- `docs/SAFETY_BOUNDARIES.md` exists.
- Every CLI command has a documented safety classification.
- Agent-handoff, ticket, export, and portfolio docs preserve boundaries.
- No docs imply external writes or autonomous remediation.
- No runtime feature behavior changes are introduced.
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

