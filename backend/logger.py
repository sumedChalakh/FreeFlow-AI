# logger configuration with secret redaction
import logging
from collections.abc import Mapping
from typing import Any

import structlog


# Simple redaction filter for secret-like fields
class SecretRedactor:
    SECRET_KEYS = {"api_token", "token", "secret", "password", "key"}

    @classmethod
    def __call__(
        cls, logger: logging.Logger, method_name: str, event_dict: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        # redact any values whose key matches secret keys (case-insensitive)
        redacted = {}
        for k, v in event_dict.items():
            if isinstance(k, str) and k.lower() in cls.SECRET_KEYS:
                redacted[k] = "<redacted>"
            else:
                redacted[k] = v
        return redacted


def configure_logger(log_level: str = "INFO"):
    logging.basicConfig(level=log_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            SecretRedactor(),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()


# Export a module‑level logger for use throughout the app
logger = configure_logger()
