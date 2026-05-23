# W41-S05 — Add CLI Command: `ai-debt tickets`

**Wave:** Wave 41 — v1.6.0 Ticket Draft Export  
**Slice:** W41-S05  
**Title:** Add CLI command: `ai-debt tickets`  
**Risk:** Medium  
**Impact class:** New user-facing command; local sidecar output only  
**Release target:** v1.6.0  
**Implementation unit:** Atomic slice; may be merged independently after W41-S01–S04

---

## 1. Scope

Expose ticket draft generation through a new CLI command:

```bash
ai-debt tickets
```

The command generates local ticket draft artifacts only. It must not create external tickets or make network calls.

### In scope

- Add `tickets` command to the CLI.
- Generate Markdown ticket drafts.
- Generate `ticket-drafts.json`.
- Generate `reports/ticket-draft-summary.md`.
- Add CLI options for output directory, deferred handling, and overwrite behavior.
- Print a concise console summary.
- Add CLI tests.
- Update command help tests if present.

### Out of scope

- No Jira API calls.
- No Linear API calls.
- No GitHub Issues API calls.
- No Azure DevOps API calls.
- No external ticket creation.
- No automatic assignment, sprint planning, or remediation.
- No scoring changes.
- No canonical artifact mutation.

---

## 2. Goals

1. Make ticket draft export usable by Product Engineering Teams from the standard CLI.
2. Keep the command local, deterministic, and safe.
3. Preserve review-aware filtering behavior from W41-S04.
4. Provide clear console feedback about generated and excluded drafts.
5. Keep future external integrations out of v1.6.0.

---

## 3. CLI design

### Command

```bash
ai-debt tickets
```

### Recommended options

```bash
ai-debt tickets \
  --workspace .ai-debt \
  --output .ai-debt/ticket-drafts \
  --include-deferred \
  --force
```

### Option behavior

| Option | Default | Behavior |
|---|---|---|
| `--workspace PATH` | `.ai-debt` | Pharabius workspace directory |
| `--output PATH` | `.ai-debt/ticket-drafts` | Ticket draft output directory |
| `--include-deferred` | false | Include deferred-only work packages |
| `--force` | false | Overwrite existing generated draft artifacts |

Avoid adding `--tracker`, `--jira`, `--linear`, `--github`, or API-related options in v1.6.0.

---

## 4. Command behavior

### Default run

```bash
ai-debt tickets
```

Expected output:

```text
Ticket drafts generated.
- Markdown drafts: 3
- JSON index: .ai-debt/ticket-drafts/ticket-drafts.json
- Summary report: .ai-debt/reports/ticket-draft-summary.md
- Excluded by review: 1
- External tickets created: 0
```

### No work packages

```text
No work packages found. Run `ai-debt plan` before generating ticket drafts.
```

Exit code should follow existing Pharabius CLI convention for missing prerequisite artifacts.

### Existing output without `--force`

```text
Ticket draft output already exists. Re-run with --force to overwrite generated draft artifacts.
```

Do not delete user-created files.

---

## 5. Patch set

### 5.1 Update `src/pharabius/cli.py`

Add command:

```python
@app.command("tickets")
def tickets_command(
    workspace: Path = typer.Option(Path(".ai-debt"), "--workspace"),
    output: Path | None = typer.Option(None, "--output"),
    include_deferred: bool = typer.Option(False, "--include-deferred"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    ...
```

Use existing CLI style, error handling, and console output conventions.

### 5.2 Add orchestration function

Recommended function:

```python
def generate_ticket_artifacts(
    workspace: Path,
    output_dir: Path | None = None,
    include_deferred: bool = False,
    force: bool = False,
) -> TicketDraftIndex:
    ...
```

Responsibilities:

1. Generate Markdown drafts.
2. Generate JSON index.
3. Generate summary report.
4. Return index for console summary.

### 5.3 Safe overwrite behavior

`--force` may overwrite generated files:

```text
.ai-debt/ticket-drafts/TICKET-*.md
.ai-debt/ticket-drafts/ticket-drafts.json
.ai-debt/reports/ticket-draft-summary.md
```

It must not delete arbitrary user files in `.ai-debt/ticket-drafts/`.

### 5.4 Command help

Ensure `ai-debt --help` lists `tickets`.

Ensure `ai-debt tickets --help` documents:

- local-only output;
- no external tickets are created;
- `--include-deferred` behavior;
- `--force` behavior.

---

## 6. Tests

Recommended file:

```text
tests/test_cli_tickets.py
```

Test cases:

1. `ai-debt tickets --help` succeeds.
2. `ai-debt tickets` generates Markdown drafts, JSON index, and summary report from fixture workspace.
3. Command output states external tickets created: 0.
4. `--include-deferred` includes deferred-only work packages.
5. Default command excludes deferred-only work packages.
6. Existing output without `--force` follows safe behavior.
7. Existing output with `--force` overwrites generated artifacts.
8. Missing work packages produces clear message.
9. Invalid debt register produces clear error.
10. Command does not mutate debt register.
11. Command does not mutate work packages.
12. Command does not mutate review sidecar.
13. Command performs no network/external tracker calls.

If the project has command-count/help snapshot tests, update them.

---

## 7. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest tests/test_cli_tickets.py
pytest tests/test_ticket_*.py
pytest
python scripts/validate_repo.py .
```

Manual smoke test:

```bash
ai-debt tickets --force
find .ai-debt/ticket-drafts -maxdepth 1 -type f -print | sort
cat .ai-debt/reports/ticket-draft-summary.md
```

Smoke-check absence of external tracker code introduced by this wave:

```bash
grep -R "jira\|linear\|github issues\|azure devops\|requests\.\|httpx\." -n src/pharabius || true
```

This grep is only a smoke check. It does not replace tests or review.

---

## 8. Expected behavior

After this slice:

- Users can run `ai-debt tickets`.
- Local Markdown ticket drafts are generated.
- Local JSON index is generated.
- Local summary report is generated.
- Review sidecar decisions are respected.
- Deferred work is excluded unless `--include-deferred` is provided.
- No external tickets are created.
- No canonical artifacts are mutated.

---

## 9. Acceptance criteria

- [ ] `ai-debt tickets --help` works.
- [ ] `ai-debt tickets` generates all expected sidecar artifacts.
- [ ] Console output clearly states no external tickets were created.
- [ ] Review filtering behavior matches W41-S04.
- [ ] `--include-deferred` works.
- [ ] `--force` behavior is safe and tested.
- [ ] Missing inputs produce clear messages.
- [ ] Tests prove canonical artifacts are not mutated.
- [ ] Tests prove no external API behavior exists.
- [ ] All local gates pass.
