# Known Limitations — Pharabius v0.2.1

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

## 38. Monorepo node collapse

`ai-debt graph` groups source files by the first directory level under `src/` (or repository
root for flat layouts). For monorepos using `packages/*` or `apps/*` layouts, all files within
a single top-level directory are collapsed into one node. This means:
- TypeScript/JS monorepos: `packages/bot`, `packages/core` become a single `packages` node
- Python sub-packages: `src/myapp/cli`, `src/myapp/core` become a single `myapp` node
- All inter-package imports become self-imports and are skipped
- No edges, cycles, or boundary violations are detected within the collapsed node

This affects Ghostwire, Craft-Agents, and any monorepo using first-level directory grouping.
Planned fix in v0.6.0.

## 39. Rust import detection not implemented

The scanner detects imports for Python, JavaScript/TypeScript, Java, C#, Go, PHP, and Ruby.
Rust `use` statements (e.g., `use crate::module::item`) are not matched by any import
pattern. Rust repositories produce zero `imports_detected` evidence and zero graph edges.
Planned fix in v0.6.0.

## 40. TD-ARCH findings capped at 20 per type

At most 20 cycle findings and 20 boundary violation findings are generated per analysis run.
If more exist in the graph, a note is added to the last finding's risks_and_cautions.
