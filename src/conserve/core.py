"""Core API for Conserve."""

import json as json_lib
from pathlib import Path

import tomlkit
from deepmerge import Merger
from ruamel.yaml import YAML

# Configure merger according to spec: dict recursive, list/scalar replace
conserve_merger = Merger(
    [
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


class StructuredHandle:
    """Handle for structured documents (TOML/YAML/JSON)."""

    def __init__(self, path: str | Path, format: str):
        self.path = Path(path)
        self.format = format
        self.document = {}
        self._loaded = False

    def load(self) -> "StructuredHandle":
        """Load content from disk and return self for chaining."""
        if not self.path.exists():
            self.document = {}
            self._loaded = True
            return self

        content = self.path.read_text(encoding="utf-8")

        if self.format == "toml":
            self.document = tomlkit.parse(content)
        elif self.format == "yaml":
            yaml = YAML()
            yaml.preserve_quotes = True
            self.document = yaml.load(content) or {}
        elif self.format == "json":
            if content.strip():
                self.document = json_lib.loads(content)
            else:
                self.document = {}
        else:
            raise ValueError(f"Unsupported format: {self.format}")

        self._loaded = True
        return self

    def read(self) -> dict:
        """Return current in-memory document."""
        if not self._loaded:
            self.load()
        # Convert to plain dict for user manipulation
        if hasattr(self.document, "unwrap"):  # tomlkit
            return self.document.unwrap()
        return dict(self.document)

    def replace(self, doc: dict) -> "StructuredHandle":
        """Replace in-memory content with new document and return self."""
        if not self._loaded:
            self.load()

        if self.format == "toml":
            # Keep as tomlkit document for format preservation
            self.document = tomlkit.document()
            for key, value in doc.items():
                self.document[key] = value
        else:
            self.document = doc

        return self

    def merge(self, patch: dict) -> "StructuredHandle":
        """Merge patch into in-memory document and return self."""
        if not self._loaded:
            self.load()

        # Get plain dict for merging
        current = self.read()
        merged = merge_deep(current, patch)

        # Replace with merged content
        return self.replace(merged)

    def save(self, path: str | Path | None = None) -> None:
        """Save in-memory content to file (default: original path)."""
        if not self._loaded:
            raise RuntimeError("Cannot save without loading or modifying first")

        target_path = Path(path) if path else self.path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if self.format == "toml":
            content = tomlkit.dumps(self.document)
        elif self.format == "yaml":
            from io import StringIO

            yaml = YAML()
            yaml.preserve_quotes = True
            yaml.width = 4096  # Prevent line wrapping
            stream = StringIO()
            yaml.dump(self.document, stream)
            content = stream.getvalue()
        elif self.format == "json":
            content = json_lib.dumps(self.document, indent=2, ensure_ascii=False) + "\n"
        else:
            raise ValueError(f"Unsupported format: {self.format}")

        target_path.write_text(content, encoding="utf-8")


def toml(path: str | Path) -> StructuredHandle:
    """Create a TOML document handle."""
    return StructuredHandle(path, "toml")


def yaml(path: str | Path) -> StructuredHandle:
    """Create a YAML document handle."""
    return StructuredHandle(path, "yaml")


def json(path: str | Path) -> StructuredHandle:
    """Create a JSON document handle."""
    return StructuredHandle(path, "json")


def auto(path: str | Path) -> StructuredHandle:
    """Create a document handle with auto-detected format."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".toml",):
        return toml(path)
    elif suffix in (".yaml", ".yml"):
        return yaml(path)
    elif suffix in (".json",):
        return json(path)
    else:
        # Try to detect by content
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content.startswith("{") or content.startswith("["):
                return json(path)
            elif content and "=" in content.split("\n")[0]:
                return toml(path)
            else:
                return yaml(path)
        else:
            raise ValueError(f"Cannot auto-detect format for non-existent file: {path}")
