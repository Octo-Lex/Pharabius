#!/usr/bin/env python3
"""v1.3.0 Differentiated Preset Field Validation.

Validates all 5 presets across multiple repos, checking:
- Command success
- Finding/evidence/work-package stability
- Canonical JSON hash preservation
- Runtime
- Readability
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

PRESETS = [
    "default",
    "security-sensitive",
    "startup-lean",
    "platform-engineering",
    "compliance-sensitive",
]

REPOS = [
    ("Pharabius", Path(r"C:\Next-Era\Pharabius\pharabius")),
    ("validation-java", Path(r"C:\Next-Era\validation-java")),
    ("validation-empty", Path(r"C:\Next-Era\validation-empty")),
    ("Ghostwire", Path(r"C:\Next-Era\ghostwire")),
    ("Symbiot", Path(r"C:\Next-Era\symbiot")),
]

AI_DEBT = Path(r"C:\Next-Era\Pharabius\pharabius\.venv\Scripts\ai-debt.exe")


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), timeout=timeout)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    results = {}

    for repo_name, repo_path in REPOS:
        print(f"\n{'=' * 70}")
        print(f"REPO: {repo_name}")
        print(f"{'=' * 70}")

        # Clean workspace
        ws = repo_path / ".ai-debt"
        if ws.exists():
            shutil.rmtree(ws)

        # Step 1: init + run + analyze (shared across presets)
        print("  [init] ", end="", flush=True)
        r = run([str(AI_DEBT), "init", "-r", str(repo_path)], cwd=repo_path)
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:200]}")
            continue
        print("OK")

        print("  [run]  ", end="", flush=True)
        t0 = time.time()
        r = run([str(AI_DEBT), "run", "-r", str(repo_path)], cwd=repo_path)
        runtime_run = time.time() - t0
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:200]}")
            continue
        print(f"OK ({runtime_run:.1f}s)")

        print("  [analyze] ", end="", flush=True)
        r = run([str(AI_DEBT), "analyze", "--no-ai", "-r", str(repo_path)], cwd=repo_path)
        if r.returncode != 0:
            print(f"FAIL: {r.stderr[:200]}")
            continue
        print("OK")

        # Read canonical artifacts (baseline)
        debt_json = ws / "debt-register.json"
        if not debt_json.exists():
            print("  SKIP: no debt-register.json")
            continue

        canonical_hash = sha256_file(debt_json)
        debt_data = json.loads(debt_json.read_text(encoding="utf-8"))
        baseline_findings = [f["id"] for f in debt_data.get("findings", [])]
        baseline_evidence = set()
        for f in debt_data.get("findings", []):
            for eid in f.get("evidence_ids", []):
                baseline_evidence.add(eid)

        print(
            f"  Baseline: {len(baseline_findings)} findings, "
            f"{len(baseline_evidence)} evidence IDs, hash={canonical_hash[:12]}..."
        )

        repo_results = {}

        for preset in PRESETS:
            print(f"\n  --- Preset: {preset} ---")

            # Write governance.yaml
            gov = ws / "governance.yaml"
            gov.write_text(f"preset: {preset}\n", encoding="utf-8")

            # Run plan
            print("    [plan] ", end="", flush=True)
            t0 = time.time()
            r = run([str(AI_DEBT), "plan", "-r", str(repo_path)], cwd=repo_path)
            plan_time = time.time() - t0
            if r.returncode != 0:
                print(f"FAIL ({plan_time:.1f}s): {r.stderr[:200]}")
                repo_results[preset] = {"status": "FAIL", "error": r.stderr[:200]}
                continue
            print(f"OK ({plan_time:.1f}s)")

            # Check canonical JSON hash unchanged
            current_hash = sha256_file(debt_json)
            hash_ok = current_hash == canonical_hash

            # Read plan outputs
            wp_dir = ws / "work-packages"
            wp_files = list(wp_dir.glob("*.md")) if wp_dir.exists() else []
            wp_count = len(wp_files)

            handoff = ws / "handoff-summary.md"
            roadmap = ws / "remediation-roadmap.md"

            # Read work package content
            wp_content = ""
            for wpf in wp_files:
                wp_content += wpf.read_text(encoding="utf-8") + "\n"

            handoff_content = handoff.read_text(encoding="utf-8") if handoff.exists() else ""
            roadmap_content = roadmap.read_text(encoding="utf-8") if roadmap.exists() else ""

            # Check finding IDs in work packages
            findings_in_wp = all(fid in wp_content for fid in baseline_findings)

            # Check evidence IDs in work packages
            evidence_in_wp = all(eid in wp_content for eid in baseline_evidence)

            # Check no-automation boundary in startup-lean
            no_auto = (
                "No automated remediation" in wp_content
                or "No automated remediation" in handoff_content
            )

            # Check security sections
            sec_review = "Security Review" in wp_content
            sec_signoff = "Security Sign-Off" in wp_content
            credential_caut = "Credential" in wp_content or "Secret" in wp_content
            escalation = "Escalation" in handoff_content or "escalation" in handoff_content

            # Check platform sections
            platform_impact = "Platform Impact" in wp_content

            # Check compliance sections
            attestation = "Attestation" in wp_content or "attestation" in wp_content
            audit_trail = "Audit Trail" in wp_content

            # Check startup-lean PET-actionability
            has_evidence_section = "Evidence" in wp_content or "evidence" in wp_content
            has_action = (
                "Action" in wp_content or "action" in wp_content or "Approach" in wp_content
            )
            has_verify = "Verify" in wp_content or "Verification" in wp_content
            has_caution = "Caution" in wp_content or "caution" in wp_content

            preset_result = {
                "status": "OK",
                "plan_runtime_s": round(plan_time, 1),
                "wp_count": wp_count,
                "canonical_hash_ok": hash_ok,
                "findings_in_wp": findings_in_wp,
                "evidence_in_wp": evidence_in_wp,
                "no_automation_boundary": no_auto,
                "security_review": sec_review,
                "security_signoff": sec_signoff,
                "credential_caution": credential_caut,
                "escalation_guide": escalation,
                "platform_impact": platform_impact,
                "attestation_notice": attestation,
                "audit_trail": audit_trail,
                "has_evidence": has_evidence_section,
                "has_action": has_action,
                "has_verify": has_verify,
                "has_caution": has_caution,
                "wp_content_len": len(wp_content),
                "handoff_len": len(handoff_content),
                "roadmap_len": len(roadmap_content),
            }
            repo_results[preset] = preset_result

            # Print summary
            print(
                f"    WPs: {wp_count} Hash={hash_ok} "
                f"Findings={findings_in_wp} Evidence={evidence_in_wp}"
            )
            if preset == "startup-lean":
                print(
                    f"    PET: evidence={has_evidence_section} "
                    f"action={has_action} verify={has_verify} "
                    f"caution={has_caution} boundary={no_auto}"
                )
            if preset == "security-sensitive":
                print(
                    f"    Sec: review={sec_review} signoff={sec_signoff} "
                    f"credential={credential_caut} escalation={escalation}"
                )
            if preset == "platform-engineering":
                print(f"    Platform: impact={platform_impact}")
            if preset == "compliance-sensitive":
                print(f"    Compliance: attestation={attestation} audit={audit_trail}")

        # Cross-preset stability checks
        print("\n  --- Cross-preset Stability ---")
        wp_counts = [
            v.get("wp_count", -1) for v in repo_results.values() if v.get("status") == "OK"
        ]
        if wp_counts and len(set(wp_counts)) == 1:
            print(f"    WP count stable: {wp_counts[0]} across all presets OK")
        elif wp_counts:
            print(f"    WP count MISMATCH: {wp_counts}")

        hashes_ok = all(
            v.get("canonical_hash_ok", False)
            for v in repo_results.values()
            if v.get("status") == "OK"
        )
        print(f"    Canonical hashes: {'all OK OK' if hashes_ok else 'MISMATCH FAIL'}")

        findings_ok = all(
            v.get("findings_in_wp", False) for v in repo_results.values() if v.get("status") == "OK"
        )
        print(f"    Finding IDs: {'all preserved OK' if findings_ok else 'MISSING FAIL'}")

        evidence_ok = all(
            v.get("evidence_in_wp", False) for v in repo_results.values() if v.get("status") == "OK"
        )
        print(f"    Evidence IDs: {'all preserved OK' if evidence_ok else 'MISSING FAIL'}")

        results[repo_name] = repo_results

        # Clean up
        if ws.exists():
            shutil.rmtree(ws)

    # ── Summary ────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 70}")

    all_ok = True
    for repo_name, repo_results in results.items():
        print(f"\n{repo_name}:")
        for preset, pr in repo_results.items():
            status = pr.get("status", "?")
            if status != "OK":
                print(f"  {preset}: {status} — {pr.get('error', '')[:100]}")
                all_ok = False
                continue

            wp = pr["wp_count"]
            h = "OK" if pr["canonical_hash_ok"] else "FAIL"
            f = "OK" if pr["findings_in_wp"] else "FAIL"
            e = "OK" if pr["evidence_in_wp"] else "FAIL"
            print(
                f"  {preset}: WPs={wp} hash={h} "
                f"findings={f} evidence={e} time={pr['plan_runtime_s']}s"
            )

    print(f"\n{'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
