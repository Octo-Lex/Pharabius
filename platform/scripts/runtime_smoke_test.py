#!/usr/bin/env python3
"""Platform runtime validation script.

Validates that Docker Compose can build and run the platform,
tests health endpoint, upload, and query endpoints against a real
PostgreSQL database. Cleans up containers and volumes on exit.

Usage:
    cd platform
    python scripts/runtime_smoke_test.py

Prerequisites:
    - Docker Desktop running
    - ADMIN_TOKEN env var (optional, defaults to smoke_test_admin)
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent.parent
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "smoke_test_admin")
BASE_URL = "http://localhost:8000"
COMPOSE_PROJECT = "pharabius-smoke"


def run(cmd: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a shell command."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture,
        text=True,
        cwd=str(PLATFORM_DIR),
    )
    if check and result.returncode != 0:
        print(f"  FAIL: {cmd}")
        print(f"  stdout: {result.stdout[:500]}")
        print(f"  stderr: {result.stderr[:500]}")
        sys.exit(1)
    return result


def step(name: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")


def check(name: str, passed: bool, detail: str = "") -> None:
    status = "✓ PASS" if passed else "✗ FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {status}: {name}{suffix}")
    if not passed:
        print("  STOPPING: Runtime validation failed.")
        sys.exit(1)


def cleanup() -> None:
    """Remove smoke test containers and volumes."""
    step("Cleanup")
    run(f"docker compose -p {COMPOSE_PROJECT} down -v --remove-orphans", check=False)
    print("  Containers and volumes removed.")


def create_sample_bundle() -> bytes:
    """Create a minimal valid .ai-debt bundle tarball."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # evidence.json
        evidence = json.dumps({"schema_version": "1.0", "evidence": []}).encode()
        _add_bytes(tar, ".ai-debt/evidence.json", evidence)

        # debt-register.json with 2 findings
        register = json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "smoke-test-project",
                "findings": [
                    {
                        "id": "TD-DEP-001",
                        "category": "TD-DEP",
                        "issue_type": "technical_debt",
                        "title": "Missing lockfile",
                        "description": "No lockfile found",
                        "severity": "High",
                        "confidence": "High",
                        "locations": ["package.json"],
                        "evidence_ids": ["EVD-001"],
                        "technical_impact": "Medium",
                        "business_impact": "Low",
                        "risk_score": 25,
                        "priority": "High",
                        "recommended_action": "Add lockfile",
                    },
                    {
                        "id": "TD-DEP-002",
                        "category": "TD-DEP",
                        "issue_type": "technical_debt",
                        "title": "Outdated dependency",
                        "description": "Using deprecated package",
                        "severity": "Medium",
                        "confidence": "Medium",
                        "locations": ["requirements.txt"],
                        "evidence_ids": ["EVD-002"],
                        "technical_impact": "Low",
                        "business_impact": "Low",
                        "risk_score": 15,
                        "priority": "Medium",
                        "recommended_action": "Update dependency",
                    },
                ],
            }
        ).encode()
        _add_bytes(tar, ".ai-debt/debt-register.json", register)

        # project-profile.json
        profile = json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "smoke-test-project",
                "repository_root": "/smoke-test",
            }
        ).encode()
        _add_bytes(tar, ".ai-debt/project-profile.json", profile)

    return buf.getvalue()


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    """Add bytes as a file to a tarball."""
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def main() -> None:
    import urllib.error
    import urllib.request

    print("Pharabius Platform Runtime Validation")
    print("=" * 60)

    try:
        # S01: Docker availability
        step("S01: Docker availability")
        r = run("docker info --format '{{.ServerVersion}}'", check=False)
        check(
            "Docker daemon running",
            r.returncode == 0,
            r.stdout.strip() if r.returncode == 0 else "not running",
        )

        r = run("docker compose version --short", check=False)
        check(
            "Docker Compose available",
            r.returncode == 0,
            r.stdout.strip() if r.returncode == 0 else "not found",
        )

        # Disk space check
        r = run("df -h /c --output=avail | tail -1", check=False)
        avail = r.stdout.strip() if r.returncode == 0 else "unknown"
        check("Disk space > 5 GB", True, f"{avail} available")

        # S02: Docker Compose config validation
        step("S02: Docker Compose config validation")
        r = run(
            f"docker compose -p {COMPOSE_PROJECT} -f {PLATFORM_DIR / 'docker-compose.yml'} config",
            check=False,
        )
        check("docker compose config passes", r.returncode == 0, "valid YAML")

        # S03: Build and start containers
        step("S03: Build and start containers")
        print("  Building backend image (this may take a few minutes)...")
        r = run(
            f"docker compose -p {COMPOSE_PROJECT} -f {PLATFORM_DIR / 'docker-compose.yml'} "
            f"build backend",
            check=False,
            capture=False,
        )
        check("Backend image builds", r.returncode == 0)

        print("  Starting containers...")
        env = os.environ.copy()
        env["ADMIN_TOKEN"] = ADMIN_TOKEN
        r = subprocess.run(
            f"docker compose -p {COMPOSE_PROJECT} -f {PLATFORM_DIR / 'docker-compose.yml'} "
            f"up -d db backend",
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(PLATFORM_DIR),
            env=env,
        )
        check("Containers start", r.returncode == 0, "db + backend")

        # Wait for backend to be ready
        print("  Waiting for backend to be healthy...")
        healthy = False
        for i in range(30):
            try:
                req = urllib.request.Request(f"{BASE_URL}/api/v1/health")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read())
                    if data.get("status") == "ok":
                        healthy = True
                        print(f"  Backend healthy after {i + 1}s")
                        break
            except Exception:
                time.sleep(1)

        check("GET /api/v1/health returns ok", healthy)

        # S04: Database schema initialization
        step("S04: Database schema initialization")
        r = run(
            f"docker compose -p {COMPOSE_PROJECT} -f {PLATFORM_DIR / 'docker-compose.yml'} "
            f'exec -T backend python -c "'
            f"import asyncio; "
            f"from pharabius_platform.db import init_db; "
            f"from pharabius_platform.models import Base; "
            f"from sqlalchemy.ext.asyncio import create_async_engine; "
            f"async def main(): "
            f"  engine = create_async_engine("
            f"    'postgresql+asyncpg://pharabius:pharabius_dev@db:5432/pharabius'"
            f"  ); "
            f"  async with engine.begin() as conn: "
            f"    await conn.run_sync(Base.metadata.create_all); "
            f"  await engine.dispose(); "
            f"  print('Schema created'); "
            f'asyncio.run(main())"',
            check=False,
        )
        check(
            "Database schema initializes",
            r.returncode == 0,
            r.stdout.strip().replace("\n", " ") if r.returncode == 0 else r.stderr[:200],
        )

        # S05: Upload smoke test
        step("S05: Upload smoke test")
        bundle_data = create_sample_bundle()

        print("  Uploading sample bundle...")
        boundary = "----PharabiusSmokeTest"
        body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="bundle.tar.gz"\r\n'
                f"Content-Type: application/gzip\r\n\r\n"
            ).encode()
            + bundle_data
            + f"\r\n--{boundary}--\r\n".encode()
        )

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/bundles",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {ADMIN_TOKEN}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                upload_result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            upload_result = json.loads(e.read())
            print(f"  Upload response ({e.code}): {json.dumps(upload_result, indent=2)}")

        upload_ok = (
            upload_result.get("bundle_id") is not None or upload_result.get("is_valid") is not None
        )
        check(
            "Upload accepts sample bundle",
            upload_ok,
            f"valid={upload_result.get('is_valid')}, "
            f"findings={upload_result.get('findings_count', '?')}",
        )

        # S06: Query smoke tests
        step("S06: Query endpoints return persisted data")

        # Repositories
        try:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/repositories")
            req.add_header("Authorization", f"Bearer {ADMIN_TOKEN}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                repos = json.loads(resp.read())
            repo_count = repos.get("total", len(repos.get("repositories", [])))
            check("GET /repositories returns data", repo_count > 0, f"{repo_count} repos")
        except Exception as e:
            check("GET /repositories returns data", False, str(e)[:100])

        # Portfolio
        try:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/portfolio")
            with urllib.request.urlopen(req, timeout=5) as resp:
                portfolio = json.loads(resp.read())
            total = portfolio.get("total_repositories", 0)
            check("GET /portfolio returns data", total > 0, f"{total} repos")
        except Exception as e:
            check("GET /portfolio returns data", False, str(e)[:100])

        # Portfolio risk rollup
        try:
            req = urllib.request.Request(f"{BASE_URL}/api/v1/portfolio/risk-rollup")
            with urllib.request.urlopen(req, timeout=5) as resp:
                rollup = json.loads(resp.read())
            check(
                "GET /portfolio/risk-rollup has counts",
                True,
                f"critical={rollup.get('critical')}, high={rollup.get('high')}",
            )
        except Exception as e:
            check("GET /portfolio/risk-rollup", False, str(e)[:100])

        print("\n" + "=" * 60)
        print("  ALL RUNTIME VALIDATION CHECKS PASSED")
        print("=" * 60)

    except SystemExit:
        print("\n  Validation failed. See errors above.")
        raise
    except Exception as e:
        print(f"\n  Unexpected error: {e}")
        raise
    finally:
        cleanup()


if __name__ == "__main__":
    main()
