# W41-S04 — Respect PET Review Sidecar Decisions

**Wave:** Wave 41 — v1.6.0 Ticket Draft Export  
**Slice:** W41-S04  
**Title:** Respect PET review sidecar decisions  
**Risk:** Medium  
**Impact class:** Sidecar selection/filtering logic only  
**Release target:** v1.6.0  
**Implementation unit:** Atomic slice; may be merged independently after W41-S01–S03

---

## 1. Scope

Apply existing Product Engineering Team review sidecar decisions when generating local ticket drafts.

Ticket generation may respect review workflow state, but review decisions must never influence risk scores, priority bands, scoring provenance, debt finding IDs, evidence IDs, or canonical findings.

### In scope

- Load the existing PET review sidecar using the project’s current artifact path and schema.
- Map review decisions to linked debt findings.
- Include accepted, needs-review, and unreviewed findings by default.
- Exclude false-positive and rejected findings by default.
- Exclude deferred-only work packages by default, unless `include_deferred=True` is used.
- Record excluded counts in `ticket-drafts.json` summary.
- Add review metadata to each draft.
- Add tests for all decision states and mixed work packages.

### Out of scope

- No new review sidecar schema.
- No review sidecar mutation.
- No scoring changes.
- No canonical debt register mutation.
- No CLI options yet; CLI comes in W41-S05.
- No external issue tracker behavior.

---

## 2. Goals

1. Prevent false-positive findings from becoming ticket drafts by default.
2. Keep deferred work out of the default implementation queue unless explicitly requested.
3. Preserve PET review decisions as workflow state, not analyzer truth.
4. Make generated ticket drafts transparent about review status.
5. Keep review behavior deterministic and testable.

---

## 3. Decision behavior

### Finding-level decisions

| Review decision | Default ticket behavior |
|---|---|
| `accepted` | Include |
| `needs_review` | Include and mark as needs review |
| `not_reviewed` / missing sidecar | Include and mark as unreviewed |
| `deferred` | Exclude by default; include only with `include_deferred=True` |
| `false_positive` | Exclude |
| `rejected` | Exclude |

Use the project’s actual review decision enum names. If the implementation uses different canonical values, map them into these semantic buckets.

### Work-package-level behavior

| Linked finding decisions | Default behavior |
|---|---|
| All accepted / needs_review / not_reviewed | Include |
| All deferred | Exclude by default |
| All false_positive / rejected | Exclude |
| Mixed include + deferred | Include, mark deferred linked items separately |
| Mixed include + false_positive/rejected | Include, but exclude rejected/false-positive linked items from recommended scope |
| Missing review sidecar | Include all, mark `not_reviewed` |

### Draft metadata

For included drafts, add optional metadata:

```json
"review_decision": "mixed",
"review_summary": {
  "accepted": 1,
  "needs_review": 0,
  "deferred": 1,
  "false_positive": 0,
  "rejected": 0,
  "not_reviewed": 0
},
"excluded_linked_debt_items": []
```

If W41-S01 schema needs extension, add backward-compatible optional fields:

```python
review_summary: dict[str, int] = Field(default_factory=dict)
excluded_linked_debt_items: list[str] = Field(default_factory=list)
```

---

## 4. Patch set

### 4.1 Add review loader adapter

Recommended location:

```text
src/pharabius/core/tickets.py
```

or reuse/import the existing review module if one already exists.

```python
def load_review_decisions(workspace: Path) -> dict[str, str]:
    """Return finding_id -> review_decision using the existing review sidecar if present."""
```

Behavior:

- If no review sidecar exists, return `{}`.
- If sidecar exists but is invalid, follow current Pharabius sidecar error conventions.
- Do not create or modify review sidecar files.

### 4.2 Add filtering policy

```python
@dataclass(frozen=True)
class TicketReviewPolicy:
    include_deferred: bool = False
    include_false_positives: bool = False  # default must remain False
```

Add decision function:

```python
def classify_work_package_for_ticketing(
    linked_debt_items: list[str],
    review_decisions: dict[str, str],
    policy: TicketReviewPolicy,
) -> TicketReviewClassification:
    ...
```

### 4.3 Apply filtering in generation

Extend generation APIs:

```python
def generate_ticket_markdown_drafts(..., include_deferred: bool = False) -> list[TicketDraft]:
    ...
```

Update JSON index summary counts accordingly.

### 4.4 Update Markdown template

Add:

```markdown
## PET Review Status

- Overall decision: Mixed
- Included linked findings: TD-ARCH-001
- Deferred linked findings: TD-TEST-002
- Excluded linked findings: None
```

If no review sidecar exists:

```markdown
## PET Review Status

No PET review sidecar was found. This draft is marked as not reviewed.
```

### 4.5 Update summary report

Add:

```markdown
## Review Decision Summary

| Decision | Count |
|---|---:|
| Accepted | 2 |
| Needs review | 1 |
| Deferred | 1 |
| False positive | 0 |
| Rejected | 0 |
| Not reviewed | 3 |
```

---

## 5. Tests

Recommended file:

```text
tests/test_ticket_review_filtering.py
```

Test cases:

1. No review sidecar includes all work packages as `not_reviewed`.
2. Accepted finding is included.
3. Needs-review finding is included and marked.
4. Deferred-only work package is excluded by default.
5. Deferred-only work package is included with `include_deferred=True`.
6. False-positive-only work package is excluded.
7. Rejected-only work package is excluded.
8. Mixed accepted + deferred work package is included with deferred item marked.
9. Mixed accepted + false-positive work package is included, but false-positive linked item is excluded from recommended scope.
10. Review sidecar does not change risk scores.
11. Review sidecar does not mutate debt register.
12. Review sidecar does not mutate work packages.
13. Summary counts include excluded-by-review totals.
14. JSON index includes review metadata.
15. Markdown includes PET review status section.

---

## 6. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest tests/test_ticket_review_filtering.py
pytest tests/test_ticket_draft_schema.py tests/test_ticket_markdown_generation.py tests/test_ticket_draft_index.py
pytest
python scripts/validate_repo.py .
```

Manual smoke test:

```bash
python - <<'PY'
from pathlib import Path
from pharabius.core.tickets import generate_ticket_markdown_drafts

workspace = Path('.ai-debt')
print('default:')
print([d.ticket_id for d in generate_ticket_markdown_drafts(workspace)])
print('include deferred:')
print([d.ticket_id for d in generate_ticket_markdown_drafts(workspace, include_deferred=True)])
PY
```

---

## 7. Expected behavior

After this slice:

- Ticket generation respects PET review sidecar decisions.
- False-positive and rejected findings are excluded by default.
- Deferred-only work is excluded by default.
- Deferred work can be included through internal API option.
- Review decisions appear in Markdown and JSON outputs.
- Review decisions do not affect canonical scoring or findings.
- No CLI option is exposed yet.
- No external APIs are called.

---

## 8. Acceptance criteria

- [ ] Existing review sidecar is loaded without changing its schema or path.
- [ ] Missing review sidecar degrades safely to `not_reviewed`.
- [ ] False-positive/rejected findings are not drafted by default.
- [ ] Deferred-only work packages are excluded by default.
- [ ] `include_deferred=True` includes deferred-only work packages.
- [ ] Mixed decision behavior is tested and deterministic.
- [ ] JSON index includes review metadata and counts.
- [ ] Markdown drafts include PET review status.
- [ ] Tests prove review decisions do not influence risk scores.
- [ ] No canonical artifacts are mutated.
