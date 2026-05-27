# Wave 52 — v2.0 Strategy & Boundary Planning

Goal: Decide what v2.0 is allowed to become, what remains forbidden, and which expansion path creates the highest value without breaking Pharabius’ trust model.

Release target: planning artifact set, not implementation release by default  
Branch target: `strategy/v2.0-boundary-planning` or `roadmap/v2.0-planning`  
Boundary: Strategy, architecture, risk modeling, and roadmap decision artifacts only. No implementation of v2 runtime capabilities in this wave.

# W52-S03 — External Integration Risk Model

Risk: Medium  
Slice type: Integration risk planning  
Artifact impact: Planning and risk model documents only

## Scope

Define the risk model for future external integrations: Jira, Linear, GitHub Issues, Azure DevOps, GitHub/GitLab repositories, SBOM/security tools, CI providers, and identity/ownership systems.

This slice must not implement integrations. It defines requirements, controls, and go/no-go criteria.

## Goals

- Categorize external integrations by risk.
- Define read-only vs write-capable integration classes.
- Define credential and permission constraints.
- Define audit logging requirements.
- Define dry-run and preview requirements.
- Define idempotency and duplicate-prevention requirements.
- Define failure modes and mitigation strategies.
- Preserve local-first operation as the default.

## Patch Set

Expected files:

```text
docs/v2/EXTERNAL_INTEGRATION_RISK_MODEL.md
docs/v2/V2_OPTION_MAP.md                       # link/update only
```

Recommended integration classes:

| Class | Description | Risk |
|---|---|---|
| I0 | No integration, file export only | Low |
| I1 | Read-only local file import | Low |
| I2 | Read-only external API | Medium |
| I3 | External draft/staged object creation | Medium-high |
| I4 | External write with explicit approval | High |
| I5 | Bidirectional sync | Very high |
| I6 | Autonomous external operations | Forbidden / not recommended |

Recommended tracker-specific risks:

| Tracker | Main risks |
|---|---|
| Jira | project permissions, field schemes, issue type mismatch, duplicate tickets |
| Linear | team/workspace IDs, label drift, workflow state assumptions |
| GitHub Issues | repository permissions, label creation, milestone assumptions |
| Azure DevOps | area/iteration paths, work item type variance, org/project permissions |

Required controls for write-capable integrations:

- explicit opt-in
- credential scope documentation
- dry-run mode
- preview artifact
- action manifest
- confirmation prompt or approval file
- duplicate detection
- write audit log
- failure recovery guidance

## Tests

Documentation-only slice. Optional docs tests:

- Integration classes appear in docs.
- Every write-capable class requires dry-run and approval.
- Docs state that v1 export bundles remain no-API-write artifacts.

## Expected Behavior

The team has a risk model for evaluating any future integration before implementation.

## Acceptance Criteria

- Integration risk classes are defined.
- Read-only and write-capable integrations are clearly separated.
- Credential, permission, dry-run, approval, and audit requirements are documented.
- v1 export-bundle safety semantics remain unchanged.
- No external integration code is implemented.
- All repository gates pass.
## Guardrails

- Do not implement v2 product capabilities in this wave.
- Do not add external API writes.
- Do not add autonomous remediation.
- Do not add production code modification.
- Do not add dashboard/server/database runtime unless only documented as an option.
- Do not add remote repository crawling.
- Do not weaken the v1 artifact contract.
- Do not change v1 safety boundaries.
- Do not alter v1 scoring behavior.
- Treat all outputs as planning, design, and decision artifacts.

## Verification Commands

Planning-only slices should still pass the normal repository gates if committed to the codebase:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

If a slice is documentation-only, run the documentation/link checks available in the repository in addition to the full gates.

