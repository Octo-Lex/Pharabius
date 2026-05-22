# W41-S01 — Ticket Draft Artifact Contract and Schema

**Wave:** Wave 41 — v1.6.0 Ticket Draft Export  
**Slice:** W41-S01  
**Title:** Ticket draft artifact contract and schema  
**Risk:** Medium  
**Impact class:** Sidecar artifact contract and schema only  
**Release target:** v1.6.0  
**Implementation unit:** Atomic slice; may be merged independently

---

## 1. Scope

Define the repository-local ticket draft artifact contract: paths, schema, identifier rules, allowed values, and safety invariants. This slice defines the contract only; it does not generate ticket drafts or add a CLI command.

### In scope

- Define `.ai-debt/ticket-drafts/` as the ticket draft output directory.
- Define Pydantic models or JSON schema for ticket drafts and the ticket draft index.
- Define deterministic ticket ID and filename rules.
- Define allowed status, source, and review-decision values.
- Add example JSON and Markdown fixtures.
- Add schema and ID helper tests.

### Out of scope

- No Markdown generation from real work packages.
- No JSON index generation from real artifacts.
- No CLI command.
- No external tracker integration.
- No mutation of debt register, work packages, scoring, governance, or review sidecar.
- No review-sidecar filtering yet.

---

## 2. Goals

1. Establish a stable sidecar contract for local ticket drafts.
2. Make ticket drafts both machine-readable and human-readable.
3. Preserve the v1 planning boundary: no external writes and no autonomous remediation.
4. Keep generated ticket identifiers deterministic and diffable.
5. Prepare later slices for Markdown generation, JSON indexing, review filtering, and CLI exposure.

---

## 3. Artifact contract

### Output directory

```text
.ai-debt/ticket-drafts/
```

### Full Wave 41 target output

```text
.ai-debt/ticket-drafts/ticket-drafts.json
.ai-debt/ticket-drafts/TICKET-WP-001.md
.ai-debt/ticket-drafts/TICKET-WP-002.md
.ai-debt/reports/ticket-draft-summary.md
```

All ticket draft artifacts are sidecars. They are generated from canonical artifacts but do not become canonical analyzer truth.

---

## 4. Schema design

### Ticket draft index

```json
{
  "schema_version": "1.0",
  "tool_version": "1.6.0-dev",
  "generated_at": "2026-05-22T00:00:00Z",
  "repository": "example-repo",
  "commit": "abc1234",
  "branch": "main",
  "source_artifacts": {
    "debt_register": ".ai-debt/debt-register.json",
    "work_packages_dir": ".ai-debt/work-packages",
    "review_sidecar": null
  },
  "summary": {
    "total_drafts": 1,
    "included_drafts": 1,
    "excluded_by_review": 0,
    "deferred": 0,
    "false_positive": 0,
    "unreviewed": 1
  },
  "drafts": []
}
```

### Ticket draft item

```json
{
  "ticket_id": "TICKET-WP-001",
  "title": "Reduce risk in authentication boundary",
  "source_type": "work_package",
  "source_id": "WP-001",
  "artifact_path": ".ai-debt/ticket-drafts/TICKET-WP-001.md",
  "linked_debt_items": ["TD-ARCH-001", "TD-TEST-002"],
  "categories": ["TD-ARCH", "TD-TEST"],
  "priority": "High",
  "risk_score": 24,
  "review_decision": "not_reviewed",
  "status": "draft",
  "labels": ["technical-debt", "pharabius", "TD-ARCH"],
  "external_system": null,
  "external_id": null,
  "content_hash": "sha256:...",
  "body_markdown": "# Ticket: Reduce risk in authentication boundary\n..."
}
```

### Allowed values

```text
source_type: work_package | finding
status: draft | excluded
review_decision: accepted | needs_review | deferred | false_positive | rejected | not_reviewed | mixed
external_system: null only in v1.6.0
external_id: null only in v1.6.0
```

`finding` source type is reserved for future fallback use. v1.6.0 should primarily generate from work packages.

---

## 5. Deterministic ID and filename rules

```text
WP-001      → TICKET-WP-001
WP-002      → TICKET-WP-002
TD-ARCH-001 → TICKET-TD-ARCH-001  # reserved fallback form
```

Filename rule:

```text
{ticket_id}.md
```

Examples:

```text
.ai-debt/ticket-drafts/TICKET-WP-001.md
.ai-debt/ticket-drafts/TICKET-WP-002.md
```

IDs must not depend on wall-clock time, draft count, OS ordering, or review state.

---

## 6. Patch set

### 6.1 Add ticket schema models

Recommended file:

```text
src/pharabius/schemas/tickets.py
```

Recommended models:

```python
class TicketDraftSourceArtifacts(BaseModel):
    debt_register: str
    work_packages_dir: str
    review_sidecar: str | None = None

class TicketDraftSummary(BaseModel):
    total_drafts: int = 0
    included_drafts: int = 0
    excluded_by_review: int = 0
    deferred: int = 0
    false_positive: int = 0
    unreviewed: int = 0

class TicketDraft(BaseModel):
    ticket_id: str
    title: str
    source_type: Literal["work_package", "finding"]
    source_id: str
    artifact_path: str
    linked_debt_items: list[str]
    categories: list[str] = []
    priority: str | None = None
    risk_score: int | None = None
    review_decision: str = "not_reviewed"
    status: Literal["draft", "excluded"] = "draft"
    labels: list[str] = []
    external_system: None = None
    external_id: None = None
    content_hash: str | None = None
    body_markdown: str = ""

class TicketDraftIndex(BaseModel):
    schema_version: str = "1.0"
    tool_version: str
    generated_at: str
    repository: str | None = None
    commit: str | None = None
    branch: str | None = None
    source_artifacts: TicketDraftSourceArtifacts
    summary: TicketDraftSummary
    drafts: list[TicketDraft]
```

Use the project’s current Pydantic version and style.

### 6.2 Add deterministic ID helpers

Recommended file:

```text
src/pharabius/core/tickets.py
```

Initial pure helpers:

```python
def ticket_id_for_work_package(work_package_id: str) -> str:
    return f"TICKET-{work_package_id}"

def ticket_filename(ticket_id: str) -> str:
    return f"{ticket_id}.md"
```

### 6.3 Add examples

Recommended files:

```text
docs/examples/ticket-drafts.example.json
docs/examples/ticket-draft.example.md
```

The examples must state that the draft is local only, not sent to any tracker, and has no external ticket ID.

---

## 7. Tests

Recommended file:

```text
tests/test_ticket_draft_schema.py
```

Test cases:

1. `TicketDraftIndex` validates a minimal valid index.
2. `TicketDraft` validates a minimal valid draft.
3. External system and external ID are always `None` in v1.6.0.
4. `WP-001` maps to `TICKET-WP-001`.
5. `TICKET-WP-001` maps to `TICKET-WP-001.md`.
6. Draft status accepts only `draft` and `excluded`.
7. Review decision accepts documented values.
8. Example JSON parses and validates.
9. Generated IDs are deterministic across repeated calls.

---

## 8. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest tests/test_ticket_draft_schema.py
pytest
python -m build
```

---

## 9. Expected behavior

After this slice:

- Ticket draft schema models exist.
- Ticket draft examples exist.
- Ticket ID rules are deterministic.
- No generation behavior exists yet.
- No CLI command exists yet.
- No canonical artifact changes occur.

---

## 10. Acceptance criteria

- [ ] Ticket draft schema/model exists.
- [ ] Ticket draft index and item models validate expected fields.
- [ ] Deterministic ticket ID helper exists and is tested.
- [ ] Example JSON validates.
- [ ] External integration fields are constrained to `null` for v1.6.0.
- [ ] Tests pass.
- [ ] No CLI behavior changes.
- [ ] No canonical artifact mutation.
- [ ] No network or external tracker integration.
