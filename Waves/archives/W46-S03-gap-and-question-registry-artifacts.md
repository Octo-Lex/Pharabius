# Wave 46 — v1.9.0 Operational Claims & Gap Registry

Goal: Add first-class operational claims, gap registry, confidence reporting, and traceability matrices derived from existing Pharabius evidence, findings, work packages, and reports.

Release target: `v1.9.0`  
Branch target: `roadmap/v1.9.0-operational-claims`  
Boundary: Repository-local specification and traceability artifacts only. No code modification, no autonomous remediation, no external API writes.

# W46-S03 — Gap and Question Registry Artifacts

Risk: Medium  
Slice type: Gap registry / handoff artifacts  
Artifact impact: New `.ai-debt/claims/gaps.md` and `.ai-debt/claims/questions.md`

## Scope

Create explicit gap and question registry artifacts derived from operational claims, work-package preconditions, limitations, and uncertainty markers. This slice promotes gaps from generic limitations into first-class review artifacts for Product Engineering Teams.

## Goals

- Generate `.ai-debt/claims/gaps.md`.
- Generate `.ai-debt/claims/questions.md`.
- Separate blocking gaps from non-blocking gaps.
- Link gaps to claims, findings, work packages, and evidence when available.
- Generate human-validation questions.
- Keep gaps explicit and reviewable.
- Avoid treating gaps as failures; they are controlled uncertainty.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/claims.py
src/pharabius/schemas/claims.py
tests/test_gap_question_registry.py
docs/OPERATIONAL_CLAIMS.md                    # optional incremental update
```

Recommended schema additions:

```python
class GapItem(BaseModel):
    gap_id: str
    claim_id: str | None = None
    linked_findings: list[str] = []
    linked_work_packages: list[str] = []
    severity: Literal["blocking", "non_blocking"]
    question: str
    reason: str
    evidence_ids: list[str] = []
    recommended_owner: str | None = None
```

Recommended gap sources:

| Source | Gap type |
|---|---|
| Operational claim with `status=gap` | gap item |
| Claim requiring human validation | question item |
| Work-package precondition mentioning validation | question item |
| Missing evidence for high-priority finding | blocking gap |
| Missing locations/evidence for low-priority finding | non-blocking gap |
| Known limitation affecting implementation | blocking or non-blocking based on severity |

Recommended Markdown sections:

```markdown
# Gaps

## Blocking Gaps
## Non-Blocking Gaps
## Gaps by Finding
## Gaps by Work Package

# Questions

## Product Engineering Questions
## Architecture Questions
## Security/Compliance Questions
## Testing/Verification Questions
```

## Tests

Add tests for:

- Gap claim produces gap item.
- Human-validation claim produces question.
- Missing evidence on high-priority finding produces blocking gap.
- Missing evidence on low-priority finding produces non-blocking gap.
- Work-package validation precondition produces question.
- Gaps link to claim/finding/work package IDs.
- Markdown groups blocking and non-blocking gaps.
- Outputs are deterministic.
- No canonical artifact mutation.

## Targeted Verification

```bash
pytest tests/test_gap_question_registry.py
```

## Expected Behavior

Pharabius emits clear gap and question registries:

```text
.ai-debt/claims/gaps.md
.ai-debt/claims/questions.md
```

Example gap:

```markdown
### GAP-0001 — Blocking

- Question: Which authorization behavior must be preserved during remediation?
- Linked claim: CLM-000004
- Linked finding: TD-SEC-001
- Linked work package: WP-001
- Reason: Finding is security-sensitive and implementation semantics cannot be safely inferred from repository evidence alone.
```

## Acceptance Criteria

- Gap and question artifacts are generated.
- Blocking vs non-blocking gaps are distinguished.
- Gaps and questions are linked to traceable IDs where possible.
- High-risk uncertainty is not buried in limitations.
- No canonical artifacts are mutated.
- No scoring behavior changes.
- All 7 local gates pass.

## Guardrails

- Do not modify production/source code.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external APIs.
- Do not mutate `debt-register.json`, `evidence.json`, work packages, ticket drafts, export bundles, or portfolio outputs.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence risk scores.
- Do not convert inferred claims into confirmed claims without direct evidence.
- Do not hide gaps inside generic limitations; gaps must remain explicit.
- Treat operational claims as handoff/specification artifacts, not implementation authority.


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
