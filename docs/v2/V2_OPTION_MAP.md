# Pharabius v2 Option Map

**Status**: Planning draft  
**Date**: 2026-05-27  
**Not an implementation commitment**

This document maps credible v2 expansion options. Each option includes value, risk, boundary implications, and a preliminary trust-model assessment.

## Option Categories

### A. Governed Automation

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| A1: Approval-gated patch proposals | Generate code change proposals with human approval gate | High (actionable remediation) | High (code modification boundary) | Requires explicit opt-in, preview, reject/approve flow |
| A2: Controlled refactoring plans | Structured refactoring plans with step-by-step verification | Medium | Medium | Preview-only; execution remains human |
| A3: Dependency update suggestions | Specific version upgrade recommendations with changelog diff | Medium | Low | Advisory only; no auto-apply |

### B. Human Validation Workflow

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| B1: Claim review and sign-off records | Structured review workflow for operational claims | High (governance) | Low | Read-only records; no mutations |
| B2: Gap closure tracking | Track when blocking gaps are resolved | Medium | Low | Status tracking only |
| B3: Risk acceptance records | Formal risk acceptance with rationale | Medium | Medium | Requires clear "not a guarantee" language |

### C. External Integrations

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| C1: Tracker write APIs (Jira, Linear, GitHub, Azure) | Create issues/tickets from ticket drafts | High (workflow integration) | High (external writes) | Requires explicit consent per write; preview first |
| C2: CI/CD integration (GitHub Actions, etc.) | Run Pharabius in CI pipelines with structured output | Medium | Low | Read-only in CI; same local-first |
| C3: Notification channels (Slack, email) | Send summary notifications on analysis completion | Low | Low | Opt-in; no analysis changes |

### D. Portfolio Platform

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| D1: Web dashboard | Interactive visualization of portfolio data | High (visibility) | Medium (requires server) | Read-only dashboard; no mutations |
| D2: REST API | API for querying portfolio data | Medium | Medium (requires server) | Read-only queries |
| D3: Scheduled audits | Periodic automated analysis runs | Medium | Medium (requires scheduler) | Same local-first analysis; scheduling is orchestration |

### E. Organization-Scale Scanning

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| E1: Remote repo discovery | Scan GitHub/GitLab organizations for repos | High (scale) | High (network access, auth) | Discovery is read-only; analysis remains local |
| E2: Multi-repo policy engine | Define org-wide debt policies | High (governance) | Medium (policy complexity) | Policy is declarative; enforcement is advisory |
| E3: Cross-repo dependency mapping | Map dependencies across repositories | Medium | Medium (scale, accuracy) | Read-only analysis |

### F. Policy Engine

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| F1: Custom scoring rules | User-defined scoring formulas | Medium | Low | Local config; no external impact |
| F2: Artifact completeness policies | Required artifact enforcement per repo type | Medium | Low | Validation only |
| F3: Threshold-based alerts | Alert when debt metrics exceed thresholds | Low | Low | Advisory only |

### G. Agent Orchestration

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| G1: Controlled multi-agent audit | Orchestrate multiple analysis agents | High (depth) | High (complexity, trust) | Requires sandboxing, audit trails, human review |
| G2: Agent capability registry | Register and validate agent capabilities | Medium | Medium | Capability declarations must be verifiable |
| G3: Agent result verification | Cross-validate agent outputs against evidence | High (trust) | Medium | Verification is deterministic |

### H. Enterprise Governance

| Option | Description | Value | Risk | Trust Model |
|---|---|---|---|---|
| H1: Audit trails | Structured logs of all Pharabius operations | High (compliance) | Low | Read-only records |
| H2: Ownership assignment | Assign debt ownership to teams/individuals | Medium | Low | Metadata only |
| H3: Exception management | Formal exception process for accepted debt | Medium | Medium | Requires clear lifecycle |

## Boundary Analysis

### Options That Preserve Trust Model
- B1, B2, F1, F2, F3, H1, H2 (advisory/read-only)
- A3, C2 (advisory/local-first)

### Options That Require New Consent Mechanisms
- A1, C1, D1, D2, D3, E1, E3, G1 (writes, servers, network)

### Options That Risk Weakening Trust Model
- A1 (code modification — requires strongest safeguards)
- G1 (multi-agent — requires sandboxing and verification)

## Scoring Preview

Options will be scored in [V2_ROADMAP_DECISION_MATRIX.md](V2_ROADMAP_DECISION_MATRIX.md) using the decision framework from the [Product Thesis](V2_PRODUCT_THESIS.md).

Preliminary high-value candidates:

1. **B1** (Claim review/sign-off) — High value, low risk, preserves trust
2. **C1** (Tracker write APIs) — High value, high risk, requires consent gates
3. **A3** (Dependency update suggestions) — Medium value, low risk
4. **H1** (Audit trails) — High value, low risk
5. **F1** (Custom scoring rules) — Medium value, low risk
