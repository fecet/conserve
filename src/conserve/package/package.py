"""Package metadata query module based on PURL standard."""

from __future__ import annotations

from typing import Self

from packageurl import PackageURL

from .provider import PackageProvider, get_provider
from .types import PackageVersionInfo


def _normalize_input(s: str) -> str:
    """Normalize user input into full PURL string.

    Accepts three shorthands:
    - pkg:type/name[@v]
    - type/name[@v]
    - type:name[@v]
    """
    # Keep as-is if already a full PURL
    if s.startswith("pkg:"):
        return s

    # Allow colon shorthand: type:name -> type/name (only first ':')
    if ":" in s:
        s = s.replace(":", "/", 1)

    # Ensure full PURL prefix
    return f"pkg:{s}"


class Package:
    """Package object encapsulating PURL query interface."""

    def __init__(self, purl: str):
        """Initialize Package from string in short or full PURL forms."""
        try:
            self._purl = PackageURL.from_string(_normalize_input(purl))
        except ValueError as e:
            raise ValueError(f"Invalid PURL format: {purl}") from e

        self._provider: PackageProvider | None = None

    @property
    def version(self) -> str | None:
        """Get version from PURL (None if not specified in PURL)."""
        return self._purl.version

    @property
    def type(self) -> str:
        """Get package system type (e.g., 'pypi', 'conda', 'github')."""
        return self._purl.type

    def _ensure_provider(self) -> PackageProvider:
        """Ensure provider is initialized and package type is supported.

        Returns:
            Provider instance

        Raises:
            ValueError: If package type is not supported
            NotImplementedError: If provider is not yet implemented
        """
        if self._provider is None:
            self._provider = get_provider(self._purl.type)

        return self._provider

    def _get_full_name(self) -> str:
        """Get full package name including namespace if applicable.

        Returns:
            Full package name (e.g., 'owner/repo' for GitHub)
        """
        if self._purl.type == "github" and self._purl.namespace:
            return f"{self._purl.namespace}/{self._purl.name}"
        return self._purl.name

    def latest(self) -> Self:
        """Get Package object for latest version.

        Returns:
            New Package object with latest version from registry

        Raises:
            ValueError: If package not found or no versions available
        """
        provider = self._ensure_provider()
        latest_version = provider.get_latest_version(self._get_full_name())

        # Build new PURL with latest version
        new_purl = self._purl.to_string().replace(f"@{self.version}", "") if self.version else self._purl.to_string()
        if "@" not in new_purl:
            new_purl = f"{new_purl}@{latest_version}"

        return Package(new_purl)

    def info(self) -> PackageVersionInfo:
        """Get package version metadata.

        Returns:
            PackageVersionInfo containing version metadata.

            Always returns detailed version information:
            - If version specified: returns that version's metadata
            - If no version: automatically fetches latest version's metadata

            Core fields (all providers):
                version: Version string
                published_at: Publication timestamp

            DepsDevProvider additional fields:
                licenses: SPDX license identifiers
                links: Documentation and repository links
                is_default: Whether this is the default version
                registries: Package registry URLs

            GitHubProvider additional fields:
                tag_name: Git tag name
                name: Release name
                body: Release notes
                prerelease: Whether this is a pre-release
                assets: Downloadable assets

        Raises:
            ValueError: If package or version not found
        """
        provider = self._ensure_provider()
        full_name = self._get_full_name()

        if self.version:
            return provider.get_version_info(full_name, self.version)
        else:
            # Auto-fetch latest version's detailed info
            latest_version = provider.get_latest_version(full_name)
            return provider.get_version_info(full_name, latest_version)

    def to_pypi(self) -> Self:
        """Convert Conda package to a new PyPI Package.

        Raises:
            ValueError: If not a conda package or mapping not found.
        """
        if self._purl.type != "conda":
            raise ValueError(f"to_pypi() only available for conda packages, got: {self._purl.type}")

        from .conda import conda_to_pypi

        mapped = conda_to_pypi(self._purl.name)
        if not mapped:
            raise ValueError(f"No PyPI mapping for conda package: {self._purl.name}")
        return Package(f"pypi:{mapped}")

    def to_conda(self) -> Self:
        """Convert PyPI package to a new Conda Package.

        Raises:
            ValueError: If not a pypi package or mapping not found.
        """
        if self._purl.type != "pypi":
            raise ValueError(f"to_conda() only available for pypi packages, got: {self._purl.type}")

        from .conda import pypi_to_conda

        mapped = pypi_to_conda(self._purl.name)
        if not mapped:
            raise ValueError(f"No Conda mapping for PyPI package: {self._purl.name}")
        return Package(f"conda:{mapped}")
