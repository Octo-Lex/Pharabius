"""Shared constants for scanner and analyzer modules.

Single source of truth for evidence-type names, thresholds, and
quality metadata conventions used across the analysis pipeline.

v3.1.0 accepted a cross-module import (scanner→analyzer) for
LARGE_FILE_LINE_THRESHOLD. v3.2.0 consolidates all shared
constants here to eliminate that coupling.
"""

# ── Evidence type names ────────────────────────────────────────────────

EVIDENCE_LARGE_FILE = "large_file_detected"
EVIDENCE_DEBT_MARKER = "debt_marker_detected"
EVIDENCE_SOURCE_FILE_SKIPPED = "source_file_skipped"
EVIDENCE_COVERAGE_REPORT = "coverage_report_detected"
EVIDENCE_COVERAGE_METRIC = "coverage_metric_detected"
EVIDENCE_COVERAGE_GAP = "coverage_gap_detected"
EVIDENCE_LONG_FUNCTION = "long_function_detected"
EVIDENCE_BROAD_EXCEPTION = "broad_exception_detected"
EVIDENCE_DEPENDENCY_SIGNAL = "dependency_health_signal"

# ── Thresholds ─────────────────────────────────────────────────────────

LARGE_FILE_LINE_THRESHOLD = 1000
MIN_DEBT_MARKER_OCCURRENCES = 5
LONG_FUNCTION_LINE_THRESHOLD = 80
BROAD_EXCEPTION_PER_FILE_THRESHOLD = 3
DEFAULT_MAX_FILE_SIZE_KB = 500
COVERAGE_LOW_THRESHOLD_PCT = 60.0

# ── Evidence quality metadata values ───────────────────────────────────

OBSERVATION_STRENGTH_DIRECT = "direct"
OBSERVATION_STRENGTH_DERIVED = "derived"
OBSERVATION_STRENGTH_HEURISTIC = "heuristic"
OBSERVATION_STRENGTH_LIMITATION = "limitation"

COMPLETENESS_COMPLETE = "complete"
COMPLETENESS_PARTIAL = "partial"
COMPLETENESS_SKIPPED = "skipped"
COMPLETENESS_UNKNOWN = "unknown"

PARSER_BUILTIN_REGEX = "builtin_regex"
PARSER_MANIFEST = "manifest_parser"
PARSER_COVERAGE = "coverage_parser"
PARSER_LOCKFILE = "lockfile_parser"
PARSER_FILESYSTEM = "filesystem"

READ_MODE_TEXT = "text"
READ_MODE_JSON = "json"
READ_MODE_XML = "xml"
READ_MODE_TOML = "toml"
READ_MODE_YAML = "yaml"
READ_MODE_SKIPPED = "skipped"
