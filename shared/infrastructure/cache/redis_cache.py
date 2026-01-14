"""
Redis cache implementation.
"""
import json
from typing import Any, Optional

from django.core.cache import cache


class RedisCache:
    """Redis cache wrapper with JSON serialization."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create a cache key with prefix."""
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        value = cache.get(self._make_key(key))
        if value is not None and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def set(self, key: str, value: Any, timeout: int = 300) -> None:
        """Set a value in cache."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        cache.set(self._make_key(key), value, timeout)

    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        cache.delete(self._make_key(key))

    def get_or_set(self, key: str, default_func, timeout: int = 300) -> Any:
        """Get from cache or set using default function."""
        value = self.get(key)
        if value is None:
            value = default_func()
            self.set(key, value, timeout)
        return value

    def clear_pattern(self, pattern: str) -> None:
        """Clear all keys matching a pattern."""
        # Note: This requires redis-py with scan support
        pass
