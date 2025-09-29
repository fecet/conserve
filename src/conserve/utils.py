"""Utilities for file operations supporting both local and remote sources."""

from upath import UPath
from pathlib import Path
import tempfile
from typing import Optional
import os


class File:
    def __init__(self, path: Optional[str | Path | UPath] = None):
        self._temp_file: Optional[Path] = None

        if path is None:
            # Create temporary file when no path provided
            fd, tmp_path = tempfile.mkstemp()
            os.close(fd)  # Close the file descriptor
            self.path = UPath(tmp_path)
            self._temp_file = Path(tmp_path)
        elif isinstance(path, UPath):
            self.path = path
        elif isinstance(path, (str, Path)):
            # Treat as path/URL
            self.path = UPath(path)
        else:
            raise TypeError(f"File expects a path or URL, got {type(path).__name__}")

    def to_tmpfile(self, suffix: Optional[str] = None) -> Path:
        # If already created as temp file, return it
        if self._temp_file:
            return self._temp_file

        # Check if it's a local file
        if not hasattr(self.path, "protocol") or self.path.protocol == "file" or not self.path.protocol:
            # Local file - return as Path
            return Path(str(self.path))

        # Remote file - download to temporary file
        content = self.path.read_text()
        suffix = suffix or self.path.suffix if hasattr(self.path, "suffix") else ""
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, text=True)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)

        return Path(tmp_path)

    def cleanup(self):
        """Clean up any automatically created temporary files."""
        if self._temp_file and self._temp_file.exists():
            try:
                self._temp_file.unlink()
            except Exception:
                pass  # Ignore cleanup errors
            self._temp_file = None

    def __getattr__(self, name):
        """Delegate all undefined attributes/methods to self.path (UPath)."""
        return getattr(self.path, name)

    def __str__(self) -> str:
        """String representation."""
        return str(self.path)

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"File({self.path!r})"

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.cleanup()

    def __del__(self):
        """Clean up temporary files on deletion."""
        self.cleanup()
