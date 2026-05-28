"""Runtime smoke test for review workflow against Docker/PostgreSQL.

Run manually: python platform/scripts/runtime_smoke_reviews.py
Requires Docker Compose running with backend + PostgreSQL.
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://localhost:8000/api/v1"
ADMIN_TOKEN = "pharabius_admin_dev"
HEADERS = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json",
}


def _req(method: str, path: str, data: dict | None = None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _get(path: str):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main() -> None:
    errors: list[str] = []

    # 1. Health check
    code, body = _get("/health")
    if code != 200:
        errors.append(f"Health check failed: {code}")
        print(f"FAIL Health check: {code}")
        sys.exit(1)
    print(f"OK Health check: {body['status']}")

    # 2. Find repo
    code, body = _get("/repositories")
    repos = body["repositories"]
    if not repos:
        errors.append("No repositories found - upload a bundle first")
        print("FAIL No repositories")
        sys.exit(1)
    repo_id = repos[0]["id"]
    print(f"OK Repository: {repos[0]['name']} ({repo_id[:8]}...)")

    # 3. Create review decision
    code, body = _req(
        "POST",
        f"/repositories/{repo_id}/reviews",
        {
            "finding_id": "TD-DEP-001",
            "status": "accepted",
            "reviewer": "smoke-test",
            "rationale": "Runtime validation",
        },
    )
    if code != 201:
        errors.append(f"Create review: expected 201, got {code}")
    else:
        decision_id = body["id"]
        print(f"OK Create review: {body['status']} ({decision_id[:8]}...)")

        assert body["previous_status"] == ""

        # 4. Update decision
        code, body = _req(
            "PATCH",
            f"/repositories/{repo_id}/reviews/{decision_id}",
            {
                "status": "rejected",
                "rationale": "Updated",
            },
        )
        if code != 200:
            errors.append(f"Update review: expected 200, got {code}")
        elif body["previous_status"] != "accepted":
            errors.append(f"previous_status: expected accepted, got {body['previous_status']!r}")
        else:
            print(f"OK Update review: {body['status']} (prev: {body['previous_status']})")

        # 5. Soft-delete
        code, body = _req(
            "DELETE",
            f"/repositories/{repo_id}/reviews/{decision_id}",
            {
                "deleted_by": "smoke-test",
                "delete_reason": "Runtime cleanup",
            },
        )
        if code != 200:
            errors.append(f"Delete review: expected 200, got {code}")
        elif not body.get("deleted_at"):
            errors.append("Delete: expected deleted_at to be set")
        else:
            print(f"OK Soft-delete: deleted_at={body['deleted_at'][:19]}")

    # 6. Audit log
    code, body = _get(f"/repositories/{repo_id}/reviews/audit-log")
    if code != 200:
        errors.append(f"Audit log: expected 200, got {code}")
    else:
        deleted_count = sum(1 for e in body["entries"] if e["is_deleted"])
        print(f"OK Audit log: {body['total']} entries ({deleted_count} deleted)")

    # 7. Bulk review
    code, body = _req(
        "POST",
        f"/repositories/{repo_id}/reviews/bulk",
        {
            "decisions": [
                {"finding_id": "TD-ARCH-001", "status": "deferred", "reviewer": "smoke-test"},
                {"finding_id": "TD-FAKE-999", "status": "accepted"},
            ],
        },
    )
    if code != 200:
        errors.append(f"Bulk review: expected 200, got {code}")
    else:
        warnings = body.get("warnings", [])
        print(f"OK Bulk review: {body['created']} created, {len(warnings)} warnings")

    # Summary
    if errors:
        print(f"\nFAIL {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nOK All review runtime checks passed")


if __name__ == "__main__":
    main()
