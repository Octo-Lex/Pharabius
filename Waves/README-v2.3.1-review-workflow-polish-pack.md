# v2.3.1 — Review Workflow Polish & Evidence Linking

Goal: Improve finding-review usability by surfacing review filters, audit details, evidence links, decision completeness, and review summary clarity without expanding into claims/gaps/readiness review.

Release posture: patch release for the hosted finding-review workflow.

Core boundaries:
- No claim review, gap closure tracking, readiness sign-off, or work-package review expansion
- No OAuth / RBAC
- No policy engine
- No tracker writes, PR comments, notifications, or webhooks
- No autonomous remediation or source-code modification
- Review decisions remain hosted workflow state, not canonical analyzer truth

Guardrails:
- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate canonical finding records.
- Do not change finding severity, risk score, evidence, category, or source content.
- Preserve soft-delete and audit history from v2.3.0.
- Keep the scope limited to finding-review usability.


## Pack contents

| Slice | File |
|---|---|
| S01 | `S01-review-filters-undecided-decided-views.md` |
| S02 | `S02-evidence-finding-context-review-modal.md` |
| S03 | `S03-review-audit-timeline-readability.md` |
| S04 | `S04-review-completeness-summary-metrics.md` |
| S05 | `S05-review-export-report-documentation.md` |
| S06 | `S06-docs-tests-changelog-release.md` |

## Recommended branch

```text
roadmap/v2.3.1-review-workflow-polish
```

## Recommended release headline

```text
Pharabius v2.3.1 improves hosted finding-review usability with review filters, evidence context, clearer audit timelines, completeness metrics, and review reporting guidance.
```

## Product definition

```text
Open repository findings
→ filter undecided/decided findings
→ open review modal
→ see finding context and evidence references
→ record or update decision
→ understand audit history
→ see review completeness summary
→ export or document review status
```
