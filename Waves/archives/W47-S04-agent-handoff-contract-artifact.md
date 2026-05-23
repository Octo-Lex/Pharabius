# Wave 47 — v1.9.1 Operational Claims Polish & Agent-Handoff Pack

Goal: Improve operational claims usability, examples, validation, and agent-handoff readiness while preserving the no-remediation boundary.

Release target: `v1.9.1`  
Branch target: `roadmap/v1.9.1-operational-claims-polish`  
Boundary: Repository-local specification, validation, documentation, and handoff artifacts only. No code modification, no autonomous remediation, no external API writes.

# W47-S04 — Agent-Handoff Contract Artifact

Risk: Medium  
Slice type: New handoff artifact / safety contract  
Artifact impact: New `.ai-debt/agent-handoff-contract.md`

## Scope

Add an optional repository-local agent-handoff contract artifact that summarizes what downstream AI agents may rely on, what must be preserved, what is inferred, what is blocked by gaps, and what requires human validation.

This artifact must not authorize code modification. It is a safety and review contract, not an execution permission slip.

## Goals

- Generate `.ai-debt/agent-handoff-contract.md`.
- Summarize confirmed claims that may be used as reliable context.
- Summarize inferred claims that must be treated cautiously.
- Summarize blocking gaps that prevent safe implementation.
- Summarize preservation requirements.
- Summarize forbidden actions.
- Link to operational claims, gaps, questions, confidence report, traceability matrices, and work packages.
- Make the no-remediation boundary explicit.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/claims.py
src/pharabius/core/agent_handoff.py              # new, if useful
src/pharabius/schemas/claims.py
tests/test_agent_handoff_contract.py
docs/OPERATIONAL_CLAIMS.md
```

Recommended artifact path:

```text
.ai-debt/agent-handoff-contract.md
```

Recommended structure:

```markdown
# Agent Handoff Contract

## Purpose
## Safety Boundary
## Reliable Context: Confirmed Claims
## Caution Context: Inferred Claims
## Blocking Gaps
## Human Validation Required
## Preservation Requirements
## Allowed Uses
## Forbidden Actions
## Required Verification Before Implementation
## Linked Artifacts
```

Required forbidden actions:

```text
- Do not modify production code based solely on this artifact.
- Do not change authentication, authorization, data retention, payment, migration, or public API behavior without human approval.
- Do not treat inferred claims as confirmed facts.
- Do not proceed on work packages with blocking gaps.
- Do not call external systems or create issues unless separately authorized by the Product Engineering Team.
```

Recommended allowed uses:

```text
- Use confirmed claims as context for planning.
- Use inferred claims as hypotheses requiring validation.
- Use gaps/questions to ask Product Engineering for clarification.
- Use traceability matrices to inspect evidence relationships.
- Use work packages as planning inputs, not implementation authority.
```

## Tests

Add tests for:

- Agent-handoff contract is generated.
- Contract includes safety boundary.
- Contract lists confirmed claims.
- Contract lists inferred claims.
- Contract lists blocking gaps.
- Contract lists human-validation questions.
- Contract includes forbidden actions.
- Contract links to claims/gaps/confidence/traceability artifacts.
- Contract does not include language authorizing code changes.
- Output is deterministic.

## Targeted Verification

```bash
pytest tests/test_agent_handoff_contract.py
```

## Expected Behavior

Pharabius emits:

```text
.ai-debt/agent-handoff-contract.md
```

The contract helps downstream agents and human operators understand safe usage boundaries.

## Acceptance Criteria

- Agent-handoff contract is generated and tested.
- Contract explicitly preserves the no-remediation boundary.
- Contract distinguishes confirmed, inferred, and gap claims.
- Contract identifies blocking gaps and human-validation requirements.
- Contract does not authorize code changes.
- No canonical artifacts are mutated.
- No external API behavior is introduced.
- All 7 local gates pass.
## Guardrails

- Do not modify production/source code.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external APIs.
- Do not mutate `debt-register.json`, `evidence.json`, work packages, ticket drafts, export bundles, portfolio outputs, or existing claim registers except when explicitly regenerating claims artifacts.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence risk scores.
- Do not convert inferred claims into confirmed claims without direct evidence.
- Do not let the agent-handoff contract authorize code modification.
- Treat the agent-handoff contract as a safety and review artifact, not an execution mandate.

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

