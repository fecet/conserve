"""JSON Schema Store integration using schemastore package."""

import schemastore as _schemastore
from typing import Optional, List, Union, Dict
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


# Main API - just query
def query(names: Union[str, List[str]]) -> Union[Optional[str], List[Optional[str]]]:
    """Query schema URL(s) by name(s).

    Args:
        names: Single schema name or list of names

    Returns:
        Schema URL(s) or None for not found schemas

    Examples:
        >>> query("package.json")
        "https://www.schemastore.org/package.json"
        >>> query(["package.json", "tsconfig", "unknown"])
        ["https://...", "https://...", None]
    """
    query_tool = MappingQuery(_get_lookup_func())
    return query_tool.query(names)


# Optional: search function for discovery
def search(pattern: str) -> Dict[str, str]:
    """Search schemas by pattern in name or description.

    Args:
        pattern: Search pattern (case-insensitive)

    Returns:
        Dictionary of matching schema names to URLs

    Example:
        >>> search("docker")
        {"docker-compose.yml": "https://...", ...}
    """
    if _store is None:
        _get_lookup_func()  # Initialize if needed

    results = {}
    pattern_lower = pattern.lower()

    for schema in _store.catalog.get("schemas", []):
        name = schema.get("name", "")
        desc = schema.get("description", "")
        url = schema.get("url")

        if url and (pattern_lower in name.lower() or pattern_lower in desc.lower()):
            results[name] = url

    return results
