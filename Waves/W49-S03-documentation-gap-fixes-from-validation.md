# Wave 49 — v1.10.1 RC Hardening & Field Validation

Goal: Validate v1.10.0 across representative repositories, fix documentation/validation gaps, and produce a field-validation evidence pack without adding new product capability.

Release target: `v1.10.1`  
Branch target: `roadmap/v1.10.1-rc-hardening`  
Boundary: Release-candidate hardening only. No new product capability, no new command surface, no external integrations, no remediation automation.

# W49-S03 — Documentation Gap Fixes from Validation

Risk: Low  
Slice type: Documentation hardening  
Artifact impact: Docs only

## Scope

Apply documentation fixes discovered during W49-S01 and W49-S02 validation. This slice is intentionally limited to clarifying existing capabilities, commands, artifact behavior, preconditions, and known limitations.

No runtime behavior should be introduced here.

## Goals

- Fix unclear golden-path instructions.
- Clarify command preconditions.
- Clarify optional vs required artifacts.
- Clarify readiness status semantics.
- Clarify no-API/no-remediation boundaries where validation surfaced ambiguity.
- Keep docs coherent and navigable.
- Avoid marketing claims or unsupported empirical claims.

## Patch Set

Expected files:

```text
docs/README.md
docs/QUICKSTART.md
docs/CLI.md
docs/ARTIFACT_CONTRACT.md
docs/SCHEMA_MAP.md
docs/KNOWN_LIMITATIONS.md or KNOWN_LIMITATIONS.md
README.md                                  # link updates only, if needed
```

Recommended fixes:

| Area | Fix type |
|---|---|
| Golden path | Exact command sequence and preconditions |
| Artifacts | Required vs optional vs conditional outputs |
| Readiness | Meaning of ready/partial/needs_review |
| Portfolio | Local path aggregation only |
| Export bundles | No external tracker API writes |
| Agent handoff | Contract is not implementation authority |
| Operational claims | Confidence is not factual precision |

## Tests

Documentation-only slice. Add or update docs tests only if existing docs test framework supports it.

Recommended lightweight checks:

- Docs mention all public commands from `docs/CLI.md`.
- Docs include no unsupported API-write claims.
- Quickstart command sequence remains valid.
- Known limitations include validation caveats.

## Targeted Verification

```bash
grep -R "ai-debt portfolio" docs README.md || true
grep -R "does not call" docs README.md || true
grep -R "does not modify production code" docs README.md || true
pytest tests/test_docs*.py || true
```

## Expected Behavior

Documentation accurately reflects v1.10.1 behavior and resolves issues discovered by validation.

## Acceptance Criteria

- Docs clarify gaps found during field validation.
- No runtime behavior changes are introduced.
- No new capability is documented unless it already exists.
- Safety boundaries remain explicit.
- Docs remain coherent and linked.
- All 7 local gates pass.
## Guardrails

- Do not add new product capability.
- Do not add new CLI commands unless required only for validation and explicitly scoped as internal/script tooling.
- Do not change risk scoring behavior.
- Do not mutate canonical artifacts during validation except by normal command execution in temporary validation workspaces.
- Do not modify production/source code in analyzed repositories.
- Do not call external APIs or remote repository services.
- Do not introduce dashboards, servers, schedulers, databases, queues, or background jobs.
- Do not create external issues, tickets, pull requests, assignments, milestones, or tracker updates.
- Do not weaken the v1 no-remediation boundary.
- Treat all outputs as repository-local validation and evidence artifacts.

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

