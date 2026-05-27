# Wave 52 — v2.0 Strategy & Boundary Planning

Goal: Decide what v2.0 is allowed to become, what remains forbidden, and which expansion path creates the highest value without breaking Pharabius’ trust model.

Release target: planning artifact set, not implementation release by default  
Branch target: `strategy/v2.0-boundary-planning` or `roadmap/v2.0-planning`  
Boundary: Strategy, architecture, risk modeling, and roadmap decision artifacts only. No implementation of v2 runtime capabilities in this wave.

# W52-S01 — v2 Option Map and Product Thesis

Risk: Low  
Slice type: Strategy / product thesis  
Artifact impact: Planning documents only

## Scope

Create a structured option map for v2.0. The purpose is to define what v2.0 could become, which directions are strategically attractive, which are risky, and which should remain out of scope.

This slice should not choose the final roadmap. It establishes the decision space.

## Goals

- Define the v2 product thesis.
- Enumerate credible v2 expansion paths.
- Separate product-value options from engineering-risk options.
- Identify options that preserve Pharabius’ trust model.
- Identify options that would break or weaken the trust model.
- Define v2 planning constraints inherited from v1.
- Produce a clear option map for later scoring in W52-S05.

## Patch Set

Expected files:

```text
docs/v2/V2_OPTION_MAP.md
docs/v2/V2_PRODUCT_THESIS.md
docs/v2/README.md
```

Recommended option categories:

| Category | Example options |
|---|---|
| Governed automation | Approval-gated patch planning, controlled remediation proposals |
| Human validation workflow | Claim review, gap closure, sign-off records |
| External integrations | Jira, Linear, GitHub Issues, Azure DevOps write APIs |
| Portfolio platform | Server, dashboard, API, persistence |
| Organization-scale scanning | Remote repo discovery, scheduled audits, multi-repo policy |
| Policy engine | Local rules for scoring, artifact completeness, safety checks |
| Agent orchestration | Controlled multi-agent audit workflows |
| Enterprise governance | ownership, audit trails, exceptions, risk acceptance |

Recommended v2 thesis draft:

```text
Pharabius v2 should expand from repository-local intelligence artifacts into governed technical-debt operations, but only where every automated action remains evidence-backed, auditable, reversible, and human-authorized.
```

## Tests

Documentation-only slice. Add tests only if the repository has docs validation utilities.

Recommended checks:

- Docs exist.
- Docs link from `docs/README.md` or a v2 planning index.
- Option map contains all major v2 options.
- Product thesis explicitly preserves evidence, traceability, and human authorization.
- No implementation files are changed beyond docs if this slice is kept documentation-only.

## Expected Behavior

After this slice, the team has a shared v2 decision space and product thesis, but no v2 implementation commitment.

## Acceptance Criteria

- v2 option map exists.
- v2 product thesis exists.
- Options include value, risks, and boundary implications.
- The document distinguishes exploration from commitment.
- No v2 runtime capability is implemented.
- v1 contract and safety boundaries remain unchanged.
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

