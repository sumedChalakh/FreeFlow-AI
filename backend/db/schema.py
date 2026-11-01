"""Database schema DDL and versioned migration runner for FreeFlow AI.

Uses SQLite PRAGMA user_version for sequential, transactional schema migrations.
Never writes raw secrets, prompts, or sensitive message contents.
"""

import sqlite3
from collections.abc import Callable

from backend.logger import logger

SCHEMA_V1 = """
-- Providers table (non-secret configuration)
CREATE TABLE IF NOT EXISTS providers (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    base_url TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    credential_ref TEXT,
    extra_config_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Catalog models table (normalized model deployments)
CREATE TABLE IF NOT EXISTS catalog_models (
    composite_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    is_local INTEGER NOT NULL DEFAULT 0,
    supports_streaming INTEGER NOT NULL DEFAULT 0,
    supports_tools INTEGER NOT NULL DEFAULT 0,
    supports_vision INTEGER NOT NULL DEFAULT 0,
    context_window INTEGER,
    is_stale INTEGER NOT NULL DEFAULT 0,
    last_seen_at REAL,
    last_checked_at REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_catalog_models_provider ON catalog_models(provider_id);
CREATE INDEX IF NOT EXISTS idx_catalog_models_model_id ON catalog_models(model_id);
CREATE INDEX IF NOT EXISTS idx_catalog_models_stale ON catalog_models(is_stale);

-- Routing profiles table
CREATE TABLE IF NOT EXISTS routing_profiles (
    name TEXT PRIMARY KEY,
    description TEXT,
    candidates_json TEXT NOT NULL,
    max_retries INTEGER NOT NULL DEFAULT 2,
    timeout_seconds REAL,
    required_capabilities_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Execute v1 initial schema migration."""
    conn.executescript(SCHEMA_V1)
    conn.execute("PRAGMA user_version = 1;")
    logger.info("Executed SQLite migration v1")


MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, _migrate_v1),
]


def run_migrations(conn: sqlite3.Connection) -> int:
    """Run all pending schema migrations sequentially in transactions.

    Returns the resulting user_version.
    """
    cursor = conn.execute("PRAGMA user_version;")
    row = cursor.fetchone()
    current_version: int = int(row[0]) if row is not None else 0

    for target_version, migration_func in MIGRATIONS:
        if current_version < target_version:
            logger.info(
                "Applying SQLite migration",
                from_version=current_version,
                to_version=target_version,
            )
            with conn:
                migration_func(conn)
            current_version = target_version

    return current_version
