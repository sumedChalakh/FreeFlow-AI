"""Tests for structured logging and secret redaction (P1-T4).

Verifies that the SecretRedactor processor removes sensitive values
from log event dictionaries before they reach the output.
"""

from backend.logger import SecretRedactor


class TestSecretRedaction:
    """SecretRedactor must replace sensitive field values with <redacted>."""

    def setup_method(self):
        self.redactor = SecretRedactor()

    def test_redacts_token_field(self):
        event = {"event": "login", "token": "sk-abc123"}
        result = self.redactor(None, "info", event)
        assert result["token"] == "<redacted>"

    def test_redacts_api_token_field(self):
        event = {"event": "startup", "api_token": "my-secret"}
        result = self.redactor(None, "info", event)
        assert result["api_token"] == "<redacted>"

    def test_redacts_password_field(self):
        event = {"event": "connect", "password": "hunter2"}
        result = self.redactor(None, "info", event)
        assert result["password"] == "<redacted>"

    def test_redacts_secret_field(self):
        event = {"event": "config", "secret": "s3cr3t"}
        result = self.redactor(None, "info", event)
        assert result["secret"] == "<redacted>"

    def test_redacts_key_field(self):
        event = {"event": "provider", "key": "OPENAI_KEY_xxx"}
        result = self.redactor(None, "info", event)
        assert result["key"] == "<redacted>"

    def test_preserves_non_secret_fields(self):
        event = {"event": "health_check", "status": "ok", "latency_ms": 42}
        result = self.redactor(None, "info", event)
        assert result["event"] == "health_check"
        assert result["status"] == "ok"
        assert result["latency_ms"] == 42

    def test_case_insensitive_matching(self):
        event = {"event": "test", "Token": "abc", "PASSWORD": "xyz"}
        result = self.redactor(None, "info", event)
        # SecretRedactor checks k.lower() against the set
        assert result["Token"] == "<redacted>"
        assert result["PASSWORD"] == "<redacted>"

    def test_does_not_redact_event_field(self):
        """The 'event' key should never be redacted."""
        event = {"event": "secret_rotation_complete"}
        result = self.redactor(None, "info", event)
        assert result["event"] == "secret_rotation_complete"

    def test_multiple_secrets_in_one_event(self):
        event = {
            "event": "multi",
            "token": "t1",
            "password": "p1",
            "key": "k1",
            "user": "alice",
        }
        result = self.redactor(None, "info", event)
        assert result["token"] == "<redacted>"
        assert result["password"] == "<redacted>"
        assert result["key"] == "<redacted>"
        assert result["user"] == "alice"
