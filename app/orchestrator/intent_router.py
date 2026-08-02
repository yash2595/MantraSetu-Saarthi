"""Fast-path Intent Router bypassing unnecessary LLM invocations in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import ResponseType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FastPathIntentRouter"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class FastPathResolution:
    """Immutable resolution returned by FastPathIntentRouter."""

    is_fast_path: bool
    response_text: str = ""
    target_route: str | None = None
    intent_name: str = "UNKNOWN"
    response_type: ResponseType = ResponseType.CHAT
    confidence: float = 0.0


class FastPathIntentRouter:
    """Router detecting deterministic requests (greetings, FAQs, direct route requests) to bypass LLM calls."""

    _GREETINGS = {"hello", "hi", "namaste", "hey", "good morning", "good evening"}
    _FAQS = {
        "what is mantrasetu": "MantraSetu AgentOS is an enterprise AI assistant for spiritual rituals, temple pujas, and astrology consultations.",
        "help": "I can help you navigate to Pujas, Bookings, Services, Astrology, or Payment pages. Just tell me what you need!",
    }
    _ROUTE_KEYWORDS = {
        "puja": "/puja",
        "booking": "/booking",
        "services": "/services",
        "astrology": "/astrology",
        "payment": "/payment",
        "login": "/login",
    }

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._evaluations_count = 0
        self._fast_path_hits_count = 0

    def evaluate_fast_path(self, user_message: str) -> FastPathResolution:
        """Evaluate input message for deterministic fast-path response."""
        with self._lock:
            self._evaluations_count += 1
            msg_clean = user_message.strip().lower()

            # 1. Greetings
            if msg_clean in self._GREETINGS:
                self._fast_path_hits_count += 1
                return FastPathResolution(
                    is_fast_path=True,
                    response_text="Namaste! Welcome to MantraSetu AgentOS. How can I assist your spiritual journey today?",
                    intent_name="GREETING",
                    confidence=1.0,
                )

            # 2. FAQs
            if msg_clean in self._FAQS:
                self._fast_path_hits_count += 1
                return FastPathResolution(
                    is_fast_path=True,
                    response_text=self._FAQS[msg_clean],
                    intent_name="FAQ",
                    confidence=1.0,
                )

            # 3. Direct Route Match
            for kw, route in self._ROUTE_KEYWORDS.items():
                if msg_clean in (f"go to {kw}", f"open {kw}", f"navigate to {kw}"):
                    self._fast_path_hits_count += 1
                    return FastPathResolution(
                        is_fast_path=True,
                        response_text=f"Navigating to {kw.capitalize()} page.",
                        target_route=route,
                        intent_name="DIRECT_NAVIGATE",
                        response_type=ResponseType.NAVIGATION_DIRECTIVE,
                        confidence=0.98,
                    )

            return FastPathResolution(is_fast_path=False)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return intent router statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluations_count": self._evaluations_count,
                "fast_path_hits_count": self._fast_path_hits_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="FastPathIntentRouter operational.",
        )
