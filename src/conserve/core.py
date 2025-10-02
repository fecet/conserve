"""Core API for Conserve - BaseHandle only."""

from pathlib import Path

from .utils import File


class BaseHandle:
    """Base class for all Handles with simplified Plan integration."""

    def __init__(self, path: str | Path | File):
        # Accept File instance or path
        self.file = path if isinstance(path, File) else File(path)
        self.path = self.file.path
        self._loaded = False

    def _parse(self, content: str):
        """Parse content into document. Format-specific implementation."""
        raise NotImplementedError

    def _dump(self) -> str:
        """Dump document to string. Format-specific implementation."""
        raise NotImplementedError

    def _get_serialized_content(self) -> str:
        """Return serialized content."""
        return self._dump()
