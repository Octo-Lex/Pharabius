# Template Overrides — Pharabius v1.2.0

## Overview

Template overrides let you customize Markdown output artifacts using
`{{ placeholder }}` substitution. No code execution, no external template
engines.

---

## Templateable Artifacts

| Artifact | Template Name | Rendered By |
|---|---|---|
| Work package | `work-package.md` | `ai-debt plan` |
| Handoff summary | `handoff-summary.md` | `ai-debt plan` |
| Remediation roadmap | `remediation-roadmap.md` | `ai-debt plan` |

Other Markdown reports (architecture-map, dependency-health, etc.) are
data-driven and not templateable in v1.2. JSON artifacts are never templateable.

---

## Lookup Order

Pharabius looks for templates in this order:

1. **Explicit override directory** — from `governance.yaml` `templates.override_dir`
2. **Conventional directory** — `.ai-debt/templates/{artifact_name}`
3. **Bundled preset template** — from selected preset
4. **Built-in default** — hardcoded rendering (same as v1.1)

If no template file is found, the built-in default is used.

---

## Setting Up Overrides

### Method 1: Conventional directory (recommended)

```bash
mkdir -p .ai-debt/templates
```

Create template files:

```
.ai-debt/templates/
  work-package.md
  handoff-summary.md
  remediation-roadmap.md
```

### Method 2: Custom directory

Edit `.ai-debt/governance.yaml`:

```yaml
templates:
  override_dir: "custom-templates"
```

Then place templates in `custom-templates/` at the repository root.

---

## Placeholder Reference

### work-package.md

| Placeholder | Content |
|---|---|
| `{{ package_id }}` | Work package ID (e.g., WP-001) |
| `{{ package_title }}` | Work package title |
| `{{ package_status }}` | Current status |
| `{{ linked_findings }}` | Bulleted list of linked debt IDs |
| `{{ package_objective }}` | Objective text |
| `{{ evidence_list }}` | Bulleted list of evidence IDs |
| `{{ current_risk }}` | Current risk description |
| `{{ recommended_approach }}` | Numbered list of steps |
| `{{ expected_affected_areas }}` | Bulleted list of areas |
| `{{ preconditions }}` | Bulleted list of preconditions |
| `{{ verification_recommendations }}` | Bulleted list |
| `{{ risks_and_cautions }}` | Bulleted list |
| `{{ definition_of_done }}` | Bulleted list |
| `{{ estimated_effort }}` | Effort estimate |
| `{{ expected_risk_reduction }}` | Risk reduction expectation |
| `{{ suggested_owner_area }}` | Suggested owner |

### handoff-summary.md

| Placeholder | Content |
|---|---|
| `{{ repository_section }}` | Repository metadata |
| `{{ executive_summary }}` | Finding count and top risk |
| `{{ top_risks_table }}` | Markdown table of top risks |
| `{{ recommended_first_actions }}` | Numbered action list |
| `{{ pet_decisions }}` | PET decisions needed |
| `{{ risks_and_cautions }}` | Risk and caution notes |
| `{{ uncertainties }}` | Uncertainty and limitations |
| `{{ generated_artifacts }}` | List of generated artifacts |

### remediation-roadmap.md

| Placeholder | Content |
|---|---|
| `{{ summary_section }}` | Finding/package counts |
| `{{ roadmap_buckets }}` | Immediate/Next/Later tables |
| `{{ work_package_list }}` | List of work packages |

---

## Unknown Placeholders

Unknown placeholders produce warnings and render as-is:

```markdown
{{ unknown_placeholder }}
```

stays as literal `{{ unknown_placeholder }}` text in the output.

---

## Invalid/Empty Templates

- **Empty template** → warning + fallback to built-in default
- **Unreadable template** → warning + fallback to built-in default
- **Missing template** → silently use built-in default (no warning needed)

---

## Examples

### Minimal work-package.md

```markdown
# {{ package_id }}: {{ package_title }}

**Status:** {{ package_status }}

### Evidence
{{ evidence_list }}

### Action
{{ recommended_approach }}
```

### Custom handoff-summary.md

```markdown
# Tech Debt Report

{{ executive_summary }}

## Priority Findings
{{ top_risks_table }}

## Next Steps
{{ recommended_first_actions }}
```

---

## Safety

Templates can only change **presentation**. They cannot:

- Suppress findings
- Change severity or priority
- Alter evidence IDs
- Modify canonical JSON artifacts
- Affect provider behavior
- Enable remediation
