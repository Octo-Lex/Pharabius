# W41-S06 — Docs, Tests, Changelog, Release

**Wave:** Wave 41 — v1.6.0 Ticket Draft Export  
**Slice:** W41-S06  
**Title:** Docs, tests, changelog, release  
**Risk:** Low  
**Impact class:** Finalization, documentation, versioning, release readiness  
**Release target:** v1.6.0  
**Implementation unit:** Final wave closure slice

---

## 1. Scope

Finalize Wave 41 for v1.6.0 release after W41-S01 through W41-S05 are complete.

### In scope

- Bump version to `1.6.0`.
- Update changelog.
- Update roadmap.
- Update known limitations.
- Add or update ticket draft documentation.
- Update CLI docs/help references.
- Ensure all tests and quality gates pass.
- Prepare release notes.

### Out of scope

- No new ticket draft behavior.
- No new schema fields unless required to document existing behavior.
- No threshold/scoring changes.
- No external tracker integrations.
- No autonomous remediation features.
- No canonical artifact changes beyond examples/docs.

---

## 2. Goals

1. Make v1.6.0 understandable and usable by Product Engineering Teams.
2. Communicate local-only ticket draft behavior clearly.
3. Preserve the no-external-writes boundary.
4. Lock down all tests and release gates.
5. Close Wave 41 cleanly without scope creep.

---

## 3. Documentation plan

### 3.1 Add `docs/TICKET_DRAFTS.md`

Recommended structure:

```markdown
# Ticket Draft Export

## Purpose
Pharabius can generate repository-local ticket drafts from work packages and linked debt findings.

## Safety model
- Local files only
- No external tickets created
- No API calls
- No assignment or sprint planning
- No remediation or code modification

## Command
```bash
ai-debt tickets
```

## Output files
- `.ai-debt/ticket-drafts/TICKET-WP-001.md`
- `.ai-debt/ticket-drafts/ticket-drafts.json`
- `.ai-debt/reports/ticket-draft-summary.md`

## PET review sidecar behavior
...

## Deferred work
...

## Copy-paste workflow
...

## Known limitations
...
```

### 3.2 Update `README.md` or command docs

Add a short usage block:

```bash
ai-debt plan
ai-debt review   # if applicable in current workflow
ai-debt tickets
```

Do not imply external ticket creation.

### 3.3 Update `CHANGELOG.md`

Add:

```markdown
## v1.6.0 — Ticket Draft Export

### Added
- Added repository-local ticket draft export via `ai-debt tickets`.
- Added Markdown ticket drafts under `.ai-debt/ticket-drafts/`.
- Added machine-readable `ticket-drafts.json` index.
- Added ticket draft summary report.
- Added review-aware filtering for deferred and false-positive findings.

### Safety
- No external tickets are created.
- No issue tracker APIs are called.
- Canonical debt register and work packages are not mutated.
```

### 3.4 Update `ROADMAP.md`

Mark v1.6.0 as released when release is complete. Keep external tracker integrations in a future opt-in connector wave.

### 3.5 Update `KNOWN_LIMITATIONS.md`

Add limitations:

- Ticket drafts are local files only.
- No Jira/Linear/GitHub/Azure DevOps API writes in v1.6.0.
- Markdown work package parsing is conservative.
- Ticket draft content should be reviewed by Product Engineering Teams before being copied into trackers.
- Review sidecar decisions affect ticket draft inclusion only, not scoring.

---

## 4. Versioning patch set

### 4.1 Update version

Update:

```text
pyproject.toml
```

Expected:

```text
1.6.0
```

Also update any project-specific version files if present.

### 4.2 Build validation

```bash
python -m build
```

Expected build outputs should include:

```text
pharabius-1.6.0
```

---

## 5. Test consolidation

Expected ticket-related test groups after Wave 41:

```text
tests/test_ticket_draft_schema.py
tests/test_ticket_markdown_generation.py
tests/test_ticket_draft_index.py
tests/test_ticket_review_filtering.py
tests/test_cli_tickets.py
```

Expected release conditions:

- All existing tests pass.
- New ticket draft tests pass.
- Coverage does not materially regress.
- CLI help tests are updated if the project tracks command count.
- Field validation still passes.

---

## 6. Verification commands

Run all release gates:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Optional smoke test after build/install:

```bash
ai-debt --version
ai-debt tickets --help
ai-debt tickets --force
```

Expected version:

```text
1.6.0
```

---

## 7. Expected behavior

After this slice:

- Version reports `1.6.0`.
- Build artifacts are for `1.6.0`.
- Documentation explains ticket drafts clearly.
- Release notes explain local-only behavior.
- Known limitations are explicit.
- All tests and gates pass.
- Wave 41 is ready for PR, CI, merge, tag, and release.

---

## 8. Release acceptance criteria

- [ ] `pyproject.toml` version is `1.6.0`.
- [ ] Build outputs include `pharabius-1.6.0`.
- [ ] `CHANGELOG.md` includes v1.6.0.
- [ ] `ROADMAP.md` reflects v1.6.0 completion or readiness.
- [ ] `KNOWN_LIMITATIONS.md` includes ticket draft limitations.
- [ ] `docs/TICKET_DRAFTS.md` exists.
- [ ] `ai-debt tickets --help` is documented.
- [ ] Full test suite passes.
- [ ] All seven gates pass.
- [ ] CI is green.
- [ ] No external tracker/API behavior exists.
- [ ] No autonomous remediation behavior exists.

---

## 9. Suggested PR and release text

### PR title

```text
v1.6.0: Add repository-local ticket draft export
```

### Release headline

```text
Pharabius v1.6.0 adds repository-local ticket draft export for Product Engineering Teams, generating Markdown drafts and a JSON index without creating external tickets.
```

### Release summary

```markdown
v1.6.0 improves Product Engineering Team actionability by generating local ticket drafts from Pharabius work packages and linked debt findings. The new `ai-debt tickets` command writes Markdown drafts, a machine-readable JSON index, and a summary report under `.ai-debt/`. PET review sidecar decisions are respected so false-positive and deferred work are not drafted by default.

This release does not call Jira, Linear, GitHub Issues, Azure DevOps, or any external issue tracker. It does not mutate canonical debt findings, work packages, scores, or review sidecars.
```
