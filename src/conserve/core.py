"""Core API for Conserve."""

import json as json_lib
from io import StringIO
from pathlib import Path

import tomlkit
from deepmerge import Merger
from ruamel.yaml import YAML

# Import special types for format-preserving merge
from ruamel.yaml.comments import CommentedMap
from tomlkit.items import Table as TOMLTable
from tomlkit.toml_document import TOMLDocument

from .utils import File


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


class BaseHandle:
    """Base class for structured document handles supporting both local and remote files."""

    def __init__(self, path: str | Path | File):
        # Accept File instance or path
        self.file = path if isinstance(path, File) else File(path)
        self.document = {}
        self._loaded = False

    def _parse(self, content: str):
        """Parse content into document. Format-specific implementation."""
        raise NotImplementedError

    def _dump(self) -> str:
        """Dump document to string. Format-specific implementation."""
        raise NotImplementedError

    def _ensure_loaded(self):
        """Ensure document is loaded."""
        if not self._loaded:
            self.load()

    def load(self) -> "BaseHandle":
        """Load content from disk or remote location and return self for chaining."""
        if self.file.exists():
            content = self.file.read_text(encoding="utf-8")
            self._parse(content)
        else:
            self.document = {}
        self._loaded = True
        return self

    def read(self) -> dict:
        """Return current in-memory document."""
        self._ensure_loaded()
        return self.document.unwrap() if hasattr(self.document, "unwrap") else dict(self.document)

    def replace(self, doc: dict) -> "BaseHandle":
        """Replace in-memory content with new document and return self."""
        self._ensure_loaded()
        self._replace_impl(doc)
        return self

    def _replace_impl(self, doc: dict):
        """Default replace implementation. Can be overridden."""
        self.document = doc

    def merge(self, patch: dict) -> "BaseHandle":
        """Merge patch into in-memory document and return self."""
        self._ensure_loaded()
        self.document = conserve_merger.merge(self.document, patch)
        return self

    def save(self, path: str | Path | None = None) -> None:
        """Save in-memory content to file or remote location (default: original path)."""
        self._ensure_loaded()
        target_file = File(path) if path else self.file

        # Create parent directories for local files
        if hasattr(target_file.path, "parent") and hasattr(target_file.path.parent, "mkdir"):
            target_file.path.parent.mkdir(parents=True, exist_ok=True)

        target_file.write_text(self._dump(), encoding="utf-8")


class TOMLHandle(BaseHandle):
    """Handle for TOML documents with format preservation."""

    def _parse(self, content: str):
        self.document = tomlkit.parse(content)

    def _dump(self) -> str:
        return tomlkit.dumps(self.document)

    def _replace_impl(self, doc: dict):
        self.document.clear()
        self.document.update(doc)


class YAMLHandle(BaseHandle):
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


class JSONHandle(BaseHandle):
    """Handle for JSON documents."""

    def _parse(self, content: str):
        self.document = json_lib.loads(content) if content.strip() else {}

    def _dump(self) -> str:
        return json_lib.dumps(self.document, indent=2, ensure_ascii=False) + "\n"


def AutoHandle(path: str | Path) -> BaseHandle:
    """Auto-detecting factory that creates appropriate format handler.

    Supports both local and remote files.
    Currently uses file extension detection.
    Can be upgraded to use libmagic or other detection methods in the future.
    """
    # Format mapping table (easily extensible)
    HANDLERS = {
        ".toml": TOMLHandle,
        ".yaml": YAMLHandle,
        ".yml": YAMLHandle,
        ".json": JSONHandle,
    }

    # Use File to handle both local and remote paths
    file = File(path)
    suffix = file.path.suffix.lower()
    handler_class = HANDLERS.get(suffix)

    if not handler_class:
        raise ValueError(f"Cannot detect format from extension '{suffix}' for file: {path}")

    return handler_class(path)


# Export public API
__all__ = [
    "TOMLHandle",
    "YAMLHandle",
    "JSONHandle",
    "AutoHandle",
    "BaseHandle",
    "merge_deep",
]
