"""RAG (Retrieval-Augmented Generation) domain subsystem for MantraSetu AgentOS."""

from app.rag.base import (
    BaseChunker,
    BaseDocumentIndexer,
    BaseEmbeddingProvider,
    BaseRAGService,
    BaseReranker,
    BaseRetriever,
    BaseVectorDatabase,
    EmbeddingError,
    HealthCheckError,
    RAGError,
    RerankingError,
    RetrievalError,
    VectorDatabaseError,
)
from app.rag.contracts import BaseEmbeddingClient, BaseVectorDatabaseClient
from app.rag.embeddings import EmbeddingProvider
from app.rag.models import (
    BaseRAGModel,
    ChunkSource,
    DocumentChunk,
    EmbeddingVector,
    KnowledgeDocument,
    RetrievalStatus,
    RetrievedChunk,
    SearchMetadata,
    SearchQuery,
    SearchResult,
)
from app.rag.retriever import Retriever
from app.rag.service import RAGService
from app.rag.vectordb import VectorDatabase

__all__ = [
    "BaseRAGModel",
    "ChunkSource",
    "RetrievalStatus",
    "SearchMetadata",
    "EmbeddingVector",
    "DocumentChunk",
    "KnowledgeDocument",
    "SearchQuery",
    "RetrievedChunk",
    "SearchResult",
    "BaseEmbeddingProvider",
    "BaseVectorDatabase",
    "BaseRetriever",
    "BaseReranker",
    "BaseChunker",
    "BaseDocumentIndexer",
    "BaseRAGService",
    "BaseEmbeddingClient",
    "BaseVectorDatabaseClient",
    "EmbeddingProvider",
    "VectorDatabase",
    "Retriever",
    "RAGService",
    "RAGError",
    "EmbeddingError",
    "VectorDatabaseError",
    "RetrievalError",
    "RerankingError",
    "HealthCheckError",
]
