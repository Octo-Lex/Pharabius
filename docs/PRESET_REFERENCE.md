# Preset Reference — Pharabius v1.2.0

## Available Presets

### default

General-purpose preset matching Pharabius v1.1 output.

- **Intended use**: All repositories. Safe starting point.
- **Supported artifacts**: work-package.md, handoff-summary.md, remediation-roadmap.md
- **Review**: Full evidence review and business impact review
- **Handoff**: Includes escalation guide and triage guide, max 10 work packages

### Platform Engineering (planned)

Emphasizes dependency health, CI/CD, and observability.

> **Note**: Preset metadata is available. Template differences are deferred to
> a follow-up release. Selecting this preset uses the default templates with
> the platform-engineering label in governance.yaml.

### Security-Sensitive (planned)

Security-first organizations. Escalation guide prioritizes TD-SEC/TD-COMP.

> **Note**: Preset metadata is available. Template differences are deferred to
> a follow-up release.

### Compliance-Sensitive (planned)

Regulated industries. Handoff includes compliance attestation.

> **Note**: Preset metadata is available. Template differences are deferred to
> a follow-up release.

### Startup-Lean (planned)

Small teams, fast iteration. Minimal handoff, fewer review checkpoints.

> **Note**: Preset metadata is available. Template differences are deferred to
> a follow-up release.

---

## Selecting a Preset

Edit `.ai-debt/governance.yaml`:

```yaml
preset: security-sensitive
```

Then re-run `ai-debt plan` to regenerate Markdown artifacts.

---

## Preset Does NOT

- Change what findings are generated
- Change finding severity or priority
- Suppress findings
- Alter evidence IDs
- Change canonical JSON artifacts
- Affect AI provider behavior
- Enable remediation
