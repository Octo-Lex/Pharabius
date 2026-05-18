# Release Checklist — Pharabius

This checklist must be completed before tagging any release.

---

## 1. Local Quality Gates

All must pass:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
```

- [ ] `ruff format --check .` — all files formatted
- [ ] `ruff check .` — no lint errors
- [ ] `mypy src` — no type errors
- [ ] `lint-imports` — architecture boundaries kept
- [ ] `pytest` — all tests pass, coverage ≥ 80%
- [ ] `python -m build` — sdist and wheel build successfully

---

## 2. Full Command Sequence

Each command must succeed individually:

```bash
ai-debt init
ai-debt profile
ai-debt scan
ai-debt analyze --no-ai
ai-debt report
ai-debt plan
ai-debt run
```

- [ ] `ai-debt init` — creates `.ai-debt/` workspace
- [ ] `ai-debt profile` — generates `project-profile.json`
- [ ] `ai-debt scan` — generates `evidence.json` with evidence items
- [ ] `ai-debt analyze --no-ai` — generates `debt-register.json` and `.md`
- [ ] `ai-debt report` — generates all 6 domain reports
- [ ] `ai-debt plan` — generates roadmap, work packages, and handoff
- [ ] `ai-debt run` — full pipeline + run metadata

---

## 3. Validation Matrix

See `docs/VALIDATION_MATRIX.md`.

- [ ] All 8 repository categories tested
- [ ] Results recorded using `docs/templates/validation-result.md`
- [ ] Minimum passing criteria met

---

## 4. Schema Compatibility Check

- [ ] `project-profile.json` validates against `RepositoryProfile` schema
- [ ] `evidence.json` validates against `EvidenceStore` schema
- [ ] `debt-register.json` validates against `DebtRegister` schema
- [ ] `work-packages/WP-*.md` content matches `WorkPackage` schema
- [ ] `runs/RUN-*.json` validates against `RunMetadata` schema
- [ ] All schema versions are `1.0`

---

## 5. No Unsupported Findings Check

- [ ] Every finding has at least one `evidence_id`
- [ ] No finding has an empty `title`
- [ ] No finding has an empty `description`
- [ ] No finding has an empty `technical_impact`
- [ ] No finding has an empty `recommended_action`
- [ ] No finding has `confidence: "High"` without direct evidence
- [ ] Business impact is marked as inferred where applicable

---

## 6. Evidence IDs Attached to All Findings

- [ ] `debt-register.json` — every `findings[].evidence_ids` is non-empty
- [ ] `debt-register.md` — evidence IDs appear in each finding section
- [ ] Work packages reference the correct evidence IDs through linked debt items

---

## 7. Work Packages Linked to Debt IDs

- [ ] Every `WP-*.md` has a non-empty `## Linked Debt Items` section
- [ ] Every linked debt ID exists in `debt-register.json`
- [ ] Work packages include definition of done
- [ ] Work packages include verification recommendations

---

## 8. Run Metadata Generated

- [ ] `ai-debt run` creates a `RUN-*.json` file under `.ai-debt/runs/`
- [ ] Run metadata includes `evidence_count`, `finding_count`, `work_package_count`
- [ ] Run metadata includes all `commands_run`
- [ ] Run metadata includes all `files_written`

---

## 9. Version and Metadata

- [ ] `pyproject.toml` version is `0.1.0`
- [ ] `RunMetadata.tool_version` is `0.1.0`
- [ ] README.md reflects current command list

---

## 10. Changelog Updated

- [ ] `CHANGELOG.md` exists and documents v0.1.0 features
- [ ] All implemented commands listed
- [ ] Known limitations documented

---

## 11. Tagging Checklist

- [ ] All quality gates green
- [ ] All validation runs completed
- [ ] Release checklist fully signed off
- [ ] Tag `v0.1.0` created
- [ ] Tag message includes summary of v1 capabilities

---

## 12. Step 7.4 Release-Hardening Fixes

Completed 2026-05-16.

- [x] P0: Ecosystem-specific lockfile detection — each ecosystem checked independently
- [x] P0: Package-root-aware manifest/lockfile matching — nested manifests matched against same-directory lockfiles
- [x] P1: Shared exclusion module (`core/exclusions.py`) — scanner and profiler use identical exclusion logic
- [x] P1: Nested `.mypy_cache`, `.ruff_cache`, `node_modules`, `target` excluded at all depths
- [x] P2: `bun.lock` and `bun.lockb` recognized as Node.js lockfiles
- [x] P2: `*_test.go` detected as Go test files (scanner + profiler)
- [x] Rust `Cargo.toml` without `Cargo.lock` produces cautious Medium-severity finding
- [x] 18 new regression tests pass
- [x] Elephant Rock Platform: 0→1 finding (Python TD-DEP), 28714→8622 evidence, 108s→9s runtime
- [x] All quality gates green after fixes

---

## 13. Step 7.5 Node Workspace Lockfile Policy

Completed 2026-05-16.

- [x] Node workspace satisfaction rule: nested packages covered by root lockfile when workspace evidence exists
- [x] Workspace markers detected: `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, `rush.json`, root `package.json` with `"workspaces"`
- [x] Root-only enforcement: only root `package.json` inspected for workspaces field
- [x] Standalone nested packages without workspace markers still produce TD-DEP
- [x] Non-Node ecosystems remain package-root-aware (Python, Go, Rust, etc. unchanged)
- [x] 11 new regression tests pass
- [x] Ghostwire: 6→0 Node.js TD-DEP findings (false positives eliminated)
- [x] Craft Agents: 1→0 TD-DEP (bun.lock + workspace satisfied)
- [x] All quality gates green

---

## 14. Step 7.6 Release Candidate Freeze

Completed 2026-05-16.

- [x] `pyproject.toml` version is `0.1.0` with accurate metadata
- [x] `CHANGELOG.md` created with v0.1.0 release notes
- [x] `docs/KNOWN_LIMITATIONS.md` created with 13 documented limitations
- [x] `docs/ROADMAP.md` created with v0.1.1 / v0.2.0 / v0.3.0 backlog
- [x] `README.md` links to CHANGELOG, KNOWN_LIMITATIONS, ROADMAP, VALIDATION_SUMMARY
- [x] `.gitignore` covers `.ai-debt/`, `dist/`, `build/`, cache dirs
- [x] Clean wheel install works — `ai-debt --help` succeeds from installed wheel outside repo
- [x] Python version confirmed from installed wheel venv
- [x] `ai-debt run` works from installed wheel on a temp repo outside source tree
- [x] No license metadata added (no LICENSE file exists — deferred)
- [x] Tagging prepared but not executed (requires separate approval)
- [x] All 7 release gates green

---

## 15. Step 8 — Analysis Unit IR

Completed 2026-05-17.

- [x] `ai-debt map` command added
- [x] `.ai-debt/analysis-units.json` output with deterministic AU-* IDs
- [x] 9 unit types implemented (package, service, cli, test_suite, ci_workflow, infra_area, config_surface, documentation_area, security_sensitive_area)
- [x] Finding-to-unit linkage via `analysis_unit_ids`
- [x] Run metadata includes `analysis_unit_count`
- [x] Report sections for analysis units in 4 domain reports
- [x] Noise reduction: type-specific evidence, security grouping, cache filtering, zero-evidence filtering
- [x] 113 tests, 86.72% coverage
- [x] All 7 release gates green
- [x] Tagged v0.2.0

---

## 16. Step 9 — v0.2.1 Maintenance

- [ ] Remove phantom limitation #13 (profile boolean fields — fields never existed)
- [ ] Renumber remaining known limitations
- [ ] CHANGELOG.md: proper v0.2.0 heading + new [Unreleased]
- [ ] ROADMAP.md: v0.1.1 → v0.2.1, maintenance-focused
- [ ] RELEASE_CHECKLIST.md: v0.2.1 section added
- [ ] GitHub Actions: update to checkout@v6 + setup-python@v6
- [ ] Audit helper: `scripts/audit_analysis_units.py`
- [ ] pyproject.toml version set to `0.2.1`
- [ ] All 7 release gates green
- [ ] CI passes on PR

---

## 17. Step 10 — ai-debt verify

Completed 2026-05-17.

- [x] `ai-debt verify` command added
- [x] Verification schemas (VerificationResult, WorkPackageVerificationResult, VerificationReport)
- [x] Deterministic matching (category+evidence, locations, title, ID fallback)
- [x] 6 verification statuses implemented
- [x] Location verification (file path existence)
- [x] Structured work package verification
- [x] Runs analyze_evidence() in memory, does not write debt-register.json
- [x] Writes verification-report.json and verification-report.md
- [x] Standalone command, not added to ai-debt run
- [x] 145 tests passing, all 7 release gates green
- [x] Tagged v0.3.0

---

## 18. Step 11 — v0.3.1 Stabilization & Verification UX

- [ ] Verification report readability improved
- [ ] All 6 verification statuses covered by explicit edge-case tests
- [ ] `ai-debt status` read-only workspace summary command
- [ ] Lifecycle documentation added to ARCHITECTURE.md
- [ ] ROADMAP cleaned up (duplicate headings fixed)
- [ ] RELEASE_CHECKLIST updated
- [ ] KNOWN_LIMITATIONS updated
- [ ] pyproject.toml version set to `0.3.1`
- [ ] All 7 release gates green
- [ ] CI passes on PR

---

## 19. Step 13 — v0.3.2 Field-Validation Bug Fixes

- [x] .NET manifest suffix detection (BUG-001 fixed)
- [x] .sln emits solution_file_detected, not manifest_detected
- [x] .NET TD-DEP findings for .csproj without packages.lock.json
- [x] Maven parent POM no longer produces TD-DEP
- [x] Maven library modules no longer produce TD-DEP
- [x] CI keyword false positives suppressed (checkout, deploy, release, monitoring)
- [x] .terraform.lock.hcl detected as lockfile evidence
- [x] 195 tests passing, 87% coverage
- [x] All 7 release gates green
- [x] CI passes on PR

---

## 20. Step 15 — v0.4.0 Export Formats

- [x] `ai-debt export` command added
- [x] SARIF v2.1.0 export
- [x] CSV export (UTF-8 BOM)
- [x] JSONL export
- [x] Verification status enrichment
- [x] Work package linkage
- [x] Source artifact immutability verified
- [x] 219 tests passing, 86% coverage
- [x] All 7 release gates green
- [x] CI passes on PR

---

## 21. Step 17 — v0.5.0 Architecture Graph IR

- [x] `ai-debt graph` command added
- [x] `schemas/architecture_graph.py` (Pydantic models + policy schema)
- [x] `core/grapher.py` (graph construction, cycles, coupling, boundary)
- [x] Deterministic stable IDs (node, cycle, violation)
- [x] Tarjan SCC cycle detection (no new dependencies)
- [x] Optional boundary policy via architecture-policy.yaml
- [x] No TD-ARCH findings created
- [x] No changes to ai-debt run
- [x] No changes to ai-debt export
- [x] No .importlinter parsing
- [x] 282 tests passing, 84% coverage
- [x] All 7 release gates green
- [x] CI passes on PR
