# Pharabius v2 External Integration Risk Model

**Status**: Planning draft  
**Date**: 2026-05-27  
**Not an implementation commitment**

This document defines risk classes, controls, and go/no-go criteria for future external integrations.

## Integration Classes

| Class | Description | Automation Level | Risk | v2 Candidate |
|---|---|---|---|---|
| **I0** | No integration, file export only | A1 | Low | ✅ (v1 current) |
| **I1** | Read-only local file import | A0 | Low | ✅ |
| **I2** | Read-only external API (repo metadata, org info) | A0 | Medium | Maybe |
| **I3** | External draft/staged object creation (no submit) | A2 | Medium-high | Maybe |
| **I4** | External write with explicit approval | A3 | High | Maybe, with controls |
| **I5** | Bidirectional sync | A3+ | Very high | Not recommended for v2.0 |
| **I6** | Autonomous external operations | A6 | Forbidden | **Forbidden** |

## v1 Current State

Pharabius v1 uses I0 exclusively:

- Export bundles are local files (CSV, YAML, JSON, Markdown)
- No API calls to external systems
- No credential storage beyond optional AI provider env var
- No tracker-specific SDKs

This remains the default. v2 integrations must be **opt-in**.

## Tracker-Specific Risk Analysis

### Jira

| Risk | Mitigation |
|---|---|
| Project permissions insufficient | Pre-flight permission check before any write |
| Field scheme mismatch | Map Pharabius fields to Jira fields explicitly; warn on unmapped |
| Issue type variance | Validate issue type exists before creation |
| Duplicate ticket creation | Search by title/source_id before creating |
| Rate limiting | Respect Jira rate limits; retry with backoff |
| Webhook side effects | Jira-side; document as user responsibility |

### Linear

| Risk | Mitigation |
|---|---|
| Team/workspace ID mismatch | Require explicit team ID in config |
| Label drift | Create labels on first use; document label mapping |
| Workflow state assumptions | Only use standard states (backlog, todo, in progress, done) |
| Priority mapping ambiguity | Conservative mapping: Critical→Urgent, High→High, etc. |

### GitHub Issues

| Risk | Mitigation |
|---|---|
| Repository write permission required | Pre-flight permission check |
| Label creation as side effect | Create labels explicitly; warn if exceeds rate limit |
| Milestone assumptions | Do not assume milestones exist |
| Duplicate issues | Search by title before creation |

### Azure DevOps

| Risk | Mitigation |
|---|---|
| Area/iteration path variance | Require explicit paths in config |
| Work item type mismatch | Validate work item type exists in target project |
| Org/project permissions | Pre-flight permission check |
| Tag semicolon syntax | Escape commas, quotes, newlines in tag values |

## Required Controls for Write-Capable Integrations (I3+)

Any integration at I3 or above must implement:

1. **Explicit opt-in**: Integration disabled by default; user must enable via config or flag
2. **Credential scope documentation**: Document minimum required permissions
3. **Dry-run mode**: Show exactly what would be created without creating it
4. **Preview artifact**: Generate a local preview file showing planned writes
5. **Action manifest**: Record all writes in a structured log
6. **Confirmation prompt**: Require user confirmation before each write batch
7. **Duplicate detection**: Check for existing items before creating
8. **Write audit log**: Record timestamp, action, target, result for every write
9. **Failure recovery**: Document what happens on partial failure
10. **Rollback guidance**: Document how to undo each write action

## Credential and Permission Model

| Requirement | Details |
|---|---|
| Storage | Credentials via environment variables only; never stored in config files |
| Scope | Minimum required permissions documented per integration |
| Rotation | No credential rotation handling; user responsibility |
| Display | Never log or display credentials; redact from all output |
| Testing | All integration tests use mock transports; no real API calls in CI |

## Failure Mode Analysis

| Failure | Detection | Recovery |
|---|---|---|
| Network timeout | Timeout error | Retry with backoff; log partial state |
| Authentication failure | 401/403 response | Halt; report to user; do not retry |
| Rate limiting | 429 response | Backoff; retry with exponential delay |
| Partial write success | Action manifest audit | Report which writes succeeded/failed; manual cleanup |
| Validation error | 400 response | Report field mismatches; halt batch |
| Permission error | 403 response | Report missing permissions; halt |

## Go/No-Go Criteria for Integration Implementation

Before implementing any external integration:

- [ ] Integration class is assigned (I0-I6)
- [ ] Automation level is assigned (A0-A6)
- [ ] Required controls are designed
- [ ] Tracker-specific risks are documented
- [ ] Credential model is defined
- [ ] Failure modes are documented
- [ ] Dry-run mode is designed
- [ ] Audit logging is designed
- [ ] v1 export bundles remain I0-safe

## Related Documents

- [Automation Boundary Model](V2_AUTOMATION_BOUNDARY_MODEL.md)
- [v2 Option Map](V2_OPTION_MAP.md)
- [v2 Product Thesis](V2_PRODUCT_THESIS.md)
