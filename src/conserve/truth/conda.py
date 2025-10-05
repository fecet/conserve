"""Conda package information and Conda-PyPI mapping."""

import json
from pathlib import Path
from typing import Optional, Dict, List, Union

from .utils import MappingQuery
from conserve.utils import File


def normalize_pypi_name(name: str) -> str:
    """Normalize PyPI package name per PEP 503 (lowercase, [._-] → -)."""
    normalized = name.lower().replace(".", "-").replace("_", "-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized


class CondaMapping:
    """Access Conda-PyPI package name mappings from parselmouth."""

    MAPPING_URL = "https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/mapping_as_grayskull.json"

    def __init__(self, cache_dir: Optional[Path] = None, ttl: Optional[int] = None):
        self._file = File(self.MAPPING_URL)
        self._ttl = ttl
        self._mapping_data: Optional[Dict[str, str]] = None
        self._reverse_mapping: Optional[Dict[str, str]] = None

    def _ensure_loaded(self) -> None:
        if self._mapping_data is None:
            cached = self._file.cache(ttl=self._ttl) if self._ttl else self._file
            text = cached.read_text()
            self._mapping_data = json.loads(text)

    def _build_reverse_mapping(self) -> Dict[str, str]:
        if self._reverse_mapping is None:
            self._ensure_loaded()
            self._reverse_mapping = {}
            for conda, pypi in self._mapping_data.items():
                if pypi not in self._reverse_mapping:
                    self._reverse_mapping[pypi] = conda
        return self._reverse_mapping

    def conda_to_pypi(self, conda_name: str) -> Optional[str]:
        self._ensure_loaded()
        return self._mapping_data.get(conda_name)

    def pypi_to_conda(self, pypi_name: str) -> Optional[str]:
        """Try PEP 503 normalized name first, fallback to original."""
        reverse = self._build_reverse_mapping()

        # Try with normalized name first (PEP 503)
        normalized = normalize_pypi_name(pypi_name)
        result = reverse.get(normalized)

        # Fallback to original name if not found
        if result is None:
            result = reverse.get(pypi_name)

        return result

    def search(self, pattern: str) -> Dict[str, str]:
        self._ensure_loaded()
        results = {}
        pattern_lower = pattern.lower()
        for conda, pypi in self._mapping_data.items():
            if pattern_lower in conda.lower() or pattern_lower in pypi.lower():
                results[conda] = pypi
        return results

    def get_all(self) -> Dict[str, str]:
        self._ensure_loaded()
        return self._mapping_data.copy()

    def clear_cache(self) -> None:
        self._mapping_data = None
        self._reverse_mapping = None


# Module-level singleton instance
_default_mapper = None


def _get_mapper() -> CondaMapping:
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = CondaMapping()
    return _default_mapper


# Simple API functions with unified query interface
def query_pypi(conda_names: Union[str, List[str]]) -> Union[Optional[str], List[Optional[str]]]:
    mapper = _get_mapper()
    query_tool = MappingQuery(mapper.conda_to_pypi)
    return query_tool.query(conda_names)


def query_conda(pypi_names: Union[str, List[str]]) -> Union[Optional[str], List[Optional[str]]]:
    mapper = _get_mapper()
    query_tool = MappingQuery(mapper.pypi_to_conda)
    return query_tool.query(pypi_names)


def search(pattern: str) -> Dict[str, str]:
    mapper = _get_mapper()
    return mapper.search(pattern)
