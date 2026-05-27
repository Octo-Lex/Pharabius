# W53-S04 — SARIF Enhancement for GitHub Code Scanning

Risk: Low-medium  
Slice type: Export enhancement

## Scope

Enhance the existing SARIF exporter to produce output compatible with GitHub Code Scanning upload (`github/codeql-action/upload-sarif`). This enables Pharabius findings to appear in GitHub's Security tab.

## Goals

- Existing SARIF exporter produces GitHub-compatible output.
- SARIF includes proper `ruleId`, `message`, `locations` with `uri` and `line`.
- SARIF includes `level` mapping (Critical→error, High→error, Medium→warning, Low→note).
- SARIF includes `helpUri` pointing to category documentation if available.
- Validate output against SARIF v2.1.0 schema.
- No external network calls.

## Patch Set

```text
src/pharabius/core/exporter.py            # enhance existing SARIF export
tests/test_sarif_github_compatibility.py  # new
tests/test_sarif_schema_validation.py     # new
```

## SARIF Requirements for GitHub

| Field | Requirement |
|---|---|
| `$schema` | `https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json` |
| `version` | `"2.1.0"` |
| `runs[].tool.driver.name` | `"Pharabius"` |
| `runs[].tool.driver.version` | installed version |
| `runs[].results[].ruleId` | finding ID (e.g., `"TD-DEP-001"`) |
| `runs[].results[].level` | severity mapping |
| `runs[].results[].message.text` | finding title + description |
| `runs[].results[].locations[].physicalLocation.artifactLocation.uri` | relative file path |
| `runs[].results[].locations[].physicalLocation.region.startLine` | line number |

## Tests

- SARIF output validates against v2.1.0 JSON schema.
- Severity maps correctly: Critical→error, High→error, Medium→warning, Low→note.
- File URIs are relative (not absolute).
- Tool driver includes name and version.
- Empty findings produce valid SARIF with empty results array.
- Existing SARIF tests still pass.

## Acceptance Criteria

- SARIF output is GitHub Code Scanning compatible.
- Validated against SARIF v2.1.0 schema.
- No breaking changes to existing export formats.
- 7 gates pass.
