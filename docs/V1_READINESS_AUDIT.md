# V1 Readiness Audit — v0.11.0

**Date:** 2026-05-19
**Version:** v0.11.0
**Status:** Audit complete

## Executive Summary

Pharabius v0.11.0 adds minimal config runtime to the v1 readiness baseline. Config.yaml
is now read by commands (`analysis.exclude_paths` and `analysis.max_file_size_kb` are
authoritative). Missing/malformed config produces safe defaults with appropriate warnings.
No credentials, model selection, or provider consent are stored in config. Provider safety
boundaries are preserved.

## 1. Config Decision

**Status:** Implemented and narrow.

`ai-debt init` creates `.ai-debt/config.yaml` with safe defaults:
- `ai.enabled: false` — matches CLI default
- `ai.provider: "disabled"` — matches `--provider disabled` default
- No `model: "auto"` — model must be explicitly set
- No secrets, API keys, or credentials

Commands now read config for:
- `analysis.exclude_paths` — supplements hardcoded exclusions
- `analysis.max_file_size_kb` — file size threshold

CLI flags always override config values. Malformed config produces warnings and uses
safe defaults. Unknown keys produce warnings and are ignored.

Config does NOT store credentials, model selection, or provider consent. The
`ai.provider` field is parsed but does NOT enable real provider calls without
explicit CLI `--provider` and `--allow-external-provider` flags.

## 2. Risk Scoring Audit

**Status:** Structurally complete, two factors deferred.

The `RISK_SCORE_TEMPLATE` includes all 12 factors from blueprint §12.1.
Priority bands match §12.3 exactly (Low 0–10, Medium 11–20, High 21–35, Critical 36+).

Two factors always default to Low (1):
- `architecture_centrality` — requires import graph wiring (deferred to v0.11.0)
- `change_frequency` — requires git history analysis (deferred to v0.11.0)

Defaulting to 1 (Low) is conservative — no score inflation.

**No formula changes, no scoring changes.**

## 3. First-Run Audit

**Status:** Clean.

10 automated first-run smoke tests verify the full workflow on a tiny fixture repo:
- `init` → creates workspace with config.yaml
- `scan` → produces evidence.json
- `analyze --no-ai` → produces debt-register.json/md
- `report` → produces 5 markdown reports + foundation-audit-report
- `plan` → produces remediation-roadmap.md, handoff-summary.md, work-packages/
- `export --format all` → produces SARIF, CSV, JSONL
- `status` → exits cleanly
- `enrich --provider mock` → writes AI sidecar
- `ai-status` → reads sidecar

All tests pass in ~4 seconds. No network, no credentials.

## 4. `.ai-debt/` Contract Audit

**Status:** Complete.

### Blueprint-required artifacts (15/15)

| Artifact | Command | Status |
|---|---|---|
| `config.yaml` | `init` | ✅ Written (not read) |
| `project-profile.json` | `profile` | ✅ |
| `evidence.json` | `scan` | ✅ |
| `debt-register.json` | `analyze` | ✅ |
| `debt-register.md` | `analyze` | ✅ |
| `architecture-map.md` | `report` | ✅ |
| `dependency-health.md` | `report` | ✅ |
| `test-health.md` | `report` | ✅ |
| `security-exposure.md` | `report` | ✅ |
| `business-risk-proxy.md` | `report` | ✅ |
| `remediation-roadmap.md` | `plan` | ✅ |
| `handoff-summary.md` | `plan` | ✅ |
| `work-packages/` | `plan` | ✅ |
| `reports/` | `report` | ✅ |
| `runs/` | `run` | ✅ |

### Post-blueprint additions

| Artifact | Command | Status |
|---|---|---|
| `architecture-graph.json` | `graph` | ✅ v0.5.0+ |
| `analysis-units.json` | `map` | ✅ v0.2.0+ |
| `ai/` | `enrich` | ✅ v0.7.0+ (sidecar) |
| `README.md` | `init` | ✅ |

## 5. Report/Work-Package Readability Audit

**Status:** All sections present, matches blueprint §16 templates.

### Handoff Summary (§16.1)
All sections present: Repository, Executive Summary, Top Risks, Recommended First Actions,
Remediation Roadmap, Product Engineering Decisions Needed, Risks and Cautions,
Uncertainties and Missing Evidence, Generated Artifacts. ✅

### Debt Register Markdown (§16.2)
All sections present: Summary table, per-finding sections with category, severity,
confidence, score, priority, locations, evidence, impacts. ✅

### Work Packages (§16.3)
All sections present: Status, Linked Debt Items, Objective, Evidence, Current Risk,
Recommended Engineering Approach, Expected Affected Areas, Preconditions,
Verification Recommendations, Risks and Cautions, Definition of Done, Estimated Effort,
Expected Risk Reduction, Suggested Owner Area. ✅

### Foundation Audit Report (§16.4)
Present with repository context, methodology, findings, and recommendations. ✅

**No readability changes needed.**

## 6. Remaining V1 Follow-ups

| Follow-up | Scope | Target |
|---|---|---|
| `architecture_centrality` factor unused | v1.1 | Requires graph wiring |
| `change_frequency` factor unused | v1.1 | Requires git history |
| Git history analysis | v1.1 | Major feature |
| Incremental analysis mode | v1.1 | Major feature |
| Jira/GitHub Issues export | v1.1 | New format |
| Report integration for AI enrichments | v1.1 | Integration |
| Sample output gallery | v1.1 | Documentation |

## 7. What Was NOT Changed

- No new taxonomy categories
- No new providers
- No provider default changes
- No config reading behavior
- No export format changes
- No risk scoring formula changes
- No AI-generated canonical findings
- No remediation/code modification behavior
- No enrich integration into run
- No real provider calls in CI
