# Evidence Catalog

## Evidence model overview

Pharabius emits evidence items during repository scanning. Each evidence item
is a factual observation about the repository state. Evidence does not
automatically imply a finding — analyzers consume evidence and may or may not
produce findings based on policy thresholds.

## Evidence ID conventions

Evidence IDs follow the pattern `EVD-NNNNNNN` (7-digit zero-padded).
IDs are assigned sequentially during scanning and are deterministic for
identical repository content scanned with identical configuration.

## Evidence location conventions

- `location.file` uses POSIX-style forward slashes regardless of platform
- Root-relative paths: `src/main.py`, not `/repo/src/main.py`
- `.` for repository-level signals (lockfile conflicts, runtime pins)

## Evidence quality metadata

Newer evidence types (v3.2.0+) include four advisory quality metadata fields.
Older evidence types may not include all four fields for backward compatibility.
Consumers must treat these fields as optional unless a specific evidence type
documents them as required.

| Field                  | Values                                                        | Meaning                                 |
|------------------------|---------------------------------------------------------------|-----------------------------------------|
| `observation_strength` | direct, derived, heuristic, limitation                        | How the observation was made            |
| `completeness`         | complete, partial, skipped, unknown                           | How much data was available             |
| `parser`               | filesystem, manifest_parser, coverage_parser, builtin_regex   | What produced the evidence              |
| `read_mode`            | text, json, xml, toml, yaml, skipped                          | How the file was read                   |

### observation_strength values

- **direct**: Read directly from filesystem or file content (e.g., file exists, manifest parsed)
- **derived**: Computed from other evidence (e.g., coverage % from counters)
- **heuristic**: Pattern-based detection with known false-positive potential (e.g., regex matching)
- **limitation**: Scanner could not fully process the target (e.g., file too large, malformed)

## Evidence type catalog

### large_file_detected

- **Category:** code_structure
- **Producer:** scanner (per-file loop)
- **Introduced in:** v3.1.0
- **Purpose:** Flag source files exceeding the line threshold (default 1000)
- **Typical metadata:** `line_count`, `language`, `threshold`
- **Observation strength:** heuristic (line counting is precise but significance is heuristic)
- **Completeness:** complete
- **Analyzer consumers:** `_analyze_large_files` → TD-CODE finding
- **Known limitations:** Only counts lines, not complexity
- **Example:** A 1200-line Python file triggers this evidence

### debt_marker_detected

- **Category:** code_structure
- **Producer:** scanner (per-file loop)
- **Introduced in:** v3.1.0
- **Purpose:** Count TODO/FIXME/HACK/XXX markers in source files
- **Typical metadata:** `marker_counts` (dict of marker→count), `total_count`, `threshold`
- **Observation strength:** heuristic
- **Completeness:** complete
- **Analyzer consumers:** `_analyze_debt_markers` → TD-CODE finding
- **Known limitations:** Regex-based, not AST-aware; only counts occurrences
- **Example:** A file with 6 TODO comments triggers this evidence

### source_file_skipped

- **Category:** repository
- **Producer:** scanner (per-file loop)
- **Introduced in:** v3.2.0
- **Purpose:** Record that a source file was skipped due to size limits
- **Typical metadata:** `size_kb`, `max_file_size_kb`, `reason`
- **Observation strength:** limitation
- **Completeness:** skipped
- **Analyzer consumers:** None (informational only)
- **Known limitations:** Skipped files may contain undetected evidence
- **Example:** A 600KB `.py` file with `max_file_size_kb=500`

### long_function_detected

- **Category:** code_structure
- **Producer:** scanner (per-file loop, Python only)
- **Introduced in:** v3.2.0
- **Purpose:** Flag Python functions exceeding the line threshold (default 80)
- **Typical metadata:** `function_name`, `line_count`, `line_start`, `line_end`, `language`, `threshold`
- **Observation strength:** heuristic (indentation-based, not AST)
- **Completeness:** partial
- **Analyzer consumers:** `_analyze_long_functions` → TD-CODE finding
- **Known limitations:** Python only; indentation heuristic may miscount in edge cases
- **Example:** A 120-line Python function triggers this evidence

### broad_exception_detected

- **Category:** code_structure
- **Producer:** scanner (per-file loop)
- **Introduced in:** v3.2.0
- **Purpose:** Detect bare except / catch-all patterns (Python, JS, Java)
- **Typical metadata:** `pattern`, `line_number`
- **Observation strength:** heuristic
- **Completeness:** partial
- **Analyzer consumers:** `_analyze_broad_exceptions` → TD-CODE finding (3+ per file)
- **Known limitations:** Regex-based, not AST-aware
- **Example:** `except:` on line 42 in a Python file

### dependency_health_signal

- **Category:** dependencies
- **Producer:** scanner (per-file loop + repository level)
- **Introduced in:** v3.2.0 (expanded in v3.3.0)
- **Purpose:** Local dependency health observations (unpinned, lockfile consistency)
- **Typical metadata:** `signal`, `ecosystem`, `count`, `examples`
- **Signal types:**
  - `unpinned_dependency` — broad version constraint detected
  - `lockfile_conflict` — multiple Node.js lockfiles
  - `poetry_manifest_without_lockfile` — Poetry config but no poetry.lock
  - `poetry_lockfile_without_manifest` — poetry.lock but no Poetry section
  - `pipfile_without_lockfile` — Pipfile but no Pipfile.lock
  - `pipfile_lock_without_manifest` — Pipfile.lock but no Pipfile
  - `dependency_manifest_parse_failure` — malformed TOML
- **Observation strength:** direct (lockfile), direct (manifest parse), limitation (parse failure)
- **Completeness:** complete or partial
- **Analyzer consumers:** `_analyze_dependency_signals` → TD-DEP finding
- **Known limitations:** No CVE scanning, no dependency resolution
- **Example:** `package.json` with `"lodash": "*"`

### runtime_version_signal

- **Category:** dependencies
- **Producer:** scanner (repository level)
- **Introduced in:** v3.3.0
- **Purpose:** Detect runtime version pinning or absence
- **Typical metadata:** `signal`, `runtime`, `version`, `source_file`
- **Signal types:**
  - `runtime_version_pinned` — version pin file found
  - `runtime_version_missing` — manifest exists but no pin file
- **Observation strength:** direct (pinned), limitation (missing)
- **Completeness:** complete (pinned), partial (missing)
- **Analyzer consumers:** `_analyze_runtime_version_signals` → TD-DEP finding
- **Known limitations:** Python + Node.js only; Ruby/Java deferred; conflict detection deferred
- **Example:** `.nvmrc` containing "18"

### coverage_report_detected

- **Category:** test_health
- **Producer:** scanner (repository level + per-file loop)
- **Introduced in:** v3.2.0
- **Purpose:** Record that a coverage report was found
- **Typical metadata:** `format`
- **Observation strength:** direct
- **Completeness:** complete
- **Analyzer consumers:** None directly (enables coverage_metric_detected processing)
- **Known limitations:** None
- **Example:** `coverage/coverage-summary.json` detected

### coverage_metric_detected

- **Category:** test_health
- **Producer:** coverage parsers (v3.2.0 Istanbul/Python/LCOV, v3.3.0 Cobertura/JaCoCo)
- **Introduced in:** v3.2.0
- **Purpose:** Extract specific coverage percentage metrics
- **Typical metadata:** `metric`, `percent`, `format`
- **Observation strength:** direct or derived
- **Completeness:** complete
- **Analyzer consumers:** `_analyze_coverage_gaps` → TD-TEST finding (below threshold)
- **Known limitations:** Report-level metrics only (not per-package/class)
- **Example:** Istanbul JSON showing 45.2% line coverage

### coverage_gap_detected

- **Category:** test_health
- **Producer:** scanner (error handling in coverage parsing)
- **Introduced in:** v3.2.0
- **Purpose:** Record that a coverage report could not be fully parsed
- **Typical metadata:** `format`, `reason`
- **Observation strength:** limitation
- **Completeness:** partial
- **Analyzer consumers:** None (informational only)
- **Known limitations:** Indicates scanner gap, not code gap
- **Example:** Malformed JaCoCo XML triggers this evidence

## Relationship to findings, claims, work packages, and traceability

```text
Evidence → Finding → Claim → Work Package
```

- Evidence is factual observation
- Findings are policy-driven judgments (analyzer consumes evidence)
- Claims are operational statements about codebase state
- Work packages are actionable remediation units

Not all evidence produces a finding. Not all findings produce a claim.

## Backward compatibility policy

Evidence type names are stable once introduced. Renaming requires a major
version bump. New metadata keys may be added in minor versions. Existing
metadata keys will not be removed without a deprecation period.
