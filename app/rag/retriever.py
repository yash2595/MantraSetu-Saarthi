"""Concrete Retriever module for MantraSetu AgentOS.

This module implements Retriever for coordinating query text vector embedding generation and
vector database similarity search to produce immutable SearchResult models.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from app.rag.base import (
    BaseEmbeddingProvider,
    BaseRetriever,
    BaseVectorDatabase,
    RetrievalError,
)
from app.rag.models import (
    RetrievalStatus,
    RetrievedChunk,
    SearchMetadata,
    SearchQuery,
    SearchResult,
)


class Retriever(BaseRetriever):
    """Concrete retriever component implementing BaseRetriever contract.

    Responsibility:
        Validates SearchQuery requests, delegates embedding generation to BaseEmbeddingProvider,
        executes similarity queries against BaseVectorDatabase, filters results by threshold,
        measures total latency, and wraps output into immutable SearchResult models.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_db: BaseVectorDatabase,
    ) -> None:
        """Initialize Retriever with injected embedding provider and vector database.

        Args:
            embedding_provider: BaseEmbeddingProvider instance for query vectorization.
            vector_db: BaseVectorDatabase instance for similarity search.
        """
        self._embedding_provider = embedding_provider
        self._vector_db = vector_db

    async def retrieve(self, query: SearchQuery) -> SearchResult:
        """Execute vector search retrieval for a SearchQuery payload.

        Args:
            query: SearchQuery payload model.

        Returns:
            SearchResult: Search response model containing retrieved chunks and latency.

        Raises:
            RetrievalError: If query validation fails or sub-component execution fails.
        """
        self._validate_query(query)
        start_time = time.perf_counter()

        try:
            query_vector = await self._embedding_provider.embed_text(query.text)
            raw_chunks = await self._vector_db.search(
                query_vector=query_vector,
                top_k=query.top_k,
                filters=query.metadata.filters,
            )

            # Apply min_score filtering threshold
            filtered_chunks = tuple(
                c for c in raw_chunks if c.score >= query.min_score
            )

            status = (
                RetrievalStatus.SUCCESS
                if filtered_chunks
                else RetrievalStatus.EMPTY
            )
            latency_ms = (time.perf_counter() - start_time) * 1000

            return self._build_search_result(
                query_id=query.query_id,
                status=status,
                chunks=filtered_chunks,
                latency_ms=latency_ms,
                metadata=query.metadata,
            )
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError("Retrieval operation failed.") from exc

    async def health_check(self) -> bool:
        """Check health status across embedding provider and vector database components.

        Returns:
            bool: True if both sub-components are operational, False otherwise.
        """
        try:
            embed_healthy = await self._embedding_provider.health_check()
            vdb_healthy = await self._vector_db.health_check()
            return embed_healthy and vdb_healthy
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private Helper Methods
    # ------------------------------------------------------------------

    def _validate_query(self, query: SearchQuery) -> None:
        """Validate input SearchQuery model integrity.

        Args:
            query: SearchQuery instance.

        Raises:
            RetrievalError: If query is None or text is empty/whitespace.
        """
        if not query or not isinstance(query, SearchQuery):
            raise RetrievalError("SearchQuery cannot be None.")

        if not query.text or not query.text.strip():
            raise RetrievalError("SearchQuery text cannot be empty or blank.")

        if query.top_k <= 0:
            raise RetrievalError("SearchQuery top_k parameter must be greater than zero.")

    def _build_search_result(
        self,
        query_id: UUID,
        status: RetrievalStatus,
        chunks: tuple[RetrievedChunk, ...],
        latency_ms: float,
        metadata: SearchMetadata,
    ) -> SearchResult:
        """Construct an immutable SearchResult domain model.

        Args:
            query_id: Associated query identifier UUID.
            status: RetrievalStatus enum outcome.
            chunks: Immutable tuple of RetrievedChunk models.
            latency_ms: Measured execution latency in milliseconds.
            metadata: SearchMetadata instance.

        Returns:
            SearchResult: Final response model.
        """
        return SearchResult(
            query_id=query_id,
            status=status,
            retrieved_chunks=chunks,
            latency_ms=latency_ms,
            metadata=metadata,
        )
