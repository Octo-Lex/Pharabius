# Dependency Signals

Pharabius produces local dependency health evidence by reading manifest and
lockfile contents. It does not resolve dependency graphs, check live CVEs,
or recommend safe upgrade versions.

## Philosophy

Dependency signals are local observations about version pinning discipline
and lockfile consistency. They are **not** vulnerability assessments.

A finding about unpinned dependencies means "this manifest uses broad version
ranges," not "this dependency is unsafe."

## Supported manifest formats

| Format             | Signals detected                                         |
|--------------------|----------------------------------------------------------|
| `package.json`     | Unpinned dependencies, `engines.node` runtime pin        |
| `requirements.txt` | Unpinned dependencies                                    |
| `pyproject.toml`   | PEP 621 deps, optional deps, Poetry deps, Poetry groups  |
| `Pipfile`          | Unpinned deps, lockfile consistency                      |

## Supported lockfile consistency signals

| Signal                                   | Condition                                |
|------------------------------------------|------------------------------------------|
| `lockfile_conflict`                      | Multiple Node.js lockfiles coexist       |
| `poetry_manifest_without_lockfile`       | Poetry in pyproject.toml, no poetry.lock |
| `poetry_lockfile_without_manifest`       | poetry.lock exists, no Poetry section    |
| `pipfile_without_lockfile`               | Pipfile exists, no Pipfile.lock          |
| `pipfile_lock_without_manifest`          | Pipfile.lock exists, no Pipfile          |

## Pinning classifier

`classify_python_specifier(specifier, source_format)` in `dependency_utils.py`
classifies dependency strings as `pinned`, `broad`, or `unknown`.

### PEP 508 examples

| Specifier            | Classification | Why                    |
|----------------------|----------------|------------------------|
| `requests==2.31.0`  | pinned         | Exact pin with `==`    |
| `requests===2.31.0` | pinned         | Exact pin with `===`   |
| `package @ file://`  | pinned         | Direct reference       |
| `requests`           | broad          | No version constraint  |
| `requests>=2.0`      | broad          | Minimum-only           |
| `requests~=2.0`      | broad          | Compatible release     |
| `requests<3`         | broad          | Upper bound only       |
| `requests>=2,<3`     | broad          | Compound range         |

### Poetry / Pipfile examples

| Specifier | Classification | Why                    |
|-----------|----------------|------------------------|
| `^3.11`   | broad          | Caret allows minor     |
| `~2.0`    | broad          | Tilde allows patch     |
| `1.2.3`   | pinned         | Exact version          |
| `*`       | broad          | Wildcard               |

## Runtime version pinning

| File                        | Runtime         | Signal                    |
|-----------------------------|-----------------|---------------------------|
| `.python-version`           | Python          | `runtime_version_pinned`  |
| `.nvmrc`                    | Node.js         | `runtime_version_pinned`  |
| `.node-version`             | Node.js         | `runtime_version_pinned`  |
| `.tool-versions`            | Python, Node.js | `runtime_version_pinned`  |
| `package.json` engines.node | Node.js         | `runtime_version_pinned`  |

Missing runtime pins emit `runtime_version_missing` when a relevant manifest
exists. This is framed as **reproducibility evidence**, not a security finding.

## What Pharabius does not claim

- Does not resolve dependency graphs
- Does not check live CVEs
- Does not recommend safe upgrade versions
- Does not claim a dependency is vulnerable
- Does not treat missing runtime pins as security vulnerabilities

## Signal governance (v3.16.0)

Dependency signals are now governed through `SignalFamily.DEPENDENCY`.
Adapters in `dependency_adapters.py` convert dependency evidence into
`GovernedSignal` instances with deterministic dispositions.

The analyzer uses `output_behavior()` for promotion decisions instead of
hardcoded branching. Output before and after migration is identical.

See `docs/SIGNAL_GOVERNANCE.md` for the full governance model.

## Deferred formats

These are not yet supported:

- `Pipfile` extras and `[requires]` section
- `pyproject.toml` Poetry extras
- `pnpm-lock.yaml` content parsing
- Ruby `Gemfile` / `Gemfile.lock`
- Java `pom.xml` dependency resolution
- `.tool-versions` Ruby / Java entries
- Runtime version conflict detection
