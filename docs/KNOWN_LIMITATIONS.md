# Known Limitations — Pharabius v1.6.0

This document lists known limitations of Pharabius v0.1.0. These are honest constraints, not bugs.

---

## 1. No AI behavior in v0.1.0

All analysis is deterministic and rule-based. The `--ai` flag exists as a placeholder but is not connected to any AI provider. Every finding must be traceable to collected repository evidence.

## 2. No autonomous remediation

Pharabius generates findings and recommendations but does not modify source code, configuration, or dependencies. It is an analysis and planning tool only.

## 3. No vulnerability scanner integration

Pharabius detects missing CI, tests, docs, lockfiles, and risk-sensitive paths. It does not run SAST/DAST tools, query CVE databases, or assess dependency vulnerabilities.

## 4. No coverage report ingestion

Test detection is file-based (test directory/file patterns such as `*_test.go`, `test_*.py`, `*.test.ts`). Pharabius does not parse coverage reports or measure actual test effectiveness.

## 5. Limited code complexity analysis

Complexity signals come from risk keywords in paths and file contents (auth, token, billing, etc.). Pharabius does not compute cyclomatic complexity, cognitive complexity, or function-length metrics.

## 6. Limited architecture graph analysis

Import statements are collected as evidence but are not used for dependency graph analysis, coupling metrics, or circular dependency detection in v0.1.0.

## 7. Dependency freshness not assessed

Pharabius detects manifest and lockfile presence but does not check for outdated, deprecated, or vulnerable dependency versions.

## 8. Business impact is inferred

Business impact is inferred from repository evidence (path names, keywords, file structure). It does not reflect actual business criticality. Validate inferred impact with the Product Engineering team.

## 9. Rust Cargo.lock policy may require project validation

Rust library crates may intentionally omit `Cargo.lock`. Findings include a caution note in the description, risks_and_cautions, and verification_recommendations. Users must validate repository policy before acting on Rust lockfile findings.

## 10. Node workspace lockfile handling assumes root workspace governance

Nested `package.json` files are considered lockfile-satisfied when workspace evidence exists (pnpm-workspace.yaml, turbo.json, nx.json, lerna.json, rush.json, or root `package.json` with `"workspaces"`) **and** a root Node lockfile exists. This may not cover all workspace manager configurations or unconventional monorepo layouts.

## 11. Non-Node ecosystems are strictly package-root-aware

Python, Go, Rust, Java, PHP, Ruby, and .NET lockfile checks require the lockfile to be in the same directory as the manifest. Root-level lockfiles do not satisfy nested manifests for these ecosystems. This is by design to prevent false negatives in multi-service repositories.

## 12. No license metadata in package

v0.1.0 does not include a `LICENSE` file or `license` field in `pyproject.toml`. License metadata is deferred to a future release. Users should not redistribute without clarifying licensing terms.

## 13. Analysis Units are directory-convention-based

Service detection relies on directory conventions (apps/, services/, packages/, crates/, modules/, cmd/).
Repositories that don't follow these conventions may not produce service units.

## 14. Trust-boundary tags are keyword-inferred

Security-sensitive area tags are inferred from file path and content keywords.
They do not represent verified security boundaries.

## 15. Security-sensitive units use heuristic grouping

Security-sensitive analysis units are grouped by the nearest package or service root.
This may merge distinct security boundaries into a single unit or miss boundaries
that don't align with package/service structure.

## 16. Risk evidence in docs and tests is excluded from security units

Risk-sensitive keyword matches in documentation and test directories do not create
security-sensitive analysis units. This reduces noise but may miss legitimate
security concerns documented in those directories.

## 17. Verification is evidence-based, not proof of remediation

`ai-debt verify` checks whether repository evidence still supports prior findings.
It does not prove risk has been eliminated. A `likely_remediated` status means the
deterministic analyzer no longer detects the condition \u2014 manual review is recommended.

## 18. verify does not modify the debt register

`ai-debt verify` writes `verification-report.json` and `verification-report.md` only.
It does not modify `debt-register.json`, `evidence.json`, or any existing artifact.

## 19. verify is not part of ai-debt run

`ai-debt verify` is a standalone command. It is not included in `ai-debt run` and
must be invoked explicitly when verification is desired.

## 20. ai-debt status is read-only and does not verify findings

`ai-debt status` reads existing `.ai-debt/` artifacts and prints a summary.
It does not run scan, analyze, or verify. Status information may be stale
if the workspace has not been recently updated.

## 21. Maven library modules are conservatively skipped

Maven modules without application signals (Spring Boot plugin, shade plugin, etc.)
do not produce TD-DEP dependency reproducibility findings. This is conservative:
some library modules benefit from reproducibility evidence. If a POM cannot be read
or its role is ambiguous, it is also skipped to avoid false positives.

## 22. Terraform dependency reproducibility analysis is deferred

`.terraform.lock.hcl` is detected as lockfile evidence, but no TD-DEP finding is
generated for missing Terraform lockfiles. Terraform provider locking differs
from package manager lockfiles and requires dedicated analysis logic.

## 23. .NET manifest detection is suffix-based

.NET project files (`.csproj`, `.fsproj`, `.vbproj`) are detected by file extension,
not by exact filename. This matches standard .NET conventions where project
filenames vary. `.sln` files are detected as solution/workspace files and do not
produce dependency findings.

## 24. CI/deployment workflow files receive narrowed risk keyword scanning

Operational keywords (deploy, release, monitoring, logging, tracing) and the
payment keyword "checkout" are excluded from risk-sensitive evidence when detected
in CI/deployment workflow files. This prevents false security signals from
standard CI tooling like `actions/checkout`. These keywords remain active as risk
signals in application source files and configuration.

## 25. Export is a point-in-time snapshot

`ai-debt export` reads the current state of `.ai-debt/` artifacts. It does not
track changes over time or produce incremental exports. Re-run `ai-debt run`
before export to ensure fresh data.

## 26. SARIF upload is not automated

`ai-debt export` generates SARIF files but does not upload them to GitHub Code
Scanning or any other service. Use `gh code-scanning` or your CI pipeline to
upload the SARIF file.

## 27. Export does not create new findings

Export formats contain only findings already present in `debt-register.json`.
No new analysis or findings are generated during export.

## 28. Architecture graph is IR only

`ai-debt graph` produces `architecture-graph.json` as an intermediate representation.
It does not create TD-ARCH findings in `debt-register.json`. Graph IR is separate from the finding pipeline.

## 29. Architecture graph is not part of `ai-debt run`

`ai-debt graph` is a standalone command. It is not included in the `ai-debt run` pipeline.
Users must run it separately.

## 30. Architecture graph is not exported by `ai-debt export`

`ai-debt export` only exports `debt-register.json` findings. Architecture graph data is not
included in SARIF, CSV, or JSONL exports.

## 31. Import resolution is regex-based

`ai-debt graph` uses regex-based import extraction from `imports_detected` evidence.
No AST parsing is performed. Dynamic imports (`importlib.import_module()`) are not detected.
Re-export chains (`from x import y`) resolve to `x`, not to `y`'s origin.

## 32. TypeScript/JavaScript path aliases not supported

`tsconfig.json` path aliases are not resolved in v0.5.0. Relative imports are resolved by
probing file extensions (`.ts`, `.tsx`, `.js`, `.jsx`, `index.*`).

## 33. `.importlinter` is not parsed

Pharabius detects the presence of `.importlinter` but does not parse it for layer boundaries.
Users must translate their import-linter configuration into `.ai-debt/architecture-policy.yaml`
for boundary checking.

## 34. Go/Rust/Java/.NET node derivation is best-effort

Python and TypeScript/JavaScript have full import resolution. Other languages use
best-effort node derivation based on directory structure and manifest locations.

## 35. No external import edges

`ai-debt graph` only creates `internal_import` edges. External dependencies and standard library
imports are filtered out. Unresolved internal-looking imports are recorded as limitations.

## 36. TD-ARCH findings require pre-existing architecture-graph.json

TD-ARCH findings are only generated when `ai-debt graph` has been run before
`ai-debt analyze --no-ai`. Without the graph file, no TD-ARCH findings are created.
`ai-debt run` does not include the graph step.

## 37. High-coupling metrics are not findings

Coupling metrics (fan-in, fan-out, instability) are included in `architecture-graph.json`
but do not generate TD-ARCH findings in v0.5.1. Thresholds for coupling-based findings
require further field validation.

## 38. Monorepo node splitting — mostly resolved

v0.6.0 adds package-level node splitting for TS/JS monorepos using `package.json` detection.
v0.6.1 adds Rust `crates/*` node splitting using `Cargo.toml` `[package]` discovery.
Python sub-package splitting is enabled when `architecture-policy.yaml` targets subdirectory layers.

**Remaining limitations:**
- Non-standard monorepo layouts not using the recognized root directories
- Python sub-packages only split when a policy exists; no automatic detection without policy

## 39. Rust import detection — mostly resolved

v0.6.0 adds Rust `use` statement extraction including grouped import expansion.
v0.6.1 adds `crates/*` node splitting and workspace-local cross-crate import resolution
with kebab→snake name normalization.

**Remaining limitations:**
- Block comments (`/* use crate::fake; */`) are not filtered; `use` inside block comments may
  be captured as false positives
- `super::` and `crate::` intra-crate imports do not create module-level graph edges (crate-level only)
- Rust module-level graph remains deferred

## 40. TD-ARCH findings capped at 20 per type

At most 20 cycle findings and 20 boundary violation findings are generated per analysis run.
If more exist in the graph, a note is added to the last finding's risks_and_cautions.

## 41. AI enrichment is optional and disabled by default

`ai-debt enrich` requires `--provider mock` to produce output.
Without an explicit provider, the command prints a disabled message and exits.
AI enrichment is not part of `ai-debt run`.

## 42. No real AI provider in v0.7.0

Only `mock` and `disabled` providers are available. No OpenAI, Claude, local model,
or any network-based provider is included. Real providers are planned for future releases.

## 43. AI enrichments are sidecar records, not canonical findings

AI output is written to `.ai-debt/ai/` and is not read by `ai-debt status`,
`ai-debt verify`, `ai-debt export`, `ai-debt report`, or `ai-debt run`.
Deterministic findings in `debt-register.json` remain canonical.

## 44. AI does not mutate canonical artifacts

`ai-debt enrich` never modifies `debt-register.json`, `evidence.json`,
`analysis-units.json`, `architecture-graph.json`, `verification-report.json`,
work packages, reports, or source files. All AI output is sidecar-only.

## 45. Context assembly is bounded

AI context includes only evidence linked to the selected finding(s), subject to budget
controls (max evidence items, max context chars, max graph records).
Evidence exceeding the budget is omitted and recorded in the context summary.

## 46. AI output validation rejects claims without evidence IDs

Every enrichment must reference existing finding IDs and at least one evidence ID.
Empty `evidence_ids` lists are rejected. Output with unknown IDs, invalid confidence values,
or empty limitations is rejected and recorded in `rejected-ai-output.json`.

## 47. No report integration for AI enrichments

AI enrichments are not included in deterministic reports. Reports render normally
when `.ai-debt/ai/` is absent or present. Report integration is planned for a future release.

## 48. Unknown --finding-id fails clearly

Running `ai-debt enrich --finding-id NONEXISTENT` exits with code 1 and a clear error message.
It does not silently return 0 enrichments.

## 49. Sidecar files may contain summarized repository context

`.ai-debt/ai/` sidecar files may contain summarized evidence and repository context.
Review before sharing with external parties. Consider adding `.ai-debt/ai/` to
`.gitignore` for sensitive repositories.

## 50. ai-status is informational only

`ai-debt ai-status` summarizes sidecar state but does not validate correctness of
enrichment content. Review enrichment-report.md for detailed findings.

## 51. No real AI provider in v0.8.0

v0.8.0 is a provider interface readiness release. It hardens adapter interfaces and adds
provider simulation tests but does not include any real external provider (OpenAI, Claude,
local models). Available providers remain `disabled` (default) and `mock` (testing).

## 52. Context preview is informational only

`ai-debt enrich --context-preview` previews the bounded context that would be sent to a
provider. It does not call any provider, write files, or validate context against provider
requirements. The actual context sent may differ when a real provider is configured.

## 53. Strict JSON requirement — no markdown wrapping or comments

Provider output must be strict JSON. Markdown-fenced JSON (```` ```json ... ``` ````),
JSON with comments (`// ...`), and partial/truncated JSON are all rejected by the
validation pipeline. Providers must return raw JSON only.

## 54. OpenAI-compatible adapter requires optional dependency

The `openai-compatible` provider requires `httpx`, installed via the optional extra:
`pip install "pharabius[openai-compatible]"`. Without it, the provider fails with a clear
install instruction. No official OpenAI SDK is used.

## 55. No Azure-specific support

The `openai-compatible` adapter targets the standard `/v1/chat/completions` request and
response shape. It does not include Azure-specific endpoint/version handling. Users may
set `PHARABIUS_OPENAI_BASE_URL` to an Azure endpoint if it implements the expected shape,
but this is not explicitly tested.

## 56. External provider consent is per-invocation

`--allow-external-provider` is a per-invocation CLI flag. It does not persist between runs.
There is no config file or persistent consent mechanism in v0.9.0.

## 57. No automatic retry

Provider calls do not retry automatically on failure. The `max_provider_retries` field exists
in `AIBudget` but defaults to 0 and is not exposed in the CLI. Retry behavior may be added
in a future release.

## 58. Manual smoke validation is optional and manual

The `scripts/manual_provider_smoke.py` script requires real API credentials and makes
actual network calls. It is not part of CI or release gates. Validation results are
noted manually using the template at `docs/templates/provider-smoke-result.md`.

## 59. Output budget does not count tokens

`max_output_chars` (default: 10,000) counts raw characters, not tokens. A provider
returning 4,000 characters of JSON may use significantly more tokens. Token counting
is the provider's responsibility; Pharabius only enforces character limits.

## 60. Duplicate detection is per-run

Duplicate enrichment detection only applies within a single enrichment run. Running
`ai-debt enrich` twice may produce duplicate enrichments in the sidecar. The second
run overwrites the first.

## 61. New taxonomy rules are conservative (v0.10.0)

The 7 new analysis rules (TD-CODE, TD-COMP, TD-OPS, TD-DATA, TD-PERF, TD-OBS,
TD-PROCESS) use conservative detection thresholds and require explicit evidence.
They may miss valid debt that requires deeper code analysis (AST, runtime metrics,
or git history). False negatives are expected; false positives are minimized.

## 62. TD-PERF does not measure performance

The performance debt rule detects synchronous/blocking keyword patterns near
risk-sensitive areas. It does NOT run benchmarks, measure latency, or profile code.
Findings represent potential concern, not confirmed bottlenecks.

## 63. TD-DATA does not inspect database state

The data debt rule checks for migration/schema files without rollback evidence.
It does NOT connect to databases, inspect schema state, or assess data integrity.

## 64. TD-COMP does not perform legal compliance assessment

The compliance rule detects compliance-related keywords (PII, GDPR, HIPAA, PCI).
It does NOT perform legal compliance assessment, gap analysis, or regulatory review.
All findings are "potential exposure" based on keyword evidence.

## 65. Config runtime implemented with narrow scope (v0.11.0)

`ai-debt init` creates `.ai-debt/config.yaml` with safe defaults. Commands now read
config for `analysis.exclude_paths` and `analysis.max_file_size_kb`. CLI flags always
override config values. Malformed config produces warnings and uses safe defaults.
Unknown keys produce warnings and are ignored.

Config does NOT store credentials, model selection, or provider consent. The
`ai.provider` field is parsed but does NOT enable real provider calls without
explicit CLI `--provider` and `--allow-external-provider` flags.

The following fields remain non-authoritative (parsed but not behavior-changing):
- `project.*` (informational only)
- `analysis.mode` (only "baseline" exists)
- `analysis.include_git_history` (not implemented)
- `ai.enabled` (parsed but real providers require CLI consent)
- `risk_scoring.priority_bands` (not wired to scoring)
- `output.directory` (does not relocate workspace)
- `output.formats` (always produces both JSON + Markdown)
- Policy fields (parsed, all default true, do not weaken safety)

## 66. Risk scoring not fully aligned to blueprint §12 (v0.10.1)

The `RISK_SCORE_TEMPLATE` structurally includes all 12 factors from blueprint §12.1.
Priority bands match §12.3 exactly (Low 0–10, Medium 11–20, High 21–35, Critical 36+).

Two factors default to Low (1) and are not overridden by any analysis rule:
- `architecture_centrality`: requires wiring import graph data into the analyzer (deferred)
- `change_frequency`: requires git history analysis (deferred)

Both factors defaulting to 1 (Low) is conservative — it does not inflate scores.
Full graph/git-backed scoring alignment requires v0.11.0+ work.

## 13. Enhanced scoring calibration limitations

- Enhanced scoring remains opt-in (disabled by default).
- Architecture centrality depends on availability and quality of `architecture-graph.json`.
- Change frequency depends on local git history; shallow clones fall back to Low.
- Rename history may be incomplete for complex path moves.
- Calibration evidence packs are sidecar validation artifacts, not canonical product outputs.
- No threshold changes were made in v1.5.1; v1.5.0 thresholds remain unchanged.

## 14. Ticket draft export limitations

- Ticket drafts are repository-local planning artifacts. Pharabius v1.6.x does not create, sync, assign, or update external tracker tickets.
- Markdown work package parsing is conservative; missing sections use placeholders.
- `finding` source type is reserved for future use; v1.6.0 generates from work packages only.
- Ticket draft content should be reviewed by Product Engineering Teams before creating real tickets.
- Review sidecar decisions affect ticket draft inclusion only, not risk scores or canonical findings.
- Completeness checks identify missing fields but do not enrich content automatically.
- Malformed work packages are skipped with validation warnings rather than failing the command.

## 15. Export bundle limitations

- Export bundles are repository-local handoff artifacts. Pharabius v1.7.x does not call Jira, Linear, GitHub Issues, or Azure DevOps APIs.
- No automatic issue or work-item creation from export bundles.
- No assignment, sprint, milestone, cycle, area path, or iteration path handling.
- Priority mappings (e.g., Critical → Urgent for Linear) are suggestions only.
- Default work item type (Azure DevOps: User Story) may need adjustment per project.
- Export bundles do not modify ticket drafts, debt register, or scoring artifacts.
- Manifest validation detects structural issues but does not repair them.
- Completeness checks are advisory (partial/needs_review bundles remain usable).
