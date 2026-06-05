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
- **No CodeQL, Trivy, Syft, Grype** — not implemented in v3.1.0
- **No SBOM generation** — not in scope
- **No automatic analysis merge** — imported evidence is stored, not consumed by `analyze`
- **No live API integration** — no GitHub Advanced Security, no ticket creation
- **No autonomous remediation** — connectors never modify code

## Future Connectors

Potential future additions (not committed):

- CodeQL SARIF ingestion
- Trivy JSON import
- Syft/Grype SBOM evidence
- Coverage report ingestion (JUnit, Cobertura)
- GitHub Advanced Security API integration
