"""Conserve - Configuration fragment synchronizer with format preservation."""

from .core import (
    TOMLHandle,
    YAMLHandle,
    JSONHandle,
    AutoHandle,
    BaseHandle,
    merge_deep,
)
from . import truth
from .utils import File

__all__ = [
    "TOMLHandle",
    "YAMLHandle",
    "JSONHandle",
    "AutoHandle",
    "BaseHandle",
    "merge_deep",
    "truth",
    "File",
]

__version__ = "0.1.0"
