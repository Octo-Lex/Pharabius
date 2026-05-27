# Wave 52 — v2.0 Strategy & Boundary Planning

Goal: Decide what v2.0 is allowed to become, what remains forbidden, and which expansion path creates the highest value without breaking Pharabius’ trust model.

Release target: planning artifact set, not implementation release by default  
Branch target: `strategy/v2.0-boundary-planning` or `roadmap/v2.0-planning`  
Boundary: Strategy, architecture, risk modeling, and roadmap decision artifacts only. No implementation of v2 runtime capabilities in this wave.

# W52-S05 — v2 Roadmap Decision Matrix

Risk: Low-medium  
Slice type: Strategic decision support  
Artifact impact: Planning report only

## Scope

Create a decision matrix that scores the v2 options from W52-S01 through W52-S04. The matrix should make tradeoffs explicit and recommend a primary v2 direction.

This slice should not implement the chosen direction.

## Goals

- Score v2 options against consistent criteria.
- Compare user value, trust impact, safety risk, implementation complexity, adoption value, and maintenance burden.
- Identify a recommended v2 primary track.
- Identify secondary/deferred tracks.
- Identify explicitly rejected tracks.
- Produce a clear go/no-go decision basis.

## Patch Set

Expected files:

```text
docs/v2/V2_ROADMAP_DECISION_MATRIX.md
docs/v2/V2_OPTION_MAP.md                    # optional update with recommendation pointer
```

Recommended evaluation criteria:

| Criterion | Meaning |
|---|---|
| PET value | Direct value to Product Engineering Teams |
| Enterprise value | Value to managers, architects, platform/security teams |
| Trust-model fit | Preserves evidence, traceability, human control |
| Safety risk | Risk of unintended external/code changes |
| Implementation complexity | Engineering effort and architectural burden |
| Maintenance burden | Long-term support cost |
| Adoption acceleration | Helps teams adopt Pharabius faster |
| v1 continuity | Builds on existing v1 artifacts cleanly |
| Differentiation | Strengthens unique market position |

Candidate options to score:

| Option | Description |
|---|---|
| Policy engine | Local rules and governance policy over artifacts |
| Human validation workflow | Claim/gap review and approval records |
| External tracker writes | Jira/Linear/GitHub/Azure issue creation with approval |
| Static dashboard | Local static HTML portfolio/report viewer |
| API server/dashboard | Hosted/local service with persistence |
| Multi-repo crawler | Remote org/repo discovery and scheduled audits |
| Governed patch proposals | Patch artifacts only, no apply/PR creation |
| Autonomous remediation | Code modification without human approval |

Recommended default recommendation, subject to team decision:

```text
Primary v2 track should likely be a local policy and human-validation workflow before external writes or server/dashboard work.
```

## Tests

Documentation-only slice. Optional docs checks:

- Matrix file exists.
- Every candidate option has scores.
- Recommendation section exists.
- Rejected tracks are explicit.

## Expected Behavior

The team can choose a v2 direction based on explicit criteria rather than momentum or feature pressure.

## Acceptance Criteria

- Decision matrix exists.
- Scoring criteria are defined.
- Options are scored consistently.
- Primary recommendation is stated.
- Deferred and rejected options are stated.
- No implementation of selected option occurs in this slice.
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

