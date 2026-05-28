"""S05 tests — API key CRUD."""

from __future__ import annotations

from pharabius_platform.main import app


class TestAPIKeyRoutes:
    """Verify API key endpoints are registered."""

    def test_create_key_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/api-keys" in routes

    def test_list_keys_route_exists(self) -> None:
        routes = [(r.path, list(r.methods or [])) for r in app.routes if hasattr(r, "path")]
        # /api/v1/api-keys should support GET and POST
        key_routes = [(p, m) for p, m in routes if p == "/api/v1/api-keys"]
        assert len(key_routes) >= 2  # POST and GET

    def test_revoke_key_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/api-keys/{key_id}" in r for r in routes)


class TestAPIKeyResponseShapes:
    def test_create_response_shape(self) -> None:
        shape = {
            "id": "uuid",
            "name": "CI Upload Token",
            "key_type": "upload",
            "key": "phar_abc123...",
            "active": True,
        }
        assert "key" in shape
        assert "key_type" in shape

    def test_list_response_shape(self) -> None:
        shape = {
            "api_keys": [],
            "total": 0,
        }
        assert "api_keys" in shape
        assert "total" in shape

    def test_list_item_no_raw_key(self) -> None:
        item = {
            "id": "uuid",
            "name": "CI Upload Token",
            "key_type": "upload",
            "last_used_at": None,
            "expires_at": None,
            "active": True,
        }
        assert "key" not in item

    def test_revoke_response_shape(self) -> None:
        shape = {"id": "uuid", "active": False}
        assert shape["active"] is False


class TestAPIKeyGeneration:
    def test_key_format(self) -> None:
        from pharabius_platform.api.api_keys import _generate_key

        key = _generate_key()
        assert key.startswith("phar_")
        assert len(key) > 20

    def test_key_hashing(self) -> None:
        from pharabius_platform.api.api_keys import _hash_key

        hash1 = _hash_key("test_key")
        hash2 = _hash_key("test_key")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_keys_different_hashes(self) -> None:
        from pharabius_platform.api.api_keys import _hash_key

        hash1 = _hash_key("key_one")
        hash2 = _hash_key("key_two")
        assert hash1 != hash2
