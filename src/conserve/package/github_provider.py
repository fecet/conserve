"""GitHub implementation of PackageProvider."""

from __future__ import annotations

from githubkit import GitHub
from githubkit.exception import RequestFailed


class GitHubClient:
    """Client for GitHub API (singleton)."""

    _instance: GitHubClient | None = None
    _github: GitHub | None = None

    def __new__(cls) -> GitHubClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._github = GitHub()
        return cls._instance

    def get_latest_release(self, owner: str, repo: str) -> dict | None:
        """Get latest release information.

        Returns:
            Release object or None if not found
        """
        try:
            response = self._github.rest.repos.get_latest_release(owner=owner, repo=repo)
            return response.parsed_data.model_dump()
        except RequestFailed:
            return None

    def list_releases(self, owner: str, repo: str) -> list[dict] | None:
        """List all releases.

        Returns:
            List of release objects or None on error
        """
        try:
            response = self._github.rest.repos.list_releases(owner=owner, repo=repo, per_page=100)
            return [r.model_dump() for r in response.parsed_data]
        except RequestFailed:
            return None

    def get_release_by_tag(self, owner: str, repo: str, tag: str) -> dict | None:
        """Get release by tag name.

        Returns:
            Release object or None if not found
        """
        try:
            response = self._github.rest.repos.get_release_by_tag(owner=owner, repo=repo, tag=tag)
            return response.parsed_data.model_dump()
        except RequestFailed:
            return None

    def get_repository(self, owner: str, repo: str) -> dict | None:
        """Get repository information.

        Returns:
            Repository object or None if not found
        """
        try:
            response = self._github.rest.repos.get(owner=owner, repo=repo)
            return response.parsed_data.model_dump()
        except RequestFailed:
            return None


class GitHubProvider:
    """Provider for package metadata from GitHub releases."""

    def __init__(self):
        """Initialize GitHub provider."""
        self._client = GitHubClient()

    def get_latest_version(self, name: str) -> str | None:
        """Get latest release version from GitHub.

        Args:
            name: Repository name in 'owner/repo' format

        Returns:
            Latest release tag name

        Raises:
            ValueError: If repository not found or no releases available
        """
        owner, repo = self._parse_name(name)
        release = self._client.get_latest_release(owner, repo)

        if not release:
            raise ValueError(f"No releases found for: {name}")

        return release.get("tag_name")

    def get_package_info(self, name: str) -> dict | None:
        """Get repository metadata without specific version.

        Args:
            name: Repository name in 'owner/repo' format

        Returns:
            Dictionary with repository metadata (name, description, releases)
        """
        owner, repo = self._parse_name(name)
        repo_info = self._client.get_repository(owner, repo)

        if not repo_info:
            return None

        releases = self._client.list_releases(owner, repo) or []

        return {
            "name": name,
            "description": repo_info.get("description"),
            "url": repo_info.get("html_url"),
            "stars": repo_info.get("stargazers_count"),
            "releases": [r.get("tag_name") for r in releases],
        }

    def get_version_info(self, name: str, version: str) -> dict | None:
        """Get specific release metadata.

        Args:
            name: Repository name in 'owner/repo' format
            version: Release tag name

        Returns:
            Dictionary with release metadata
        """
        owner, repo = self._parse_name(name)
        release = self._client.get_release_by_tag(owner, repo, version)

        if not release:
            return None

        return {
            "tag_name": release.get("tag_name"),
            "name": release.get("name"),
            "body": release.get("body"),
            "published_at": release.get("published_at"),
            "prerelease": release.get("prerelease"),
            "assets": [
                {"name": asset.get("name"), "download_url": asset.get("browser_download_url")}
                for asset in release.get("assets", [])
            ],
        }

    def _parse_name(self, name: str) -> tuple[str, str]:
        """Parse 'owner/repo' format.

        Args:
            name: Repository name in 'owner/repo' format

        Returns:
            Tuple of (owner, repo)

        Raises:
            ValueError: If name format is invalid
        """
        parts = name.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid GitHub repository name: {name} (expected 'owner/repo')")
        return parts[0], parts[1]
