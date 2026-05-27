"""Release artifact and version consistency checks.

Validates that pyproject.toml, package metadata, CLI output, build
artifacts, changelog, and roadmap all agree on the expected version.
"""

from __future__ import annotations

import json
import re
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

import typer.testing

from pharabius.cli import app


def validate_release_consistency(
    expected_version: str,
    repo_root: Path,
    dist_dir: Path | None = None,
) -> dict[str, object]:
    """Check version consistency across all release surfaces."""
    checks: list[dict[str, object]] = []

    # 1. pyproject.toml
    pyproject = repo_root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', text)
        if match:
            v = match.group(1)
            if v == expected_version:
                checks.append({"source": "pyproject", "status": "ok", "version": v})
            else:
                checks.append(
                    {
                        "source": "pyproject",
                        "status": "mismatch",
                        "expected": expected_version,
                        "found": v,
                    }
                )
        else:
            checks.append({"source": "pyproject", "status": "error", "message": "No version found"})
    else:
        checks.append({"source": "pyproject", "status": "error", "message": "File not found"})

    # 2. Installed package metadata
    try:
        installed = pkg_version("pharabius")
        if installed == expected_version:
            checks.append({"source": "installed_metadata", "status": "ok", "version": installed})
        else:
            checks.append(
                {
                    "source": "installed_metadata",
                    "status": "mismatch",
                    "expected": expected_version,
                    "found": installed,
                }
            )
    except Exception as exc:
        checks.append({"source": "installed_metadata", "status": "error", "message": str(exc)})

    # 3. CLI --version
    runner = typer.testing.CliRunner()
    result = runner.invoke(app, ["--version"])
    if expected_version in result.output:
        checks.append({"source": "cli", "status": "ok"})
    else:
        checks.append(
            {
                "source": "cli",
                "status": "mismatch",
                "expected": expected_version,
                "output": result.output.strip(),
            }
        )

    # 4. Build artifacts
    if dist_dir and dist_dir.exists():
        wheels = list(dist_dir.glob("*.whl"))
        sdists = list(dist_dir.glob("*.tar.gz"))

        if wheels:
            if expected_version in wheels[0].name:
                checks.append({"source": "wheel", "status": "ok", "filename": wheels[0].name})
            else:
                checks.append(
                    {
                        "source": "wheel",
                        "status": "mismatch",
                        "expected": expected_version,
                        "filename": wheels[0].name,
                    }
                )
        else:
            checks.append({"source": "wheel", "status": "missing"})

        if sdists:
            if expected_version in sdists[0].name:
                checks.append({"source": "sdist", "status": "ok", "filename": sdists[0].name})
            else:
                checks.append(
                    {
                        "source": "sdist",
                        "status": "mismatch",
                        "expected": expected_version,
                        "filename": sdists[0].name,
                    }
                )
        else:
            checks.append({"source": "sdist", "status": "missing"})

    # 5. Changelog
    changelog = repo_root / "CHANGELOG.md"
    if changelog.exists():
        text = changelog.read_text()
        if expected_version in text:
            checks.append({"source": "changelog", "status": "ok"})
        else:
            checks.append(
                {
                    "source": "changelog",
                    "status": "missing_entry",
                    "expected": expected_version,
                }
            )

    # 6. Roadmap
    roadmap = repo_root / "docs" / "ROADMAP.md"
    if roadmap.exists():
        text = roadmap.read_text()
        if expected_version in text:
            checks.append({"source": "roadmap", "status": "ok"})
        else:
            checks.append(
                {
                    "source": "roadmap",
                    "status": "missing_entry",
                    "expected": expected_version,
                }
            )

    errors = sum(1 for c in checks if c["status"] not in ("ok", "missing"))
    return {
        "expected_version": expected_version,
        "total_checks": len(checks),
        "errors": errors,
        "status": "ready" if errors == 0 else "inconsistent",
        "checks": checks,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Release consistency checks")
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--dist", default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    dist = Path(args.dist) if args.dist else None
    report = validate_release_consistency(args.expected_version, root, dist)

    print(json.dumps(report, indent=2, default=str))
    return 1 if report["status"] != "ready" else 0


if __name__ == "__main__":
    sys.exit(main())
