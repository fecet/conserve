"""Type definitions for package metadata."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class DepsDevLink(TypedDict):
    """Link metadata from deps.dev."""

    label: str
    url: str


class GitHubAsset(TypedDict):
    """GitHub release asset metadata."""

    name: str
    download_url: str


class PackageVersionInfo(TypedDict):
    """Unified package version information across all providers.

    Core fields (present in all providers):
        version: Version string
        published_at: Publication timestamp (ISO format) or None

    DepsDevProvider fields:
        licenses: SPDX license identifiers
        links: Documentation and repository links
        is_default: Whether this is the default/latest version
        registries: Package registry URLs

    GitHubProvider fields:
        tag_name: Git tag name
        name: Release name
        body: Release notes/description
        prerelease: Whether this is a pre-release
        assets: Downloadable release assets
    """

    # Core fields (all providers)
    version: str
    published_at: str | None

    # DepsDevProvider fields
    licenses: NotRequired[list[str]]
    links: NotRequired[list[DepsDevLink]]
    is_default: NotRequired[bool]
    registries: NotRequired[list[str]]

    # GitHubProvider fields
    tag_name: NotRequired[str]
    name: NotRequired[str]
    body: NotRequired[str]
    prerelease: NotRequired[bool]
    assets: NotRequired[list[GitHubAsset]]
