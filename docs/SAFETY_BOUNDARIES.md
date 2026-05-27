# Pharabius v1 Safety Boundaries

**Effective version**: v1.11.0  
**Status**: Stable commitment  
**Last updated**: 2026-05-27

This document defines the non-negotiable safety boundaries for the Pharabius v1 product line.

## Boundary 1: No Production Code Modification

Pharabius never modifies, patches, or rewrites production or source code. All output is analytical and planning-focused. Remediation plans describe *what should change*, not *how to change it*.

## Boundary 2: No Autonomous Remediation

Pharabius never generates or applies code patches, pull requests, or automated fixes. Work packages and ticket drafts are human-readable recommendations that require human review and manual implementation.

## Boundary 3: No External API Writes

Pharabius never writes to external systems including:

- Issue trackers (Jira, Linear, GitHub Issues, Azure DevOps)
- CI/CD systems
- Cloud services
- Chat systems
- Any external API

Export bundles are local file artifacts that users manually import.

## Boundary 4: No Issue Creation

Pharabius does not create issues, tickets, work items, or pull requests in any external system. Ticket drafts are local Markdown files. Export bundles are tracker-preparation artifacts requiring manual import.

## Boundary 5: No Remote Repository Crawling

Pharabius operates exclusively on local filesystem paths. It does not:

- Clone repositories
- Fetch from remotes
- Access GitHub/GitLab/Bitbucket APIs
- Require network access for core workflow

Portfolio summaries aggregate pre-existing local `.ai-debt/` directories.

## Boundary 6: No Dashboard/Server/Database Requirement

Pharabius requires no:

- Web server or dashboard
- Database or persistent storage service
- Scheduler or background worker
- Cloud service or hosted component

All operations are CLI-driven, local, and stateless between runs.

## Boundary 7: No Risk Acceptance Decisions

Pharabius produces risk assessments and severity ratings as advisory information. It does not:

- Accept or reject risk on behalf of users
- Make go/no-go deployment decisions
- Override human engineering judgment
- Prescribe specific remediation timelines

## Boundary 8: Human Ownership Model

All Pharabius outputs are recommendations for human review:

- Findings require human triage
- Work packages require human approval
- Ticket drafts require human review before import
- Review decisions require human input
- Operational claims require human validation
- Agent-handoff contracts require human acceptance

## Command Safety Classifications

| Command | Classification | Writes |
|---|---|---|
| `ai-debt init` | Repository-local artifact writer | Creates `.ai-debt/` structure |
| `ai-debt profile` | Repository-local artifact writer | Writes `project-profile.json` |
| `ai-debt scan` | Repository-local artifact writer | Writes `evidence.json` |
| `ai-debt map-units` | Repository-local artifact writer | Writes `analysis-units.json` |
| `ai-debt analyze` | Repository-local artifact writer | Writes `debt-register.json`, `debt-register.md` |
| `ai-debt report` | Repository-local artifact writer | Writes reports under `.ai-debt/reports/` |
| `ai-debt plan` | Repository-local artifact writer | Writes work packages, roadmap |
| `ai-debt verify` | Read-only diagnostic | Console output only |
| `ai-debt status` | Read-only diagnostic | Console output only |
| `ai-debt graph` | Repository-local artifact writer | Writes `architecture-graph.json` |
| `ai-debt export` | Export artifact writer | Writes local export bundle files |
| `ai-debt enrich` | Repository-local artifact writer | Writes AI sidecar under `.ai-debt/ai/` |
| `ai-debt ai-status` | Read-only diagnostic | Console output only |
| `ai-debt run` | Repository-local artifact writer | Orchestrates write commands |
| `ai-debt review` | Repository-local artifact writer | Writes `.ai-debt/review/decisions.json` (init only) |
| `ai-debt tickets` | Repository-local artifact writer | Writes local ticket drafts |
| `ai-debt portfolio` | Repository-local artifact writer | Writes local portfolio summary |
| `ai-debt doctor` | Read-only diagnostic | Console output only |

## Agent-Handoff Limitations

The agent-handoff contract (`agent-handoff-contract.md`) explicitly states:

- It does **not** authorize code modification.
- It does **not** authorize autonomous remediation.
- It does **not** authorize external system writes.
- It describes forbidden actions explicitly.
- It requires human validation for all claims.

## Related Documentation

- [v1 Stability Contract](V1_STABILITY_CONTRACT.md)
- [Artifact Contract](ARTIFACT_CONTRACT.md)
- [CLI Reference](CLI.md)
- [Adoption Checklist](ADOPTION_CHECKLIST.md)
