"""v3.10.0 S05a — Pin-quality predicate and missing-pin semantics.

Validates that is_runtime_pin() correctly distinguishes reproducibility pins
from compatibility baselines, and that UNKNOWN evidence coexists with
missing-pin advisories.
"""

from __future__ import annotations

from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceGrade,
    RuntimeSourceType,
)
from pharabius.core.runtime.policy import is_runtime_pin


def _evidence(
    runtime_name: str = "Test",
    ecosystem: RuntimeEcosystem = RuntimeEcosystem.PYTHON,
    kind: RuntimeConstraintKind = RuntimeConstraintKind.EXACT,
    value: str = "3.11",
    source_type: RuntimeSourceType = RuntimeSourceType.VERSION_FILE,
    source_path: str = ".python-version",
    source_grade: RuntimeSourceGrade = RuntimeSourceGrade.VERSION_FILE,
    source_detail: str | None = None,
    confidence: Confidence = Confidence.HIGH,
) -> RuntimeEvidence:
    return RuntimeEvidence(
        runtime_evidence_id=f"test:{runtime_name}:{source_path}:{value}",
        ecosystem=ecosystem,
        runtime_name=runtime_name,
        constraint=RuntimeConstraint(kind=kind, value=value),
        source_type=source_type,
        source_path=source_path,
        source_grade=source_grade,
        source_detail=source_detail,
        confidence=confidence,
        raw_version=value,
    )


class TestIsRuntimePin:
    """Pin-quality predicate tests."""

    def test_exact_version_file_is_pin(self) -> None:
        ev = _evidence(kind=RuntimeConstraintKind.EXACT, source_type=RuntimeSourceType.VERSION_FILE)
        assert is_runtime_pin(ev) is True

    def test_exact_tool_versions_is_pin(self) -> None:
        ev = _evidence(source_type=RuntimeSourceType.TOOL_VERSIONS)
        assert is_runtime_pin(ev) is True

    def test_exact_manifest_is_pin(self) -> None:
        ev = _evidence(
            source_type=RuntimeSourceType.MANIFEST,
            source_path="pyproject.toml",
            source_detail="requires-python",
        )
        assert is_runtime_pin(ev) is True

    def test_range_is_not_pin(self) -> None:
        ev = _evidence(kind=RuntimeConstraintKind.RANGE, value=">=3.11")
        assert is_runtime_pin(ev) is False

    def test_unknown_is_not_pin(self) -> None:
        ev = _evidence(kind=RuntimeConstraintKind.UNKNOWN, value="stable")
        assert is_runtime_pin(ev) is False

    def test_go_directive_is_not_pin(self) -> None:
        ev = _evidence(
            runtime_name="Go",
            ecosystem=RuntimeEcosystem.PYTHON,  # placeholder
            source_path="go.mod",
            source_detail="go-directive",
        )
        assert is_runtime_pin(ev) is False

    def test_target_framework_is_not_pin(self) -> None:
        ev = _evidence(
            source_path="App.csproj",
            source_detail="target-framework",
        )
        assert is_runtime_pin(ev) is False

    def test_rust_version_field_is_not_pin(self) -> None:
        ev = _evidence(
            source_path="Cargo.toml",
            source_detail="rust-version",
        )
        assert is_runtime_pin(ev) is False

    def test_docker_exact_is_not_project_pin(self) -> None:
        ev = _evidence(source_type=RuntimeSourceType.CONTAINER)
        assert is_runtime_pin(ev) is False

    def test_ci_exact_is_not_project_pin(self) -> None:
        ev = _evidence(source_type=RuntimeSourceType.CI)
        assert is_runtime_pin(ev) is False


class TestUnknownMissingPinSemantics:
    """UNKNOWN evidence may coexist with missing-pin advisory."""

    def test_unknown_evidence_detected_but_not_pinned(self) -> None:
        """Rust project with only 'stable' → detected but not pinned."""
        ev = _evidence(
            runtime_name="Rust",
            kind=RuntimeConstraintKind.UNKNOWN,
            value="stable",
            source_path="rust-toolchain.toml",
        )
        assert is_runtime_pin(ev) is False
        # Evidence exists → ecosystem detected
        assert ev.runtime_name == "Rust"
        # But not a pin → missing-pin advisory should fire
