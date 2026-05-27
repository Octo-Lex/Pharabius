# Pharabius v2.0 — Local CI Quality Gate

Product thesis: Pharabius v2.0 enters developer workflow through a local, deterministic CI quality gate without becoming infrastructure.

Core boundary:
- No server
- No database requirement
- No dashboard service
- No remote repository crawling
- No external API writes
- No issue creation
- No autonomous remediation
- No production code modification

Primary command target:

```bash
ai-debt gate
```

Primary outputs:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

## 1. Why the v2.0 plan changed

The earlier v2 planning favored a general policy engine as the primary v2.0 track. The competitive gap analysis shows that this is too internally oriented.

The most urgent adoption question is:

```text
How does Pharabius enter developer workflow without becoming infrastructure?
```

The answer is:

```text
CI gate first
→ temporal trends second
→ static dashboard third
→ policy engine as control layer
→ external writes only after consent infrastructure
```

## 2. Corrected v2 thesis

Pharabius v2 should bring evidence-backed technical debt intelligence into developer and engineering-management workflows while preserving the v1 trust model.

The product must remain local-first, file-based by default, deterministic where possible, evidence-backed, explicit about gaps and uncertainty, and safe by default.

## 3. Corrected v2 roadmap

| Version | Focus | Purpose |
|---|---|---|
| v2.0 | Local CI Quality Gate | Enter merge/CI workflow |
| v2.1 | Temporal Trends | Answer whether debt is improving or worsening |
| v2.2 | Static HTML Dashboard | Provide visual summaries without infrastructure |
| v2.3 | Policy Engine | Standardize enforcement and reporting rules |
| v2.4+ | External Tracker Writes | Only after consent, audit, dry-run, and idempotency controls |

## 4. Policy engine repositioning

Incorrect:

```text
v2.0 = policy engine
```

Correct:

```text
v2.0 = CI quality gate
minimal policy substrate = gate configuration only
```

## 5. Decision

The v2.0 target is:

```text
v2.0 — Local CI Quality Gate
```

All other v2 planning should defer to this workflow-first adoption path.
