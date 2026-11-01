"""Deployment health and cooldown tracking for FreeFlow AI.

Maintains consecutive failure counts and temporary exclusion windows per deployment
to protect upstream providers and avoid routing traffic to degraded backends.
"""

import time
from collections.abc import Callable

from backend.logger import logger
from backend.providers.errors import ProviderError


class CooldownTracker:
    """Tracks consecutive failures and cooldown windows for model deployments."""

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initialize tracker with configurable threshold, duration, and clock.

        Args:
            failure_threshold: Number of consecutive retryable failures before cooldown triggers.
            cooldown_seconds: Duration in seconds a deployment is temporarily excluded.
            clock: Time function, injectable for deterministic testing.
        """
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = max(1.0, cooldown_seconds)
        self._clock = clock

        # consecutive failure count per composite_id
        self._failure_counts: dict[str, int] = {}
        # timestamp when cooldown expires per composite_id
        self._cooldown_expirations: dict[str, float] = {}

    def record_success(self, composite_id: str) -> None:
        """Record a successful invocation, resetting consecutive failures and clearing cooldown."""
        if composite_id in self._failure_counts or composite_id in self._cooldown_expirations:
            self._failure_counts.pop(composite_id, None)
            self._cooldown_expirations.pop(composite_id, None)
            logger.debug("Deployment cooldown and failures cleared on success", target=composite_id)

    def record_failure(self, composite_id: str, error: ProviderError) -> bool:
        """Record a failure for a deployment.

        Only retryable errors contribute to cooldown.
        Returns True if this failure caused the deployment to enter cooldown.
        """
        if not error.is_retryable:
            # Non-retryable errors (auth, bad request) represent request or client issues,
            # not backend unavailability, so they don't trigger provider cooldowns.
            return False

        now = self._clock()
        count = self._failure_counts.get(composite_id, 0) + 1
        self._failure_counts[composite_id] = count

        if count >= self.failure_threshold:
            self._cooldown_expirations[composite_id] = now + self.cooldown_seconds
            logger.warning(
                "Deployment entered cooldown due to consecutive failures",
                composite_id=composite_id,
                failures=count,
                cooldown_seconds=self.cooldown_seconds,
            )
            return True

        return False

    def is_in_cooldown(self, composite_id: str) -> bool:
        """Check if a deployment is currently in an active cooldown window."""
        exp = self._cooldown_expirations.get(composite_id)
        if exp is None:
            return False

        now = self._clock()
        if now >= exp:
            # Cooldown expired, clear it
            self._cooldown_expirations.pop(composite_id, None)
            return False

        return True

    def get_cooldown_remaining(self, composite_id: str) -> float:
        """Return the number of seconds remaining in cooldown, or 0.0 if not in cooldown."""
        exp = self._cooldown_expirations.get(composite_id)
        if exp is None:
            return 0.0

        now = self._clock()
        remaining = exp - now
        if remaining <= 0:
            self._cooldown_expirations.pop(composite_id, None)
            return 0.0

        return remaining

    def get_failure_count(self, composite_id: str) -> int:
        """Get the current count of consecutive failures for a deployment."""
        return self._failure_counts.get(composite_id, 0)

    def reset(self) -> None:
        """Reset all tracked failure counts and cooldown expirations."""
        self._failure_counts.clear()
        self._cooldown_expirations.clear()
