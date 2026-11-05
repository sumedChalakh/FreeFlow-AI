"""Automated tests for Phase 9: Packaging, Distribution & Configuration.

Validates:
- Configuration defaults and environment variable overrides.
- Dockerfile structure, non-root user creation, volume persistence, and healthcheck.
- Dockerignore filtering rules for sensitive and ephemeral files.
- GitHub Actions CI workflow configuration and platform matrix.
"""

from pathlib import Path

from backend.config import Settings
from backend.providers.ollama import OllamaAdapter


def test_config_defaults():
    """Verify safe default settings for local-first loopback operation."""
    cfg = Settings(_env_file=None)
    assert cfg.api_host == "127.0.0.1"
    assert cfg.api_port == 8000
    assert cfg.db_path == "freeflow.db"
    assert cfg.log_level == "INFO"
    assert cfg.ollama_base_url == "http://127.0.0.1:11434"


def test_config_environment_overrides(monkeypatch):
    """Verify FREEFLOW_ prefix environment variables override defaults cleanly."""
    monkeypatch.setenv("FREEFLOW_API_HOST", "0.0.0.0")
    monkeypatch.setenv("FREEFLOW_API_PORT", "9000")
    monkeypatch.setenv("FREEFLOW_DB_PATH", "/data/custom.db")
    monkeypatch.setenv("FREEFLOW_OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    monkeypatch.setenv("FREEFLOW_LOG_LEVEL", "DEBUG")

    cfg = Settings(_env_file=None)
    assert cfg.api_host == "0.0.0.0"
    assert cfg.api_port == 9000
    assert cfg.db_path == "/data/custom.db"
    assert cfg.ollama_base_url == "http://host.docker.internal:11434"
    assert cfg.log_level == "DEBUG"


def test_ollama_adapter_custom_base_url():
    """Verify OllamaAdapter respects custom base_url configured from settings."""
    custom_url = "http://host.docker.internal:11434"
    adapter = OllamaAdapter(adapter_id="ollama", default_base_url=custom_url)
    assert adapter._default_base_url == custom_url


def test_dockerfile_structure_and_security():
    """Verify Dockerfile contains required security and persistence directives."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile must exist in project root"
    content = dockerfile_path.read_text(encoding="utf-8")

    # Non-root user setup
    assert "useradd" in content
    assert "USER freeflow" in content

    # Volume persistence for SQLite
    assert 'VOLUME ["/data"]' in content
    assert "FREEFLOW_DB_PATH=/data/freeflow.db" in content

    # Port, healthcheck, and runtime path
    assert "EXPOSE 8000" in content
    assert "HEALTHCHECK" in content
    assert "/health" in content
    assert 'ENV PATH="/app/.venv/bin:$PATH"' in content


def test_dockerignore_excludes_secrets_and_ephemeral():
    """Verify .dockerignore excludes virtualenvs, credentials, and local database files."""
    ignore_path = Path(".dockerignore")
    assert ignore_path.exists(), ".dockerignore must exist in project root"
    content = ignore_path.read_text(encoding="utf-8")

    assert ".git/" in content
    assert ".venv/" in content
    assert ".env" in content
    assert "*.db" in content
    assert "__pycache__/" in content


def test_github_actions_ci_workflow_structure():
    """Verify GitHub Actions CI workflow has least privilege and multi-OS matrix."""
    ci_path = Path(".github/workflows/ci.yml")
    assert ci_path.exists(), "CI workflow must exist in .github/workflows/ci.yml"
    content = ci_path.read_text(encoding="utf-8")

    # Least privilege permissions
    assert "permissions:" in content
    assert "contents: read" in content

    # Matrix coverage
    assert "ubuntu-latest" in content
    assert "windows-latest" in content

    # Key quality commands
    assert "uv sync --extra dev" in content
    assert "uv run ruff check ." in content
    assert "uv run ruff format --check ." in content
    assert "uv run mypy ." in content
    assert "uv run pytest -v" in content
