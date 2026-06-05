# External Evidence Connectors

> **Since:** v3.1.0
> **Status:** Foundation — SARIF and Semgrep fixture import supported

## Philosophy

Pharabius is evidence-first. External scanner output becomes normalized evidence, not final conclusions.

The connector contract is:

```
External scanner output → Connector normalization → Evidence[] → Pharabius pipeline
```

**Not:**

```
External scanner output → Final Pharabius finding
```

Connectors produce `EvidenceItem` objects. They never create `DebtFinding` objects. Analysis, scoring, classification, and governance remain Pharabius-internal responsibilities.

## Supported Formats (v3.1.0)

| Format | Connector | Status |
|---|---|---|
| SARIF v2.1.0 | `SarifConnector` | Foundation — minimal subset |
| Semgrep JSON | `SemgrepConnector` | Foundation — fixture import |
| Trivy JSON | `TrivyConnector` | Foundation — vulnerability scan import |
| Grype JSON | `GrypeConnector` | Foundation — vulnerability match import |
| Syft JSON (SBOM) | `SyftConnector` | Foundation — package inventory import |

### SARIF Support Level

Supported fields:
- `runs[].tool.driver.name` / `version`
- `runs[].results[].ruleId`
- `runs[].results[].message.text`
- `runs[].results[].locations[].physicalLocation.artifactLocation.uri`
- `runs[].results[].locations[].physicalLocation.region.startLine`

Unsupported SARIF fields are skipped with warnings. The connector does not attempt full SARIF schema coverage.

### Semgrep Support Level

Supported fields:
- `results[].check_id`
- `results[].path`
- `results[].start.line`
- `results[].extra.severity`
- `results[].extra.message`

## Provenance Model

Every imported evidence item carries provenance metadata:

```json
{
  "source": "external_connector",
  "metadata": {
    "connector_provenance": {
      "connector_name": "sarif",
      "connector_version": "1.0.0",
      "source_format": "sarif",
      "source_file": "results.sarif.json",
      "source_tool_name": "Semgrep",
      "source_tool_version": "1.20.0",
      "source_rule_id": "python.lang.security.injection",
      "source_record_index": 1,
      "imported_at": "2026-06-05T00:00:00Z"
    }
  }
}
```

Connector evidence can be distinguished from native evidence by `source == "external_connector"`. The specific scanner identity is in `metadata.connector_provenance.connector_name`.

## Confidence Model

External evidence receives conservative confidence:

| Level | Condition | Reason |
|---|---|---|
| High | Location + rule ID + message present | `location_rule_and_message_present` |
| Medium | Partial location or missing rule | `partial_location_or_missing_rule` |
| Low | Missing location or fallback parsing | `missing_location_or_fallback` |

Confidence and reason are stored in `confidence` and `metadata.confidence_reason`.

## CLI Usage

```bash
# Import SARIF output
ai-debt import-evidence --format sarif --input results.sarif.json

# Import Semgrep output
ai-debt import-evidence --format semgrep --input semgrep-results.json

# Deterministic output for testing
ai-debt import-evidence --format sarif --input results.sarif.json --output test-output.json
```

Imported evidence is written to `.ai-debt/external-evidence/` as `EvidenceStore` JSON files. These are optional artifacts — they are not required for a valid workspace.

## Artifact Behavior

| Artifact | Location | Status |
|---|---|---|
| External evidence | `.ai-debt/external-evidence/*.json` | Optional — produced by `import-evidence` only |

- Native `evidence.json` is **never modified** by connectors
- `import-evidence` does **not** wire into `analyze` automatically
- External evidence is stored separately for future merge/consume paths

## How to Add a Connector

1. Create a new module in `src/pharabius/core/connectors/`
2. Implement `ConnectorInterface` (properties: `name`, `version`; method: `parse`)
3. Set `source="external_connector"` on all evidence items
4. Attach `ConnectorProvenance` in metadata
5. Apply confidence via `apply_confidence()`
6. Return `ConnectorResult` with `ok=False` for malformed input
7. Write tests covering valid, partial, empty, and malformed fixtures
8. Register in the CLI `import-evidence` command's connector map
9. Add fixtures to `tests/fixtures/connectors/<format>/`

## Known Limitations

- **No scanner execution** — connectors import fixture files, they do not run scanners
- **No CodeQL, Snyk, OSV** — not implemented
- **No SBOM generation** — Syft connector imports SBOM, does not generate one
- **No automatic analysis merge** — imported evidence is stored, not consumed by `analyze`
- **No live API integration** — no GitHub Advanced Security, no ticket creation
- **No autonomous remediation** — connectors never modify code
- **No license compliance** — Syft licenses stored as metadata, not analyzed
- **No vulnerability confirmation** — scanner output is evidence, not confirmed Pharabius findings
- **No CVSS/EPSS scoring** — external severity stored as-is, not calculated

## Confidence Models

### Vulnerability Scanners (Trivy, Grype, SARIF, Semgrep)

| Level | Condition | Reason |
|---|---|---|
| High | Package locator + vulnerability ID + message | `locator_vulnerability_id_and_message_present` |
| Medium | Package locator or vulnerability ID | `locator_or_vulnerability_id_present` |
| Low | Weak package/vulnerability metadata | `weak_vulnerability_metadata` |

### SBOM Scanner (Syft)

| Level | Condition | Reason |
|---|---|---|
| High | Package name + version/purl + real file location | `sbom_name_version_and_location_present` |
| Medium | Package name or purl | `sbom_name_or_purl_present` |
| Low | Weak package metadata | `weak_sbom_package_metadata` |

SBOM evidence is not penalized for lacking vulnerability rule IDs.

## Future Connectors

Potential future additions (not committed):

- CodeQL SARIF ingestion
- Snyk JSON import
- OSV/OSV-scanner import
- Coverage report ingestion (JUnit, Cobertura)
- GitHub Advanced Security API integration
- CycloneDX/SPDX SBOM import (in addition to Syft JSON)

## Evidence Intake (v3.2.0+)

### Combine Workflow

```bash
# Step 1: Import external evidence (v3.1.0)
ai-debt import-evidence --format sarif --input results.sarif.json

# Step 2: Combine native + external evidence (v3.2.0)
ai-debt combine-evidence

# Step 3: Analyze with combined evidence (opt-in)
ai-debt analyze --evidence .ai-debt/combined-evidence.json
```

Default behavior is unchanged: `ai-debt analyze` reads native evidence only.

### Intake Policy

| Control | Default | Description |
|---|---|---|
| `allow_external` | True | Accept external evidence |
| `deduplicate` | True | Skip semantic duplicates |
| `preserve_lineage` | True (immutable) | Always preserve provenance |
| `max_external_items` | 1000 | Safety cap per source |

### Duplicate Handling

Duplicates are detected by semantic fingerprint (source + connector + rule + location + summary). First deterministic occurrence wins. Later duplicates are skipped and counted.

No evidence is silently overwritten.

### ID Namespacing

External evidence IDs are namespaced during combination:

```
EXT-{CONNECTOR}-{PATH_HASH}-{SEQUENCE}
```

Original IDs are preserved in `metadata.intake.original_evidence_id`.

## External Evidence Review (v3.4.0)

Imported and combined external evidence is reviewable in reports.

The `ai-debt report` command now generates:

```text
.ai-debt/reports/external-evidence-report.md
```

### What the review shows

| Section | Content |
|---|---|
| External Evidence Files | File counts, readability, evidence item counts |
| Evidence by Connector | Per-connector item counts |
| Combined Evidence | Native/external/total counts, deduplication stats |
| Combination Manifest | Imported, duplicates, skipped counts from manifest |
| Top Rules | Most frequent rule IDs from structured metadata |
| Top Packages | Most frequent package names from coordinates |
| Confidence Distribution | High/Medium/Low counts |
| Severity Distribution | Severity counts from depsec metadata (not mapped to confidence) |
| Warnings | Malformed files and other issues |

### What the review does NOT do

```text
No new connectors.
No scanner execution.
No vulnerability confirmation.
No finding creation.
```

External evidence is observational. It is not confirmed as findings.

### Status reader

`ai-debt status` now shows:

```text
Ext. evidence: 3 files
Combined:     12 items (8 native, 4 external)
```

When absent:

```text
Ext. evidence: absent
Combined:     absent
```
