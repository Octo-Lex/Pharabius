# Validation Result

## Repository

- **Repository name:** Symbiot
- **Repository path:** `C:\Next-Era\Symbiot`
- **Repository URL:** N/A (internal)
- **Repository type:** Rust library
- **Stack:** Rust, Cargo

## Run Details

- **Date:** 2026-05-16
- **Pharabius version:** 0.1.0
- **Command used:** `python scripts/validate_repo.py C:/Next-Era/Symbiot`
- **Runtime:** ~6.3s

## Results

| Metric | Value |
|---|---|
| Evidence count | 63 |
| Finding count | 2 |
| Work package count | 2 |
| Critical findings | 0 |
| High findings | 2 |
| Medium findings | 0 |
| Low findings | 0 |

## Top Findings

1. **TD-SEC-001** (High): Risk-sensitive areas detected without test evidence
2. **TD-TEST-001** (High): No test evidence detected

## False Positives

- The "risk-sensitive areas without tests" finding includes risk keywords like `unwrap`, `panic`, and error-related patterns from Rust code. While these are real risk signals in Rust, the severity of High may be slightly aggressive for a library crate. However, the finding is technically correct — these patterns exist without corresponding test coverage.

## False Negatives / Missed Risks

- `target/` directory was scanned, contributing to evidence count. Should be excluded.
- No `Cargo.lock` finding despite having one — correct because Rust libraries should not commit Cargo.lock.

## Output Artifacts Reviewed

- [x] `project-profile.json` — detects Rust, TOML; identifies `cargo` package manager
- [x] `evidence.json` — 63 items (reasonable)
- [x] `debt-register.json` — 2 findings, both with strong evidence IDs
- [x] `debt-register.md` — readable and accurate
- [x] `work-packages/WP-001-*.md` — actionable
- [x] `work-packages/WP-002-*.md` — actionable

## Decision

- [x] **Pass** — Correct findings for a Rust project with no tests.

## Notes

- Good example of Pharabius correctly identifying a real risk (missing tests in a Rust crate with sensitive operations).
- The profile correctly notes "No test framework or test directory detected" as a limitation.

## Follow-up Actions

- None required. The findings are correct and actionable.
