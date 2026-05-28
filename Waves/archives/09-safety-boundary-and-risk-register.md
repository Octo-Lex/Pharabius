# Pharabius v2.0 — Local CI Quality Gate

Product thesis: Pharabius v2.0 enters developer workflow through a local, deterministic CI quality gate without becoming infrastructure.

Core boundary:
- No server
- No database requirement
- No dashboard service
- No remote repository crawling
- No external API writes
- No issue creation
- No autonomous remediation
- No production code modification

Primary command target:

```bash
ai-debt gate
```

Primary outputs:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

## Safety boundary

The quality gate is enforcement-oriented but not action-oriented.

It may read Pharabius artifacts, evaluate thresholds, generate reports, return CI exit codes, and recommend next actions.

It must not modify source code, mutate canonical Pharabius artifacts, create issues, write to trackers, post PR comments, call external APIs, approve or reject business decisions, remediate code, or generate patches.

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Gate blocks teams unexpectedly | Medium | Defaults documented, warn/advisory modes available |
| Missing artifact causes false failure | Medium | Clear missing-required vs missing-optional semantics |
| Thresholds too strict | Medium | Configurable thresholds and CLI overrides |
| Gate confused with policy engine | Low-medium | Docs state v2.0 has minimal gate config only |
| Gate confused with security scanner | Medium | Docs clarify Pharabius reports debt/risk, not exploit proof |
| Gate output treated as business approval | Medium | Reports say PET/security review remains required |
| CI examples imply external writes | High | Examples must not include API tokens or tracker calls |
| Canonical artifacts accidentally mutated | High | Hash-based mutation tests |
| Blocking gaps ignored in warn mode | Medium | Result remains fail even if exit code is 0 in warn/advisory |
| Users bypass analysis freshness | Medium | Report includes generated_at and source artifact timestamps when feasible |

## Required report disclaimer

```text
The quality gate evaluates local Pharabius artifacts. It does not modify code, create issues, call external services, or replace Product Engineering Team review.
```

## Acceptance criteria

- Safety boundary appears in docs and report.
- CI examples preserve no-external-write behavior.
- Tests assert no canonical mutation.
- Gate result and exit behavior are clearly distinguished.
