# CLI Command Reference

This document lists every command in the `ai-debt` CLI surface with its purpose, safety classification, and artifact output.

## Command Inventory

| Command | Purpose | Writes Artifacts | Safety |
|---|---|---|---|
| `ai-debt init` | Create `.ai-debt/` workspace | config.yaml | Safe |
| `ai-debt profile` | Detect repository structure | project-profile.json | Regenerates |
| `ai-debt scan` | Collect repository evidence | evidence.json | Regenerates |
| `ai-debt map-units` | Map evidence to analysis units | analysis-units.json | Regenerates |
| `ai-debt graph` | Build import dependency graph | architecture-graph.json | Regenerates |
| `ai-debt analyze` | Generate deterministic findings | debt-register.json/.md | Regenerates |
| `ai-debt report` | Generate Markdown reports | reports/* | Regenerates |
| `ai-debt plan` | Generate remediation plan | roadmap, work packages, handoff | Regenerates |
| `ai-debt verify` | Verify findings against evidence | — (read-only) | Read-only |
| `ai-debt status` | Show workspace status | — (read-only) | Read-only |
| `ai-debt export` | Export to SARIF/CSV/JSONL | export-bundles/* | Regenerates, no external APIs |
| `ai-debt enrich` | AI enrichment sidecar | ai/* | Sidecar only |
| `ai-debt ai-status` | Show AI sidecar status | — (read-only) | Read-only |
| `ai-debt run` | Full pipeline + metadata | All canonical + runs/* | Regenerates |
| `ai-debt review` | Manage review decisions | review/decisions.json | Non-canonical sidecar |
| `ai-debt tickets` | Generate ticket drafts | ticket-drafts/* | Local only, no external issues |
| `ai-debt portfolio` | Portfolio summary | portfolio/* | Read-only rollup, no remote |
| `--version` | Show version | — | Read-only |

## Safety Classifications

| Classification | Meaning |
|---|---|
| **Safe** | Creates initial workspace, no analysis artifacts |
| **Regenerates** | Overwrites previous output each run |
| **Read-only** | Produces no files, only prints to stdout |
| **Sidecar only** | Writes to non-canonical sidecar directory |
| **Non-canonical sidecar** | Writes workflow state that does not affect findings |
| **Local only, no external issues** | Generates local files; no tracker API calls |
| **Read-only rollup, no remote** | Aggregates existing local artifacts; no network |

## Pipeline Order

The recommended command sequence for a full analysis:

```
ai-debt init          # Create workspace
ai-debt profile       # Detect structure
ai-debt scan          # Collect evidence
ai-debt map-units     # Map analysis units
ai-debt graph         # Build dependency graph (optional, for TD-ARCH)
ai-debt analyze       # Generate findings
ai-debt report        # Generate reports
ai-debt plan          # Generate remediation plan
```

Or use the single-command pipeline:

```
ai-debt run           # All of the above plus run metadata
```

## Post-Analysis Commands

After `analyze` and `plan`:

```
ai-debt verify        # Cross-check findings
ai-debt status        # Show workspace summary
ai-debt review --init # Initialize PET review sidecar
ai-debt tickets       # Generate ticket drafts
ai-debt export        # Export bundles for trackers
ai-debt portfolio     # Multi-repo portfolio summary
```

## Related Documentation

- [Artifact Contract](ARTIFACT_CONTRACT.md)
- [Schema Map](SCHEMA_MAP.md)
- [Adoption Guide](ADOPTION_GUIDE.md)
