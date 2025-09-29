"""JSON Schema Store integration using schemastore package.

Provide lightweight query/search built on top of the upstream catalog.
Adds name→content resolution and makes it the default for `query`.
"""

import schemastore as _schemastore
from typing import Optional, List, Union
import schemastore as _ss
from .utils import MappingQuery

# Cache for the store and mapping
_store = None
_lookup_func = None


def _get_lookup_func():
    """Get the lookup function with lazy initialization."""
    global _store, _lookup_func

    if _lookup_func is None:
        # Initialize store
        _store = _schemastore._Store()

        # Build name-to-URL mapping
        name_to_url = {}
        for schema in _store.catalog.get("schemas", []):
            if "name" in schema and "url" in schema:
                name = schema["name"]
                url = schema["url"]

                # Add various name variants for flexible lookup
                name_to_url[name] = url
                name_to_url[name.lower()] = url

                # Remove common extensions for convenience
                for ext in [".json", ".yaml", ".yml", ".toml"]:
                    if name.lower().endswith(ext):
                        base = name[: -len(ext)]
                        name_to_url[base.lower()] = url

        # Create lookup function
        def lookup(name: str) -> Optional[str]:
            # Try direct lookup
            result = name_to_url.get(name)
            if result:
                return result

            # Try lowercase
            result = name_to_url.get(name.lower())
            if result:
                return result

            # Try adding extensions if no dot in name
            if "." not in name:
                for ext in [".json", ".yml", ".yaml", ".toml"]:
                    test = f"{name}{ext}".lower()
                    if test in name_to_url:
                        return name_to_url[test]

            return None

        _lookup_func = lookup

    return _lookup_func


def _get_content_lookup_func():
    """Return a callable that maps schema name → JSON content (dict)."""
    url_lookup = _get_lookup_func()
    registry = _ss.registry()

    def lookup(name: str) -> Optional[dict]:
        url = url_lookup(name)
        if not url:
            return None
        try:
            return registry.get_or_retrieve(url).value.contents  # type: ignore[no-any-return]
        except Exception:
            return None

    return lookup


def query(
    names: Union[str, List[str]],
) -> Union[Optional[dict], List[Optional[dict]]]:
    """Query schema by name(s).

    Returns JSON content (dict) for each name.
    Returns None for schemas that cannot be found or retrieved.
    """
    tool = MappingQuery(_get_content_lookup_func())
    return tool.query(names)
