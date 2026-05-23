# Wave 46 — v1.9.0 Operational Claims & Gap Registry

Goal: Add first-class operational claims, gap registry, confidence reporting, and traceability matrices derived from existing Pharabius evidence, findings, work packages, and reports.

Release target: `v1.9.0`  
Branch target: `roadmap/v1.9.0-operational-claims`  
Boundary: Repository-local specification and traceability artifacts only. No code modification, no autonomous remediation, no external API writes.

# W46-S05 — Traceability Matrices: Evidence → Finding → Claim → Work Package

Risk: Medium  
Slice type: Traceability reporting  
Artifact impact: New `.ai-debt/traceability/` matrices

## Scope

Generate traceability matrices connecting evidence, findings, operational claims, and work packages. This slice strengthens auditability and prepares Pharabius outputs for safer human or AI-agent handoff without granting implementation authority.

## Goals

- Generate `.ai-debt/traceability/evidence-finding-matrix.md`.
- Generate `.ai-debt/traceability/finding-claim-matrix.md`.
- Generate `.ai-debt/traceability/claim-workpackage-matrix.md`.
- Preserve exact evidence IDs, finding IDs, claim IDs, and work-package IDs.
- Identify orphan evidence, findings without claims, claims without evidence, and work packages with unresolved gaps.
- Keep matrices deterministic and diff-friendly.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/claims.py
src/pharabius/core/traceability.py             # new, if useful
src/pharabius/schemas/claims.py
tests/test_traceability_matrices.py
docs/OPERATIONAL_CLAIMS.md                    # optional incremental update
```

Recommended matrix files:

```text
.ai-debt/traceability/
  evidence-finding-matrix.md
  finding-claim-matrix.md
  claim-workpackage-matrix.md
```

Recommended sections:

```markdown
# Evidence → Finding Matrix

| Evidence ID | Finding IDs | Location | Summary |
|---|---|---|---|

# Finding → Claim Matrix

| Finding ID | Claim IDs | Claim Statuses | Gap Count |
|---|---|---|---|

# Claim → Work Package Matrix

| Claim ID | Work Package IDs | Blocking Gaps | Human Validation Required |
|---|---|---|---|
```

Recommended warnings:

| Warning | Meaning |
|---|---|
| `orphan_evidence` | Evidence not linked to any finding |
| `finding_without_claim` | Finding has no generated claim |
| `claim_without_evidence` | Claim is inferred/gap or weakly supported |
| `work_package_with_blocking_gap` | Work package should not be executed before validation |

## Tests

Add tests for:

- Evidence-to-finding matrix includes expected links.
- Finding-to-claim matrix includes expected claims.
- Claim-to-work-package matrix includes expected links.
- Orphan evidence warning.
- Finding without claim warning.
- Claim without evidence warning.
- Work package with blocking gap warning.
- Deterministic row ordering.
- Markdown escaping for paths/titles.
- No source artifact mutation.

## Targeted Verification

```bash
pytest tests/test_traceability_matrices.py
```

## Expected Behavior

Pharabius emits traceability matrices:

```text
.ai-debt/traceability/evidence-finding-matrix.md
.ai-debt/traceability/finding-claim-matrix.md
.ai-debt/traceability/claim-workpackage-matrix.md
```

The matrices make it clear which implementation plans are strongly supported and which require additional validation.

## Acceptance Criteria

- All three traceability matrices are generated.
- ID links are accurate and deterministic.
- Weak traceability warnings are visible.
- Work packages with blocking gaps are identifiable.
- No canonical artifacts are mutated.
- No scoring behavior changes.
- All 7 local gates pass.

## Guardrails

- Do not modify production/source code.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external APIs.
- Do not mutate `debt-register.json`, `evidence.json`, work packages, ticket drafts, export bundles, or portfolio outputs.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence risk scores.
- Do not convert inferred claims into confirmed claims without direct evidence.
- Do not hide gaps inside generic limitations; gaps must remain explicit.
- Treat operational claims as handoff/specification artifacts, not implementation authority.


## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.
