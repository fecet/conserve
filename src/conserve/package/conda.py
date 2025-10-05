"""Conda-PyPI package name mapping."""

from __future__ import annotations

import json

from conserve.file import File


def normalize_pypi_name(name: str) -> str:
    """Normalize PyPI package name per PEP 503 (lowercase, [._-] → -)."""
    normalized = name.lower().replace(".", "-").replace("_", "-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized


class _CondaMapping:
    """Internal Conda-PyPI package name mapping from parselmouth."""

    MAPPING_URL = "https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/mapping_as_grayskull.json"

    def __init__(self, ttl: int | None = None):
        self._file = File(self.MAPPING_URL)
        self._ttl = ttl
        self._mapping_data: dict[str, str] | None = None
        self._reverse_mapping: dict[str, str] | None = None

    def _ensure_loaded(self) -> None:
        if self._mapping_data is None:
            cached = self._file.cache(ttl=self._ttl) if self._ttl else self._file
            text = cached.read_text()
            self._mapping_data = json.loads(text)

    def _build_reverse_mapping(self) -> dict[str, str]:
        if self._reverse_mapping is None:
            self._ensure_loaded()
            self._reverse_mapping = {}
            assert self._mapping_data is not None
            for conda, pypi in self._mapping_data.items():
                if pypi not in self._reverse_mapping:
                    self._reverse_mapping[pypi] = conda
        return self._reverse_mapping

    def conda_to_pypi(self, conda_name: str) -> str | None:
        self._ensure_loaded()
        assert self._mapping_data is not None
        return self._mapping_data.get(conda_name)

    def pypi_to_conda(self, pypi_name: str) -> str | None:
        """Try PEP 503 normalized name first, fallback to original."""
        reverse = self._build_reverse_mapping()

        # Try with normalized name first (PEP 503)
        normalized = normalize_pypi_name(pypi_name)
        result = reverse.get(normalized)

        # Fallback to original name if not found
        if result is None:
            result = reverse.get(pypi_name)

        return result


# Module-level singleton
_default_mapper: _CondaMapping | None = None


def _get_mapper() -> _CondaMapping:
    global _default_mapper
    if _default_mapper is None:
        _default_mapper = _CondaMapping()
    return _default_mapper


def conda_to_pypi(conda_name: str) -> str | None:
    """Convert Conda package name to PyPI name."""
    return _get_mapper().conda_to_pypi(conda_name)


def pypi_to_conda(pypi_name: str) -> str | None:
    """Convert PyPI package name to Conda name (PEP 503 normalized)."""
    return _get_mapper().pypi_to_conda(pypi_name)
