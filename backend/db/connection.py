"""SQLite connection and lifecycle management for FreeFlow AI.

Enforces WAL journal mode, foreign key constraints, busy timeouts, and corruption
preservation with explicit degraded mode fallback. Never performs I/O in constructors.
"""

import asyncio
import os
import shutil
import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from backend.logger import logger

from .schema import run_migrations

T = TypeVar("T")


class DatabaseManager:
    """Manages SQLite database connections, WAL pragmas, migrations, and degraded mode."""

    def __init__(self, db_path: str = "freeflow.db") -> None:
        """Initialize configuration without performing file I/O."""
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self._thread_lock = threading.RLock()
        self.is_degraded: bool = False
        self.degraded_reason: str | None = None
        self.is_initialized: bool = False

    @property
    def write_lock(self) -> threading.RLock:
        """Return the re-entrant lock used to synchronize connection access."""
        return self._thread_lock

    def get_connection(self) -> sqlite3.Connection:
        """Return the active SQLite connection, or raise RuntimeError if not initialized."""
        if self._conn is None:
            raise RuntimeError("DatabaseManager has not been initialized. Call initialize() first.")
        return self._conn

    def _open_and_configure_connection(self, path: str) -> sqlite3.Connection:
        """Open SQLite connection and apply required performance/safety pragmas."""
        conn = sqlite3.connect(
            path,
            check_same_thread=False,
            timeout=5.0,
        )
        conn.row_factory = sqlite3.Row

        # Apply pragmas
        if path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _check_integrity(self, conn: sqlite3.Connection) -> bool:
        """Perform quick integrity verification."""
        cursor = conn.execute("PRAGMA quick_check;")
        result = cursor.fetchone()
        return result is not None and result[0] == "ok"

    def _preserve_corrupt_file(self, file_path: str) -> str | None:
        """Preserve a corrupt database file for diagnosis and forensic recovery."""
        src = Path(file_path)
        if not src.exists():
            return None

        timestamp = int(time.time() * 1000)
        dest = src.with_name(f"{src.stem}.corrupt.{timestamp}{src.suffix}")
        counter = 1
        while dest.exists():
            dest = src.with_name(f"{src.stem}.corrupt.{timestamp}_{counter}{src.suffix}")
            counter += 1

        try:
            shutil.copy2(src, dest)
            logger.error(
                "Corrupt database file preserved for recovery",
                original=str(src),
                preserved_copy=str(dest),
            )
            return str(dest)
        except Exception as exc:
            logger.error("Failed to copy corrupt database file", error=str(exc))
            return None

    def initialize(self) -> None:
        """Open database, verify integrity, run migrations, or activate degraded mode.

        Explicitly performs I/O on demand rather than inside __init__.
        """
        if self.is_initialized and self._conn is not None:
            return

        preserved_path: str | None = None
        try:
            # Check if directory exists, create if missing and not :memory:
            if self.db_path != ":memory:":
                p = Path(self.db_path)
                if p.parent and not p.parent.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)

            conn = self._open_and_configure_connection(self.db_path)

            # Check integrity if opening an existing file
            if (
                self.db_path != ":memory:"
                and os.path.exists(self.db_path)
                and not self._check_integrity(conn)
            ):
                conn.close()
                preserved_path = self._preserve_corrupt_file(self.db_path)
                raise sqlite3.DatabaseError(
                    f"Database integrity check failed. Preserved as {preserved_path}"
                )

            # Execute versioned schema migrations
            run_migrations(conn)

            self._conn = conn
            self.is_degraded = False
            self.degraded_reason = None
            self.is_initialized = True
            logger.info("SQLite database initialized successfully", db_path=self.db_path)

        except Exception as exc:
            # Preserve corrupt database file for recovery (only if not already preserved)
            if (
                self.db_path != ":memory:"
                and os.path.exists(self.db_path)
                and preserved_path is None
            ):
                self._preserve_corrupt_file(self.db_path)

            self.is_degraded = True
            self.degraded_reason = str(exc)
            logger.warning(
                "Failed to initialize SQLite database; activating degraded in-memory mode",
                db_path=self.db_path,
                reason=str(exc),
            )

            # Fallback to an in-memory database to allow observable operation
            try:
                fallback_conn = self._open_and_configure_connection(":memory:")
                run_migrations(fallback_conn)
                self._conn = fallback_conn
                self.is_initialized = True
            except Exception as inner_exc:
                logger.error("Even in-memory fallback database failed", error=str(inner_exc))
                self._conn = None
                self.is_initialized = False

    def _execute_sync(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        with self._thread_lock:
            return func(*args, **kwargs)

    async def run_in_thread(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a blocking database operation in a worker thread to keep the event loop free."""
        return await asyncio.to_thread(self._execute_sync, func, *args, **kwargs)

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as exc:
                logger.warning("Error closing SQLite connection", error=str(exc))
            finally:
                self._conn = None
                self.is_initialized = False

    def get_health_status(self) -> dict[str, Any]:
        """Report honest database health and degraded mode status."""
        if not self.is_initialized or self._conn is None:
            return {
                "available": False,
                "degraded": True,
                "reason": self.degraded_reason or "Database not initialized",
                "mode": "none",
            }

        if self.is_degraded:
            return {
                "available": True,
                "degraded": True,
                "reason": self.degraded_reason,
                "mode": "in_memory_fallback",
            }

        return {
            "available": True,
            "degraded": False,
            "reason": None,
            "mode": "wal" if self.db_path != ":memory:" else "memory",
        }
