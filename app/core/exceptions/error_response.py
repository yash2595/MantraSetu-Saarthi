"""Standardized API error response schema models.

Defines Pydantic response models matching the standard API error structure.
"""

from typing import Any, Self

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Model representing detailed error metadata payload."""

    code: str = Field(
        ...,
        description="Machine-readable error code string identifier.",
        examples=["RESOURCE_NOT_FOUND"],
    )
    message: str = Field(
        ...,
        description="Human-readable error description.",
        examples=["The requested resource was not found."],
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional contextual key-value error details.",
    )


class ErrorResponse(BaseModel):
    """Standardized top-level API error response model."""

    success: bool = Field(
        default=False,
        description="Boolean status indicating request outcome.",
    )
    error: ErrorDetail = Field(
        ...,
        description="Container for detailed error info.",
    )

    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> Self:
        """Helper factory method to build a standardized ErrorResponse.

        Args:
            code: Machine-readable error code string.
            message: Human-readable error description message.
            details: Optional dictionary containing extra error metadata details.

        Returns:
            ErrorResponse: Configured error response model instance.
        """
        return cls(
            success=False,
            error=ErrorDetail(
                code=code,
                message=message,
                details=details if details is not None else {},
            ),
        )
