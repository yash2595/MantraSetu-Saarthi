"""Centralized Application Lifecycle Management Module for MantraSetu AgentOS.

This module provides LifecycleState enum, BaseLifecycleService abstract interface, and LifecycleManager
for orchestrating sequential application startup, state transitions, and reverse-order graceful shutdown.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from enum import Enum
from typing import Sequence

from app.core.dependency import ApplicationContainer
from app.core.exceptions import ApplicationError, ConfigurationError


class LifecycleState(str, Enum):
    """Enumeration of application lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"


class BaseLifecycleService(ABC):
    """Abstract interface defining the lifecycle contract for application services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique service identifier name string.

        Returns:
            str: Unique service name.
        """
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service resources, background tasks, and connections."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close service connections and release allocated resources gracefully."""
        ...


class LifecycleManager:
    """Centralized lifecycle manager coordinating startup and shutdown orchestration.

    Responsibility:
        Maintains application LifecycleState transitions, registers BaseLifecycleService components,
        initializes services sequentially in registration order, and closes services in reverse
        registration order during shutdown.
    """

    def __init__(self, container: ApplicationContainer) -> None:
        """Initialize LifecycleManager with an ApplicationContainer dependency.

        Args:
            container: ApplicationContainer instance.

        Raises:
            ConfigurationError: If container is None.
        """
        if container is None:
            raise ConfigurationError("ApplicationContainer cannot be None.")

        self._container = container
        self._state = LifecycleState.CREATED
        self._services: list[BaseLifecycleService] = []
        self._service_names: set[str] = set()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> LifecycleState:
        """Expose current application LifecycleState.

        Returns:
            LifecycleState: Current lifecycle state enum value.
        """
        return self._state

    def register_service(self, service: BaseLifecycleService) -> None:
        """Register a BaseLifecycleService component for startup and shutdown management.

        Args:
            service: BaseLifecycleService instance.

        Raises:
            ConfigurationError: If service is None or service.name is already registered.
        """
        if service is None:
            raise ConfigurationError("Lifecycle service cannot be None.")

        name = service.name
        if not name or not isinstance(name, str):
            raise ConfigurationError("Lifecycle service must have a non-empty name property.")

        if name in self._service_names:
            raise ConfigurationError(
                f"Duplicate lifecycle service registration for '{name}'."
            )

        self._services.append(service)
        self._service_names.add(name)

    async def initialize(self) -> None:
        """Sequential startup orchestration initializing registered services in order.

        Transitions:
            CREATED -> INITIALIZING -> READY (or FAILED on error)

        Raises:
            ApplicationError: If initialization fails or state transition is invalid.
        """
        async with self._lock:
            if self._state == LifecycleState.READY:
                return

            if self._state not in (LifecycleState.CREATED, LifecycleState.FAILED):
                raise ApplicationError(
                    f"Cannot initialize application from state '{self._state}'."
                )

            self._state = LifecycleState.INITIALIZING

            for service in self._services:
                try:
                    await service.initialize()
                except Exception as exc:
                    self._state = LifecycleState.FAILED
                    raise ApplicationError(
                        f"Lifecycle initialization failed at service '{service.name}'."
                    ) from exc

            self._state = LifecycleState.READY

    async def shutdown(self) -> None:
        """Graceful shutdown orchestration closing registered services in reverse order.

        Transitions:
            READY / INITIALIZING / FAILED -> SHUTTING_DOWN -> STOPPED
        """
        async with self._lock:
            if self._state in (LifecycleState.STOPPED, LifecycleState.SHUTTING_DOWN):
                return

            self._state = LifecycleState.SHUTTING_DOWN

            for service in reversed(self._services):
                try:
                    await service.close()
                except Exception:
                    # Ignore shutdown failures to guarantee all services get a close attempt
                    pass

            self._state = LifecycleState.STOPPED
