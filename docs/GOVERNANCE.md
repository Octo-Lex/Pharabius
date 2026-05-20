# Governance — Pharabius v1.2.0

Pharabius governance controls **how findings are presented**, not what findings
are generated. Deterministic finding generation is never affected by governance
settings.

---

## Governance vs Config

| File | Controls |
|---|---|
| `config.yaml` | Scanner/runtime settings: exclude paths, file size limits, AI settings |
| `governance.yaml` | Output style, handoff policy, template overrides |

Governance is **separate from config** by design. Changing governance does not
affect what evidence is collected, what findings are generated, or how providers
behave.

---

## Governance Artifact

`.ai-debt/governance.yaml` is created by `ai-debt init`.

```yaml
preset: default  # default, platform-engineering, security-sensitive,
                 # compliance-sensitive, startup-lean

review:
  require_evidence_review: true
  require_business_impact_review: true
  review_checklist: true

templates:
  override_dir: ""  # empty = no overrides

handoff:
  include_escalation_guide: true
  include_triage_guide: true
  max_work_packages: 10

safety:
  # These are enforced by the engine regardless of this file.
  no_finding_suppression: true
  no_severity_escalation: true
  no_evidence_id_changes: true
  no_canonical_json_mutation: true
  no_ai_canonical_mutation: true
  no_remediation_execution: true
```

### Missing or Malformed

- **Missing** `governance.yaml` → safe defaults (same as `default` preset)
- **Malformed** YAML → warning + safe defaults
- **Unknown preset** → warning + fallback to `default`
- **Unknown keys** → warning + ignore

---

## Safety Invariants

These are **enforced by the engine**, not configurable:

1. **No finding suppression** — governance cannot hide or remove findings
2. **No severity escalation** — governance cannot raise severity/priority
3. **No priority changes** — governance cannot reorder findings by priority
4. **No evidence ID changes** — governance cannot alter evidence references
5. **No canonical JSON mutation** — JSON artifacts are always deterministic
6. **No AI canonical mutation** — AI sidecars never modify canonical artifacts
7. **No remediation execution** — no code modification behavior
8. **No provider behavior changes** — governance does not affect providers
9. **No run/enrich integration** — `enrich` remains standalone

---

## Governance Principles

1. **Evidence-first**: Every finding traces to repository evidence. Governance
   cannot change this.

2. **Presentation-only**: Governance affects Markdown wording, section order,
   emphasis, and review checklists. It does not affect JSON schemas or
   finding generation.

3. **Explicit consent**: Real provider use requires per-invocation consent.
   Governance does not weaken this.

4. **PET ownership**: Product Engineering Teams approve, implement, verify,
   and own all outcomes. Governance does not automate remediation.

5. **Uncertainty language**: Inferred impact is always marked. Governance
   cannot suppress uncertainty warnings.

6. **No code modification**: Pharabius does not modify production code.
   Governance cannot enable remediation.

---

## Governance and AI Sidecars

Governance does not affect AI enrichment behavior:
- AI remains disabled by default (`--provider disabled`)
- Consent is still required for real providers
- Sidecar output remains separate from canonical artifacts
- Governance affects deterministic Markdown output only

---

## Path Safety

The `templates.override_dir` field is validated:
- Paths must resolve **inside** the repository root
- Path traversal (`../../escape`) is rejected with a warning
- Absolute paths outside the repository are rejected
- Non-existent directories are handled gracefully (no crash)
- Bundled preset templates are always safe (inside package)

---

## Deferred Features

The following are deferred to v1.4+:
- Graph/git-backed risk scoring (separate validation-heavy release)
- Manual review/decision sidecar
- `debt-register.md` template override
- `foundation-audit-report.md` template override
