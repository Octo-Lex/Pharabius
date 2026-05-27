# Pharabius v1 Adoption and Upgrade Guide

**Target version**: v1.11.0  
**Audience**: Engineering teams adopting or upgrading Pharabius  
**Last updated**: 2026-05-27

## Who Should Use This Guide

This guide is for engineering teams who want to:

- Adopt Pharabius v1 for the first time
- Upgrade from earlier v1.x releases
- Understand the stable v1 workflow and safety boundaries

## Recommended Adoption Path

1. **Install and verify** → 2. **First run** → 3. **Read results** → 4. **Review findings** → 5. **Generate work packages** → 6. **Export (optional)** → 7. **Portfolio (optional)**

## Install and Verify

```bash
pip install pharabius
ai-debt --version
ai-debt doctor
```

`ai-debt doctor` provides read-only diagnostics about your workspace state and recommends the next command.

## First Run

```bash
cd /path/to/your/repository
ai-debt init
ai-debt run
```

This creates `.ai-debt/` and runs the full analysis pipeline.

## Golden Path Workflow

The recommended command sequence for a comprehensive analysis:

```bash
ai-debt init          # Create workspace
ai-debt profile       # Detect repository ecosystem
ai-debt scan          # Collect evidence
ai-debt map-units     # Map analysis units
ai-debt graph         # Build architecture graph (optional)
ai-debt analyze       # Generate findings
ai-debt report        # Generate reports
ai-debt plan          # Generate work packages
ai-debt verify        # Validate findings
ai-debt status        # Show status summary
```

Or use the orchestrator:

```bash
ai-debt run           # Runs the core pipeline
ai-debt doctor        # Check readiness
```

## Reading Readiness Results

After running the pipeline, check readiness:

```bash
ai-debt doctor
```

This reports:
- **Status**: ready / partial / needs_review
- **Blocking issues**: missing required artifacts
- **Optional warnings**: missing optional artifacts
- **Next recommended command**

## Using Work Packages and Ticket Drafts

```bash
ai-debt plan              # Generate work packages
ai-debt review --init     # Initialize PET review sidecar
ai-debt tickets           # Generate ticket drafts
```

Ticket drafts are **local Markdown files only**. They are never automatically sent to external trackers.

## Using Export Bundles

```bash
ai-debt export --tracker jira
ai-debt export --tracker linear
ai-debt export --tracker github-issues
ai-debt export --tracker azure-devops
```

Export bundles are **tracker-preparation artifacts**. They are local files that you manually import into your tracker. Pharabius does not create issues or write to external systems.

## Using Portfolio Summaries

```bash
ai-debt portfolio --repo /path/to/repo1 --repo /path/to/repo2
```

Portfolio aggregates existing `.ai-debt/` directories. It does not crawl remote repositories or require network access.

## Using Operational Claims and Agent-Handoff Contracts

After running the full pipeline with claims generation:

- **Operational claims**: Map evidence to behavioral claims about the repository
- **Traceability matrices**: Link evidence → findings → claims → work packages
- **Agent-handoff contract**: Safe handoff document for AI agents (explicitly forbids code modification)

All claims artifacts are advisory and require human validation.

## Upgrading from Earlier v1.x Versions

### From v1.5.x

- Review enhanced scoring documentation (`docs/SCORING_EVIDENCE_PACK.md`)
- Enhanced scoring is opt-in via `--enhanced-scoring` flag
- Default behavior is unchanged

### From v1.6.x

- Ticket draft workflow now includes completeness checks
- Review `docs/PET_TICKET_WORKFLOW.md` for recommended PET process
- Ticket drafts remain local-only

### From v1.7.x

- Export bundles now include manifest validation
- Review `docs/TRACKER_EXPORT_WORKFLOW.md` for import workflow
- No external API writes added

### From v1.8.x

- Portfolio command aggregates local `.ai-debt/` directories
- No remote crawling or network access required
- Review `docs/PORTFOLIO.md` for multi-repo usage

### From v1.9.x

- Operational claims are specification artifacts, not implementation authority
- Agent-handoff contract explicitly forbids code modification
- Review `docs/OPERATIONAL_CLAIMS_ADOPTION.md`

### From v1.10.x

- `ai-debt doctor` provides read-only diagnostics
- Artifact contract freeze checks available via `scripts/validate_artifact_contract.py`
- Packaging verification via `scripts/validate_packaging.py`
- Stability contract published at `docs/V1_STABILITY_CONTRACT.md`
- Safety boundaries documented at `docs/SAFETY_BOUNDARIES.md`

## Go-Live Checklist

- [ ] Package installs successfully (`pip install pharabius`)
- [ ] `ai-debt --version` reports v1.11.0
- [ ] `ai-debt doctor` reports workspace status
- [ ] `ai-debt run` completes without errors
- [ ] Required artifacts present in `.ai-debt/`
- [ ] Findings reviewed by engineering team
- [ ] Work packages understood and prioritized
- [ ] No external writes are expected
- [ ] No autonomous remediation is expected

## Rollback and Safe Cleanup

Pharabius writes all output under `.ai-debt/`. To rollback:

```bash
rm -rf .ai-debt/
```

This removes all Pharabius artifacts. Your source code is never modified.

## Related Documentation

- [Quickstart Guide](QUICKSTART.md)
- [Adoption Checklist](ADOPTION_CHECKLIST.md)
- [v1 Stability Contract](V1_STABILITY_CONTRACT.md)
- [Safety Boundaries](SAFETY_BOUNDARIES.md)
- [CLI Reference](CLI.md)
- [Artifact Contract](ARTIFACT_CONTRACT.md)
