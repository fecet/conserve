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
        """Query registry for default/stable version."""
        ...

    def get_version_info(self, name: str, version: str) -> PackageVersionInfo: ...


def get_provider(purl_type: str) -> PackageProvider:
    if purl_type in ("pypi", "npm", "cargo", "maven", "rubygems", "nuget"):
        from .deps_dev_provider import DepsDevProvider

        return DepsDevProvider(purl_type)
    elif purl_type == "github":
        from .github_provider import GitHubProvider

        return GitHubProvider()
    else:
        raise ValueError(f"Unsupported package type: {purl_type}")
