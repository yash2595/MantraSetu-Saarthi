"""RAG Subsystem Service Facade for MantraSetu AgentOS.

This module provides RAGService as the primary public entry point for the RAG subsystem,
coordinating search retrieval via BaseRetriever, optional reranking via BaseReranker,
and document lifecycle management via BaseDocumentIndexer without implementing lower-level logic.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.rag.base import (
    BaseDocumentIndexer,
    BaseRAGService,
    BaseReranker,
    BaseRetriever,
    RAGError,
)
from app.rag.models import (
    DocumentChunk,
    KnowledgeDocument,
    SearchQuery,
    SearchResult,
)


class RAGService(BaseRAGService):
    """Public facade service implementing BaseRAGService contract.

    Responsibility:
        Coordinates end-to-end vector search retrieval, optional reranking, and document lifecycle
        indexing/deletion by delegating strictly to specialized injected components: BaseRetriever,
        BaseReranker, and BaseDocumentIndexer.
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        indexer: BaseDocumentIndexer,
        reranker: BaseReranker | None = None,
    ) -> None:
        """Initialize RAGService with injected retriever, indexer, and optional reranker dependencies.

        Args:
            retriever: BaseRetriever instance for vector search retrieval.
            indexer: BaseDocumentIndexer instance for document chunking, embedding, and deletion lifecycle.
            reranker: Optional BaseReranker instance for post-retrieval relevance reranking.
        """
        self._retriever = retriever
        self._indexer = indexer
        self._reranker = reranker

    async def search(self, query: SearchQuery) -> SearchResult:
        """Execute vector search retrieval and optional reranking for a SearchQuery payload.

        Args:
            query: SearchQuery payload model.

        Returns:
            SearchResult: Complete search response model containing retrieved and reranked chunks.

        Raises:
            RAGError: If retrieval or reranking execution fails.
        """
        try:
            result = await self._retriever.retrieve(query)

            if self._reranker and result.retrieved_chunks:
                reranked_chunks = await self._reranker.rerank(
                    query=query,
                    chunks=result.retrieved_chunks,
                )
                result = result.model_copy(
                    update={"retrieved_chunks": reranked_chunks}
                )

            return result
        except RAGError:
            raise
        except Exception as exc:
            raise RAGError("RAG search operation failed.") from exc

    async def index_document(
        self,
        document: KnowledgeDocument,
    ) -> tuple[DocumentChunk, ...]:
        """Delegate document chunking, embedding generation, and vector indexing to BaseDocumentIndexer.

        Args:
            document: KnowledgeDocument entity to index.

        Returns:
            tuple[DocumentChunk, ...]: Immutable tuple of indexed DocumentChunk models.

        Raises:
            RAGError: If document validation or indexing execution fails.
        """
        self._validate_document(document)

        try:
            return await self._indexer.index(document)
        except RAGError:
            raise
        except Exception as exc:
            raise RAGError("Document indexing operation failed.") from exc

    async def delete_document(self, document_id: UUID) -> None:
        """Delegate document and associated chunk deletion to BaseDocumentIndexer.

        Args:
            document_id: Unique document identifier UUID.

        Raises:
            RAGError: If document_id is invalid or deletion execution fails.
        """
        self._validate_document_id(document_id)

        try:
            await self._indexer.delete_document(document_id)
        except RAGError:
            raise
        except Exception as exc:
            raise RAGError("Document deletion operation failed.") from exc

    async def health_check(self) -> dict[str, bool]:
        """Aggregate operational health booleans across all RAG sub-components.

        Returns:
            dict[str, bool]: Mapping of sub-component names ('retriever', 'document_indexer', 'reranker') to status booleans.
        """
        health_status: dict[str, bool] = {}

        try:
            health_status["retriever"] = await self._retriever.health_check()
        except Exception:
            health_status["retriever"] = False

        try:
            health_status["document_indexer"] = await self._indexer.health_check()
        except Exception:
            health_status["document_indexer"] = False

        if self._reranker:
            try:
                health_status["reranker"] = await self._reranker.health_check()
            except Exception:
                health_status["reranker"] = False

        return health_status

    # ------------------------------------------------------------------
    # Private Validation Helpers
    # ------------------------------------------------------------------

    def _validate_document(self, document: KnowledgeDocument) -> None:
        """Validate input KnowledgeDocument model integrity.

        Args:
            document: KnowledgeDocument instance.

        Raises:
            RAGError: If document is None, missing title, or missing content.
        """
        if not document or not isinstance(document, KnowledgeDocument):
            raise RAGError("KnowledgeDocument cannot be None.")

        if not document.title or not document.title.strip():
            raise RAGError("KnowledgeDocument title cannot be empty or blank.")

        if not document.content or not document.content.strip():
            raise RAGError("KnowledgeDocument content cannot be empty or blank.")

    def _validate_document_id(self, document_id: UUID) -> None:
        """Validate input document identifier UUID.

        Args:
            document_id: Unique document identifier UUID.

        Raises:
            RAGError: If document_id is None or not a UUID instance.
        """
        if not document_id or not isinstance(document_id, UUID):
            raise RAGError("document_id must be a valid UUID instance.")
