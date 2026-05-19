#!/usr/bin/env python3
"""Manual smoke validation for the OpenAI-compatible provider.

This script is OPTIONAL and never run in CI.
It validates the real-provider path with actual network calls.

Requirements:
    - PHARABIUS_OPENAI_API_KEY must be set
    - PHARABIUS_OPENAI_MODEL must be set or passed as --model
    - httpx must be installed (pip install "pharabius[openai-compatible]")

Usage:
    python scripts/manual_provider_smoke.py
    python scripts/manual_provider_smoke.py --model gpt-4o
    python scripts/manual_provider_smoke.py --repo /path/to/repo
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _check_prerequisites() -> tuple[str, str]:
    """Check prerequisites. Returns (api_key, model)."""
    api_key = os.environ.get("PHARABIUS_OPENAI_API_KEY", "")
    if not api_key:
        print("FAIL: PHARABIUS_OPENAI_API_KEY not set.")
        print("  export PHARABIUS_OPENAI_API_KEY=sk-...")
        sys.exit(1)

    model = os.environ.get("PHARABIUS_OPENAI_MODEL", "")
    # Allow --model override
    for i, arg in enumerate(sys.argv):
        if arg == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]

    if not model:
        print("FAIL: Model not specified.")
        print("  export PHARABIUS_OPENAI_MODEL=gpt-4o")
        print("  or:  python scripts/manual_provider_smoke.py --model gpt-4o")
        sys.exit(1)

    return api_key, model


def _get_repo() -> Path:
    """Get repository path from args or create fixture."""
    for i, arg in enumerate(sys.argv):
        if arg == "--repo" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])

    # Create minimal fixture repo
    tmpdir = tempfile.mkdtemp(prefix="pharabius-smoke-")
    repo = Path(tmpdir)
    src = repo / "src" / "pkg_a"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "main.py").write_text("import os\nprint('hello')\n", encoding="utf-8")

    (repo / "pyproject.toml").write_text(
        '[project]\nname = "smoke-test"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    return repo


def _run(cmd: list[str]) -> tuple[int, str]:
    """Run command, return (exit_code, output)."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    return result.returncode, result.stdout + result.stderr


def _hash_file(path: Path) -> str:
    """Hash file contents."""
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> None:
    print("=" * 60)
    print("Pharabius Provider Manual Smoke Validation")
    print("=" * 60)
    print()

    api_key, model = _check_prerequisites()
    print(f"Model: {model}")
    print(f"API key: ...{api_key[-4:]}")
    print()

    repo = _get_repo()
    print(f"Repository: {repo}")
    is_temp = "--repo" not in sys.argv
    print(f"Temporary: {is_temp}")
    print()

    results: dict[str, Any] = {
        "model": model,
        "repo": str(repo),
        "checks": {},
    }

    # Step 1: Init
    print("Step 1: ai-debt init")
    code, out = _run(["ai-debt", "init", "-r", str(repo)])
    print(f"  Exit code: {code}")
    results["checks"]["init"] = code == 0
    if code != 0:
        print(f"  Output: {out[:200]}")
        _cleanup(repo, is_temp)
        sys.exit(1)
    print()

    # Step 2: Scan
    print("Step 2: ai-debt scan")
    code, out = _run(["ai-debt", "scan", "-r", str(repo)])
    print(f"  Exit code: {code}")
    results["checks"]["scan"] = code == 0
    if code != 0:
        _cleanup(repo, is_temp)
        sys.exit(1)
    print()

    # Step 3: Analyze
    print("Step 3: ai-debt analyze --no-ai")
    code, out = _run(["ai-debt", "analyze", "--no-ai", "-r", str(repo)])
    print(f"  Exit code: {code}")
    results["checks"]["analyze"] = code == 0
    print()

    # Record canonical hashes
    register = repo / ".ai-debt" / "debt-register.json"
    evidence = repo / ".ai-debt" / "evidence.json"
    register_hash_before = _hash_file(register)
    evidence_hash_before = _hash_file(evidence)

    # Step 4: Context preview
    print("Step 4: Context preview (no provider call)")
    code, out = _run(
        [
            "ai-debt",
            "enrich",
            "--provider",
            "openai-compatible",
            "--model",
            model,
            "--context-preview",
            "-r",
            str(repo),
        ]
    )
    print(f"  Exit code: {code}")
    no_call = "No provider was called" in out
    no_write = "No files were written" in out
    print(f"  No provider called: {no_call}")
    print(f"  No files written: {no_write}")
    results["checks"]["context_preview"] = code == 0 and no_call and no_write
    print()

    # Step 5: Real provider call
    print("Step 5: Real provider call (--allow-external-provider)")
    code, out = _run(
        [
            "ai-debt",
            "enrich",
            "--provider",
            "openai-compatible",
            "--model",
            model,
            "--allow-external-provider",
            "-r",
            str(repo),
        ]
    )
    print(f"  Exit code: {code}")
    results["checks"]["enrich"] = code == 0
    print(f"  Output: {out[:300]}")
    print()

    # Step 6: Validate sidecar
    print("Step 6: Sidecar validation")
    sidecar = repo / ".ai-debt" / "ai" / "enrichment-report.json"
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            print("  Sidecar valid JSON: True")
            print(f"  Provider: {data.get('provider', 'unknown')}")
            print(f"  Enrichments: {len(data.get('enrichments', []))}")
            print(f"  Rejections: {len(data.get('rejections', []))}")
            results["checks"]["sidecar_valid"] = True
        except json.JSONDecodeError:
            print("  Sidecar valid JSON: False")
            results["checks"]["sidecar_valid"] = False
    else:
        print("  Sidecar missing")
        results["checks"]["sidecar_valid"] = False
    print()

    # Step 7: Credential leakage check
    print("Step 7: Credential leakage check")
    leaked = False
    for path in [
        repo / ".ai-debt" / "ai" / "enrichment-report.json",
        repo / ".ai-debt" / "ai" / "enrichment-report.md",
    ]:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if api_key in content:
                print(f"  LEAKED in {path.name}!")
                leaked = True
    if not leaked:
        print("  No leakage detected")
    results["checks"]["no_leak"] = not leaked
    print()

    # Step 8: Canonical immutability
    print("Step 8: Canonical immutability")
    register_hash_after = _hash_file(register)
    evidence_hash_after = _hash_file(evidence)
    register_unchanged = register_hash_before == register_hash_after
    evidence_unchanged = evidence_hash_before == evidence_hash_after
    print(f"  debt-register.json: {'unchanged' if register_unchanged else 'CHANGED'}")
    print(f"  evidence.json: {'unchanged' if evidence_unchanged else 'CHANGED'}")
    results["checks"]["canonical"] = register_unchanged and evidence_unchanged
    print()

    # Step 9: ai-status
    print("Step 9: ai-debt ai-status")
    code, out = _run(["ai-debt", "ai-status", "-r", str(repo)])
    print(f"  Exit code: {code}")
    if api_key in out:
        print("  LEAKED in ai-status output!")
        results["checks"]["ai_status_safe"] = False
    else:
        results["checks"]["ai_status_safe"] = True
    print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    all_pass = all(results["checks"].values())
    for check, passed in results["checks"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")
    print()
    if all_pass:
        print("Decision: PASS")
    else:
        print("Decision: FAIL")
    print()

    # Cleanup
    _cleanup(repo, is_temp)

    sys.exit(0 if all_pass else 1)


def _cleanup(repo: Path, is_temp: bool) -> None:
    if is_temp:
        import contextlib

        with contextlib.suppress(Exception):
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    main()
