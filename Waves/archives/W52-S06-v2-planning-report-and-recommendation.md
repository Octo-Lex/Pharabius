# Wave 52 — v2.0 Strategy & Boundary Planning

Goal: Decide what v2.0 is allowed to become, what remains forbidden, and which expansion path creates the highest value without breaking Pharabius’ trust model.

Release target: planning artifact set, not implementation release by default  
Branch target: `strategy/v2.0-boundary-planning` or `roadmap/v2.0-planning`  
Boundary: Strategy, architecture, risk modeling, and roadmap decision artifacts only. No implementation of v2 runtime capabilities in this wave.

# W52-S06 — v2 Planning Report and Recommendation

Risk: Low  
Slice type: Final planning synthesis  
Artifact impact: Planning report, roadmap, changelog if desired

## Scope

Synthesize Wave 52 into a final v2 planning report and recommendation. This slice closes the planning wave and gives the team a clear decision for the next implementation wave.

This is not a release implementation slice unless the project chooses to publish planning artifacts as a documentation-only release.

## Goals

- Summarize the v2 product thesis.
- Summarize automation boundaries.
- Summarize external integration risks.
- Summarize data/deployment options.
- Summarize roadmap decision matrix results.
- Recommend the next v2 implementation wave.
- Define what remains forbidden in early v2.
- Define v1 maintenance posture.

## Patch Set

Expected files:

```text
docs/v2/V2_PLANNING_REPORT.md
docs/v2/README.md
ROADMAP.md                                  # optional v2 planning update
CHANGELOG.md                                # optional if released as docs/planning version
```

Recommended report structure:

```markdown
# v2.0 Planning Report

## Executive Recommendation
## v2 Product Thesis
## What v2 May Become
## What Remains Forbidden
## Automation Boundary
## External Integration Risk Posture
## Data and Deployment Recommendation
## Roadmap Decision Matrix Summary
## Recommended v2 Primary Track
## Deferred Tracks
## Rejected Tracks
## v1 Maintenance Posture
## Next Wave Proposal
```

Recommended next-wave options:

| Option | Suggested wave |
|---|---|
| Policy engine first | Wave 53 — v2.0 Local Policy Engine Foundation |
| Human validation workflow first | Wave 53 — v2.0 Human Validation Workflow |
| Static dashboard first | Wave 53 — v2.0 Static Portfolio Viewer |
| External writes first | Not recommended as first v2 wave |
| Autonomous remediation | Reject |

Recommended final recommendation:

```text
Start v2 with a local policy and human-validation workflow. Defer external writes, dashboards, servers, remote crawling, and code-modification automation until the governance layer is proven.
```

## Tests

Documentation-only slice. Optional checks:

- Planning report exists.
- Next-wave recommendation exists.
- Forbidden actions are listed.
- v1 maintenance posture is stated.

## Expected Behavior

Wave 52 ends with an actionable v2 recommendation and a clear boundary between planning and implementation.

## Acceptance Criteria

- v2 planning report exists.
- Recommended v2 primary track is explicit.
- Deferred and rejected tracks are explicit.
- v1 maintenance posture is stated.
- No implementation capability is added.
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

