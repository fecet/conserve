"""Common utilities for truth module."""

from typing import Optional, Union, List, Callable, TypeVar, Type, Literal

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
