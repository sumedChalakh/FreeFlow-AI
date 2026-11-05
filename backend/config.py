# pyrefly: ignore[missing-import]
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables with FREEFLOW_ prefix."""

    api_host: str = Field("127.0.0.1", description="Bind address, loopback by default")
    api_port: int = Field(8000, ge=1, le=65535, description="Port to listen on")
    api_token: str = Field("", description="Secret token for authentication")
    db_path: str = Field("freeflow.db", description="Path to SQLite database file")
    log_level: str = Field("INFO", description="Logging level")
    ollama_base_url: str = Field(
        "http://127.0.0.1:11434", description="Default Ollama host base URL"
    )

    model_config = {
        "env_file": ".env",
        "env_prefix": "FREEFLOW_",
        "case_sensitive": False,
    }


settings = Settings()
