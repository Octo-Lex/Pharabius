# v4 Readiness Memo

> **Status:** This memo documents viable v4 directions without implementing them.
> No v4 behavior exists in the codebase.

## Current v3 Governance Contract

The v3 governance platform (v3.12.0–v3.26.0) provides:

- **Mechanism:** GovernedSignal, SignalDisposition, output_behavior
- **Coverage:** All 10 signal families governed (29 adapters)
- **Trust:** Audit, boundary safety, reviewer UX
- **Measurement:** Per-run governance quality metrics (GQM-001–GQM-005)
- **Trends:** Historical governance quality baselines
- **Portability:** Machine-readable governance exports (JSON/JSONL, schema v1.0)

See `docs/GOVERNANCE_CONTRACT.md` for the full stable surface.

## What Is Stable

| Surface | Stability |
|---|---|
| GovernedSignal model | Frozen — fields, types, immutability |
| SignalDisposition (4 values) | Frozen — semantics documented |
| SignalFamily (10 values) | Frozen for v3; v4 may add with migration |
| Invariants (INV_001–INV_008) | Frozen — behavioral guarantees |
| Export schema v1.0 | Additive-only — breaking changes require version bump |
| GQM diagnostic codes | Frozen for v3; v4 may extend |
| Summary/quality/trend shapes | Additive-only |

## What Is Explicitly Non-Policy

The v3 contract does not:

- Apply quality gates or pass/fail thresholds
- Score governance health
- Promote or demote signals
- Change risk scores from governance
- Create work packages from governance
- Enforce policy decisions
- Collect runtime telemetry

Governance analytics describe; they do not prescribe.

## Known Extension Points

Where v4 could plug in without breaking v3:

1. **`output_behavior()`** — currently returns finding/advisory/informational/suppressed; a policy engine could return richer behavior objects
2. **`build_governance_quality_metrics()`** — pure function; a policy layer could consume its output
3. **Export schema** — additive fields; a policy engine could add `policy_decisions` without breaking consumers
4. **Run-history summary** — additive fields; new governance behavior could write new summary fields
5. **Adapter registry** — currently module-level functions; a policy engine could wrap or intercept them

## v4 Options

### Option A: Configurable Policy Engine

**What it adds:** Rules that consume governance metrics and produce decisions.

```
IF finding_evidence_coverage < 0.5 THEN warn_in_report
IF advisory_count > 20 THEN flag_for_review
```

**Extension approach:** New `policy/` module, new `PolicyDecision` model, consumed by reporter/exporter.

**Risk:** The line between "descriptive" and "prescriptive" is narrow. Policy rules can quietly become gates.

**Decision criteria:**
- Is there a concrete customer request for enforcement?
- Can policy decisions be made optional and per-repository?
- Does the policy engine respect the non-mutation boundary?

### Option B: Governance Dashboard / Reviewer UI

**What it adds:** Visual representation of governance trends, family coverage, and diagnostics.

**Extension approach:** New output format (HTML or JSON for frontend consumption), reads existing export data.

**Risk:** Dashboards can imply health scoring through visual cues (red/green coloring, progress bars).

**Decision criteria:**
- Is the dashboard read-only, or does it allow configuration?
- Does it maintain the non-policy boundary in its visual design?
- Is it a Pharabius feature or a downstream consumer responsibility?

### Option C: Enterprise Reporting and Integrations

**What it adds:** Structured outputs for SIEM, GRC platforms, enterprise reporting pipelines.

**Extension approach:** New export formats (CSAF, OpenVEX, custom enterprise schemas), reads existing data.

**Risk:** Integration formats can carry policy implications (e.g., "compliant"/"noncompliant" fields).

**Decision criteria:**
- Do integration outputs remain descriptive?
- Are integration formats optional and opt-in?
- Does Pharabius remain local and repository-oriented?

### Option D: Policy Packs / Organizational Profiles

**What it adds:** Configurable rule sets that organizations can apply across repositories.

**Extension approach:** New `policy_packs/` directory, `.ai-debt/governance-policy.yaml`, consumed by policy engine.

**Risk:** Organizational profiles centralize decisions that v3 keeps local.

**Decision criteria:**
- Are policy packs optional per-repository?
- Can a repository opt out of organizational defaults?
- Does the policy pack system respect the v3 invariant boundary?

## Risks Before v4

1. **Scope creep:** v4 could try to be all four options simultaneously.
2. **Policy drift:** Enforcement features can emerge accidentally through terminology and defaults.
3. **Contract breakage:** Adding families, changing disposition semantics, or modifying export schema without migration notes breaks downstream consumers.
4. **Complexity:** The v3 arc added 488 tests across 14 releases. v4 complexity should be justified by concrete demand.
5. **Local-first erosion:** Enterprise features may require centralized state, conflicting with the repository-local architecture.

## Recommended v4 Decision Criteria

Before choosing a v4 direction:

1. **Is there concrete demand?** — Not theoretical, but actual users asking for this.
2. **Does it respect the v3 contract?** — No breaking changes, additive only.
3. **Does it maintain non-policy?** — Or does it deliberately and explicitly cross the line with clear documentation?
4. **Is it incremental?** — Can it be delivered in a single release, or does it require a long arc?
5. **Does it justify its test budget?** — Every new feature needs proportional testing.

## v3 Family/Adapter Freeze Note

v3.26.0 freezes the current v3 governance surface at 10 families and 29 adapters.
Future major versions may add families/adapters with explicit contract migration notes.
This is a v3 contract boundary, not a permanent product ceiling.
