# Tracker Export Workflow Guide

## Purpose

This guide explains how Product Engineering Teams (PETs) can use Pharabius export bundles to prepare issues for Jira, Linear, GitHub Issues, and Azure DevOps — **without giving Pharabius tracker credentials or API access**.

## Safety Boundary

> Export bundles are **tracker-preparation artifacts, not tracker integrations**.
> Pharabius does not call external tracker APIs, create issues, assign users,
> or sync status. All operations are repository-local.

## Recommended PET Workflow

1. **Analyze** — Run the full Pharabius pipeline on your repository
2. **Review findings** — Use `ai-debt review` to accept, reject, or defer findings
3. **Generate ticket drafts** — Run `ai-debt tickets` to create local drafts
4. **Generate export bundles** — Run the export bundle generator for your tracker(s)
5. **Validate completeness** — Check the bundle summary and completeness statuses
6. **Review drafts** — Inspect each draft before importing
7. **Import manually** — Copy relevant fields into your tracker
8. **Add tracker-specific fields** — Assign project, sprint, labels, assignees manually

## Pre-Import Checklist

Before importing any export bundle content into your tracker:

- [ ] **Review confirmation**: All included drafts have been reviewed via `ai-debt review`
- [ ] **False-positive exclusion**: Rejected and false-positive findings are excluded by default
- [ ] **Priority validation**: Verify that priorities match your team's conventions
- [ ] **No auto-assignees**: Pharabius never assigns users — add assignees manually
- [ ] **Label review**: Check that labels/tags are appropriate for your tracker
- [ ] **Sensitive-information check**: Review body content for any sensitive data
- [ ] **Target project/repository**: Confirm you are importing into the correct project

## Jira Import Notes

### CSV Preparation
- The CSV file uses standard RFC 4180 escaping (quotes, commas)
- **Issue Type** defaults to "Task" — adjust to your project's types
- **Labels** are comma-separated — verify they exist in your Jira project
- **Priority** values (High, Medium, Low) must match your Jira priority scheme

### Manual Steps Required
- Set **Project** key for each issue
- Set **Sprint** or **Fix Version** if applicable
- Add **Assignee** manually
- Review **Description** formatting (Markdown may need Jira markup conversion)

## Linear Import Notes

### Priority Mapping
Pharabius maps priorities conservatively:

| Pharabius | Linear Suggestion |
|---|---|
| Critical | Urgent |
| High | High |
| Medium | Medium |
| Low | Low |

These are **suggestions only** — adjust based on your team's workflow.

### Manual Steps Required
- Set **Team** and **Project** in Linear
- Add to **Cycle** if applicable
- Add **Assignee** manually
- Verify labels match your Linear workspace labels

## GitHub Issues Import Notes

### YAML Structure
Each YAML file contains:
```yaml
schema_version: '1.0'
title: 'Issue title'
labels: [...]
body: |
  Issue body content
```

### Manual Steps Required
- Create issues using the GitHub UI or `gh issue create`
- **No assignees or milestones** are emitted — add manually
- Labels must exist in the target repository
- Body content is in GitHub Flavored Markdown

## Azure DevOps Import Notes

### CSV Format
- **Tags** use semicolon separation (Azure DevOps convention)
- **Work Item Type** defaults to "User Story" — adjust as needed
- **No Area Path or Iteration Path** is emitted

### Manual Steps Required
- Set **Area Path** and **Iteration Path** per your Azure DevOps project
- Add **Assigned To** manually
- Verify **Work Item Type** matches your process template
- Tags may need to match your project's tag conventions

## What Pharabius Intentionally Does Not Do

- Does not store tracker credentials
- Does not authenticate with any external system
- Does not create issues or work items
- Does not assign users or teams
- Does not set sprints, milestones, cycles, or iterations
- Does not sync status between Pharabius and external trackers
- Does not modify production code
- Does not generate patches or dependency upgrades

## Troubleshooting

### "CSV import failed in my tracker"
Verify that column headers match your tracker's expected import format. The CSV files are designed for manual reference — your tracker may require different column names.

### "Labels/tags don't appear in my tracker"
Labels must already exist in your tracker before import. Create them manually first, or adjust the CSV/YAML content.

### "Markdown formatting looks wrong in Jira"
Jira uses its own markup format (Confluence wiki markup). The Markdown content is best used as a reference that you adapt when creating Jira issues.

### "Export bundles directory is empty"
Run `ai-debt tickets` first to generate ticket drafts, then generate export bundles. Export bundles are created from ticket drafts.

## Related Documentation

- [Export Bundles Reference](EXPORT_BUNDLES.md)
- [Ticket Drafts Reference](TICKET_DRAFTS.md)
- [PET Ticket Workflow](PET_TICKET_WORKFLOW.md)
