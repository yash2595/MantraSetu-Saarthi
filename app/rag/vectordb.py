"""Concrete VectorDatabase module for MantraSetu AgentOS.

This module implements VectorDatabase for vector storage, deletion, and similarity search
by delegating indexing and query operations to an injected BaseVectorDatabaseClient implementation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.rag.base import BaseVectorDatabase, VectorDatabaseError
from app.rag.contracts import BaseVectorDatabaseClient
from app.rag.models import DocumentChunk, EmbeddingVector, RetrievedChunk


class VectorDatabase(BaseVectorDatabase):
    """Concrete vector database manager implementing BaseVectorDatabase contract.

    Responsibility:
        Validates document chunk and vector parameters, delegates index storage, deletion,
        and similarity search to an injected BaseVectorDatabaseClient, validates raw search results,
        translates result dictionaries into immutable RetrievedChunk models, and translates exceptions.
    """

    def __init__(self, client: BaseVectorDatabaseClient) -> None:
        """Initialize VectorDatabase with an injected vector database client.

        Args:
            client: Injected BaseVectorDatabaseClient instance.
        """
        self._client = client

    async def upsert(self, chunks: tuple[DocumentChunk, ...]) -> None:
        """Insert or update embedded DocumentChunk models in the vector index.

        Args:
            chunks: Immutable tuple of DocumentChunk instances.

        Raises:
            VectorDatabaseError: If chunks tuple is invalid or client upsert fails.
        """
        self._validate_chunks(chunks)

        try:
            await self._client.upsert_chunks(list(chunks))
        except VectorDatabaseError:
            raise
        except Exception as exc:
            raise VectorDatabaseError("Vector database failed to upsert document chunks.") from exc

    async def delete(self, chunk_ids: tuple[UUID, ...]) -> None:
        """Remove document chunks from the vector index by UUID identifiers.

        Args:
            chunk_ids: Immutable tuple of chunk UUIDs.

        Raises:
            VectorDatabaseError: If chunk_ids tuple is invalid or client deletion fails.
        """
        self._validate_chunk_ids(chunk_ids)

        try:
            await self._client.delete_chunks(list(chunk_ids))
        except VectorDatabaseError:
            raise
        except Exception as exc:
            raise VectorDatabaseError("Vector database failed to delete document chunks.") from exc

    async def search(
        self,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        """Execute vector similarity search and return immutable RetrievedChunk models.

        Args:
            query_vector: Query EmbeddingVector model.
            top_k: Maximum number of nearest neighbors to retrieve.
            filters: Optional metadata filtering dictionary.

        Returns:
            tuple[RetrievedChunk, ...]: Immutable tuple of RetrievedChunk models.

        Raises:
            VectorDatabaseError: If query parameters are invalid or search fails.
        """
        self._validate_search(query_vector, top_k)

        try:
            raw_results = await self._client.search_vector(
                vector=list(query_vector.values),
                top_k=top_k,
                filters=filters,
            )
        except VectorDatabaseError:
            raise
        except Exception as exc:
            raise VectorDatabaseError("Vector database similarity search failed.") from exc

        self._validate_results(raw_results)
        return self._parse_results(raw_results)

    async def clear(self) -> None:
        """Purge all stored vectors and indices from the database.

        Raises:
            VectorDatabaseError: If database clear fails.
        """
        try:
            await self._client.clear_index()
        except Exception as exc:
            raise VectorDatabaseError("Vector database failed to clear index.") from exc

    async def health_check(self) -> bool:
        """Check operational status of the remote vector database backend.

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

    def _validate_chunks(self, chunks: tuple[DocumentChunk, ...]) -> None:
        """Validate input document chunks collection.

        Args:
            chunks: Immutable tuple of DocumentChunk instances.

        Raises:
            VectorDatabaseError: If chunks is None, empty, or contains invalid items.
        """
        if not chunks or not isinstance(chunks, (tuple, list)):
            raise VectorDatabaseError("Document chunks collection cannot be empty or None.")

        for i, chunk in enumerate(chunks):
            if not isinstance(chunk, DocumentChunk):
                raise VectorDatabaseError(
                    f"Invalid chunk at index {i}: must be a DocumentChunk instance."
                )
            if not chunk.chunk_id:
                raise VectorDatabaseError(f"DocumentChunk at index {i} missing chunk_id.")
            if not chunk.embedding or not chunk.embedding.values:
                raise VectorDatabaseError(
                    f"DocumentChunk at index {i} missing valid embedding vector."
                )

    def _validate_chunk_ids(self, chunk_ids: tuple[UUID, ...]) -> None:
        """Validate input chunk UUIDs collection.

        Args:
            chunk_ids: Tuple of chunk UUIDs.

        Raises:
            VectorDatabaseError: If chunk_ids is None, empty, or contains non-UUID items.
        """
        if not chunk_ids or not isinstance(chunk_ids, (tuple, list)):
            raise VectorDatabaseError("Chunk IDs collection cannot be empty or None.")

        for i, cid in enumerate(chunk_ids):
            if not isinstance(cid, UUID):
                raise VectorDatabaseError(
                    f"Invalid chunk_id at index {i}: must be a UUID instance."
                )

    def _validate_search(
        self,
        query_vector: EmbeddingVector,
        top_k: int,
    ) -> None:
        """Validate vector search query parameters.

        Args:
            query_vector: Query EmbeddingVector model.
            top_k: Top K results limit.

        Raises:
            VectorDatabaseError: If vector is invalid or top_k <= 0.
        """
        if not query_vector or not isinstance(query_vector, EmbeddingVector):
            raise VectorDatabaseError("query_vector must be a valid EmbeddingVector instance.")

        if not query_vector.values:
            raise VectorDatabaseError("query_vector contains no vector values.")

        if top_k <= 0:
            raise VectorDatabaseError("top_k parameter must be greater than zero.")

    def _validate_results(self, raw_results: Any) -> None:
        """Validate raw search results returned by client.

        Args:
            raw_results: Client search response payload.

        Raises:
            VectorDatabaseError: If raw_results is not a list or tuple of valid dictionaries.
        """
        if raw_results is None or not isinstance(raw_results, (list, tuple)):
            raise VectorDatabaseError("Vector database client returned invalid search results payload.")

        for i, item in enumerate(raw_results):
            if not isinstance(item, dict):
                raise VectorDatabaseError(
                    f"Invalid search result item at index {i}: expected dictionary."
                )
            if "chunk" not in item or not isinstance(item["chunk"], DocumentChunk):
                raise VectorDatabaseError(
                    f"Search result item at index {i} missing valid 'chunk' DocumentChunk."
                )

    def _parse_results(
        self,
        raw_results: list[dict[str, Any]],
    ) -> tuple[RetrievedChunk, ...]:
        """Convert validated result dictionaries into immutable RetrievedChunk models.

        Args:
            raw_results: List of result dictionaries.

        Returns:
            tuple[RetrievedChunk, ...]: Tuple of domain RetrievedChunk models.
        """
        parsed: list[RetrievedChunk] = []
        for item in raw_results:
            chunk: DocumentChunk = item["chunk"]
            score: float = float(item.get("score", 0.0))
            explanation: str | None = item.get("relevance_explanation")

            parsed.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=score,
                    relevance_explanation=explanation,
                )
            )

        return tuple(parsed)
