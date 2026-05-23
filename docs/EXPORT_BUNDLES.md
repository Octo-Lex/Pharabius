# Export Bundles

## What Export Bundles Are

Export bundles are **repository-local handoff artifacts** that prepare Pharabius
ticket drafts for import into external issue trackers. They are generated from
existing ticket drafts and contain tracker-specific formatting.

## What Export Bundles Are Not

> Export bundles do **not** create, sync, assign, or update tickets in external
> systems. Pharabius v1.7.x does not call Jira, Linear, GitHub Issues, or
> Azure DevOps APIs.

## Supported Trackers

| Tracker | Formats | Bundle Directory |
|---|---|---|
| Jira | Markdown, CSV | `.ai-debt/export-bundles/jira/` |
| Linear | Markdown, CSV | `.ai-debt/export-bundles/linear/` |
| GitHub Issues | Markdown, YAML | `.ai-debt/export-bundles/github-issues/` |
| Azure DevOps | Markdown, CSV | `.ai-debt/export-bundles/azure-devops/` |

## Generated Artifacts

Each tracker bundle includes:

- A **Markdown summary** with all ticket drafts
- A **structured file** (CSV or YAML) for import preparation
- A **README** stating no API calls and no issue creation
- An entry in the **bundle manifest** (`.ai-debt/export-bundles/manifest.json`)

### Directory Layout

```text
.ai-debt/
  export-bundles/
    manifest.json
    jira/
      README.md
      jira-ticket-drafts.md
      jira-ticket-drafts.csv
    linear/
      README.md
      linear-ticket-drafts.md
      linear-ticket-drafts.csv
    github-issues/
      README.md
      github-issues-ticket-drafts.md
      issues/
        TICKET-WP-001.yaml
    azure-devops/
      README.md
      azure-devops-ticket-drafts.md
      azure-devops-ticket-drafts.csv
```

## Manifest

The `manifest.json` file records all generated artifacts:

```json
{
  "schema_version": "1.0",
  "tool_version": "1.7.0",
  "generated_at": "2026-05-23T00:00:00Z",
  "summary": {
    "total_bundles": 4,
    "total_artifacts": 8,
    "total_tickets": 12,
    "trackers": ["azure-devops", "github-issues", "jira", "linear"]
  },
  "artifacts": [...]
}
```

## Tracker-Specific Details

### Jira

- **CSV columns**: Summary, Issue Type, Description, Priority, Labels, Linked Findings, Work Package, Source Ticket Draft, Review Decision, Completeness
- **Issue Type**: Task (default)
- **Safe CSV escaping**: commas, quotes, and newlines handled

### Linear

- **CSV columns**: Title, Description, Priority, Labels, Linked Findings, Work Package, Source Ticket Draft, Review Decision, Completeness
- **Priority mapping**: Critical → Urgent, High → High, Medium → Medium, Low → Low
- These are **suggestions only** — PET teams should adjust

### GitHub Issues

- **YAML per issue**: `issues/TICKET-*.yaml` with schema_version, title, labels, body
- **No assignees or milestones** emitted by default
- **Body** uses YAML literal block scalar for multiline content

### Azure DevOps

- **CSV columns**: Title, Work Item Type, Description, Priority, Tags, Linked Findings, Work Package, Source Ticket Draft, Review Decision, Completeness
- **Work Item Type**: User Story (default)
- **Tags**: Semicolon-separated (Azure DevOps convention)
- **No Assigned To, Area Path, or Iteration Path** emitted by default

## Manual Review Workflow

1. Generate ticket drafts: `ai-debt tickets --repo /path/to/repo`
2. Review drafts in `.ai-debt/ticket-drafts/`
3. Generate export bundles (future CLI command or manual)
4. Inspect tracker-specific files
5. Copy relevant content into your tracker
6. Add tracker-specific fields (project, sprint, assignee) manually

## Safety Boundaries

- No external API calls
- No credential storage or authentication
- No automatic issue creation
- No assignment or milestone handling
- All artifacts are repository-local
- PET teams own review, import, and implementation

## Related Documentation

- [Tracker Export Workflow](TRACKER_EXPORT_WORKFLOW.md)
- [Ticket Drafts](TICKET_DRAFTS.md)
- [PET Ticket Workflow](PET_TICKET_WORKFLOW.md)
- [Governance Presets](PRESET_REFERENCE.md)
