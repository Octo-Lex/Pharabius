#!/usr/bin/env python3
"""v1.4.0 Review Decision Sidecar Field Validation."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

AI_DEBT = Path(r"C:\Next-Era\Pharabius\pharabius\.venv\Scripts\ai-debt.exe")

REPOS = [
    ("Pharabius", Path(r"C:\Next-Era\Pharabius\pharabius")),
    ("validation-java", Path(r"C:\Next-Era\validation-java")),
    ("validation-empty", Path(r"C:\Next-Era\validation-empty")),
    ("Ghostwire", Path(r"C:\Next-Era\ghostwire")),
    ("Symbiot", Path(r"C:\Next-Era\symbiot")),
]


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=timeout)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    all_ok = True

    for repo_name, repo_path in REPOS:
        print(f"\n{'=' * 60}")
        print(f"REPO: {repo_name}")
        print(f"{'=' * 60}")

        ws = repo_path / ".ai-debt"
        if ws.exists():
            shutil.rmtree(ws)

        # Setup
        print("  [init/run/analyze] ", end="", flush=True)
        r = run([str(AI_DEBT), "init", "-r", str(repo_path)], cwd=repo_path)
        if r.returncode != 0:
            print(f"FAIL init: {r.stderr[:100]}")
            all_ok = False
            continue
        r = run([str(AI_DEBT), "run", "-r", str(repo_path)], cwd=repo_path)
        if r.returncode != 0:
            print(f"FAIL run: {r.stderr[:100]}")
            all_ok = False
            continue
        r = run(
            [str(AI_DEBT), "analyze", "--no-ai", "-r", str(repo_path)],
            cwd=repo_path,
        )
        if r.returncode != 0:
            print(f"FAIL analyze: {r.stderr[:100]}")
            all_ok = False
            continue
        print("OK")

        # Read baseline
        debt_json = ws / "debt-register.json"
        if not debt_json.exists():
            print("  SKIP: no debt-register.json")
            continue
        hash_before = sha256_file(debt_json)
        findings = json.loads(debt_json.read_text(encoding="utf-8"))
        finding_ids = [f["id"] for f in findings.get("findings", [])]
        print(f"  Baseline: {len(finding_ids)} findings, hash={hash_before[:12]}...")

        # Test 1: review --init
        print("  [review --init] ", end="", flush=True)
        r = run(
            [str(AI_DEBT), "review", "--init", "-r", str(repo_path)],
            cwd=repo_path,
        )
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:100]}")
            all_ok = False
            continue
        sidecar = ws / "review" / "decisions.json"
        if not sidecar.exists():
            print("FAIL: sidecar not created")
            all_ok = False
            continue
        print("OK")

        # Verify empty decisions
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert data["decisions"] == [], "Should be empty"
        print("    Empty sidecar verified")

        # Test 2: review --status (empty)
        print("  [review --status (empty)] ", end="", flush=True)
        r = run(
            [str(AI_DEBT), "review", "--status", "-r", str(repo_path)],
            cwd=repo_path,
        )
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:100]}")
            all_ok = False
        else:
            assert "Undecided" in r.stdout, "Should show undecided"
            print("OK")

        # Test 3: review --validate (empty)
        print("  [review --validate (empty)] ", end="", flush=True)
        r = run(
            [str(AI_DEBT), "review", "--validate", "-r", str(repo_path)],
            cwd=repo_path,
        )
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:100]}")
            all_ok = False
        else:
            print("OK")

        # Test 4: Add a decision and re-validate
        if finding_ids:
            fid = finding_ids[0]
            print(f"  [review --validate (with decision for {fid})] ", end="", flush=True)
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            data["decisions"].append(
                {
                    "finding_id": fid,
                    "status": "accepted",
                    "reviewed_at": "2026-05-20T16:30:00Z",
                    "reviewer": "validation-script",
                    "rationale": "Field validation test",
                    "ticket_url": "",
                    "owner_area": "",
                    "target_release": "",
                    "notes": "",
                }
            )
            sidecar.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r = run(
                [str(AI_DEBT), "review", "--validate", "-r", str(repo_path)],
                cwd=repo_path,
            )
            if r.returncode != 0:
                print(f"FAIL: {r.stderr[:100]}")
                all_ok = False
            else:
                assert "Validation passed" in r.stdout
                print("OK")

            # Status with decision
            r = run(
                [str(AI_DEBT), "review", "--status", "-r", str(repo_path)],
                cwd=repo_path,
            )
            assert fid in r.stdout, f"Should show {fid}"
            assert "accepted" in r.stdout
            print(f"    Status shows {fid}=accepted")

        # Test 5: Add unknown finding
        print("  [review --validate (unknown finding)] ", end="", flush=True)
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["decisions"].append(
            {
                "finding_id": "TD-FAKE-999",
                "status": "accepted",
                "reviewed_at": "2026-05-20T16:30:00Z",
                "reviewer": "",
                "rationale": "",
                "ticket_url": "",
                "owner_area": "",
                "target_release": "",
                "notes": "",
            }
        )
        sidecar.write_text(json.dumps(data, indent=2), encoding="utf-8")

        r = run(
            [str(AI_DEBT), "review", "--validate", "-r", str(repo_path)],
            cwd=repo_path,
        )
        # Should pass (unknown is warning, not error)
        assert r.returncode == 0, f"Should pass with warning: {r.stdout[:200]}"
        assert "TD-FAKE-999" in r.stdout, "Should warn about unknown"
        print("OK (warning, not error)")

        # Test 6: Invalid status
        print("  [review --validate (invalid status)] ", end="", flush=True)
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["decisions"].append(
            {
                "finding_id": "TD-FAKE-998",
                "status": "invalid-status",
                "reviewed_at": "2026-05-20T16:30:00Z",
                "reviewer": "",
                "rationale": "",
                "ticket_url": "",
                "owner_area": "",
                "target_release": "",
                "notes": "",
            }
        )
        sidecar.write_text(json.dumps(data, indent=2), encoding="utf-8")

        r = run(
            [str(AI_DEBT), "review", "--validate", "-r", str(repo_path)],
            cwd=repo_path,
        )
        assert r.returncode != 0, "Should fail on invalid status"
        print("OK (hard error, exit 1)")

        # Test 7: Canonical hash unchanged
        hash_after = sha256_file(debt_json)
        if hash_before == hash_after:
            print(f"  Canonical hash: unchanged ({hash_before[:12]}...) OK")
        else:
            print(f"  Canonical hash: CHANGED from {hash_before[:12]} to {hash_after[:12]} FAIL")
            all_ok = False

        # Test 8: Init refuses overwrite
        r = run(
            [str(AI_DEBT), "review", "--init", "-r", str(repo_path)],
            cwd=repo_path,
        )
        assert r.returncode != 0, "Should refuse overwrite"
        assert "already exists" in r.stdout or "already exists" in r.stderr
        print("  Init overwrite: refused OK")

        # Cleanup
        shutil.rmtree(ws)

    print(f"\n{'=' * 60}")
    print(f"RESULT: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
