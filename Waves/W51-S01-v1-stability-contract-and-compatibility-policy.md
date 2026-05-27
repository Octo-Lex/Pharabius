# Wave 51 — v1.11.0 Final v1 Stabilization & Declaration

Goal: Declare the v1 product line stable by freezing the v1 artifact contract, command surface, safety boundaries, and compatibility commitments, while adding only final validation, documentation, and release-declaration artifacts.

Release target: `v1.11.0`  
Branch target: `roadmap/v1.11.0-final-v1-stabilization`  
Boundary: Stabilization and declaration only. No new product capability.

# W51-S01 — v1 Stability Contract and Compatibility Policy

Risk: Medium  
Slice type: Documentation / compatibility contract  
Artifact impact: Documentation only, unless optional validation metadata is added

## Scope

Create a formal v1 stability contract that defines what Pharabius considers stable for the v1 line: artifact paths, schema names, command surface, safety boundaries, local-first operation, and compatibility commitments.

This slice is a declaration and policy slice. It should not change runtime behavior.

## Goals

- Define v1 stability commitments.
- Freeze the v1 artifact contract at the documentation level.
- Define compatibility expectations for v1.x patch/minor releases after v1.11.0.
- Define what changes require v2.0.
- Define allowed v1.x maintenance changes.
- Clarify deprecation policy.
- Clarify schema-version policy.
- Clarify command-surface policy.
- Clarify safety-boundary policy.

## Patch Set

Expected files:

```text
docs/V1_STABILITY_CONTRACT.md        # new
docs/ARTIFACT_CONTRACT.md            # link/update only
docs/CLI.md                          # link/update only
docs/README.md                       # add link
CHANGELOG.md                         # defer detailed entry to S06 if preferred
```

Recommended document structure:

```markdown
# Pharabius v1 Stability Contract

## Purpose
## Stable v1 surface
## Artifact compatibility
## Schema compatibility
## Command compatibility
## Safety boundary commitments
## Local-first commitments
## Allowed v1.x changes
## Changes reserved for v2.0
## Deprecation policy
## Versioning policy
```

Recommended stable v1 surface:

| Surface | v1 commitment |
|---|---|
| `.ai-debt/` artifact paths | Stable unless explicitly deprecated |
| Schema names and `schema_version` fields | Stable within v1.x |
| CLI command names | Stable within v1.x |
| Default behavior | Must not become more destructive or externally connected |
| No-code-modification boundary | Stable v1 commitment |
| No external API writes | Stable v1 commitment |
| Repository-local output | Stable v1 commitment |

Recommended v2.0-only changes:

- Removing or renaming v1 artifacts.
- Breaking schema field compatibility.
- Adding default external writes.
- Adding autonomous remediation.
- Requiring a server, database, scheduler, or cloud service.
- Changing default scoring behavior in a way that reorders canonical outputs without explicit migration policy.

## Tests

Documentation-only slice. Add tests only if docs-link validation already exists.

Optional tests:

- Stability contract exists.
- Stability contract is linked from docs index.
- Stability contract includes required boundary phrases.
- Stability contract lists v2.0-only changes.

## Targeted Verification

```bash
grep -R "v1 Stability Contract" docs/V1_STABILITY_CONTRACT.md
grep -R "No external API writes" docs/V1_STABILITY_CONTRACT.md
grep -R "No autonomous remediation" docs/V1_STABILITY_CONTRACT.md
```

## Expected Behavior

Users and maintainers can clearly distinguish:

- what is stable in v1,
- what is allowed in v1.x maintenance,
- what must wait for v2.0,
- what safety boundaries remain non-negotiable.

## Acceptance Criteria

- `docs/V1_STABILITY_CONTRACT.md` exists.
- It defines stable artifact, schema, command, and safety surfaces.
- It defines allowed v1.x maintenance changes.
- It defines v2.0-only breaking changes.
- It is linked from the documentation index.
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

