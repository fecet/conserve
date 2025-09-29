"""Common utilities for truth module."""

import json
from pathlib import Path
from typing import Optional, Any, Union, List, Callable, TypeVar, Type, Literal
import urllib.request
import urllib.error

T = TypeVar("T")


class MappingQuery:
    """Generic mapping query tool supporting both single and batch queries.

    This class provides a unified interface for querying mappings that automatically
    handles both single string queries and batch list queries.
    """

    def __init__(
        self,
        lookup_func: Callable[[str], Optional[T]],
        on_missing: Literal["none", "raise"] = "none",
        exception_class: Type[Exception] = KeyError,
    ):
        """Initialize MappingQuery.

        Args:
            lookup_func: Function to look up a single key, returning value or None
            on_missing: Behavior when key is not found:
                - "none": Return None for missing keys
                - "raise": Raise exception for missing keys
            exception_class: Exception class to raise when on_missing="raise"
        """
        self.lookup_func = lookup_func
        self.on_missing = on_missing
        self.exception_class = exception_class

    def query(self, keys: Union[str, List[str]]) -> Union[Optional[T], List[Optional[T]]]:
        """Query for single or multiple keys.

        Args:
            keys: Single key string or list of keys

        Returns:
            For single key: The value or None
            For list of keys: List of values (None for missing keys)

        Raises:
            exception_class: If on_missing="raise" and key not found

        Examples:
            >>> query = MappingQuery(lambda x: {"a": 1}.get(x))
            >>> query.query("a")
            1
            >>> query.query(["a", "b"])
            [1, None]
        """
        if isinstance(keys, str):
            # Single query
            result = self.lookup_func(keys)
            if result is None and self.on_missing == "raise":
                raise self.exception_class(f"Key not found: {keys}")
            return result
        else:
            # Batch query
            results = []
            for key in keys:
                try:
                    result = self.lookup_func(key)
                    if result is None and self.on_missing == "raise":
                        raise self.exception_class(f"Key not found: {key}")
                    results.append(result)
                except Exception:
                    if self.on_missing == "raise":
                        raise
                    results.append(None)
            return results

    def __call__(self, keys: Union[str, List[str]]) -> Union[Optional[T], List[Optional[T]]]:
        """Allow calling the instance directly as a shorthand for query()."""
        return self.query(keys)


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
