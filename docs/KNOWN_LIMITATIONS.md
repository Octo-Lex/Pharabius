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
