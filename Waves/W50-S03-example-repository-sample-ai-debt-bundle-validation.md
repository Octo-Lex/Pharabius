# Wave 50 — v1.10.2 RC2 Adoption & Packaging Hardening

Goal: Harden installation, packaging, examples, release artifacts, CLI onboarding, and adoption documentation before v1 final-style declaration, without adding new product capability.

Release target: `v1.10.2`  
Branch target: `roadmap/v1.10.2-rc2-adoption-packaging`  
Boundary: Hardening, validation, packaging, examples, and adoption documentation only. No new product capability.

# W50-S03 — Example Repository / Sample `.ai-debt` Bundle Validation

Risk: Medium  
Slice type: Examples / sample artifact validation  
Artifact impact: Example fixtures and validation tests only

## Scope

Add or harden a representative sample `.ai-debt` bundle and validate that it remains internally consistent with the v1 artifact contract, schema map, command surface, and readiness checks.

This slice does not add a new analyzer capability. It improves adoption by giving users a trusted example output bundle.

## Goals

- Provide a sample `.ai-debt` bundle or example repository output set.
- Validate required artifacts exist.
- Validate optional and conditional artifacts are labeled correctly.
- Validate JSON artifacts parse and match expected schemas where practical.
- Validate Markdown examples include expected headings.
- Validate sample bundle passes readiness checks.
- Validate sample bundle does not contain secrets or private identifiers.

## Patch Set

Expected files/modules:

```text
docs/examples/sample-ai-debt/                 # new or expanded
scripts/validate_sample_bundle.py             # new, optional
tests/test_sample_ai_debt_bundle.py           # new
docs/QUICKSTART.md
docs/ARTIFACT_CONTRACT.md
```

Recommended sample layout:

```text
docs/examples/sample-ai-debt/
  README.md
  config.yaml
  project-profile.json
  evidence.json
  debt-register.json
  debt-register.md
  reports/
  work-packages/
  ticket-drafts/
  export-bundles/
  portfolio/
  claims/
  traceability/
```

If a full sample bundle is too large, provide a compact fixture bundle with clear documentation of omitted optional artifacts.

Validation rules:

| Check | Requirement |
|---|---|
| JSON parse | All `.json` files parse |
| Required artifacts | Present unless intentionally omitted with explanation |
| Markdown headings | Expected top-level headings exist |
| No secrets | No obvious token/credential placeholders except safe fake examples |
| Readiness | Sample is `ready` or intentionally documented as `partial` |
| Contract alignment | Files correspond to artifact contract categories |

## Tests

Add tests for:

- Sample bundle exists.
- Required JSON files parse.
- Sample debt register has stable finding IDs.
- Sample evidence IDs are referenced correctly.
- Sample work package references known finding IDs.
- Sample ticket drafts reference known work packages.
- Sample export manifest parses.
- Sample claims reference known finding/evidence IDs.
- Sample traceability files exist.
- No obvious secrets appear in sample files.

## Targeted Verification

```bash
pytest tests/test_sample_ai_debt_bundle.py
python scripts/validate_sample_bundle.py docs/examples/sample-ai-debt || true
```

## Expected Behavior

Users and maintainers have a validated sample output bundle that demonstrates what a healthy Pharabius handoff looks like.

## Acceptance Criteria

- Sample `.ai-debt` bundle or compact equivalent exists.
- Sample bundle validation is test-covered.
- JSON examples parse.
- Cross-references are internally consistent.
- Sample contains no secrets or private identifiers.
- No runtime behavior changes are introduced.
- All 7 local gates pass.
## Guardrails

- Do not add a new product capability.
- Do not add new canonical artifact semantics.
- Do not change scoring behavior.
- Do not mutate existing canonical artifacts during validation.
- Do not add external API calls or external service writes.
- Do not create issues, pull requests, tracker tickets, or remediation patches.
- Do not add a server, dashboard, scheduler, database, or remote crawler.
- Do not weaken the no-remediation boundary.
- Keep all additions focused on installation, packaging, examples, diagnostics, adoption, and release readiness.

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

