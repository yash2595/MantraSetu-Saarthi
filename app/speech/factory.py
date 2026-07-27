"""Speech-to-Text Provider Factory module.

Centralized registry for registering and retrieving Speech-to-Text provider adapters.
"""

import logging

from app.speech.base import BaseSpeechToTextProvider

logger = logging.getLogger(__name__)


class SpeechToTextProviderFactory:
    """Factory and registry manager for Speech-to-Text providers."""

    def __init__(self) -> None:
        """Initialize the factory with an empty provider registry."""
        self._provider_registry: dict[str, BaseSpeechToTextProvider] = {}
        logger.info("SpeechToTextProviderFactory initialized")

    def register(
        self,
        provider: BaseSpeechToTextProvider,
        overwrite: bool = False,
    ) -> None:
        """Register a BaseSpeechToTextProvider instance using its provider_name property.

        Args:
            provider: Concrete BaseSpeechToTextProvider instance to register.
            overwrite: Flag indicating whether to overwrite an existing registration.

        Raises:
            ValueError: If provider is None, has invalid provider_name, or is already registered when overwrite=False.
        """
        if provider is None or not isinstance(provider, BaseSpeechToTextProvider):
            raise ValueError("Provider must be an instance of BaseSpeechToTextProvider.")

        if not hasattr(provider, "provider_name") or not provider.provider_name:
            raise ValueError("Provider must expose a non-empty 'provider_name' property.")

        provider_name = provider.provider_name.strip().lower()

        if provider_name in self._provider_registry and not overwrite:
            raise ValueError(f"Provider '{provider_name}' is already registered.")

        self._provider_registry[provider_name] = provider
        logger.info("Provider registered [name=%s]", provider_name)

    def get(self, provider_name: str) -> BaseSpeechToTextProvider:
        """Retrieve a registered BaseSpeechToTextProvider instance by name.

        Args:
            provider_name: Case-insensitive provider name string identifier.

        Returns:
            BaseSpeechToTextProvider: Registered provider adapter instance.

        Raises:
            ValueError: If provider_name is empty or not registered in factory.
        """
        if not provider_name or not isinstance(provider_name, str) or not provider_name.strip():
            raise ValueError("provider_name must be a non-empty string.")

        normalized_name = provider_name.strip().lower()

        if normalized_name not in self._provider_registry:
            raise ValueError(f"Speech-to-Text provider '{provider_name}' is not registered.")

        logger.info("Provider retrieved [name=%s]", normalized_name)
        return self._provider_registry[normalized_name]


# Module-level singleton instance export
speech_to_text_factory = SpeechToTextProviderFactory()
