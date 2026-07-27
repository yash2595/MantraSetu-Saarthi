"""Concrete EmbeddingProvider module for MantraSetu AgentOS.

This module implements EmbeddingProvider for converting input text into immutable EmbeddingVector
domain models by delegating vector generation to an injected BaseEmbeddingClient implementation.
"""

from __future__ import annotations

from typing import Sequence

from app.rag.base import BaseEmbeddingProvider, EmbeddingError
from app.rag.contracts import BaseEmbeddingClient
from app.rag.models import EmbeddingVector


class EmbeddingProvider(BaseEmbeddingProvider):
    """Concrete text embedding provider implementing BaseEmbeddingProvider contract.

    Responsibility:
        Validates input text and batch parameters, delegates vector generation to an injected
        BaseEmbeddingClient instance, validates raw provider output, converts raw float arrays into
        immutable EmbeddingVector models, and translates errors into EmbeddingError exceptions.
    """

    def __init__(
        self,
        client: BaseEmbeddingClient,
        model_name: str = "text-embedding-v3",
    ) -> None:
        """Initialize EmbeddingProvider with an injected embedding client.

        Args:
            client: Injected BaseEmbeddingClient instance.
            model_name: Model identifier string.
        """
        self._client = client
        self._model_name = model_name

    async def embed_text(self, text: str) -> EmbeddingVector:
        """Generate an immutable EmbeddingVector for a single input text string.

        Args:
            text: Input text string.

        Returns:
            EmbeddingVector: Immutable domain vector model.

        Raises:
            EmbeddingError: If text validation fails, provider output is invalid, or client errors.
        """
        self._validate_text(text)

        try:
            raw_vector = await self._client.generate_embedding(text)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError("Embedding client failed to generate vector.") from exc

        self._validate_raw_vector(raw_vector)
        return self._create_embedding_vector(raw_vector)

    async def embed_batch(
        self,
        texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]:
        """Generate immutable EmbeddingVector models for a batch of text strings.

        Args:
            texts: Immutable tuple of input text strings.

        Returns:
            tuple[EmbeddingVector, ...]: Immutable tuple of domain vector models.

        Raises:
            EmbeddingError: If batch validation fails, provider output is invalid, or client errors.
        """
        self._validate_batch(texts)

        try:
            raw_vectors = await self._client.generate_batch_embeddings(list(texts))
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError("Embedding client failed to generate batch vectors.") from exc

        if not isinstance(raw_vectors, (list, tuple)) or len(raw_vectors) != len(texts):
            raise EmbeddingError(
                f"Embedding client returned invalid batch count: expected {len(texts)}."
            )

        results: list[EmbeddingVector] = []
        for i, raw_vector in enumerate(raw_vectors):
            try:
                self._validate_raw_vector(raw_vector)
            except EmbeddingError as exc:
                raise EmbeddingError(
                    f"Embedding client returned invalid vector at batch index {i}."
                ) from exc
            results.append(self._create_embedding_vector(raw_vector))

        return tuple(results)

    async def health_check(self) -> bool:
        """Check operational health of the remote embedding client backend.

        Returns:
            bool: True if operational, False otherwise.
        """
        try:
            return await self._client.health_check()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private Helper Methods
    # ------------------------------------------------------------------

    def _validate_text(self, text: str) -> None:
        """Validate single input text integrity.

        Args:
            text: Input text string.

        Raises:
            EmbeddingError: If text is None, non-string, empty, or whitespace-only.
        """
        if text is None:
            raise EmbeddingError("Input text cannot be None.")

        if not isinstance(text, str):
            raise EmbeddingError("Input text must be a string.")

        if not text.strip():
            raise EmbeddingError("Input text cannot be empty or whitespace-only.")

    def _validate_batch(self, texts: tuple[str, ...]) -> None:
        """Validate input batch integrity.

        Args:
            texts: Tuple of input text strings.

        Raises:
            EmbeddingError: If batch is empty, None, or contains invalid items.
        """
        if not texts or not isinstance(texts, (tuple, list)):
            raise EmbeddingError("Input texts batch cannot be empty or None.")

        for i, item in enumerate(texts):
            if item is None or not isinstance(item, str) or not item.strip():
                raise EmbeddingError(
                    f"Invalid text element at batch index {i}: must be a non-empty string."
                )

    def _validate_raw_vector(self, raw_vector: Sequence[float]) -> None:
        """Validate raw vector output from embedding client.

        Args:
            raw_vector: Raw response from client.

        Raises:
            EmbeddingError: If raw_vector is None, non-sequence, empty, or contains non-numeric values.
        """
        if raw_vector is None:
            raise EmbeddingError("Embedding client returned None for vector.")

        if not isinstance(raw_vector, (list, tuple)):
            raise EmbeddingError("Embedding client output must be a list or tuple of floats.")

        if not raw_vector:
            raise EmbeddingError("Embedding client returned an empty vector.")

        for val in raw_vector:
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise EmbeddingError("Embedding client vector contains non-numeric values.")

    def _create_embedding_vector(
        self,
        raw_vector: Sequence[float],
    ) -> EmbeddingVector:
        """Construct an immutable EmbeddingVector domain model from raw float values.

        Args:
            raw_vector: Sequence of float values.

        Returns:
            EmbeddingVector: Domain vector model.
        """
        values = tuple(float(v) for v in raw_vector)
        return EmbeddingVector(
            values=values,
            dimension=len(values),
            model=self._model_name,
        )
