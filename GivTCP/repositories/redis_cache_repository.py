# -*- coding: utf-8 -*-
"""
Redis-based cache repository implementation.

This module provides a Redis-backed cache repository for better concurrency
and performance in multi-process environments.

Phase 2 Refactoring: Alternative cache backend

Benefits over pickle:
- Native multi-process support (no file locking needed)
- Better performance for concurrent access
- Built-in TTL support
- Atomic operations
- No filesystem limitations
"""

from typing import Any, Optional
import pickle
import logging
from .cache_repository import CacheRepository

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class RedisCacheRepository(CacheRepository):
    """
    Redis-based cache implementation with native concurrency support.

    This implementation uses Redis for caching, which provides:
    - Automatic handling of concurrent access
    - No file system race conditions
    - Better performance under load
    - Built-in expiration (TTL) support

    Example:
        >>> import redis
        >>> redis_client = redis.Redis(host='localhost', port=6379, db=0)
        >>> cache = RedisCacheRepository(redis_client, prefix='givtcp')
        >>> cache.set('regCache_1', {'data': 'value'})
        >>> data = cache.get('regCache_1')
    """

    def __init__(self, redis_client: 'redis.Redis', key_prefix: str = 'givtcp',
                 default_ttl: Optional[int] = None):
        """
        Initialize Redis cache repository.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for all cache keys (default: 'givtcp')
            default_ttl: Default time-to-live in seconds (None = no expiration)

        Raises:
            ImportError: If redis-py is not installed
            redis.ConnectionError: If cannot connect to Redis
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis-py is not installed. Install with: pip install redis"
            )

        self.redis = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

        # Test connection
        try:
            self.redis.ping()
            logger.info(f"RedisCacheRepository initialized with prefix '{key_prefix}'")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """
        Generate full Redis key with prefix.

        Args:
            key: Cache key identifier

        Returns:
            Prefixed key for Redis
        """
        return f"{self.key_prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data from Redis.

        Args:
            key: Cache key identifier

        Returns:
            Cached data if exists, None otherwise
        """
        redis_key = self._make_key(key)

        try:
            data_bytes = self.redis.get(redis_key)

            if data_bytes is None:
                return None

            # Deserialize from pickle
            data = pickle.loads(data_bytes)
            logger.debug(f"Redis cache hit: {key}")
            return data

        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"Failed to unpickle Redis cache {key}: {e}")
            return None
        except redis.RedisError as e:
            logger.error(f"Redis error getting {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting Redis cache {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store data in Redis with optional TTL.

        Args:
            key: Cache key identifier
            value: Data to cache (must be picklable)
            ttl: Time-to-live in seconds (overrides default_ttl)

        Raises:
            redis.RedisError: If Redis operation fails
        """
        redis_key = self._make_key(key)
        expiration = ttl if ttl is not None else self.default_ttl

        try:
            # Serialize to pickle
            data_bytes = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)

            # Store in Redis
            if expiration is not None:
                self.redis.setex(redis_key, expiration, data_bytes)
            else:
                self.redis.set(redis_key, data_bytes)

            logger.debug(f"Redis cache written: {key}")

        except (pickle.PicklingError, TypeError) as e:
            logger.error(f"Failed to pickle data for {key}: {e}")
            raise
        except redis.RedisError as e:
            logger.error(f"Redis error setting {key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error setting Redis cache {key}: {e}")
            raise

    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.

        Args:
            key: Cache key identifier

        Returns:
            True if key exists, False otherwise
        """
        redis_key = self._make_key(key)

        try:
            return self.redis.exists(redis_key) > 0
        except redis.RedisError as e:
            logger.error(f"Redis error checking existence of {key}: {e}")
            return False

    def delete(self, key: str) -> None:
        """
        Remove cached data from Redis.

        Args:
            key: Cache key identifier

        Raises:
            redis.RedisError: If Redis operation fails
        """
        redis_key = self._make_key(key)

        try:
            deleted = self.redis.delete(redis_key)
            if deleted:
                logger.debug(f"Redis cache deleted: {key}")
        except redis.RedisError as e:
            logger.error(f"Redis error deleting {key}: {e}")
            raise

    def clear(self, pattern: Optional[str] = None) -> None:
        """
        Clear cache keys matching pattern.

        Args:
            pattern: Redis pattern to match (default: all keys with prefix)
                    e.g., 'regCache_*' to clear only regCache keys

        WARNING: Uses SCAN to find keys, may be slow on large databases
        """
        if pattern:
            search_pattern = f"{self.key_prefix}:{pattern}"
        else:
            search_pattern = f"{self.key_prefix}:*"

        try:
            # Use SCAN for better performance on large databases
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, match=search_pattern, count=100)

                if keys:
                    self.redis.delete(*keys)
                    logger.debug(f"Cleared {len(keys)} Redis cache keys")

                if cursor == 0:
                    break

        except redis.RedisError as e:
            logger.error(f"Redis error clearing cache: {e}")
            raise

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining time-to-live for a key.

        Args:
            key: Cache key identifier

        Returns:
            Remaining TTL in seconds, None if key doesn't exist or has no TTL,
            -1 if key exists but has no expiration
        """
        redis_key = self._make_key(key)

        try:
            ttl = self.redis.ttl(redis_key)

            if ttl == -2:
                # Key doesn't exist
                return None
            elif ttl == -1:
                # Key exists but has no expiration
                return -1
            else:
                return ttl

        except redis.RedisError as e:
            logger.error(f"Redis error getting TTL for {key}: {e}")
            return None
