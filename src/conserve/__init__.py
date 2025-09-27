"""Conserve - Configuration fragment synchronizer with format preservation."""

from .core import (
    toml,
    yaml,
    json,
    auto,
    merge_deep,
)

__all__ = [
    "toml",
    "yaml",
    "json",
    "auto",
    "merge_deep",
]

__version__ = "0.1.0"
