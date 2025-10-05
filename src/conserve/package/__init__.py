"""Package metadata query module."""

from .package import Package as Package
from .types import PackageVersionInfo as PackageVersionInfo

__all__ = ["Package", "PackageVersionInfo"]
