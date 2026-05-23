# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# W45-S05 — CLI Command: `ai-debt portfolio`

Risk: Medium  
Slice type: CLI / user-facing workflow  
Artifact impact: New `.ai-debt/portfolio/` outputs

## Scope

Add a user-facing CLI command for generating repository-local or workspace-local portfolio summaries from one or more local repository paths.

This command must read existing `.ai-debt/` outputs and write portfolio sidecar artifacts. It must not scan remote repositories, call external APIs, or modify source repository artifacts.

## Goals

- Add `ai-debt portfolio` command.
- Support default single-repo mode.
- Support multiple local paths via repeated option or paths argument.
- Write portfolio artifacts to `.ai-debt/portfolio/` by default.
- Support explicit output directory.
- Print concise summary to console.
- Preserve deterministic ordering.

## Patch Set

Expected files/modules:

```text
src/pharabius/cli.py
src/pharabius/core/portfolio.py
src/pharabius/schemas/portfolio.py
tests/test_cli_portfolio.py
docs/PORTFOLIO.md
```

Recommended CLI shape:

```bash
ai-debt portfolio
ai-debt portfolio --repo ../service-a --repo ../service-b
ai-debt portfolio --output .ai-debt/portfolio
ai-debt portfolio --format markdown
ai-debt portfolio --format json
ai-debt portfolio --format all
```

Recommended outputs:

```text
.ai-debt/portfolio/
  portfolio-summary.json
  portfolio-summary.md
  repository-index.json
  validation-rollup.md
```

Recommended console output:

```text
Portfolio summary generated
Repositories: 3
Total findings: 42
High/Critical findings: 9
Output: .ai-debt/portfolio/
```

## Tests

Add tests for:

- CLI help includes `portfolio`.
- Default single-repo mode works with fixture `.ai-debt/`.
- Multiple `--repo` paths work.
- Missing repo path produces graceful error/warning.
- Output directory override works.
- JSON-only output works if supported.
- Markdown-only output works if supported.
- Generated files exist.
- Source `.ai-debt/debt-register.json` is not mutated.
- No external API calls are attempted.

## Targeted Verification

```bash
pytest tests/test_cli_portfolio.py
python -m pharabius.cli portfolio --help
python -m pharabius.cli portfolio --repo . --output .ai-debt/portfolio
```

## Expected Behavior

Running `ai-debt portfolio` creates portfolio summary artifacts from existing Pharabius outputs.

The command should be safe to run locally and should not require credentials, network access, or tracker configuration.

## Acceptance Criteria

- `ai-debt portfolio` exists and is documented in help.
- Command generates expected portfolio files.
- Command supports one or more local repo paths.
- Command supports output directory override.
- Command does not mutate source debt registers or work packages.
- Command performs no external API calls.
- All 7 local gates pass.
## Guardrails

- Do not add a dashboard, web server, API server, scheduler, queue, or persistent database.
- Do not crawl remote repositories or organizations.
- Do not call GitHub, GitLab, Bitbucket, Jira, Linear, Azure DevOps, or other external APIs.
- Do not create or modify external issues.
- Do not mutate source repositories outside Pharabius output directories.
- Do not mutate source `.ai-debt/debt-register.json` files during aggregation.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence scores.
- Do not introduce autonomous remediation or code modification.
- Treat portfolio output as a read-only rollup over existing Pharabius artifacts.

## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.

