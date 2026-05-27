# Wave 50 — v1.10.2 RC2 Adoption & Packaging Hardening

Goal: Harden installation, packaging, examples, release artifacts, CLI onboarding, and adoption documentation before v1 final-style declaration, without adding new product capability.

Release target: `v1.10.2`  
Branch target: `roadmap/v1.10.2-rc2-adoption-packaging`  
Boundary: Hardening, validation, packaging, examples, and adoption documentation only. No new product capability.

# W50-S01 — Installation and Packaging Verification Matrix

Risk: Medium  
Slice type: Packaging / install verification  
Artifact impact: New validation documentation and optional validation script only

## Scope

Create an installation and packaging verification matrix for Pharabius v1.10.2. This slice validates that the package can be built, installed, imported, and executed through the CLI in representative local environments.

This slice should not introduce new runtime product behavior. It may add scripts/tests that verify existing installation and packaging assumptions.

## Goals

- Define a packaging verification matrix.
- Validate source tree execution.
- Validate wheel build output.
- Validate sdist build output.
- Validate package metadata.
- Validate `ai-debt --version` or equivalent version display.
- Validate CLI entrypoint availability after install.
- Validate importability of key modules.
- Document supported Python version expectations.
- Keep the process offline and local.

## Patch Set

Expected files/modules:

```text
scripts/validate_packaging.py                  # new, optional
scripts/validate_release_artifacts.py          # optional, can defer to S04
tests/test_packaging_metadata.py               # new
docs/PACKAGING.md                              # new or expanded in S06
```

Recommended verification matrix:

| Environment | Check |
|---|---|
| Source checkout | `python -m pharabius.cli --version` |
| Wheel install | CLI entrypoint exists |
| sdist install | package imports successfully |
| Python minimum version | package metadata matches `pyproject.toml` |
| Clean venv | dependencies resolve |
| Build artifacts | wheel and sdist names contain `1.10.2` |

Recommended script behavior:

```bash
python scripts/validate_packaging.py --dist dist/
```

The script should report:

- build artifacts found
- expected version
- wheel filename
- sdist filename
- import check status
- CLI entrypoint check status
- warnings/errors

## Tests

Add tests for:

- Package metadata version can be read.
- `pyproject.toml` version matches expected release target when appropriate.
- Wheel/sdist filename parser handles expected names.
- Packaging validation returns structured success for valid fixture artifacts.
- Packaging validation returns actionable error for missing wheel.
- Packaging validation returns actionable error for missing sdist.
- No network access is required.

## Targeted Verification

```bash
pytest tests/test_packaging_metadata.py
python -m build
python scripts/validate_packaging.py --dist dist/
python -m pharabius.cli --version || ai-debt --version
```

## Expected Behavior

The repository includes a repeatable way to verify that a release package is buildable, installable, importable, and exposes the expected CLI entrypoint.

Example report:

```text
Packaging validation: ready
Version: 1.10.2
Wheel: found
sdist: found
CLI entrypoint: available
Imports: ok
```

## Acceptance Criteria

- Packaging verification matrix is defined.
- Build artifacts can be validated locally.
- Version consistency is checked.
- CLI entrypoint is checked.
- Importability is checked.
- No external network or service dependency is introduced.
- No product behavior changes are introduced.
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

