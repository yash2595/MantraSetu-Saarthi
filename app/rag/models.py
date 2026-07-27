"""Domain models and schemas for the RAG (Retrieval-Augmented Generation) subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 models, enums, knowledge documents, chunks,
embeddings, search queries, retrieved chunks, and search result schemas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseRAGModel(BaseModel):
    """Base Pydantic v2 model for immutable RAG domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ChunkSource(str, Enum):
    """Enumeration of origin sources for document chunks."""

    TEXT = "text"
    DOCUMENT = "document"
    URL = "url"
    DATABASE = "database"
    USER = "user"
    SYSTEM = "system"


class RetrievalStatus(str, Enum):
    """Enumeration of vector search retrieval outcomes."""

    SUCCESS = "success"
    EMPTY = "empty"
    PARTIAL = "partial"
    FAILED = "failed"


class SearchMetadata(BaseRAGModel):
    """Domain model capturing search configuration metadata and filtering parameters.

    Attributes:
        source: Optional search caller identifier string.
        filters: Metadata filter dictionary for query narrowing.
        custom: Custom metadata key-value pairs.
    """

    source: str | None = Field(
        default=None,
        description="Search caller identifier string.",
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata filter dictionary.",
    )
    custom: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata dictionary.",
    )


class EmbeddingVector(BaseRAGModel):
    """Domain model representing a numerical vector embedding.

    Attributes:
        vector_id: Unique vector identifier UUID.
        values: Immutable tuple of floating-point vector dimensions.
        dimension: Length of the vector values tuple.
        model: Name of the embedding model that generated this vector.
    """

    vector_id: UUID = Field(
        default_factory=uuid4,
        description="Unique vector identifier UUID.",
    )
    values: tuple[float, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of floating-point vector values.",
    )
    dimension: int = Field(
        default=0,
        ge=0,
        description="Length of vector values tuple.",
    )
    model: str = Field(
        default="",
        description="Name of the embedding model that generated this vector.",
    )


class DocumentChunk(BaseRAGModel):
    """Domain model representing a chunked fragment of a KnowledgeDocument.

    Attributes:
        chunk_id: Unique chunk identifier UUID.
        document_id: Parent document identifier UUID.
        content: Text content string of this chunk.
        chunk_index: Chronological position index within parent document.
        source: ChunkSource enum category.
        embedding: Optional EmbeddingVector instance for this chunk.
        metadata: Key-value metadata dictionary.
        created_at: UTC creation timestamp.
    """

    chunk_id: UUID = Field(
        default_factory=uuid4,
        description="Unique chunk identifier UUID.",
    )
    document_id: UUID = Field(
        ...,
        description="Parent document identifier UUID.",
    )
    content: str = Field(
        ...,
        description="Text content string of this chunk.",
    )
    chunk_index: int = Field(
        default=0,
        ge=0,
        description="Position index within parent document.",
    )
    source: ChunkSource = Field(
        default=ChunkSource.TEXT,
        description="ChunkSource enum category.",
    )
    embedding: EmbeddingVector | None = Field(
        default=None,
        description="Optional EmbeddingVector instance.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class KnowledgeDocument(BaseRAGModel):
    """Domain model representing an entire ingested knowledge document entity.

    Attributes:
        document_id: Unique document identifier UUID.
        title: Document title string.
        content: Full raw text content of the document.
        uri: Optional source URI location.
        chunks: Immutable tuple of DocumentChunk fragments.
        metadata: Key-value metadata dictionary.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    document_id: UUID = Field(
        default_factory=uuid4,
        description="Unique document identifier UUID.",
    )
    title: str = Field(
        ...,
        description="Document title string.",
    )
    content: str = Field(
        ...,
        description="Full raw text content of the document.",
    )
    uri: str | None = Field(
        default=None,
        description="Optional source URI location.",
    )
    chunks: tuple[DocumentChunk, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of DocumentChunk fragments.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )


class SearchQuery(BaseRAGModel):
    """Domain model representing a vector or hybrid retrieval query request.

    Attributes:
        query_id: Unique query identifier UUID.
        text: Query text string.
        top_k: Number of top results to retrieve.
        min_score: Minimum similarity score threshold (0.0 to 1.0).
        embedding: Optional pre-computed query EmbeddingVector.
        metadata: SearchMetadata instance.
        created_at: UTC creation timestamp.
    """

    query_id: UUID = Field(
        default_factory=uuid4,
        description="Unique query identifier UUID.",
    )
    text: str = Field(
        ...,
        description="Query text string.",
    )
    top_k: int = Field(
        default=5,
        gt=0,
        description="Number of top results to retrieve.",
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold.",
    )
    embedding: EmbeddingVector | None = Field(
        default=None,
        description="Optional pre-computed query EmbeddingVector.",
    )
    metadata: SearchMetadata = Field(
        default_factory=SearchMetadata,
        description="SearchMetadata instance.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class RetrievedChunk(BaseRAGModel):
    """Domain model representing a single retrieved document chunk with similarity score.

    Attributes:
        chunk: DocumentChunk model instance.
        score: Cosine/vector similarity score.
        relevance_explanation: Optional diagnostic relevance explanation string.
    """

    chunk: DocumentChunk = Field(
        ...,
        description="DocumentChunk model instance.",
    )
    score: float = Field(
        default=0.0,
        description="Cosine/vector similarity score.",
    )
    relevance_explanation: str | None = Field(
        default=None,
        description="Optional diagnostic relevance explanation string.",
    )


class SearchResult(BaseRAGModel):
    """Domain model representing the complete vector search response payload.

    Attributes:
        result_id: Unique search result identifier UUID.
        query_id: Associated query identifier UUID.
        status: RetrievalStatus enum outcome.
        retrieved_chunks: Immutable tuple of RetrievedChunk instances.
        latency_ms: Search execution latency in milliseconds.
        metadata: SearchMetadata instance.
        created_at: UTC creation timestamp.
    """

    result_id: UUID = Field(
        default_factory=uuid4,
        description="Unique search result identifier UUID.",
    )
    query_id: UUID = Field(
        ...,
        description="Associated query identifier UUID.",
    )
    status: RetrievalStatus = Field(
        default=RetrievalStatus.SUCCESS,
        description="RetrievalStatus enum outcome.",
    )
    retrieved_chunks: tuple[RetrievedChunk, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of RetrievedChunk instances.",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Search execution latency in milliseconds.",
    )
    metadata: SearchMetadata = Field(
        default_factory=SearchMetadata,
        description="SearchMetadata instance.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
