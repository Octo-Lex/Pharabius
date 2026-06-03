"""PHP runtime evidence parser.

Sources: composer.json require.php, .tool-versions,
GitHub Actions shivammathur/setup-php, Dockerfile FROM php.
"""
from __future__ import annotations

import re
from pathlib import Path

from pharabius.core.io_helpers import read_json
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.ecosystems import _make_id
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceType,
)


def detect_php_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect PHP runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # composer.json require.php
    fpath = root / "composer.json"
    if fpath.exists():
        data = read_json(fpath)
        if isinstance(data, dict):
            require = data.get("require", {})
            if isinstance(require, dict):
                php_constraint = require.get("php")
                if php_constraint and isinstance(php_constraint, str):
                    constraint = parse_constraint("PHP", php_constraint)
                    evidence.append(RuntimeEvidence(
                        runtime_evidence_id=_make_id("PHP", "composer.json", "require.php", php_constraint),
                        ecosystem=RuntimeEcosystem.PHP,
                        runtime_name="PHP",
                        constraint=constraint,
                        source_type=RuntimeSourceType.MANIFEST,
                        source_path="composer.json",
                        source_detail="require.php",
                        confidence=Confidence.HIGH,
                        raw_version=php_constraint,
                    ))

    return evidence
