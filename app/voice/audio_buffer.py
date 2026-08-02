"""Thread-safe streaming AudioBuffer for ingesting audio bytes."""

from __future__ import annotations

import io


class AudioBuffer:
    """In-memory streaming audio chunk buffer."""

    def __init__(self) -> None:
        self._buffer = io.BytesIO()

    def append(self, chunk: bytes) -> None:
        """Append raw binary audio chunk to buffer."""
        if not chunk:
            return
        self._buffer.write(chunk)

    def flush(self) -> bytes:
        """Read all accumulated bytes from buffer without clearing."""
        return self._buffer.getvalue()

    def clear(self) -> None:
        """Reset the buffer."""
        self._buffer = io.BytesIO()

    @property
    def size(self) -> int:
        """Return total accumulated buffer size in bytes."""
        return self._buffer.getbuffer().nbytes
