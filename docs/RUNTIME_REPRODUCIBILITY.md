# Runtime Reproducibility Intelligence

## Signal lifecycle

1. **Parse**: Ecosystem-specific parsers extract raw version strings → `RuntimeEvidence`
2. **Normalize**: Constraint model classifies as EXACT/RANGE/UNPINNED/MISSING/UNKNOWN
3. **Detect conflicts**: Conflict module compares normalized evidence → `RuntimeConflictGroup`
4. **Classify**: Policy module decides FINDING/ADVISORY/INFORMATIONAL
5. **Emit**: Detector converts to `EvidenceItem` and emits to evidence store
6. **Report**: Reporter surfaces runtime summary and conflict details

## Package structure

```text
src/pharabius/core/runtime/
  __init__.py          # Re-exports detect_runtime_version_pins
  models.py            # RuntimeEvidence, RuntimeConstraint, RuntimeConflictGroup
  constraints.py       # normalize_runtime_version, parse_constraint
  ecosystems.py        # Python, Node, Ruby, Java parsers
  go.py                # Go parser (go.mod go + toolchain directives)
  rust.py              # Rust parser (rust-toolchain, rust-toolchain.toml, Cargo.toml)
  dotnet.py            # .NET parser (global.json, .csproj)
  php.py               # PHP parser (composer.json)
  tool_versions.py      # .tool-versions parser (shared)
  docker.py             # Dockerfile FROM line extraction
  github_actions.py     # GitHub Actions workflow parsing
  conflict.py           # Conflict detection from RuntimeEvidence
  policy.py             # classify_conflict, classify_missing_pin, is_runtime_pin
  detector.py           # Orchestrator → EvidenceBuilder
```

Boundary enforcement:
- Parser modules produce `list[RuntimeEvidence]` — do NOT import EvidenceBuilder
- Conflict module consumes `RuntimeEvidence` — does NOT know file formats
- Policy module decides classification — does NOT parse files
- Detector is the only module that imports EvidenceBuilder

## What runtime reproducibility means

Runtime reproducibility means that the same codebase produces consistent results across different environments (development, CI, staging, production). Pharabius detects **runtime version declarations** from multiple sources and flags conflicts or missing declarations.

**Pharabius does NOT:**
- Perform full semantic-version solving
- Scan for runtime vulnerabilities
- Recommend runtime upgrades
- Resolve complex dependency constraints

---

## Supported runtime sources

### Python

| Source | File | Constraint kind |
|--------|------|-----------------|
| Version file | `.python-version` | `exact` |
| Tool versions | `.tool-versions` `python` entry | `exact` |
| Heroku runtime | `runtime.txt` | `exact` |
| Project metadata | `pyproject.toml` `requires-python` | `range` |

### Node.js

| Source | File | Constraint kind |
|--------|------|-----------------|
| NVM | `.nvmrc` | `exact` |
| Version file | `.node-version` | `exact` |
| Tool versions | `.tool-versions` `nodejs` entry | `exact` |
| Package manifest | `package.json` `engines.node` | `range` or `exact` |

### Ruby

| Source | File | Constraint kind |
|--------|------|-----------------|
| Version file | `.ruby-version` | `exact` |
| Tool versions | `.tool-versions` `ruby` entry | `exact` |
| Gem manifest | `Gemfile` `ruby` declaration | `exact` or `range` |

### Java

| Source | File | Constraint kind |
|--------|------|-----------------|
| Version file | `.java-version` | `exact` |
| Tool versions | `.tool-versions` `java` entry | `exact` |
| Maven compiler | `pom.xml` `maven.compiler.release/source` | `exact` |
| Gradle build | `build.gradle` `sourceCompatibility/toolchain` | `exact` |

### Go

| Source | File | Constraint kind | Pin? |
|--------|------|-----------------|------|
| Compatibility baseline | `go.mod` `go` directive | `range` | No |
| Toolchain pin | `go.mod` `toolchain` directive | `exact` | **Yes** |
| Tool versions | `.tool-versions` `golang` entry | `exact` | **Yes** |

Design note: The `go` directive in `go.mod` is a compatibility baseline, not a runtime pin. Only the `toolchain` directive selects a specific Go version for builds.

### Rust

| Source | File | Constraint kind | Pin? |
|--------|------|-----------------|------|
| Toolchain file | `rust-toolchain` | `exact` | **Yes** |
| Toolchain TOML | `rust-toolchain.toml` `channel` | `exact` or `unknown` | Yes if exact |
| Minimum version | `Cargo.toml` `rust-version` | `range` | No |
| Tool versions | `.tool-versions` `rust` entry | `exact` | **Yes** |

Design note: Named channels (`stable`, `beta`, `nightly`) are `UNKNOWN` — informational only. They prove detection but not reproducibility. `rust-version` is a minimum, not a pin.

### .NET

| Source | File | Constraint kind | Pin? |
|--------|------|-----------------|------|
| SDK pin | `global.json` `sdk.version` | `exact` | **Yes** |
| Target framework | `.csproj` `TargetFramework` | `range` | No |
| Multiple targets | `.csproj` `TargetFrameworks` | `range` | No |
| Tool versions | `.tool-versions` `dotnet` entry | `exact` | **Yes** |

Design note: `TargetFramework` describes compatibility intent. `global.json` controls SDK selection. .csproj scanning is bounded-recursive with `bin/`, `obj/`, and other build directories excluded.

### PHP

| Source | File | Constraint kind | Pin? |
|--------|------|-----------------|------|
| Manifest exact | `composer.json` `require.php` (exact) | `exact` | Yes (lower) |
| Manifest range | `composer.json` `require.php` (range) | `range` | No |
| Tool versions | `.tool-versions` `php` entry | `exact` | **Yes** |

### Container evidence

| Source | Pattern | Constraint kind |
|--------|---------|-----------------|
| Dockerfile | `FROM python:3.12` etc. | `exact` |
| Dockerfile (ARG) | `FROM python:${VERSION}` | `partial` |

### CI evidence

| Source | Pattern | Constraint kind |
|--------|---------|-----------------|
| GitHub Actions | `actions/setup-python` etc. | `exact` |
| GitHub Actions (matrix) | `${{ matrix.python-version }}` | `partial` |

---

## Constraint kinds

Every detected runtime source is classified with a constraint kind:

| Kind | Meaning | Conflict participation |
|------|---------|----------------------|
| `exact` | Specific version pinned | Yes — can conflict with other exacts |
| `range` | Version range/constraint | Limited — only conflicts if it clearly excludes an exact |
| `partial` | Version unknown (ARG, matrix, env var) | No — evidence only |
| `unknown` | Cannot determine | No — evidence only |

---

## Conflict detection policy

### Definite conflict → finding

```
exact vs exact: normalized versions disagree
  Example: .python-version=3.11, .tool-versions python=3.12 → CONFLICT

range vs exact: range clearly excludes exact version
  Example: requires-python=">=3.12", .python-version=3.11 → CONFLICT
```

### No conflict

```
exact vs exact: normalized versions agree
  Example: .python-version=3.12, .nvmrc is Node (different runtime) → no conflict

range vs exact: range is compatible with exact
  Example: engines.node=">=18", .nvmrc=20 → NO CONFLICT

range vs range: both are ranges
  Example: requires-python=">=3.11", .python-version=3.12 → NO CONFLICT

partial vs anything: partial evidence never conflicts
  Example: FROM python:${VERSION} vs .python-version=3.12 → no conflict
```

### Version normalization

| Runtime | Comparison level |
|---------|-----------------|
| Python | major.minor (3.12) |
| Node.js | major only (20) |
| Ruby | major.minor (3.3) |
| Java | major only (17) |

---

## Missing-pin advisory policy

Missing runtime pin advisories are emitted only when a **manifest-based trigger** exists. Source files alone do NOT trigger advisories.

| Runtime | Triggers when these exist |
|---------|--------------------------|
| Python | `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile`, `runtime.txt` |
| Node.js | `package.json` |
| Ruby | `Gemfile`, `.gemspec` |
| Java | `pom.xml`, `build.gradle`, `build.gradle.kts` |
| Go | `go.mod` |
| Rust | `Cargo.toml`, `rust-toolchain`, `rust-toolchain.toml` |
| .NET | `global.json`, `*.csproj`, `*.sln` |
| PHP | `composer.json` |

Missing-pin advisories:
- Are classified as `issue_type="advisory"` (not technical debt)
- Do NOT generate work packages
- Do NOT generate operational claims
- Are reported in the advisory section of the debt report

---

## Known limitations

1. **No full semver solving.** Comparison is major/minor or major-only. Complex ranges are assumed compatible.
2. **Range vs range never conflicts** in v3.8.0.
3. **Dockerfile internal conflicts deferred.** Multi-stage builds with different runtimes are legitimate.
4. **GitHub Actions only.** GitLab CI and CircleCI not supported.
5. **Java detection is conservative.** Maven profiles and Gradle script logic are not parsed.
6. **Ruby is runtime-only.** No Gemfile dependency resolution or Gemspec analysis.
7. **Malformed YAML produces limitation evidence.** No attempt to recover from malformed CI configs.
8. **Go `go` directive is not a pin.** Only `toolchain` provides reproducibility evidence.
9. **Rust named channels are informational.** `stable`/`beta`/`nightly` do not prove reproducibility.
10. **.NET TargetFramework is not a pin.** Only `global.json` SDK version counts.
11. **PHP Composer ranges are not pins.** Broad ranges prove compatibility, not reproducibility.

## v3.12.0 — Signal Governance Integration

Runtime evidence now adapts into platform-level governed signals via `core/signals/adapters.py`:
- Runtime conflicts → `GovernedSignal(disposition=FINDING)`
- Missing pins → `GovernedSignal(disposition=ADVISORY)`
- Observed evidence → `GovernedSignal(disposition=INFORMATIONAL)`

The analyzer consumes dispositions through explicit branching (no catch-all fallback).
Runtime-specific IR (`RuntimeEvidence`, `RuntimeConflictGroup`) is preserved unchanged.
See `docs/SIGNAL_GOVERNANCE.md` for the full signal lifecycle.
