"""Prompt manager for versioned and dynamic prompt resolution."""

from __future__ import annotations

import logging
from string import Template
from typing import Any

from app.prompts.base import BasePromptManager, PromptTemplate
from app.prompts.system_prompt import PROMPT_REGISTRY

logger = logging.getLogger(__name__)


class PromptNotFoundError(KeyError):
    """Raised when a requested prompt or version does not exist."""


class PromptManager(BasePromptManager):
    """Resolve prompts from a registry with versioning and variable injection.

    Design goals:
    - Keep prompt content outside services.
    - Resolve prompts dynamically from a registry.
    - Support versioning without changing call sites.
    - Keep the implementation light enough for hundreds of prompts.
    """

    def __init__(self, registry: dict[str, dict[str, PromptTemplate]] | None = None) -> None:
        self._registry = registry or PROMPT_REGISTRY

    def get_system_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("system", version, **variables)

    def get_navigation_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("navigation", version, **variables)

    def get_booking_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("booking", version, **variables)

    def get_pandit_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("pandit", version, **variables)

    def _resolve(self, name: str, version: str | None, **variables: Any) -> str:
        resolved_version = version or self._get_latest_version(name)
        prompt = self._load_prompt(name, resolved_version)
        rendered = self._render(prompt.template, **variables)
        logger.debug(
            "prompt_resolved",
            extra={"prompt_name": name, "version": resolved_version, "kind": prompt.kind.value},
        )
        return rendered

    def _load_prompt(self, name: str, version: str) -> PromptTemplate:
        try:
            return self._registry[name][version]
        except KeyError as exc:
            raise PromptNotFoundError(f"Prompt not found: {name} version {version}") from exc

    def _get_latest_version(self, name: str) -> str:
        try:
            versions = self._registry[name]
        except KeyError as exc:
            raise PromptNotFoundError(f"Prompt not found: {name}") from exc
        return sorted(versions.keys())[-1]

    def _render(self, template: str, **variables: Any) -> str:
        if not variables:
            return template
        normalized = {key: str(value) for key, value in variables.items()}
        return Template(template).safe_substitute(normalized)
