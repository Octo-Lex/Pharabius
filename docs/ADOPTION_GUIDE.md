# Pharabius Adoption Guide — For Product Engineering Teams

This guide helps Product Engineering Teams adopt Pharabius technical debt analysis
output in their workflow.

---

## First 30 Minutes

### 1. Generate the analysis (5 minutes)

```bash
cd /path/to/your/repository
ai-debt init
ai-debt scan
ai-debt analyze --no-ai
ai-debt report
ai-debt plan
```

### 2. Read the handoff summary (5 minutes)

Open `.ai-debt/handoff-summary.md`. This is your starting point.

- **Executive Summary** — how many findings, what the top risk is
- **Top Risks table** — sorted by priority, shows severity, score, effort
- **Recommended First Actions** — ordered list of what to address first

### 3. Review the debt register (10 minutes)

Open `.ai-debt/debt-register.md`.

For each finding, check:
- **Is the evidence real?** — follow the evidence ID to `evidence.json`
- **Is the severity appropriate?** — consider your team's context
- **Is the business impact accurate?** — validate inferred impact with your team

### 4. Scan work packages (10 minutes)

Open `.ai-debt/work-packages/`. Each package is a ready-to-implement unit.

Check:
- **Objective** — does it describe the right goal?
- **Recommended Engineering Approach** — is it feasible?
- **Verification Recommendations** — can you confirm the fix?
- **Risks and Cautions** — are there policy considerations?

---

## Triage Workflow

For each finding in the debt register, apply one of:

### Accept
The finding is valid and should be addressed.
→ Convert the linked work package into a sprint ticket.
→ Set a target sprint based on priority and effort.

### Reject
The finding is a false positive or does not apply.
→ Document why: "Library repo intentionally omits lockfile per policy."
→ Do not delete the finding — it provides audit trail.
→ Re-running analysis will reproduce it; document the exception.

### Defer
The finding is valid but not a current priority.
→ Note the deferral reason and revisit date.
→ Lower-priority findings can accumulate — review quarterly.

### Needs Investigation
Unclear whether this is valid.
→ Assign to a team member for evidence review.
→ Check the evidence ID in `evidence.json` for raw observation.
→ Resolve as Accept/Reject/Defer after investigation.

---

## Using Work Packages in Sprint Planning

### Convert to GitHub Issues

```markdown
## Title: [TD-DEP-001] Adopt Python lockfile strategy

### Context
Pharabius detected a dependency manifest without lockfile evidence.

### Evidence
- `pyproject.toml` — Python manifest detected
- Risk score: 15 (Medium)
- Work package: `WP-001`

### Scope
- [ ] Generate `requirements.lock` (or adopt `uv.lock` / `poetry.lock`)
- [ ] Update CI to use deterministic install
- [ ] Document lockfile policy in CONTRIBUTING.md

### Acceptance Criteria
- [ ] Lockfile exists in repository root
- [ ] CI installs from lockfile
- [ ] `ai-debt verify` shows `likely_remediated` for TD-DEP-001
```

### Convert to Jira

| Field | Value |
|---|---|
| Summary | [TD-DEP-001] Adopt Python lockfile strategy |
| Priority | Medium (matches risk score 15) |
| Labels | `tech-debt`, `td-dep` |
| Description | Copy work package content + evidence |
| Story Points | Map effort: Small=1, Medium=3, Large=5 |

---

## What NOT to Automate

Pharabius is an **analysis and planning** tool. It does not modify production code.

Do NOT:
- **Auto-apply dependency updates** — review compatibility first
- **Auto-generate CODEOWNERS** — team structure decisions need human input
- **Auto-fix CI configurations** — environment-specific considerations apply
- **Auto-resolve security findings** — risk acceptance requires human judgment
- **Blindly act on AI enrichment** — sidecar output is advisory only

The Product Engineering Team approves, implements, verifies, and owns all outcomes.

---

## Using AI Sidecars Safely

AI enrichment is **optional** and **disabled by default**.

### What AI Sidecars Do

- Add explanatory context to findings
- Suggest additional evidence to review
- Provide confidence assessment of finding validity

### What AI Sidecars Do NOT Do

- Modify the debt register
- Change findings, scores, or priorities
- Create new findings
- Alter reports or work packages
- Bypass the evidence-first rule

### Safe AI Usage

```bash
# Preview what context would be sent (no provider call)
ai-debt enrich --context-preview

# Enrich with mock provider (testing, no real AI)
ai-debt enrich --provider mock

# Enrich with real provider (requires explicit consent)
ai-debt enrich --provider openai-compatible \
  --allow-external-provider \
  --model gpt-4
```

### Review Checklist for AI Enrichment

1. Is the enrichment referencing valid evidence IDs?
2. Does it introduce claims not supported by evidence?
3. Are the limitations listed?
4. Does it preserve uncertainty language?

---

## Review Checklist

Use this checklist when reviewing `.ai-debt/` output:

- [ ] Handoff summary reviewed with team
- [ ] Each finding triaged (Accept / Reject / Defer / Investigate)
- [ ] Evidence IDs spot-checked in `evidence.json`
- [ ] Work packages reviewed for feasibility
- [ ] Business impact validated (not just inferred)
- [ ] AI enrichment (if used) reviewed for accuracy
- [ ] Findings with Low confidence flagged for manual review
- [ ] Sprint tickets created for accepted findings
- [ ] Rejection reasons documented
- [ ] Follow-up `ai-debt verify` scheduled after remediation

---

## Escalation Guide

| Finding Type | Escalate To |
|---|---|
| TD-SEC (security) | Security team review before any action |
| TD-COMP (compliance) | Legal/compliance team for keyword interpretation |
| TD-ARCH (architecture) | Architecture review board for cycle/boundary decisions |
| TD-DEP (dependency) | Platform engineering for lockfile policy |
| TD-PERF (performance) | Performance team for bottleneck confirmation |
| All others | Team lead triage |

---

## Preservation Boundaries

Pharabius preserves these boundaries by design:

- **No code modification** — Pharabius analyzes and plans; teams implement
- **Evidence-first** — every finding traces to repository evidence
- **Uncertainty language** — inferred impact is clearly marked
- **AI sidecar-only** — AI output never enters canonical artifacts
- **Explicit consent** — real providers require per-invocation approval

These boundaries are enforced in the tool's architecture, not just documentation.
