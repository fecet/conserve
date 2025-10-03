"""Text file handling for simple line management."""

from pathlib import Path
from typing import Self

from .core import BaseHandle
from .utils import File


class TextHandle(BaseHandle):
    """Text file line management."""

    def __init__(self, path: str | Path | File):
        super().__init__(path)
        self.lines = []
        self._loaded = False

    def _parse(self, content: str):
        """Parse content into lines."""
        self.lines = content.splitlines(keepends=False) if content else []

    def _dump(self) -> str:
        """Dump lines to string."""
        return "\n".join(self.lines) + ("\n" if self.lines else "")

    # load/_ensure_loaded are inherited from BaseHandle

    def present(self, line: str) -> Self:
        """Ensure line exists in file (idempotent)."""
        self._ensure_loaded()
        if line not in self.lines:
            self.lines.append(line)
        return self

    def absent(self, line: str) -> Self:
        """Ensure line doesn't exist in file (idempotent)."""
        self._ensure_loaded()
        while line in self.lines:
            self.lines.remove(line)
        return self

    def save(self, path: str | Path | None = None, *, stage: bool | None = None) -> None:
        """Save content to file or Plan (delegates to BaseHandle)."""
        super().save(path, stage=stage)
