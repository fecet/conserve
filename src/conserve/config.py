"""Configuration file handles for structured formats (YAML/JSON/TOML)."""

import json as json_lib
from io import StringIO
from pathlib import Path
from typing import Self

import tomlkit
from deepmerge import Merger
from ruamel.yaml import YAML

# Import special types for format-preserving merge
from ruamel.yaml.comments import CommentedMap
from tomlkit.items import Table as TOMLTable
from tomlkit.toml_document import TOMLDocument

from .core import BaseHandle
from .file import File


def format_preserving_merge(config, path, base, nxt):
    """Merge strategy that preserves formatting for TOML and YAML."""
    for key, value in nxt.items():
        if key not in base:
            base[key] = value
        else:
            # Special handling for TOML lists to preserve multiline format
            if isinstance(base, (TOMLDocument, TOMLTable)) and isinstance(value, list) and len(value) > 2:
                arr = tomlkit.array()
                arr.multiline(True)
                for item in value:
                    arr.append(item)
                base[key] = arr
            else:
                # Recursively merge nested structures
                base[key] = config.value_strategy(path + [key], base[key], value)
    return base


# Configure merger according to spec: dict recursive, list/scalar replace
conserve_merger = Merger(
    [
        # Format-preserving strategies (higher priority)
        (TOMLDocument, format_preserving_merge),
        (TOMLTable, format_preserving_merge),
        (CommentedMap, format_preserving_merge),
        # Standard strategies
        (dict, ["merge"]),  # Dict recursive merge
        (list, ["override"]),  # List replace entirely
    ],
    ["override"],  # Other types (scalars) replace
    ["override"],  # Type conflict: replace
)


def merge_deep(*docs) -> dict:
    """Deep merge multiple documents.

    Strategy:
    - Dicts: recursive merge
    - Lists: replace entirely
    - Scalars: replace
    """
    if not docs:
        return {}

    result = docs[0]
    for doc in docs[1:]:
        result = conserve_merger.merge(result, doc)
    return result


class ConfigHandle(BaseHandle):
    """Base class for structured config file handles supporting both local and remote files."""

    def __init__(self, path: str | Path | File):
        super().__init__(path)
        self.document = {}

    def _parse(self, content: str):
        """Parse content into document. Format-specific implementation."""
        raise NotImplementedError

    def _dump(self) -> str:
        """Dump document to string. Format-specific implementation."""
        raise NotImplementedError

    # load/_ensure_loaded are inherited from BaseHandle

    def read(self) -> dict:
        """Return current in-memory document."""
        self._ensure_loaded()
        return self.document.unwrap() if hasattr(self.document, "unwrap") else dict(self.document)

    def replace(self, doc: dict) -> Self:
        """Replace in-memory content with new document and return self."""
        self._replace_impl(doc)
        self._loaded = True
        return self

    def _replace_impl(self, doc: dict):
        """Default replace implementation. Can be overridden."""
        self.document = doc

    def merge(self, patch: dict, strategy: str = "deep") -> Self:
        """Merge patch into in-memory document and return self (idempotent)."""
        self._ensure_loaded()
        if strategy == "deep":
            self.document = conserve_merger.merge(self.document, patch)
        elif strategy == "shallow":
            # First level merge only
            if isinstance(self.document, dict):
                self.document.update(patch)
            else:
                self.document = patch
        elif strategy == "override":
            self.document = patch
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
        return self

    def _delete_path(self, obj: dict, parts: list[str]) -> None:
        """Delete a single path from object, silently succeed if not found."""
        for part in parts[:-1]:
            if not isinstance(obj, dict) or part not in obj:
                return
            obj = obj[part]

        if isinstance(obj, dict) and parts[-1] in obj:
            del obj[parts[-1]]

    def delete(self, *paths: str) -> Self:
        """Delete specified paths from document (idempotent).

        Supports dot-separated paths like "server.port".
        Silently succeeds if path doesn't exist.
        """
        self._ensure_loaded()
        for path in paths:
            self._delete_path(self.document, path.split("."))
        return self

    def save(self, path: str | Path | None = None, *, stage: bool | None = None) -> None:
        """Save content to file or Plan (delegates to BaseHandle)."""
        super().save(path, stage=stage)

    def _get_serialized_content(self) -> str:
        """Return serialized content."""
        return self._dump()


class TOMLHandle(ConfigHandle):
    """Handle for TOML documents with format preservation."""

    def _parse(self, content: str):
        self.document = tomlkit.parse(content)

    def _dump(self) -> str:
        return tomlkit.dumps(self.document)

    def _replace_impl(self, doc: dict):
        self.document.clear()
        self.document.update(doc)


class YAMLHandle(ConfigHandle):
    """Handle for YAML documents with format preservation."""

    def __init__(self, path: str | Path | File):
        super().__init__(path)
        # Each instance has its own YAML configuration
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096  # Prevent line wrapping

    def _parse(self, content: str):
        self.document = self.yaml.load(content) or {}

    def _dump(self) -> str:
        stream = StringIO()
        self.yaml.dump(self.document, stream)
        return stream.getvalue()


class JSONHandle(ConfigHandle):
    """Handle for JSON documents."""

    def _parse(self, content: str):
        self.document = json_lib.loads(content) if content.strip() else {}

    def _dump(self) -> str:
        return json_lib.dumps(self.document, indent=2, ensure_ascii=False) + "\n"
