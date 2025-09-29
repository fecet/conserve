"""Common utilities for truth module."""

import json
from pathlib import Path
from typing import Optional, Any
import urllib.request
import urllib.error


class CachedFetcher:
    """Generic URL data fetcher with caching support."""

    def __init__(
        self,
        url: str,
        cache_dir: Optional[Path] = None,
        cache_filename: str = "cached_data.json",
        ttl: Optional[int] = None,
        timeout: int = 30,
    ):
        """Initialize CachedFetcher.

        Args:
            url: URL to fetch data from
            cache_dir: Directory for caching data. Defaults to /tmp/conserve.
            cache_filename: Name of the cache file
            ttl: Cache time-to-live in seconds (not implemented yet)
            timeout: Request timeout in seconds
        """
        self.url = url
        self.cache_dir = Path(cache_dir) if cache_dir else Path("/tmp/conserve")
        self.cache_file = self.cache_dir / cache_filename
        self.ttl = ttl
        self.timeout = timeout
        self._data: Optional[Any] = None

    def fetch(self, force: bool = False) -> Any:
        """Fetch data from URL or cache.

        Args:
            force: Force refresh from URL, ignoring cache

        Returns:
            The fetched data (parsed as JSON)
        """
        # Try loading from cache first
        if not force and self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                self._data = json.load(f)
            return self._data

        # Fetch from URL
        try:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as response:
                self._data = json.loads(response.read())

            # Save to cache
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self._data, f)

            return self._data

        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception):
            # Return empty dict on error
            return {}

    def get_data(self) -> Any:
        """Get cached data, fetching if necessary."""
        if self._data is None:
            self._data = self.fetch()
        return self._data

    def clear_cache(self) -> None:
        """Clear the local cache file and in-memory data."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        self._data = None

    def is_cached(self) -> bool:
        """Check if cache file exists."""
        return self.cache_file.exists()
