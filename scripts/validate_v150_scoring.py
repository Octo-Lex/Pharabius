#!/usr/bin/env python3
"""v1.5.0 Enhanced Risk Scoring Field Validation."""

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


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    all_ok = True

    for name, repo in REPOS:
        print(f"\n{'=' * 60}")
        print(f"REPO: {name}")
        print(f"{'=' * 60}")

        ws = repo / ".ai-debt"
        if ws.exists():
            shutil.rmtree(ws)

        # Setup
        r = run([str(AI_DEBT), "init", "-r", str(repo)], cwd=repo)
        if r.returncode != 0:
            print(f"  FAIL init: {r.stderr[:100]}")
            all_ok = False
            continue
        r = run([str(AI_DEBT), "run", "-r", str(repo)], cwd=repo)
        if r.returncode != 0:
            print(f"  FAIL run: {r.stderr[:100]}")
            all_ok = False
            continue

        # 1. Default scoring (enhanced off)
        print("  [default analyze] ", end="", flush=True)
        r = run([str(AI_DEBT), "analyze", "--no-ai", "-r", str(repo)], cwd=repo)
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:100]}")
            all_ok = False
            continue
        print("OK")

        debt_json = ws / "debt-register.json"
        default_hash = sha256(debt_json)
        data = json.loads(debt_json.read_text(encoding="utf-8"))
        findings = data.get("findings", [])
        # Save default scores for later comparison
        default_scores = [(f["id"], f["risk_score"]) for f in findings]
        print(f"    {len(findings)} findings, hash={default_hash[:12]}...")

        for f in findings:
            bd = f.get("risk_breakdown", {})
            print(
                f"    {f['id']}: score={f['risk_score']} "
                f"priority={f['priority']} "
                f"arch_cent={bd.get('architecture_centrality', '?')} "
                f"chg_freq={bd.get('change_frequency', '?')}"
            )

        # 2. Enhanced scoring
        print("  [enhanced analyze] ", end="", flush=True)
        r = run(
            [str(AI_DEBT), "analyze", "--no-ai", "--enhanced-scoring", "-r", str(repo)],
            cwd=repo,
        )
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:100]}")
            all_ok = False
            continue
        print("OK")

        enhanced_hash = sha256(debt_json)
        data = json.loads(debt_json.read_text(encoding="utf-8"))
        findings = data.get("findings", [])

        hash_changed = default_hash != enhanced_hash
        print(f"    hash {'CHANGED' if hash_changed else 'unchanged'}")

        for f in findings:
            bd = f.get("risk_breakdown", {})
            ac_l = bd.get("architecture_centrality_level", "?")
            cf_l = bd.get("change_frequency_level", "?")
            print(
                f"    {f['id']}: score={f['risk_score']} "
                f"priority={f['priority']} "
                f"arch_cent={bd.get('architecture_centrality', '?')} "
                f"({ac_l}) "
                f"chg_freq={bd.get('change_frequency', '?')} "
                f"({cf_l})"
            )

        # 3. Reset to default — verify scores match first default run
        r = run(
            [str(AI_DEBT), "analyze", "--no-ai", "--no-enhanced-scoring", "-r", str(repo)],
            cwd=repo,
        )
        data3 = json.loads(debt_json.read_text(encoding="utf-8"))
        scores_reset = [(f["id"], f["risk_score"]) for f in data3.get("findings", [])]
        scores_default = default_scores  # Use saved default scores from step 1
        # Compare scores, not hashes (config.yaml changes affect hash)
        print("  [reset to default] ", end="")
        if scores_reset == scores_default:
            print("OK (scores match default)")
        else:
            print(f"MISMATCH: {scores_default} -> {scores_reset}")
            all_ok = False

        # 4. Scoring preview
        print("  [scoring-preview] ", end="", flush=True)
        r = run(
            [str(AI_DEBT), "analyze", "--no-ai", "--scoring-preview", "-r", str(repo)],
            cwd=repo,
        )
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:100]}")
            all_ok = False
        else:
            # Verify canonical unchanged after preview
            # Compare against the reset (default) scores
            preview_scores = [
                (f["id"], f["risk_score"])
                for f in json.loads(debt_json.read_text(encoding="utf-8")).get("findings", [])
            ]
            if preview_scores == scores_reset:
                print("OK (canonical unchanged)")
            else:
                print("FAIL (canonical mutated!)")
                all_ok = False

            preview_path = ws / "reports" / "scoring-preview.json"
            if preview_path.exists():
                pdata = json.loads(preview_path.read_text(encoding="utf-8"))
                print(f"    Preview changes: {len(pdata.get('changes', []))}")
            else:
                print("    No preview file")

        # 5. Verify finding IDs stable
        data2 = json.loads(debt_json.read_text(encoding="utf-8"))
        ids_after = [f["id"] for f in data2.get("findings", [])]
        ids_before = [f["id"] for f in findings]
        if ids_after == ids_before:
            print("  [finding IDs] stable")
        else:
            print(f"  [finding IDs] CHANGED: {ids_before} -> {ids_after}")
            all_ok = False

        # Cleanup
        shutil.rmtree(ws)

    print(f"\n{'=' * 60}")
    print(f"RESULT: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
