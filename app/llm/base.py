"""Abstract LLM contract used by all providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLM(ABC):
    """Provider-agnostic LLM interface.

    Only the ``generate()`` method is public so business logic can remain
    stable while providers change underneath it.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text response for the provided prompt."""
        raise NotImplementedError
