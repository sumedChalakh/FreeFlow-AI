"""Tests for GET /health endpoint (P1-T2)."""

from fastapi import status


class TestHealth:
    """Health endpoint must be unauthenticated and return status ok."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_json_has_status_ok(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_no_auth_required(self, client):
        """Health must succeed without any Authorization header."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        # Confirm we did not send auth
        assert "Authorization" not in (client.headers or {})

