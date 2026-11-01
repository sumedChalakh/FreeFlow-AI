"""FreeFlow AI Routing and Automatic Failover Package."""

from .cooldown import CooldownTracker
from .engine import RoutingEngine, RoutingExhaustedError, default_engine
from .models import (
    FailoverAttempt,
    RoutingDecisionEvent,
    RoutingProfile,
    TargetResolution,
)
from .resolver import ModelResolver

__all__ = [
    "CooldownTracker",
    "FailoverAttempt",
    "ModelResolver",
    "RoutingDecisionEvent",
    "RoutingEngine",
    "RoutingExhaustedError",
    "RoutingProfile",
    "TargetResolution",
    "default_engine",
]
