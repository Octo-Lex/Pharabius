# Wave 50 — v1.10.2 RC2 Adoption & Packaging Hardening

Goal: Harden installation, packaging, examples, release artifacts, CLI onboarding, and adoption documentation before v1 final-style declaration, without adding new product capability.

Release target: `v1.10.2`  
Branch target: `roadmap/v1.10.2-rc2-adoption-packaging`  
Boundary: Hardening, validation, packaging, examples, and adoption documentation only. No new product capability.

# W50-S02 — CLI Onboarding and First-Run Diagnostics

Risk: Medium  
Slice type: CLI diagnostics / onboarding polish  
Artifact impact: Help text, diagnostics output, optional report only

## Scope

Improve first-run CLI onboarding and diagnostics without adding new product capability. The goal is to help new users understand the recommended command sequence, required artifacts, missing prerequisites, and safe next steps.

This slice may add a diagnostic command or improve existing help output, but it must not alter the behavior of existing analysis/scoring/reporting commands.

## Goals

- Make CLI help text consistent with v1.10 command surface.
- Add or improve first-run diagnostics.
- Detect missing `.ai-debt/` workspace and recommend `ai-debt init`.
- Detect missing profile/evidence/debt-register artifacts and recommend next command.
- Detect missing optional artifacts without treating them as hard failures.
- Distinguish required, optional, and conditional artifacts.
- Preserve command safety classifications.

## Patch Set

Expected files/modules:

```text
src/pharabius/cli.py
src/pharabius/core/v1_readiness.py
src/pharabius/core/artifact_contract.py
tests/test_cli_onboarding.py                  # new
docs/CLI.md
```

Potential CLI shape options:

Option A — improve existing commands only:

```bash
ai-debt --help
ai-debt init --help
ai-debt validate --help
```

Option B — add a diagnostics command if it fits current command model:

```bash
ai-debt doctor
```

If adding `doctor`, keep it diagnostic only. It should not create, modify, or repair files.

Recommended diagnostic output:

```text
Pharabius workspace diagnostics
Status: needs_review
Required artifacts:
  ✓ config.yaml
  ✗ project-profile.json — run: ai-debt profile
  ✗ evidence.json — run: ai-debt scan
  ✗ debt-register.json — run: ai-debt analyze
Next recommended command: ai-debt profile
```

## Tests

Add tests for:

- Help text includes safe command sequence.
- First-run diagnostics handle missing `.ai-debt/` gracefully.
- Diagnostics identify missing required artifacts.
- Diagnostics do not classify optional artifacts as required.
- Diagnostics recommend the next command deterministically.
- Diagnostics do not mutate the workspace.
- Command safety classification appears in CLI docs.
- Existing command behavior remains unchanged.

## Targeted Verification

```bash
pytest tests/test_cli_onboarding.py
python -m pharabius.cli --help
python -m pharabius.cli init --help
python -m pharabius.cli validate --help || true
python -m pharabius.cli doctor || true
```

## Expected Behavior

A new user can run help/diagnostics and understand exactly where they are in the Pharabius workflow and what command should run next.

Diagnostics must be read-only.

## Acceptance Criteria

- CLI onboarding is clearer and consistent with v1.10 command surface.
- Missing required artifacts produce actionable diagnostics.
- Optional/conditional artifacts are not treated as hard failures.
- Diagnostics are read-only.
- Existing command behavior is not changed.
- No new product capability is added.
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

