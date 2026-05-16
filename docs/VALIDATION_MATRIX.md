# Validation Matrix

Pharabius v0.1.0 must be validated across multiple repository types before release.

This document defines the required repository categories, acceptance criteria, and tracking structure for each validation run.

---

## Repository Categories

| # | Category | Purpose |
|---|---|---|
| 1 | Small TypeScript frontend | Validate web app profiling, framework detection, and test/script evidence |
| 2 | Node.js backend/API | Validate service profiling, dependency analysis, and operational debt |
| 3 | Python API/service | Validate non-JS stack support, manifest detection, and import evidence |
| 4 | Java or JVM service | Validate enterprise stack support, Maven/Gradle detection |
| 5 | Monorepo | Validate multi-package structure, workspace detection, and cross-service reporting |
| 6 | Infrastructure-as-code repo | Validate Terraform, Kubernetes, Helm, and config debt detection |
| 7 | Legacy-style repository | Validate poor-structure detection, missing tests, missing docs, missing CI |
| 8 | Mature open-source repository | Validate low-noise reporting against a well-maintained project |

---

## Validation Criteria per Repository

For each repository tested, record the following:

| Field | Description |
|---|---|
| Repository name/path | Local path or URL |
| Repository URL | Public URL if available |
| Stack | Primary language, framework, package manager |
| Commands run | `ai-debt run` or individual commands |
| ai-debt run passed | Yes / No |
| Evidence count | Number of evidence items generated |
| Finding count | Number of debt findings |
| Work package count | Number of work packages generated |
| False positives observed | Findings that do not represent real debt |
| Missing obvious risks | Real risks the analyzer failed to detect |
| Report usefulness notes | Are the reports readable, accurate, and actionable? |
| Runtime | Wall-clock time for full pipeline |
| Follow-up rule tuning needed | Rules that need adjustment based on this run |

---

## Validation Results Tracking

Results should be recorded using the template at `docs/templates/validation-result.md`.

Copy the template for each tested repository, fill it in, and store in `docs/validation-results/`.

---

## Minimum Passing Criteria

Pharabius v0.1.0 validation passes when:

1. `ai-debt run` completes without error on all 8 repository types.
2. Every finding has at least one `evidence_id`.
3. No work package is generated without a linked debt ID.
4. Run metadata is written for every successful run.
5. No crash or unhandled exception on any repository type.
6. Reports are readable and evidence-linked across all types.
7. At least 6 of 8 repository types produce at least one finding.
8. No false positive severity exceeds Medium without supporting evidence.
9. Legacy-style repositories produce the most findings (expected behavior).
10. Mature OSS repositories produce fewer, more targeted findings (expected behavior).

---

## Current Validation Status

| # | Category | Repository | Result File | Findings | Decision | Date |
|---|---|---|---|---|---|---|
| 1 | Python tool / CLI | Pharabius | 001-pharabius.md | 1 (Medium) | Pass | 2026-05-16 |
| 2 | TypeScript monorepo | Ghostwire | 002-ghostwire.md | 0 | Pass with notes | 2026-05-16 |
| 3 | Python API + frontend | Elephant Rock Platform | 003-elephant-rock-platform.md | 0 | Pass with notes | 2026-05-16 |
| 4 | Go service | NodeSpan | 004-nodespan.md | 0 | Pass | 2026-05-16 |
| 5 | Infrastructure / microservices | Ariadne | 005-ariadne.md | 0 | Pass with notes | 2026-05-16 |
| 6 | Rust library | Symbiot | 006-symbiot.md | 2 (High) | Pass | 2026-05-16 |
| 7 | TypeScript monorepo (Electron) | Craft Agents | 007-craft-agents.md | 1 (Medium) | Pass with notes | 2026-05-16 |
| 8 | Rust multi-crate engine | AIF | 008-aif.md | 2 (Medium, Low) | Pass | 2026-05-16 |
