from __future__ import annotations

import importlib.util
import json
from pathlib import Path

# Load the script module directly since it's not part of the pharabius package.
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "validate_repo.py"

_spec = importlib.util.spec_from_file_location("validate_repo", _SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

find_run_metadata = _module.find_run_metadata
load_run_metadata = _module.load_run_metadata


def test_find_run_metadata_returns_most_recent(tmp_path: Path) -> None:
    runs_dir = tmp_path / ".ai-debt" / "runs"
    runs_dir.mkdir(parents=True)

    (runs_dir / "RUN-20260516-100000.json").write_text(
        json.dumps({"run_id": "RUN-20260516-100000"}), encoding="utf-8"
    )
    (runs_dir / "RUN-20260516-120000.json").write_text(
        json.dumps({"run_id": "RUN-20260516-120000"}), encoding="utf-8"
    )

    result = find_run_metadata(tmp_path)

    assert result is not None
    assert result.name == "RUN-20260516-120000.json"


def test_find_run_metadata_returns_none_when_no_runs(tmp_path: Path) -> None:
    result = find_run_metadata(tmp_path)

    assert result is None


def test_load_run_metadata_parses_valid_json(tmp_path: Path) -> None:
    metadata_file = tmp_path / "RUN-20260516-100000.json"
    metadata_file.write_text(
        json.dumps(
            {
                "run_id": "RUN-20260516-100000",
                "summary": {
                    "evidence_count": 50,
                    "finding_count": 2,
                    "work_package_count": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    result = load_run_metadata(metadata_file)

    assert result is not None
    assert result["run_id"] == "RUN-20260516-100000"
    assert result["summary"]["evidence_count"] == 50


def test_load_run_metadata_returns_none_for_invalid_json(tmp_path: Path) -> None:
    metadata_file = tmp_path / "RUN-bad.json"
    metadata_file.write_text("not valid json", encoding="utf-8")

    result = load_run_metadata(metadata_file)

    assert result is None
