"""Protocol contracts for the RAG subsystem in MantraSetu AgentOS.

This module defines protocol interfaces for external dependencies such as embedding clients
and vector database clients.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.rag.models import DocumentChunk


class BaseEmbeddingClient(Protocol):
    """Abstract protocol for external text embedding client dependencies."""

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a raw float vector array for a single text string."""
        ...

    async def generate_batch_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate raw float vector arrays for a batch of text strings."""
        ...

    async def health_check(self) -> bool:
        """Check operational status of the remote embedding client backend."""
        ...


class BaseVectorDatabaseClient(Protocol):
    """Abstract protocol for external vector database client dependencies."""

    async def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Insert or update embedded document chunk objects in the vector index."""
        ...

    async def delete_chunks(self, chunk_ids: list[UUID]) -> None:
        """Remove document chunks from the vector index by UUID identifiers."""
        ...

    async def search_vector(
        self,
        vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute vector similarity search returning raw result dictionaries."""
        ...

    async def clear_index(self) -> None:
        """Purge all stored vectors and index collections."""
        ...

    async def health_check(self) -> bool:
        """Check operational status of the remote vector database backend."""
        ...
