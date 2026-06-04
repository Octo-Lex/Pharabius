# Public Sync Notes — v2.5.0 → v3.0.0

> **Date:** 2026-06-04

## What Happened

Pharabius had two parallel release streams after v2.5.0:

1. **Public releases** on GitHub: v0.1.0 through v2.5.0 (53 tags)
2. **Internal development waves**: v3.0.0 through v3.26.0 (local-only tags, never pushed)

The internal waves represent 24 commits of continued development that was not published to GitHub.

## Why v3.0.0 (Not v2.6.0)

The jump from v2.5.0 to v3.0.0 reflects:

- **Signal governance model** — 10 families, 29 adapters, formal invariants and diagnostics
- **Governance export** — Machine-readable schema v1.0 with JSON/JSONL output
- **Quality metrics** — GQM-001 through GQM-005, read-only descriptive analytics
- **Trend computation** — Cross-run governance quality trend analysis
- **Contract freeze** — v3 family/adapter counts (10/29) are v3 contract boundaries
- **Platform surface** — FastAPI backend with 30 endpoints, React frontend with 8 views

This is a major version because it establishes a governance contract that downstream consumers can rely on. See `GOVERNANCE_CONTRACT.md` for the frozen v3 contract.

## What Was Not Published

The internal wave tags (v3.1.0 through v3.26.0) remain local-only. They are recorded in `internal-v3-local-tags-before-public-sync.txt` for auditability. Each wave corresponds to a specific governance arc milestone:

| Wave | Theme | Tests Added |
|---|---|---|
| v3.16.0 | Dependency Health signals | +50 |
| v3.17.0 | Security Exposure signals | +49 |
| v3.18.0 | Architecture Risk signals | +43 |
| v3.19.0 | Configuration/Environment signals | +59 |
| v3.20.0 | Observability signals | +63 |
| v3.21.0 | Governance Audit | +57 |
| v3.22.0 | Reporter UX | +32 |
| v3.23.0 | Quality Metrics | +29 |
| v3.24.0 | Trend Metrics | +33 |
| v3.25.0 | Governance Export | +36 |
| v3.26.0 | Contract Freeze | +52 |

## Tag Policy

- Only `v3.0.0` is pushed to GitHub
- Internal wave tags are NOT published
- Future public releases continue from v3.0.0

## Validation

- CLI tests: 2,970 passed, 7 skipped
- Platform backend tests: 276 passed, 5 skipped
- Frontend: not validated in this release
- Source formatting: ruff format applied to all governance arc files
