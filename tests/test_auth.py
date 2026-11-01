"""Tests for local API authentication (P1-T3).

Verifies that unauthenticated and incorrectly authenticated requests
to protected endpoints are rejected with 401.
"""

from fastapi import status
from fastapi.testclient import TestClient


class TestAuthRejection:
    """Protected endpoints must reject unauthenticated requests."""

    def test_no_token_returns_401(self, client):
        response = client.get("/protected")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_token_returns_401(self, client):
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer wrong-token-value"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_bearer_prefix_returns_401(self, client):
        response = client.get(
            "/protected",
            headers={"Authorization": "Token some-value"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_auth_header_returns_401(self, client):
        response = client.get(
            "/protected",
            headers={"Authorization": ""},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthSuccess:
    """Protected endpoints must accept valid Bearer tokens."""

    def test_valid_token_returns_200(self, monkeypatch):
        """Set a known token and verify it grants access."""
        monkeypatch.setenv("FREEFLOW_API_TOKEN", "test-secret-token-12345")

        # Re-import to pick up the new env var
        from backend.config import Settings

        test_settings = Settings()

        # Patch the settings used by the app
        import backend.main as main_module
        from backend.main import app

        original_settings = main_module.settings
        main_module.settings = test_settings

        try:
            with TestClient(app) as c:
                response = c.get(
                    "/protected",
                    headers={"Authorization": "Bearer test-secret-token-12345"},
                )
                assert response.status_code == status.HTTP_200_OK
                assert response.json()["message"] == "Authenticated access"
        finally:
            main_module.settings = original_settings

    def test_unconfigured_token_rejects_all(self, client):
        """When api_token is empty, all requests should be rejected."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer any-token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
