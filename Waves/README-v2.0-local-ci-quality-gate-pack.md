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

## Pack contents

| File | Purpose |
|---|---|
| `01-strategy-amendment-ci-gate-first.md` | Corrects v2 strategy to workflow-first adoption |
| `02-v2.0-product-scope.md` | Defines v2.0 in/out of scope |
| `03-quality-gate-artifact-contract.md` | Defines JSON/Markdown output contract |
| `04-quality-gate-rules-and-config.md` | Defines rule model and config shape |
| `05-cli-command-ai-debt-gate.md` | Defines CLI behavior and exit codes |
| `06-quality-gate-engine-design.md` | Implementation design for local deterministic engine |
| `07-ci-examples.md` | GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, shell |
| `08-tests-and-validation-plan.md` | Unit, CLI, fixture, and integration test plan |
| `09-safety-boundary-and-risk-register.md` | Safety model and risk mitigations |
| `10-docs-and-release-plan.md` | Docs, changelog, release checklist |
| `11-acceptance-checklist.md` | Final go/no-go acceptance checklist |

## Recommended branch

```text
roadmap/v2.0-local-ci-quality-gate
```

## Recommended release headline

```text
Pharabius v2.0 adds a local CI quality gate for enforcing evidence-backed technical debt thresholds without requiring infrastructure or external writes.
```

## One-sentence decision

v2.0 should ship `ai-debt gate` as the first workflow insertion point, with a minimal policy substrate limited to gate configuration.
