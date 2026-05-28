# v2.3.0 — Human Validation Workflow

Goal: Turn findings, claims, gaps, readiness, and work packages into a hosted human-review workflow with review states, comments, audit history, and sign-off, without external writes or remediation.

Release posture: major hosted-platform workflow release. This release adds human review state and auditability inside the Pharabius platform, but must not create external issues, post PR comments, modify repositories, or perform remediation.

Core boundaries:
- No OAuth / RBAC
- No policy engine
- No tracker writes
- No PR comments
- No GitHub Checks API
- No external integrations
- No autonomous remediation
- No source-code modification
- No approval automation
- No replacement for Product Engineering Team responsibility


## Pack contents

| Slice | File |
|---|---|
| S01 | `S01-review-data-model-state-machine.md` |
| S02 | `S02-review-apis-findings-claims-gaps-readiness.md` |
| S03 | `S03-claims-gaps-review-ui.md` |
| S04 | `S04-finding-work-package-review-ui.md` |
| S05 | `S05-audit-history-review-summary.md` |
| S06 | `S06-docs-tests-changelog-release.md` |

## Recommended branch

```text
roadmap/v2.3.0-human-validation-workflow
```

## Recommended release headline

```text
Pharabius v2.3.0 adds hosted human validation workflows for findings, claims, gaps, readiness, and work packages with review states, comments, audit history, and sign-off while preserving the no-external-write and no-remediation boundary.
```

## Product definition

v2.3.0 should prove this workflow:

```text
Upload .ai-debt bundle
→ browse findings / claims / gaps / readiness
→ mark items as accepted, rejected, needs clarification, blocked, or validated
→ add reviewer comments
→ view audit history
→ generate review summary
→ preserve canonical artifact data unchanged
```

## Review state model

Recommended review statuses:

```text
unreviewed
accepted
needs_clarification
rejected
blocked
validated
```

Recommended review targets:

```text
finding
claim
gap
readiness
work_package
```

## Non-goals

```text
OAuth
RBAC
policy engine
tracker writes
PR comments
external integrations
automatic approval
autonomous remediation
source-code modification
```
