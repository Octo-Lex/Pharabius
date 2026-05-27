# Wave 48 — v1.10.0 v1 Contract Consolidation & Release Candidate

Goal: Consolidate the v1 artifact contract, command surface, documentation, examples, validation scripts, and release readiness into a coherent v1.10 release candidate without adding a new product capability.

Release target: `v1.10.0`  
Branch target: `roadmap/v1.10.0-v1-contract-consolidation`  
Boundary: Consolidation, validation, documentation, and release-readiness only. No new product capability, no autonomous remediation, no external API writes.

# W48-S02 — Command Surface Audit and Help-Text Consistency

Risk: Medium  
Slice type: CLI consistency / UX hardening  
Artifact impact: CLI help text, docs, tests

## Scope

Audit the full `ai-debt` command surface and align help text, option descriptions, command ordering, documentation references, and safety language.

This slice should not add new commands or new command behavior. It is a consistency and validation slice.

## Goals

- Enumerate every CLI command and subcommand.
- Ensure help text is accurate and consistent.
- Ensure safety boundaries are visible for risky-sounding commands.
- Ensure commands that generate sidecar artifacts say so.
- Ensure commands that do not mutate canonical artifacts say so where relevant.
- Ensure docs and CLI help do not disagree.
- Add tests that prevent command surface drift.

## Patch Set

Expected files/modules:

```text
src/pharabius/cli.py
docs/CLI.md                                  # new or updated
docs/ARTIFACT_CONTRACT.md                    # link updates
tests/test_cli_command_surface.py            # new or expanded
```

Recommended command inventory:

```text
ai-debt init
ai-debt profile
ai-debt scan
ai-debt graph
ai-debt analyze
ai-debt review
ai-debt report
ai-debt plan
ai-debt tickets
ai-debt export
ai-debt portfolio
ai-debt version / --version
```

Recommended help-text checks:

| Command type | Required wording |
|---|---|
| Canonical producer | says which canonical artifact is written |
| Sidecar producer | says output is repository-local sidecar |
| Export bundle | says no external APIs are called |
| Ticket drafts | says no external issues are created |
| Portfolio | says local paths only, no remote crawling |
| Claims / agent handoff if surfaced | says no code modification authorized |

## Tests

Add tests for:

- Top-level help includes all expected commands.
- Each command help renders successfully.
- `--version` reports v1.10.0 only in S06; before S06 assert current version behavior.
- Export/ticket help contains no-API/no-create language.
- Portfolio help contains local-only/no-remote-crawling language.
- Help output has no stale references to removed commands.
- Documentation command inventory matches CLI command inventory.

## Targeted Verification

```bash
pytest tests/test_cli_command_surface.py
python -m pharabius.cli --help
python -m pharabius.cli tickets --help
python -m pharabius.cli portfolio --help
```

## Expected Behavior

The CLI command surface is coherent, discoverable, and aligned with documentation. Users can understand which commands produce canonical artifacts, sidecar artifacts, reports, exports, and validation outputs.

## Acceptance Criteria

- CLI help renders for every command.
- Command inventory is documented.
- Safety boundaries are visible in relevant help text.
- No new command behavior is introduced.
- Tests prevent command/documentation drift.
- All 7 local gates pass.
## Guardrails

- Do not add a new product capability.
- Do not modify production/source code under analysis.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call external APIs.
- Do not add a server, dashboard, scheduler, queue, remote crawler, or database.
- Do not change risk scoring behavior.
- Do not mutate canonical analysis artifacts except where explicitly regenerating validation outputs in controlled tests.
- Do not weaken the no-remediation boundary.
- Treat this wave as a v1 contract consolidation and release-candidate hardening wave.

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

