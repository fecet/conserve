"""deps.dev implementation of PackageProvider."""

from __future__ import annotations

import grpc

from conserve._generated.deps_dev.v3 import (
    GetPackageRequest,
    GetProjectPackageVersionsRequest,
    GetProjectRequest,
    GetVersionRequest,
    InsightsStub,
    Package,
    PackageKey,
    Project,
    ProjectKey,
    ProjectPackageVersions,
    System,
    Version,
    VersionKey,
)


class DepsDevClient:
    """Client for deps.dev gRPC API (singleton)."""

    _instance: DepsDevClient | None = None
    _channel: grpc.Channel | None = None
    _stub: InsightsStub | None = None

    def __new__(cls) -> DepsDevClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize channel and stub (executed only once)
            credentials = grpc.ssl_channel_credentials()
            cls._channel = grpc.secure_channel("api.deps.dev:443", credentials)
            cls._stub = InsightsStub(cls._channel)
        return cls._instance

    @staticmethod
    def purl_type_to_system(purl_type: str) -> System | None:
        """Convert PURL type to deps.dev System enum."""
        mapping = {
            "pypi": System.PYPI,
            "npm": System.NPM,
            "maven": System.MAVEN,
            "cargo": System.CARGO,
            "golang": System.GO,
            "rubygems": System.RUBYGEMS,
            "nuget": System.NUGET,
        }
        return mapping.get(purl_type.lower())

    def get_package(self, system: System, name: str) -> Package | None:
        """Get package information including available versions.

        Returns:
            Package object or None if not found or on error
        """
        try:
            request = GetPackageRequest(package_key=PackageKey(system=system, name=name))
            return self._stub.get_package(request)
        except grpc.RpcError:
            return None

    def get_version(self, system: System, name: str, version: str) -> Version | None:
        """Get specific version information.

        Returns:
            Version object or None if not found or on error
        """
        try:
            request = GetVersionRequest(version_key=VersionKey(system=system, name=name, version=version))
            return self._stub.get_version(request)
        except grpc.RpcError:
            return None

    def get_project(self, project_id: str) -> Project | None:
        """Get project information (for GitHub/GitLab/Bitbucket).

        Args:
            project_id: Project identifier like 'github.com/user/repo'

        Returns:
            Project object or None if not found or on error
        """
        try:
            request = GetProjectRequest(project_key=ProjectKey(id=project_id))
            return self._stub.get_project(request)
        except grpc.RpcError:
            return None

    def get_project_package_versions(self, project_id: str) -> ProjectPackageVersions | None:
        """Get package versions associated with a project.

        Args:
            project_id: Project identifier like 'github.com/user/repo'

        Returns:
            ProjectPackageVersions object or None if not found or on error
        """
        try:
            request = GetProjectPackageVersionsRequest(project_key=ProjectKey(id=project_id))
            return self._stub.get_project_package_versions(request)
        except grpc.RpcError:
            return None

    def close(self):
        """Close the gRPC channel."""
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None


class DepsDevProvider:
    """Provider for package metadata from deps.dev API."""

    def __init__(self, purl_type: str):
        """Initialize deps.dev provider.

        Args:
            purl_type: PURL type (e.g. 'pypi', 'npm')

        Raises:
            ValueError: If package type is not supported by deps.dev
        """
        self._client = DepsDevClient()
        self._system = self._client.purl_type_to_system(purl_type)

        if self._system is None:
            raise ValueError(f"Unsupported package type: {purl_type}")

    def get_latest_version(self, name: str) -> str | None:
        """Get latest version from deps.dev registry.

        Args:
            name: Package name

        Returns:
            Latest version string

        Raises:
            ValueError: If package not found or no versions available
        """
        package_info = self._client.get_package(self._system, name)
        if not package_info:
            raise ValueError(f"Package not found: {name}")

        # Find default version
        for version in package_info.versions:
            if version.is_default and version.version_key:
                return version.version_key.version

        # Fallback to first version if no default
        if package_info.versions and package_info.versions[0].version_key:
            return package_info.versions[0].version_key.version

        raise ValueError(f"No versions available for: {name}")

    def get_package_info(self, name: str) -> dict | None:
        """Get package metadata without specific version.

        Args:
            name: Package name

        Returns:
            Dictionary with package metadata (name, type, versions)
        """
        package_info = self._client.get_package(self._system, name)
        if not package_info:
            return None

        return {
            "name": name,
            "versions": [v.version_key.version for v in package_info.versions if v.version_key],
        }

    def get_version_info(self, name: str, version: str) -> dict | None:
        """Get specific version metadata.

        Args:
            name: Package name
            version: Version string

        Returns:
            Dictionary with version metadata
        """
        version_info = self._client.get_version(self._system, name, version)
        if not version_info:
            return None

        return {
            "version": version,
            "is_default": version_info.is_default,
            "licenses": list(version_info.licenses),
            "published_at": version_info.published_at.isoformat() if version_info.published_at else None,
            "links": [{"label": link.label, "url": link.url} for link in version_info.links],
            "registries": list(version_info.registries),
        }
