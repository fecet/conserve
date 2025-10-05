"""File helpers for local/remote paths with simple caching."""

from __future__ import annotations

import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Self

from platformdirs import user_cache_dir
from upath import UPath


def to_valid_filename(name: str) -> str:
    # keep ASCII, drop symbols, collapse spaces/dashes
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^\w\s-]", "", normalized).strip()
    return re.sub(r"[-\s]+", "_", cleaned).lower()


class File:
    """Unified file wrapper over UPath supporting local/remote/cache."""

    # Global cache directory (overridable via ENV)
    CACHE_DIR = Path(user_cache_dir("conserve", "conserve"))

    def __init__(self, path: str | Path | UPath | None = None):
        if path is None:
            # use NamedTemporaryFile to avoid os-level calls
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                self.path = UPath(tmp.name)
        elif isinstance(path, (str, Path, UPath)):
            self.path = path if isinstance(path, UPath) else UPath(path)
        else:
            raise TypeError(f"File expects a path or URL, got {type(path).__name__}")

    @property
    def is_remote(self) -> bool:
        protocol = getattr(self.path, "protocol", None) or "file"
        return protocol not in ("", "file")

    def cache(self, ttl: int = 0) -> Self:
        # fast-path for local files
        if not self.is_remote:
            return self
        cached_url = f"filecache::{self.path}"
        cached_path = UPath(cached_url, cache_storage=str(self.CACHE_DIR), expiry_time=ttl)
        return File(cached_path)

    # Delegate to self.path
    def __getattr__(self, name):
        return getattr(self.path, name)

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"File({self.path!r})"
