# Operating Doctrine — Disk-Verified Large-Wave Execution

> **Version:** 1.0
> **Established:** v3.0.1
> **Applies to:** All Pharabius releases from v3.0.0 onward

## Purpose

This document defines how large development waves are planned, executed, validated, and published. It exists because the v3 governance arc (v3.16.0–v3.26.0) was developed as 11 internal wave releases over an extended period without public visibility, creating a credibility gap that required a complex catch-up release (v3.0.0).

Future waves must not repeat this pattern.

## Principles

### 1. Public baseline is always clean

The public `master` branch must always be in a releasable state:
- All tests pass
- `ruff format --check .` and `ruff check .` are clean
- Package builds (`python -m build`) succeed
- CHANGELOG reflects current state

### 2. No invisible large waves

Development waves larger than 3 releases or 200+ tests must be published incrementally. The v3.0.0 catch-up was a one-time event justified by the transition from private to public development. Future work ships as it lands.

### 3. Internal wave tags stay local

The internal wave tags (v3.1.0–v3.15.0) are local development markers. They are never pushed to GitHub. This is documented in:

- `docs/RELEASE_STATE.md` — tag policy
- `docs/internal-v3-local-tags-before-public-sync.txt` — tag inventory
- This document — permanent reference

**Forbidden commands on any repository with a GitHub remote:**

```
git push --tags
git push --follow-tags
```

**Only use:**

```
git push origin <specific-tag>
```

### 4. Version numbering after catch-up

From v3.0.0 onward, versions follow semantic versioning publicly:

- **v3.0.x** — Stabilization patches (no new capability)
- **v3.x.0** — Capability increments (new adapters, connectors, features)
- **v4.0.0** — Breaking changes (major version)

Internal development may use descriptive branch names instead of version tags.

### 5. Disk-verified before merge

Before any PR is merged:

1. **Tests pass locally** — `pytest tests/ --tb=short -q --no-cov`
2. **Formatting clean** — `ruff format --check .`
3. **Lint clean** — `ruff check .`
4. **Package builds** — `python -m build`
5. **Platform backend** — `cd platform/backend && pytest tests/ --tb=short -q --no-cov`
6. **Platform frontend** — `cd platform/frontend && npx vitest run && npx vite build`

All six must pass. CI enforces what it can, but local verification runs first.

### 6. CI is the gate, not the verifier

CI validates what the developer already verified locally. CI failures mean the developer didn't check before pushing, not that CI found something unexpected.

Exception: CI may catch platform-specific issues (Linux vs Windows path differences, Python version quirks). These are legitimate CI-only findings.

## Release Checklist

For each public release:

- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG entry added (not "Unreleased")
- [ ] All local verification steps pass
- [ ] Branch pushed (no tags)
- [ ] PR opened with validation results in body
- [ ] CI green on all checks
- [ ] Merged via GitHub PR
- [ ] Master pulled
- [ ] Remote tag absence confirmed
- [ ] Tag created at merge commit with `git tag -a`
- [ ] Tag pushed with `git push origin <tag>` only
- [ ] GitHub release published with validation summary

## Known Technical Debt

These items are tracked as stabilization targets, not blocking issues:

| Item | Severity | Notes |
|---|---|---|
| mypy strict mode (55 errors) | Medium | Pre-existing; continue-on-error in CI |
| import-linter config missing | Low | Pre-existing; continue-on-error in CI |
| Frontend TypeScript mock errors (5) | Low | Tests pass, build succeeds, types need cleanup |
| `platform/backend/tests` cwd sensitivity | Low | Alembic tests require running from `platform/backend/` |
| `benchmarks` module not in package | Low | Tests import it via PYTHONPATH in CI |

## Wave Size Guidance

| Wave Type | Max Releases | Max New Tests | Publish Cadence |
|---|---|---|---|
| Stabilization | 1 | 0–20 | Immediate |
| Feature slice | 1–3 | 20–100 | Per slice |
| Capability wave | 4–8 | 100–500 | Per slice, incremental |
| Major version | Full planning | Full planning | After vNext planning doc |

The v3 governance arc (11 releases, 503 tests) would now be published as 4–8 incremental PRs under this doctrine, not as a single catch-up.

---

## Appendix: v3.0.0 Catch-Up Retrospective

The v3.0.0 catch-up release consolidated 25 commits and 229 changed files into a single PR. The process required 6 CI iterations to achieve green:

| Iteration | Issue | Fix |
|---|---|---|
| 1 | DCO sign-off missing | `git rebase --signoff` |
| 2 | 59 files unformatted | `ruff format` on full codebase |
| 3 | Action installed from PyPI | `pip install -e ".[openai-compatible]"` |
| 4 | 37 ruff E-level errors | noqa + fixes |
| 5 | mypy/lint-imports pre-existing failures | continue-on-error |
| 6 | benchmarks import error on CI | PYTHONPATH in CI config |

This retrospective is preserved to remind future maintainers that catching up is expensive. Ship incrementally.
