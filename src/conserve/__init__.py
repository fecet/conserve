"""Conserve - Configuration fragment synchronizer with format preservation."""

from .core import (
    TOMLHandle,
    YAMLHandle,
    JSONHandle,
    AutoHandle,
    BaseHandle,
    merge_deep,
)

__all__ = [
    "TOMLHandle",
    "YAMLHandle",
    "JSONHandle",
    "AutoHandle",
    "BaseHandle",
    "merge_deep",
]

__version__ = "0.1.0"
