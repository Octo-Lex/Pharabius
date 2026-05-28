# v2.4.0 — Finding Detail & Evidence Linking

Goal: Persist and display richer finding detail from uploaded Pharabius artifacts, including descriptions, locations, and evidence references, so reviewers can make decisions with more context.

Release posture: feature release. This release expands the hosted platform’s persisted finding detail contract and review context surface. It is not a patch release.

Core boundaries:
- No claim review
- No gap closure tracking
- No readiness sign-off
- No policy engine
- No tracker writes
- No PR comments
- No repository source browsing or cloning
- No autonomous remediation
- No source-code modification
- No external integration writes

Trust boundary:
- The platform ingests uploaded Pharabius `.ai-debt` artifacts.
- Uploaded artifacts may contain source-derived file paths, line references, hashes, summaries, and evidence snippets.
- Evidence linking must display artifact-derived evidence context, not fetch or browse source repositories.


## Pack contents

| Slice | File |
|---|---|
| S01 | `S01-finding-detail-schema-migration.md` |
| S02 | `S02-parser-persistence-descriptions-locations-evidence-ids.md` |
| S03 | `S03-finding-detail-api-expansion.md` |
| S04 | `S04-review-modal-evidence-context-panel.md` |
| S05 | `S05-evidence-sensitivity-limitations-documentation.md` |
| S06 | `S06-tests-docs-changelog-release.md` |

## Recommended branch

```text
roadmap/v2.4.0-finding-detail-evidence-linking
```

## Recommended release headline

```text
Pharabius v2.4.0 adds hosted finding detail and evidence linking so reviewers can see descriptions, locations, and artifact-derived evidence context while preserving the no-source-browsing and no-remediation boundary.
```

## Product definition

v2.4.0 should prove this workflow:

```text
Upload .ai-debt bundle
→ parser persists finding description, locations, and evidence references
→ finding detail API returns richer context
→ review modal displays evidence/context panel
→ reviewer makes better decision
→ review decision still does not mutate canonical finding/evidence data
```

## Required data additions

At minimum, persisted `Finding` records should support:

```text
description
locations
evidence_ids
evidence_references
artifact_context
```

Exact shapes may be JSON where artifact structures vary.

## Non-goals

```text
repository source browser
source-code clone/import
claim review
gap closure
readiness sign-off
policy engine
tracker writes
autonomous remediation
```
