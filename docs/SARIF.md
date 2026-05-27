# SARIF Export

Pharabius can export findings in SARIF v2.1.0 format for use in CI pipelines and code quality tools.

## Generation

```bash
# Generate SARIF from existing analysis
ai-debt export --format sarif --output-dir sarif-output
```

This creates `sarif-output/findings.sarif` as a **local file**.

## SARIF Structure

| Field | Value |
|-------|-------|
| `$schema` | SARIF v2.1.0 JSON schema |
| `version` | `2.1.0` |
| `tool.driver.name` | `Pharabius` |
| `tool.driver.version` | Installed Pharabius version |
| `results[].ruleId` | Finding category (e.g., `TD-DEP`) |
| `results[].level` | Severity mapping (see below) |
| `results[].message.text` | Finding title |
| `results[].locations[].physicalLocation.artifactLocation.uri` | Relative file path |
| `results[].fingerprints.debtId` | Finding ID for dedup |

## Severity Mapping

| Pharabius | SARIF Level |
|-----------|-------------|
| Critical | `error` |
| High | `error` |
| Medium | `warning` |
| Low | `note` |

## GitHub Code Scanning

SARIF can be uploaded to GitHub Code Scanning. **This is not done by default.**

To upload, add a step to your workflow:

```yaml
# Step 1: Generate SARIF locally
- run: ai-debt export --format sarif --output-dir sarif-output

# Step 2: Upload (optional, user-configured)
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: sarif-output/findings.sarif
```

The upload step is **user-owned**. Pharabius does not upload SARIF, post comments, or create issues.

## Safety

- SARIF is generated as a local file only.
- No network calls during generation.
- No credentials or tokens required.
- Upload to any external system is a user configuration decision.
