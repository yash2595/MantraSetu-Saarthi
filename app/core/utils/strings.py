"""String manipulation utility module.

Provides standard string transformation and normalization functions without external dependencies.
"""

import re

# Pre-compiled regular expression patterns for performance
_SNAKE_CASE_PATTERN1 = re.compile(r"(.)([A-Z][a-z]+)")
_SNAKE_CASE_PATTERN2 = re.compile(r"([a-z0-9])([A-Z])")
_NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-zA-Z0-9]+")


def to_snake_case(s: str) -> str:
    """Convert camelCase, PascalCase, or delimiter-separated text to snake_case.

    Args:
        s: Input text string to convert.

    Returns:
        str: Converted text in snake_case format.
    """
    if not s:
        return ""

    cleaned = _NON_ALPHANUMERIC_PATTERN.sub("_", s.strip())
    sub1 = _SNAKE_CASE_PATTERN1.sub(r"\1_\2", cleaned)
    sub2 = _SNAKE_CASE_PATTERN2.sub(r"\1_\2", sub1)
    result = re.sub(r"_+", "_", sub2).strip("_")
    return result.lower()


def to_camel_case(s: str) -> str:
    """Convert snake_case, kebab-case, or space-separated text to camelCase.

    Args:
        s: Input text string to convert.

    Returns:
        str: Converted text in lower camelCase format.
    """
    if not s:
        return ""

    words = _NON_ALPHANUMERIC_PATTERN.split(s.strip())
    words = [w for w in words if w]

    if not words:
        return ""

    first_word = words[0].lower()
    capitalized_words = [w.capitalize() for w in words[1:]]
    return first_word + "".join(capitalized_words)


def truncate(s: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to max_length, appending suffix if truncated.

    Args:
        s: Target string to truncate.
        max_length: Maximum allowable string length including suffix.
        suffix: Suffix string to append when truncating (default "...").

    Returns:
        str: Truncated string or original string if within limit.

    Raises:
        ValueError: If max_length is less than the length of suffix.
    """
    if max_length < len(suffix):
        raise ValueError(
            f"max_length ({max_length}) must be at least the length of suffix ({len(suffix)})."
        )

    if len(s) <= max_length:
        return s

    cut_index = max_length - len(suffix)
    return s[:cut_index] + suffix


def normalize_whitespace(s: str) -> str:
    """Collapse consecutive whitespace characters into a single space and trim margins.

    Args:
        s: Input string containing whitespace.

    Returns:
        str: Normalized string with single space delimiters and trimmed edges.
    """
    if not s:
        return ""

    return " ".join(s.split())
