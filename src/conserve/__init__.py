"""Conserve - Configuration fragment synchronizer with format preservation."""

from .config import (
    ConfigHandle as ConfigHandle,
    TOMLHandle as TOMLHandle,
    YAMLHandle as YAMLHandle,
    JSONHandle as JSONHandle,
    merge_deep as merge_deep,
)
from .core import BaseHandle as BaseHandle
from .plan import plan as plan
from .text import TextHandle as TextHandle
from .utils import File as File
from .package import Package as Package, PackageVersionInfo as PackageVersionInfo
from . import package as package

__version__ = "0.1.0"
