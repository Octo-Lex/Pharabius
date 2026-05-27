# Pharabius v2 Automation Boundary Model

**Status**: Planning draft  
**Date**: 2026-05-27  
**Not an implementation commitment**

This document defines automation levels, approval gates, and forbidden actions for Pharabius v2. It prevents scope drift by providing a clear boundary model.

## Automation Levels

| Level | Name | v1 | v2 Candidate | Description |
|---|---|---|---|---|
| **A0** | Read-only analysis | ✅ | ✅ | Scanning, evidence collection, report generation. No writes except `.ai-debt/` artifacts. |
| **A1** | Planning artifact generation | ✅ | ✅ | Work packages, ticket drafts, export bundles, portfolio summaries. Writes local files only. |
| **A2** | External draft creation | ❌ | Maybe | Generate external issue drafts in tracker format. Store locally. No submission. |
| **A3** | External write with approval | ❌ | Maybe | Create issues/tickets in external systems after explicit human approval and preview. |
| **A4** | Code patch proposal | ❌ | Maybe later | Generate a code patch as an artifact (`.patch` file or diff). No application. Human reviews and applies. |
| **A5** | PR creation with approval | ❌ | High-risk v2+ | Create pull request after human approval of patch preview. Requires strict governance. |
| **A6** | Autonomous remediation | ❌ | **Forbidden** | Automatic code modification without human review. Not recommended for Pharabius. |

## Approval Requirements by Level

| Level | Human Preview | Human Approval | Audit Log | Rollback | Idempotency |
|---|---|---|---|---|---|
| A0 | N/A | N/A | Optional | N/A | N/A |
| A1 | N/A | N/A | Optional | Delete `.ai-debt/` | N/A |
| A2 | Required | N/A | Required | Delete draft | N/A |
| A3 | Required | **Explicit per-action** | **Required** | Manual delete in tracker | Recommended |
| A4 | Required | **Explicit per-patch** | **Required** | Delete patch file | N/A |
| A5 | Required | **Explicit per-PR** | **Required** | Close/delete PR | Required |

## Required Controls for A3+

Any v2 feature at automation level A3 or above must implement:

1. **Explicit human approval**: No action without user confirmation
2. **Dry-run preview**: Show exactly what will happen before it happens
3. **Auditable action log**: Record who approved what, when, and why
4. **Idempotency key**: Prevent duplicate actions on retry
5. **Rollback/undo guidance**: Document how to reverse the action
6. **Permission scoping**: Minimal permissions for the action
7. **No hidden network action**: All network calls visible to user
8. **Visible diff/action summary**: Clear summary before execution

## Forbidden Actions

The following actions are **forbidden** in Pharabius v2 regardless of automation level:

- Silently modifying production code
- Silently creating external issues or tickets
- Changing authentication or authorization logic
- Automatically applying dependency upgrades
- Automatically changing infrastructure or deployment configuration
- Making risk acceptance decisions on behalf of users
- Bypassing human approval for high-risk actions
- Executing code modification without generating a previewable diff

## v1 Boundary Preservation

v1 automation levels (A0, A1) remain unchanged in v2:

- v1 commands continue to operate at A0/A1
- v1 artifacts remain the primary output
- v1 safety boundaries are not weakened
- v1 schema compatibility is preserved

## Classification Guide

To classify any v2 feature:

1. Does it read data? → A0
2. Does it write local files? → A1
3. Does it generate external-format drafts? → A2
4. Does it write to external systems? → A3 (requires approval controls)
5. Does it generate code patches? → A4 (requires approval controls)
6. Does it create pull requests? → A5 (requires full governance)
7. Does it modify code without review? → A6 (forbidden)

## Example Classifications

| Feature | Level | Controls Required |
|---|---|---|
| `ai-debt scan` | A0 | None (v1) |
| `ai-debt tickets` | A1 | None (v1) |
| `ai-debt export --tracker jira` | A1 | None (v1, local files) |
| `ai-debt submit --tracker jira` | A3 | Approval, preview, audit, rollback |
| `ai-debt suggest-patch` | A4 | Preview, approval, audit |
| `ai-debt create-pr` | A5 | Full governance stack |

## Related Documents

- [v2 Product Thesis](V2_PRODUCT_THESIS.md)
- [v2 Option Map](V2_OPTION_MAP.md)
- [v1 Safety Boundaries](../SAFETY_BOUNDARIES.md)
- [v1 Stability Contract](../V1_STABILITY_CONTRACT.md)
