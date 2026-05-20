# Preset Reference — Pharabius v1.3.0

## Available Presets

### default

General-purpose preset matching Pharabius v1.2.1 output.

- **Intended use**: All repositories. Safe starting point.
- **Templates**: Uses built-in rendering (no template files).
- **Review**: Full evidence review and business impact review.
- **Handoff**: Includes escalation guide and triage guide.

### security-sensitive

Security-first governance preset for security-conscious organizations.

- **Intended use**: Repositories where security and compliance review is mandatory.
- **Templates**: 3 differentiated template files.
- **Work package**: Adds "Security Review Required" section, credential/secret caution, security sign-off checklist.
- **Handoff**: Security-first review priority, security escalation guide, compliance-focused review checklist.
- **Roadmap**: Flags security and compliance findings for priority review.

### startup-lean

Lean governance preset for small teams with fast iteration cycles.

- **Intended use**: Startups and small teams that need concise, action-oriented output.
- **Templates**: 3 differentiated template files.
- **Work package**: Condensed format — linked items, evidence, risk, action, verify, cautions, effort, owner. Includes "No automated remediation" boundary.
- **Handoff**: Minimal — top findings, next steps, decisions, cautions.
- **Roadmap**: Minimal — summary, buckets, work packages.

**Note**: Startup-lean preserves all essential PET handoff data (evidence, actions, verifications, cautions, boundary) in condensed form.

### platform-engineering

Platform engineering preset emphasizing dependency and operational health.

- **Intended use**: Platform and infrastructure teams focused on dependency, CI/CD, and observability.
- **Templates**: 3 differentiated template files.
- **Work package**: Adds "Platform Impact Assessment" section.
- **Handoff**: Platform health priority, dependency/operational emphasis.
- **Roadmap**: Emphasizes TD-DEP, TD-OPS, TD-OBS, TD-BUILD for platform team attention.

### compliance-sensitive

Compliance-focused governance preset for regulated industries.

- **Intended use**: Repositories subject to regulatory, audit, or compliance requirements.
- **Templates**: 3 differentiated template files.
- **Work package**: Adds "Compliance Attestation Notice" and "Audit Trail" sections with sign-off fields.
- **Handoff**: Compliance review priority, compliance escalation guide, regulatory review checklist.
- **Roadmap**: Flags TD-COMP, TD-SEC, TD-DATA, TD-PROCESS for compliance team attention.

---

## Selecting a Preset

Edit `.ai-debt/governance.yaml`:

```yaml
preset: security-sensitive
```

Then re-run `ai-debt plan` to regenerate Markdown artifacts.

---

## What Presets Do

- Change Markdown wording, section order, emphasis, and review checklists
- Add review-only sections (sign-off, audit trail)
- Highlight specific categories in handoff text

## What Presets Do NOT

- Change what findings are generated
- Change finding severity or priority
- Suppress findings
- Alter evidence IDs
- Change canonical JSON artifacts
- Affect AI provider behavior
- Enable remediation
- Invoke AI or providers
