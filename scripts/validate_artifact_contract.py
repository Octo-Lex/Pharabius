"""Validate v1 artifact contract freeze.

Checks the documented artifact contract against actual generated
artifacts and schema mappings. Reports errors and warnings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path for imports
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from pharabius.core.artifact_contract import (
    KNOWN_DIRS,
    OPTIONAL_ARTIFACTS,
    REQUIRED_ARTIFACTS,
    check_artifact_contract_drift,
)


def validate_freeze(ai_debt: Path) -> dict[str, object]:
    """Run freeze checks against the v1 artifact contract."""
    report = check_artifact_contract_drift(ai_debt)

    return {
        "contract_version": "1.0",
        "required_count": len(REQUIRED_ARTIFACTS),
        "optional_count": len(OPTIONAL_ARTIFACTS),
        "known_dirs_count": len(KNOWN_DIRS),
        "status": report.status,
        "errors": report.errors,
        "warnings": report.warnings,
        "issues": [
            {
                "severity": i.severity,
                "code": i.code,
                "artifact_path": i.artifact_path,
                "message": i.message,
            }
            for i in report.issues
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate v1 artifact contract")
    parser.add_argument("--ai-debt", default=".ai-debt", help="Path to .ai-debt directory")
    args = parser.parse_args()

    ai_debt = Path(args.ai_debt)
    report = validate_freeze(ai_debt)

    print(json.dumps(report, indent=2, default=str))

    if report["status"] == "fail":
        print(f"\nArtifact contract validation: FAIL ({report['errors']} errors)")
        return 1
    elif report["status"] == "pass_with_warnings":
        print(f"\nArtifact contract validation: PASS WITH WARNINGS ({report['warnings']} warnings)")
        return 0
    else:
        print("\nArtifact contract validation: PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
