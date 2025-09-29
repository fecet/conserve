"""Utilities for file operations supporting both local and remote sources."""

import os
import re
import tempfile
import unicodedata
from pathlib import Path

from upath import UPath


def to_valid_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name).strip()
    name = re.sub(r"[-\s]+", "_", name)
    return name.lower()


class File:
    def __init__(self, path: str | Path | UPath | None = None):
        self._temp_file: Path | None = None

        if path is None:
            fd, tmp_path = tempfile.mkstemp()
            os.close(fd)
            self.path = UPath(tmp_path)
            self._temp_file = Path(tmp_path)
        elif isinstance(path, (str, Path, UPath)):
            self.path = UPath(path) if not isinstance(path, UPath) else path
        else:
            raise TypeError(f"File expects a path or URL, got {type(path).__name__}")

    def to_tmpfile(self, suffix: str | None = None) -> Path:
        if self._temp_file:
            return self._temp_file

        # Check if it's a local file
        if not hasattr(self.path, "protocol") or not self.path.protocol or self.path.protocol == "file":
            return Path(str(self.path))

        # Remote file - download to temporary file
        content = self.path.read_text()
        suffix = suffix or getattr(self.path, "suffix", "")
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, text=True)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return Path(tmp_path)

    def cleanup(self):
        """Clean up any automatically created temporary files."""
        if self._temp_file and self._temp_file.exists():
            self._temp_file.unlink(missing_ok=True)
            self._temp_file = None

    def __getattr__(self, name):
        """Delegate all undefined attributes/methods to self.path (UPath)."""
        return getattr(self.path, name)

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"File({self.path!r})"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
