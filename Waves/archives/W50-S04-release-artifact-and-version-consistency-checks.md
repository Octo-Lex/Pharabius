# Wave 50 — v1.10.2 RC2 Adoption & Packaging Hardening

Goal: Harden installation, packaging, examples, release artifacts, CLI onboarding, and adoption documentation before v1 final-style declaration, without adding new product capability.

Release target: `v1.10.2`  
Branch target: `roadmap/v1.10.2-rc2-adoption-packaging`  
Boundary: Hardening, validation, packaging, examples, and adoption documentation only. No new product capability.

# W50-S04 — Release Artifact and Version Consistency Checks

Risk: Medium  
Slice type: Release validation / consistency checks  
Artifact impact: Validation script/tests only

## Scope

Add release artifact and version consistency checks so the release process can verify that source metadata, package metadata, build outputs, changelog, roadmap, docs, and CLI-reported version all agree.

This slice should not change product behavior except possibly centralizing version reading if the existing implementation is inconsistent.

## Goals

- Check `pyproject.toml` version.
- Check package import metadata version.
- Check CLI `--version` output.
- Check wheel and sdist filenames.
- Check `CHANGELOG.md` has a matching release entry.
- Check `ROADMAP.md` reflects current release state.
- Check docs do not advertise stale versions where avoidable.
- Produce actionable mismatch errors.

## Patch Set

Expected files/modules:

```text
scripts/validate_release_consistency.py        # new
src/pharabius/__init__.py                      # only if needed for centralized version
tests/test_release_consistency.py             # new
CHANGELOG.md                                  # release entry later in S06
ROADMAP.md                                    # release entry later in S06
```

Recommended script usage:

```bash
python scripts/validate_release_consistency.py --expected-version 1.10.2 --dist dist/
```

Recommended checks:

| Source | Check |
|---|---|
| `pyproject.toml` | version equals expected |
| installed metadata | version equals expected |
| CLI output | contains expected version |
| wheel filename | contains expected version |
| sdist filename | contains expected version |
| changelog | has `v1.10.2` entry |
| roadmap | references `v1.10.2` |

## Tests

Add tests for:

- Valid version set passes.
- Mismatched pyproject version fails.
- Missing changelog entry fails.
- Missing roadmap entry fails.
- Missing wheel fails when dist validation requested.
- Missing sdist fails when dist validation requested.
- Error messages identify the mismatched source.
- Script can run without network access.

## Targeted Verification

```bash
pytest tests/test_release_consistency.py
python -m build
python scripts/validate_release_consistency.py --expected-version 1.10.2 --dist dist/
```

## Expected Behavior

Release maintainers can run one command to confirm that v1.10.2 metadata is internally consistent before tagging.

Example output:

```text
Release consistency: ready
Expected version: 1.10.2
pyproject: ok
CLI: ok
wheel: ok
sdist: ok
changelog: ok
roadmap: ok
```

## Acceptance Criteria

- Release consistency script exists and is test-covered.
- Version mismatches produce actionable failures.
- Build artifact names are checked.
- Changelog and roadmap release entries are checked.
- No product behavior changes are introduced beyond version reporting consistency.
- No external network dependency is introduced.
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

