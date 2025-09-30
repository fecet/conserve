"""Utilities for file operations supporting both local and remote sources."""

from __future__ import annotations
import os
import tempfile
from pathlib import Path

from platformdirs import user_cache_dir
from upath import UPath


def to_valid_filename(name: str) -> str:
    """Convert a string to a valid filename, similar to original implementation."""
    import unicodedata
    import re

    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    # Remove special characters
    name = re.sub(r"[^\w\s-]", "", name).strip()
    # Replace spaces and hyphens with underscore
    name = re.sub(r"[-\s]+", "_", name)
    return name.lower()


class File:
    """File wrapper supporting local, remote, and cached operations using fsspec."""

    # Global cache directory - can be overridden via environment variable
    CACHE_DIR = Path(os.environ.get("CONSERVE_CACHE_DIR", user_cache_dir("conserve", "conserve")))

    def __init__(self, path: str | Path | UPath | None = None):
        """Initialize File with optional path.

        Args:
            path: File path (local/remote) or None to create temporary file
        """

        if path is None:
            # Create temporary file for compatibility
            fd, tmp_path = tempfile.mkstemp()
            os.close(fd)
            self.path = UPath(tmp_path)
        elif isinstance(path, (str, Path, UPath)):
            self.path = UPath(path) if not isinstance(path, UPath) else path
        else:
            raise TypeError(f"File expects a path or URL, got {type(path).__name__}")

    @property
    def is_remote(self) -> bool:
        """Check if the file is remote (non-local)."""
        protocol = getattr(self.path, "protocol", None) or "file"
        return protocol not in ("", "file")

    def cache(self, ttl: int = 0) -> File:
        # Local files return themselves
        if not self.is_remote:
            return self

        cached_url = f"filecache::{self.path}"
        cached_path = UPath(cached_url, cache_storage=str(self.CACHE_DIR), expiry_time=ttl)

        return File(cached_path)

    # Delegate to self.path
    def __getattr__(self, name):
        """Delegate undefined attributes/methods to self.path (UPath)."""
        return getattr(self.path, name)

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"File({self.path!r})"
