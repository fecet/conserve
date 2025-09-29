"""Conda package information and Conda-PyPI mapping."""

from pathlib import Path
from typing import Optional, Dict, List, Union

from .utils import CachedFetcher


def normalize_pypi_name(name: str) -> str:
    """Normalize PyPI package name according to PEP 503.

    Converts to lowercase and replaces runs of [._-] with a single hyphen.
    This ensures consistent naming for PyPI packages.

    Examples:
        ruamel.yaml → ruamel-yaml
        ruamel_yaml → ruamel-yaml
        Pillow → pillow
    """
    # Convert to lowercase
    normalized = name.lower()
    # Replace . and _ with -
    normalized = normalized.replace(".", "-").replace("_", "-")
    # Collapse multiple hyphens to single hyphen
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized


class CondaMapping:
    """Access Conda-PyPI package name mappings from parselmouth."""

    MAPPING_URL = "https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/mapping_as_grayskull.json"

    def __init__(self, cache_dir: Optional[Path] = None, ttl: Optional[int] = None):
        """Initialize CondaMapping.

        Args:
            cache_dir: Directory for caching mapping data. Defaults to /tmp/conserve.
            ttl: Cache time-to-live in seconds (not implemented yet).
        """
        self._fetcher = CachedFetcher(
            url=self.MAPPING_URL, cache_dir=cache_dir, cache_filename="conda_pypi_mapping.json", ttl=ttl
        )
        self._mapping_data: Optional[Dict[str, str]] = None
        self._reverse_mapping: Optional[Dict[str, str]] = None

    def _ensure_loaded(self) -> None:
        """Ensure mapping data is loaded."""
        if self._mapping_data is None:
            self._mapping_data = self._fetcher.get_data()

    def _build_reverse_mapping(self) -> Dict[str, str]:
        """Build PyPI to Conda reverse mapping."""
        if self._reverse_mapping is None:
            self._ensure_loaded()
            self._reverse_mapping = {}
            if self._mapping_data:
                for conda, pypi in self._mapping_data.items():
                    # Only add if not already present (first occurrence wins)
                    if pypi not in self._reverse_mapping:
                        self._reverse_mapping[pypi] = conda
        return self._reverse_mapping

    def conda_to_pypi(self, conda_name: str) -> Optional[str]:
        """Convert a Conda package name to PyPI name."""
        self._ensure_loaded()
        return self._mapping_data.get(conda_name) if self._mapping_data else None

    def pypi_to_conda(self, pypi_name: str) -> Optional[str]:
        """Convert a PyPI package name to Conda name.

        First tries with PEP 503 normalized name, then falls back to original name.
        """
        reverse = self._build_reverse_mapping()

        # Try with normalized name first (PEP 503)
        normalized = normalize_pypi_name(pypi_name)
        result = reverse.get(normalized)

        # Fallback to original name if not found
        if result is None:
            result = reverse.get(pypi_name)

        return result

    def search(self, pattern: str) -> Dict[str, str]:
        """Search for mappings matching a pattern."""
        self._ensure_loaded()
        results = {}
        if self._mapping_data:
            pattern_lower = pattern.lower()
            for conda, pypi in self._mapping_data.items():
                if pattern_lower in conda.lower() or pattern_lower in pypi.lower():
                    results[conda] = pypi
        return results

    def get_all(self) -> Dict[str, str]:
        """Get all Conda to PyPI mappings."""
        self._ensure_loaded()
        return self._mapping_data.copy() if self._mapping_data else {}

    def clear_cache(self) -> None:
        """Clear the local cache."""
        self._fetcher.clear_cache()
        self._mapping_data = None
        self._reverse_mapping = None


# Module-level singleton instance
_default_mapper = None


def _get_mapper() -> CondaMapping:
    """Get the default mapper instance."""
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = CondaMapping()
    return _default_mapper


# Simple API functions
def to_pypi(conda_names: Union[str, List[str]]) -> Union[Optional[str], List[Optional[str]]]:
    """Convert Conda package name(s) to PyPI name(s).

    Args:
        conda_names: Single package name or list of names

    Returns:
        PyPI name(s) or None for unknown packages

    Examples:
        >>> to_pypi("pytorch")
        "torch"
        >>> to_pypi(["numpy", "pytorch", "pillow"])
        ["numpy", "torch", "Pillow"]
    """
    mapper = _get_mapper()
    if isinstance(conda_names, str):
        return mapper.conda_to_pypi(conda_names)
    return [mapper.conda_to_pypi(name) for name in conda_names]


def to_conda(pypi_names: Union[str, List[str]]) -> Union[Optional[str], List[Optional[str]]]:
    """Convert PyPI package name(s) to Conda name(s).

    Args:
        pypi_names: Single package name or list of names

    Returns:
        Conda name(s) or None for unknown packages

    Examples:
        >>> to_conda("torch")
        "pytorch"
        >>> to_conda(["numpy", "torch", "Pillow"])
        ["numpy", "pytorch", "pillow"]
    """
    mapper = _get_mapper()
    if isinstance(pypi_names, str):
        return mapper.pypi_to_conda(pypi_names)
    return [mapper.pypi_to_conda(name) for name in pypi_names]


def search(pattern: str) -> Dict[str, str]:
    """Search for Conda-PyPI mappings matching a pattern.

    Args:
        pattern: Search pattern (case-insensitive)

    Returns:
        Dictionary of matching Conda to PyPI mappings

    Example:
        >>> search("torch")
        {"pytorch": "torch", "pytorch-cpu": "torch", ...}
    """
    mapper = _get_mapper()
    return mapper.search(pattern)
