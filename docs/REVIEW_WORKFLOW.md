# Review Workflow — Pharabius v1.4.0

## Overview

The review decision sidecar lets Product Engineering Teams record structured
decisions about each finding. Review decisions are **non-canonical workflow
state** — they never modify `debt-register.json` or affect finding generation.

## Quick Start

```bash
# Run analysis first
ai-debt init -r .
ai-debt run -r .
ai-debt analyze --no-ai -r .

# Initialize review sidecar
ai-debt review --init -r .

# Check status (read-only)
ai-debt review --status -r .

# Edit decisions manually
# Open .ai-debt/review/decisions.json in your editor

# Validate decisions
ai-debt review --validate -r .
```

## Artifact Location

```
.ai-debt/review/
  decisions.json    # structured decision records
```

## Decision Schema

Each decision in `decisions.json` has:

| Field | Required | Description |
|---|---|---|
| `finding_id` | Yes | Must match a finding in debt-register.json |
| `status` | Yes | One of 7 allowed values (see below) |
| `reviewed_at` | Yes | ISO 8601 datetime |
| `reviewer` | No | Team or individual name |
| `rationale` | No | Why this decision was made |
| `ticket_url` | No | External tracking link |
| `owner_area` | No | Responsible team/area |
| `target_release` | No | Target release or sprint |
| `notes` | No | Free-form notes |

## Allowed Statuses

| Status | Meaning |
|---|---|
| `accepted` | Finding acknowledged, will remediate |
| `rejected` | Finding not applicable to this repository |
| `deferred` | Acknowledged but not prioritized now |
| `needs-investigation` | Insufficient evidence to decide |
| `duplicate` | Already covered by another finding |
| `already-fixed` | Fixed since scan |
| `risk-accepted` | Acknowledged risk, consciously accepted |

## Example Decision

```json
{
  "finding_id": "TD-DEP-001",
  "status": "accepted",
  "reviewed_at": "2026-05-20T12:00:00Z",
  "reviewer": "platform-team",
  "rationale": "Lockfile required for reproducible builds.",
  "ticket_url": "https://github.com/org/repo/issues/123",
  "owner_area": "platform",
  "target_release": "v2.1",
  "notes": ""
}
```

## Validation Behavior

| Scenario | Behavior |
|---|---|
| Valid decision | Accepted |
| Unknown finding ID | **Warning** (finding may have been removed) |
| Duplicate finding ID | First kept, subsequent warned |
| Invalid status | **Hard error** (validation fails) |
| Missing required field | **Hard error** (validation fails) |
| Missing debt-register.json | **Error** (run analysis first) |
| Missing review sidecar | **Error** for validate; **graceful** for status |
| Stale decision (finding gone) | Reported in status and validate |

## What Review Decisions Can Do

- Track PET team decisions about each finding
- Summarize acceptance/deferral/rejection rates
- Record rationale and ticket references
- Detect stale decisions when findings change

## What Review Decisions Cannot Do

- Modify `debt-register.json`
- Suppress findings
- Alter severity, priority, or risk scores
- Change evidence IDs or finding IDs
- Affect exports or reports
- Create tickets automatically
- Trigger remediation
- Invoke AI providers

## Manual Editing Workflow

1. Run `ai-debt review --init -r .` to create the sidecar
2. Open `.ai-debt/review/decisions.json` in your editor
3. Add decision entries for each finding
4. Run `ai-debt review --validate -r .` to check
5. Run `ai-debt review --status -r .` for summary

## Relationship to Other Features

- **Governance presets**: Review sidecar is independent of governance presets
- **AI enrichment**: Review sidecar is independent of AI sidecar
- **Work packages**: Review decisions reference the same finding IDs
- **Exports**: Review state is not included in SARIF/CSV/JSONL exports

## No Credentials

The review sidecar contains no secrets, API keys, provider credentials, or
authentication tokens. All fields are free-text workflow state.
