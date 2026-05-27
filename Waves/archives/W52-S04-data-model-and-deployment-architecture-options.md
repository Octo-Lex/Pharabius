# Wave 52 — v2.0 Strategy & Boundary Planning

Goal: Decide what v2.0 is allowed to become, what remains forbidden, and which expansion path creates the highest value without breaking Pharabius’ trust model.

Release target: planning artifact set, not implementation release by default  
Branch target: `strategy/v2.0-boundary-planning` or `roadmap/v2.0-planning`  
Boundary: Strategy, architecture, risk modeling, and roadmap decision artifacts only. No implementation of v2 runtime capabilities in this wave.

# W52-S04 — Data Model and Deployment Architecture Options

Risk: Medium  
Slice type: Architecture planning  
Artifact impact: Planning and architecture documents only

## Scope

Map possible v2 data and deployment architectures without selecting or implementing one. The purpose is to clarify the tradeoffs between keeping Pharabius file-based and local-only versus adding services, persistence, APIs, dashboards, queues, or scheduled audits.

## Goals

- Document possible v2 deployment models.
- Document data model options.
- Identify which options preserve local-first operation.
- Identify which options introduce operational/security burden.
- Define migration considerations from v1 `.ai-debt/` artifacts.
- Define which options are premature for v2.0.

## Patch Set

Expected files:

```text
docs/v2/DATA_MODEL_AND_DEPLOYMENT_OPTIONS.md
docs/v2/V2_OPTION_MAP.md                            # link/update only
```

Recommended deployment options:

| Option | Description | Risk |
|---|---|---|
| D0 | CLI-only, file-based | Low |
| D1 | CLI + local SQLite cache | Medium |
| D2 | CLI + static HTML dashboard | Medium |
| D3 | Local FastAPI service | Medium-high |
| D4 | Hosted API server | High |
| D5 | Multi-tenant SaaS | Very high |
| D6 | Scheduled organization crawler | High |

Recommended data model options:

| Model | Description | Notes |
|---|---|---|
| File contract only | `.ai-debt/` remains source of truth | Best continuity |
| SQLite index | Derived local index over artifacts | Rebuildable cache |
| Postgres service DB | Centralized portfolio/system state | Requires auth, migration, ops |
| Graph DB | Deep relationship queries | Likely premature |
| Object storage + metadata DB | Scalable artifact archive | v2+ only if hosted |

Required architectural principles:

- `.ai-debt/` remains portable.
- Any database is derived/rebuildable unless explicitly declared canonical.
- Local-only mode remains supported.
- No hidden network operations.
- Artifact schema compatibility must be maintained.

## Tests

Documentation-only slice. Optional checks:

- Architecture options table exists.
- Local-first principle appears.
- `.ai-debt/` portability appears.
- No implementation files are changed.

## Expected Behavior

The team can make a deliberate v2 architecture decision instead of drifting into a server, dashboard, or database prematurely.

## Acceptance Criteria

- Deployment options are documented with tradeoffs.
- Data model options are documented with tradeoffs.
- Local-first and `.ai-debt/` portability remain explicit principles.
- No deployment architecture is implemented.
- No database dependency is added.
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

