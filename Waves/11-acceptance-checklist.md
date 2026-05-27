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

## v2.0 acceptance checklist

### Product

- [ ] v2.0 scope is limited to Local CI Quality Gate.
- [ ] Policy engine is limited to minimal gate configuration.
- [ ] No dashboard is added.
- [ ] No database is added.
- [ ] No external integration write path is added.
- [ ] No autonomous remediation is added.

### CLI

- [ ] `ai-debt gate` exists.
- [ ] `ai-debt gate --help` is accurate.
- [ ] Strict mode exits 1 on fail.
- [ ] Warn mode exits 0 on fail result.
- [ ] Advisory mode exits 0 on fail result.
- [ ] Internal errors exit 2.

### Artifacts

- [ ] `.ai-debt/reports/quality-gate.json` is generated.
- [ ] `.ai-debt/reports/quality-gate.md` is generated.
- [ ] Reports are deterministic.
- [ ] Reports include safety boundary language.
- [ ] Reports include recommended actions.

### Rules

- [ ] Critical threshold rule works.
- [ ] High threshold rule works.
- [ ] Blocking gap rule works.
- [ ] Contract drift rule works.
- [ ] Readiness needs-review rule works.
- [ ] Missing required artifact rule works.
- [ ] Missing optional artifact warning works.

### Safety

- [ ] `debt-register.json` is not mutated.
- [ ] `evidence.json` is not mutated.
- [ ] Work packages are not mutated.
- [ ] Claims are not mutated.
- [ ] Export bundles are not mutated.
- [ ] Portfolio outputs are not mutated.
- [ ] No external API calls occur.
- [ ] No issues or PR comments are created.

### CI

- [ ] GitHub Actions example exists.
- [ ] GitLab CI example exists.
- [ ] Azure Pipelines example exists.
- [ ] Jenkins example exists.
- [ ] Portable shell example exists.

### Release

- [ ] Version is `2.0.0`.
- [ ] Build output is `pharabius-2.0.0`.
- [ ] Changelog updated.
- [ ] Roadmap updated.
- [ ] Known limitations updated.
- [ ] All tests pass.
- [ ] All 7 local gates pass.
- [ ] CI green.
