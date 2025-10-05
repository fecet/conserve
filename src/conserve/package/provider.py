"""Abstract provider interface for package metadata queries."""

from __future__ import annotations

from typing import Protocol

from .types import PackageVersionInfo


class PackageProvider(Protocol):
    """Abstract interface for package metadata providers.

    Providers implement package-specific logic for querying metadata
    from different sources (registries, APIs, repositories, etc.).
    """

    def get_latest_version(self, name: str) -> str | None:
        """Get latest version for a package.

        Args:
            name: Package name

        Returns:
            Latest version string, or None if not found

        Raises:
            ValueError: If package not found or no versions available
        """
        ...

    def get_version_info(self, name: str, version: str) -> PackageVersionInfo:
        """Get version metadata.

        Args:
            name: Package name
            version: Version string

        Returns:
            PackageVersionInfo with version metadata

        Raises:
            ValueError: If version not found
        """
        ...


def get_provider(purl_type: str) -> PackageProvider:
    """Get appropriate provider for PURL type.

    Args:
        purl_type: PURL type (e.g. 'pypi', 'npm', 'github')

    Returns:
        Provider instance for the given type

    Raises:
        ValueError: If package type is not supported
        NotImplementedError: If provider is not yet implemented
    """
    if purl_type in ("pypi", "npm", "cargo", "maven", "rubygems", "nuget"):
        from .deps_dev_provider import DepsDevProvider

        return DepsDevProvider(purl_type)
    elif purl_type == "github":
        from .github_provider import GitHubProvider

        return GitHubProvider()
    else:
        raise ValueError(f"Unsupported package type: {purl_type}")
