# Wave 52 — v2.0 Strategy & Boundary Planning

Goal: Decide what v2.0 is allowed to become, what remains forbidden, and which expansion path creates the highest value without breaking Pharabius’ trust model.

Release target: planning artifact set, not implementation release by default  
Branch target: `strategy/v2.0-boundary-planning` or `roadmap/v2.0-planning`  
Boundary: Strategy, architecture, risk modeling, and roadmap decision artifacts only. No implementation of v2 runtime capabilities in this wave.

# W52-S02 — Automation Boundary Model

Risk: Medium  
Slice type: Safety architecture / policy planning  
Artifact impact: Planning and policy documents only

## Scope

Define the automation boundary model for v2.0. This model should clarify what automation may be allowed, what requires approval, and what remains forbidden.

The goal is not to implement automation. The goal is to prevent accidental scope drift when v2 planning begins.

## Goals

- Define automation levels for Pharabius.
- Separate analysis automation, planning automation, workflow automation, and code-changing automation.
- Define explicit approval gates.
- Define forbidden actions.
- Define rollback and audit requirements for any future action capability.
- Preserve the v1 no-remediation boundary unless v2 explicitly introduces governed approval workflows.

## Patch Set

Expected files:

```text
docs/v2/AUTOMATION_BOUNDARY_MODEL.md
docs/v2/V2_OPTION_MAP.md                 # link/update only
```

Recommended automation levels:

| Level | Name | Allowed in v1 | Candidate for v2 | Notes |
|---|---|---:|---:|---|
| A0 | Read-only analysis | Yes | Yes | Scanning, evidence, reports |
| A1 | Planning artifact generation | Yes | Yes | Work packages, tickets, exports |
| A2 | External draft creation | No | Maybe | Draft external issues, no submit |
| A3 | External write with approval | No | Maybe | Create issue after explicit approval |
| A4 | Code patch proposal | No | Maybe later | Generates patch artifact only |
| A5 | Code modification / PR creation | No | High-risk v2+ | Requires strict governance |
| A6 | Autonomous remediation | No | Forbidden unless future major redesign | Not recommended |

Recommended required controls for A3+:

- explicit human approval
- dry-run preview
- auditable action log
- idempotency key
- rollback/undo guidance where possible
- permission scoping
- no hidden network action
- visible diff/action summary before execution

Recommended forbidden actions:

```text
- silently modifying production code
- silently creating external issues
- changing authentication/authorization logic
- applying dependency upgrades automatically
- changing infrastructure or deployment configuration automatically
- making risk acceptance decisions
- bypassing human approval for high-risk actions
```

## Tests

Documentation-only slice. If policy validation tests exist, add checks that the document contains the automation levels and forbidden actions.

## Expected Behavior

The team can evaluate any v2 feature by asking which automation level it occupies and what controls it requires.

## Acceptance Criteria

- Automation levels are defined.
- Forbidden actions are explicit.
- Approval requirements are explicit.
- The document distinguishes artifact generation from external writes and code changes.
- No automation implementation is added.
- No v1 boundary is weakened.
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

