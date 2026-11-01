"""SQLite repositories for providers, catalog models, and routing profiles.

Ensures atomic transactions per provider, honest stale restoration on startup,
and zero persistence of sensitive credentials or prompt contents.
"""

import json
import time
from typing import Any

from backend.catalog.models import CatalogEntry
from backend.logger import logger
from backend.providers.base import ModelCapability, ProviderModel
from backend.routing.models import RoutingProfile

from .connection import DatabaseManager


class CatalogRepository:
    """Manages transactional SQLite storage for provider configuration and catalog models."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def save_provider(
        self,
        provider_id: str,
        display_name: str,
        base_url: str | None = None,
        enabled: bool = True,
        extra_config: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a non-secret provider record."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        extra_json = json.dumps(extra_config or {})

        sql = """
        INSERT INTO providers (
            id, display_name, base_url, enabled, extra_config_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            display_name=excluded.display_name,
            base_url=excluded.base_url,
            enabled=excluded.enabled,
            extra_config_json=excluded.extra_config_json,
            updated_at=excluded.updated_at;
        """
        with self.db.write_lock:
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    sql,
                    (
                        provider_id,
                        display_name,
                        base_url,
                        1 if enabled else 0,
                        extra_json,
                        now_str,
                        now_str,
                    ),
                )

    def save_provider_refresh(
        self,
        provider_id: str,
        unique_models: list[ProviderModel],
        omitted_ids: set[str],
        now: float,
    ) -> None:
        """Atomically persist a provider's discovered models and mark omitted models stale.

        Executes inside an atomic transaction. If any error occurs, the transaction rolls
        back completely, preserving the previous committed state in SQLite.
        """
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

        with self.db.write_lock:
            conn = self.db.get_connection()
            with conn:
                # Ensure parent provider record exists to satisfy foreign key constraint
                conn.execute(
                    """
                    INSERT INTO providers (id, display_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING;
                    """,
                    (provider_id, provider_id.capitalize(), now_str, now_str),
                )

                # 1. Mark omitted models stale
                if omitted_ids:
                    placeholders = ",".join("?" for _ in omitted_ids)
                    stale_sql = f"""
                    UPDATE catalog_models
                    SET is_stale = 1, last_checked_at = ?, updated_at = ?
                    WHERE provider_id = ? AND model_id IN ({placeholders});
                    """
                    conn.execute(stale_sql, [now, now_str, provider_id, *list(omitted_ids)])

                # 2. Upsert discovered models
                upsert_sql = """
                INSERT INTO catalog_models (
                    composite_id, provider_id, model_id, display_name, is_local,
                    supports_streaming, supports_tools, supports_vision, context_window,
                    is_stale, last_seen_at, last_checked_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(composite_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    is_local=excluded.is_local,
                    supports_streaming=excluded.supports_streaming,
                    supports_tools=excluded.supports_tools,
                    supports_vision=excluded.supports_vision,
                    context_window=excluded.context_window,
                    is_stale=excluded.is_stale,
                    last_seen_at=excluded.last_seen_at,
                    last_checked_at=excluded.last_checked_at,
                    updated_at=excluded.updated_at;
                """

                for model in unique_models:
                    composite_id = f"{provider_id}:{model.id}"
                    conn.execute(
                        upsert_sql,
                        (
                            composite_id,
                            provider_id,
                            model.id,
                            model.display_name,
                            1 if model.is_local else 0,
                            1 if model.capabilities.supports_streaming else 0,
                            1 if model.capabilities.supports_tools else 0,
                            1 if model.capabilities.supports_vision else 0,
                            model.capabilities.context_window,
                            0,  # is_stale = False
                            now,
                            now,
                            now_str,
                            now_str,
                        ),
                    )

    def mark_provider_stale(self, provider_id: str, now: float) -> None:
        """Mark all models for a provider stale when discovery fails."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        with self.db.write_lock:
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE catalog_models
                    SET is_stale = 1, last_checked_at = ?, updated_at = ?
                    WHERE provider_id = ?;
                    """,
                    (now, now_str, provider_id),
                )

    def load_all_entries(self) -> list[CatalogEntry]:
        """Restore catalog entries from SQLite.

        Safeguard: Restores all persisted entries as STALE (is_stale=True)
        until active discovery runs to confirm current backend availability.
        """
        with self.db.write_lock:
            conn = self.db.get_connection()
            cursor = conn.execute(
                """
                SELECT composite_id, provider_id, model_id, display_name, is_local,
                       supports_streaming, supports_tools, supports_vision, context_window,
                       last_seen_at, last_checked_at
                FROM catalog_models;
                """
            )
            entries: list[CatalogEntry] = []
            for row in cursor.fetchall():
                caps = ModelCapability(
                    supports_streaming=bool(row["supports_streaming"]),
                    supports_tools=bool(row["supports_tools"]),
                    supports_vision=bool(row["supports_vision"]),
                    context_window=row["context_window"],
                )
                entry = CatalogEntry(
                    composite_id=row["composite_id"],
                    provider_id=row["provider_id"],
                    model_id=row["model_id"],
                    display_name=row["display_name"],
                    capabilities=caps,
                    is_local=bool(row["is_local"]),
                    is_stale=True,  # restored as stale on startup until discovery runs
                    last_seen_at=row["last_seen_at"],
                    last_checked_at=row["last_checked_at"],
                )
                entries.append(entry)

        logger.info("Restored catalog entries from SQLite", count=len(entries))
        return entries

    def load_all_providers(self) -> list[dict[str, Any]]:
        """Restore non-secret provider configurations from SQLite."""
        with self.db.write_lock:
            conn = self.db.get_connection()
            cursor = conn.execute(
                """
                SELECT id, display_name, base_url, enabled, extra_config_json
                FROM providers;
                """
            )
            providers: list[dict[str, Any]] = []
            for row in cursor.fetchall():
                extra = {}
                if row["extra_config_json"]:
                    try:
                        extra = json.loads(row["extra_config_json"])
                    except Exception:
                        extra = {}

                providers.append(
                    {
                        "id": row["id"],
                        "display_name": row["display_name"],
                        "base_url": row["base_url"],
                        "enabled": bool(row["enabled"]),
                        "extra_config": extra,
                    }
                )
        return providers

    def save_profile(self, profile: RoutingProfile) -> None:
        """Persist a customized routing profile."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        candidates_json = json.dumps(profile.candidates)
        req_caps_json = json.dumps(profile.required_capabilities.model_dump())

        sql = """
        INSERT INTO routing_profiles (
            name, description, candidates_json, max_retries, timeout_seconds,
            required_capabilities_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            description=excluded.description,
            candidates_json=excluded.candidates_json,
            max_retries=excluded.max_retries,
            timeout_seconds=excluded.timeout_seconds,
            required_capabilities_json=excluded.required_capabilities_json,
            updated_at=excluded.updated_at;
        """
        with self.db.write_lock:
            conn = self.db.get_connection()
            with conn:
                conn.execute(
                    sql,
                    (
                        profile.name,
                        profile.description,
                        candidates_json,
                        profile.max_retries,
                        profile.timeout_seconds,
                        req_caps_json,
                        now_str,
                        now_str,
                    ),
                )

    def load_all_profiles(self) -> list[RoutingProfile]:
        """Restore routing profiles from SQLite."""
        with self.db.write_lock:
            conn = self.db.get_connection()
            cursor = conn.execute(
                """
                SELECT name, description, candidates_json, max_retries,
                       timeout_seconds, required_capabilities_json
                FROM routing_profiles;
                """
            )
            profiles: list[RoutingProfile] = []
            for row in cursor.fetchall():
                candidates = []
                if row["candidates_json"]:
                    try:
                        candidates = json.loads(row["candidates_json"])
                    except Exception:
                        candidates = []

                caps = ModelCapability()
                if row["required_capabilities_json"]:
                    try:
                        caps_data = json.loads(row["required_capabilities_json"])
                        caps = ModelCapability(**caps_data)
                    except Exception:
                        pass

                profiles.append(
                    RoutingProfile(
                        name=row["name"],
                        description=row["description"] or "",
                        candidates=candidates,
                        max_retries=row["max_retries"],
                        timeout_seconds=row["timeout_seconds"],
                        required_capabilities=caps,
                    )
                )

        return profiles
