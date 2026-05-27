# Pharabius v1 Stability Contract

**Effective version**: v1.11.0  
**Status**: Stable declaration  
**Last updated**: 2026-05-27

## Purpose

This document defines what Pharabius considers stable for the v1 product line. It specifies compatibility commitments, allowed maintenance changes, and boundaries reserved for v2.0.

## Stable v1 Surface

The following surfaces are declared stable for the v1 line (v1.0.0 through v1.x):

### Artifact Paths

All `.ai-debt/` artifact paths produced by v1 commands are stable. Renaming or removing an artifact path requires v2.0.

### Schema Compatibility

All Pydantic schemas with `schema_version: "1.0"` follow an additive-only policy during v1.x:

- New optional fields may be added.
- Existing fields will not be removed or renamed.
- Existing field semantics will not change.
- `schema_version` will remain `"1.0"` for compatible changes.

### Command Surface

The following 18 CLI commands are stable within v1.x:

| Command | Status |
|---|---|
| `ai-debt init` | Stable |
| `ai-debt profile` | Stable |
| `ai-debt scan` | Stable |
| `ai-debt map-units` | Stable |
| `ai-debt analyze` | Stable |
| `ai-debt report` | Stable |
| `ai-debt plan` | Stable |
| `ai-debt verify` | Stable |
| `ai-debt status` | Stable |
| `ai-debt graph` | Stable |
| `ai-debt export` | Stable |
| `ai-debt enrich` | Stable |
| `ai-debt ai-status` | Stable |
| `ai-debt run` | Stable |
| `ai-debt review` | Stable |
| `ai-debt tickets` | Stable |
| `ai-debt portfolio` | Stable |
| `ai-debt doctor` | Stable |

Removing or renaming a command requires v2.0. New commands may be added in v1.x if they are diagnostic-only and do not modify canonical artifacts.

### Default Behavior

Default command behavior must not become more destructive or externally connected within v1.x. Any change that would produce different canonical output by default requires a minor version bump and release notes.

## Safety Boundary Commitments

These boundaries are non-negotiable for the entire v1 line:

| Boundary | Commitment |
|---|---|
| No code modification | Pharabius will never modify production or source code |
| No external API writes | Pharabius will never write to external tracker systems, CI systems, or cloud services |
| No autonomous remediation | Pharabius will never generate or apply code patches |
| Repository-local output | All output is written to `.ai-debt/` within the analyzed repository |
| No network requirements | Core workflow requires no network access |
| Deterministic by default | Default analysis is fully deterministic; AI features are opt-in |
| Agent-handoff safety | Agent-handoff contract explicitly forbids code modification |

## Local-First Commitments

- No server, dashboard, scheduler, or database is required.
- No remote repository crawling.
- All analysis runs against local filesystem.
- Portfolio summaries aggregate local `.ai-debt/` directories.

## Allowed v1.x Changes

The following changes are permitted within v1.x without requiring v2.0:

- Adding new optional schema fields.
- Adding new CLI flags that default to current behavior.
- Adding new diagnostic commands or scripts.
- Adding new export bundle formats.
- Adding new governance presets.
- Improving documentation, examples, and adoption materials.
- Improving test coverage.
- Fixing bugs that produce incorrect output.
- Adding new analysis rules within existing categories.
- Improving error messages and diagnostics.
- Adding new optional configuration keys.

## Changes Reserved for v2.0

The following changes require a v2.0 major version:

- Removing or renaming v1 artifact paths.
- Breaking schema field compatibility (removing/renaming existing fields).
- Removing or renaming v1 CLI commands.
- Adding default external writes (API calls, tracker integration).
- Adding autonomous remediation or code modification.
- Requiring a server, database, scheduler, or cloud service.
- Changing default scoring behavior in a way that reorders canonical outputs.
- Removing safety boundaries.
- Changing the local-first commitment.
- Requiring network access for core workflow.

## Deprecation Policy

- Deprecated features will be announced in CHANGELOG.md with at least one minor version of notice.
- Deprecated features will continue to work throughout v1.x.
- Removal of deprecated features requires v2.0.

## Versioning Policy

- **Patch (v1.x.Z)**: Bug fixes, documentation, test improvements. No behavioral changes.
- **Minor (v1.Y.0)**: New optional features, new commands, new presets. Additive-only schema changes. Default behavior preserved.
- **Major (v2.0.0)**: Breaking changes as listed above.

## Scope

This contract applies to the Pharabius CLI tool and its produced artifacts. It does not apply to:

- Internal implementation details (module structure, function signatures).
- Test infrastructure (test file names, fixture formats).
- Development tooling (linting config, CI workflows).
- Documentation file organization (may be restructured within v1.x).

## Related Documentation

- [Artifact Contract](ARTIFACT_CONTRACT.md)
- [CLI Reference](CLI.md)
- [Schema Map](SCHEMA_MAP.md)
- [Adoption Checklist](ADOPTION_CHECKLIST.md)
