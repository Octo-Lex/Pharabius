# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# Wave 44 Patch-Set Index

This directory contains standalone Markdown patch-set files for Wave 44.

| Slice | Title | Risk | File |
|---|---|---|---|
| W44-S01 | Export manifest validation improvements | Medium | `W44-S01-export-manifest-validation-improvements.md` |
| W44-S02 | Tracker bundle completeness checks | Medium | `W44-S02-tracker-bundle-completeness-checks.md` |
| W44-S03 | Add richer tracker-specific examples | Low | `W44-S03-richer-tracker-specific-examples.md` |
| W44-S04 | Add adoption guide for tracker import workflows | Low | `W44-S04-tracker-import-workflow-adoption-guide.md` |
| W44-S05 | Add export-bundle summary report | Low-medium | `W44-S05-export-bundle-summary-report.md` |
| W44-S06 | Docs, changelog, release | Low | `W44-S06-docs-changelog-release.md` |

## Wave-Level Acceptance Criteria

- Export bundles remain repository-local.
- No external tracker APIs are called.
- No issues are created automatically.
- Manifest validation and completeness checks are deterministic.
- Examples are parseable and safe.
- Summary report is generated as a sidecar artifact.
- `debt-register.json` is not mutated.
- Work packages are not mutated.
- Risk scoring behavior is unchanged.
- Review sidecar decisions do not influence scores.
- No autonomous remediation is introduced.
- All 7 local gates pass.
