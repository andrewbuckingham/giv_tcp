"""
Redis-based distributed lock manager.

Phase 5 Refactoring: Replace File Locks with Proper Synchronization

Provides process-safe locking using Redis for multi-process applications.
Uses the Redis SET NX (set if not exists) pattern with automatic expiration.
"""

from contextlib import contextmanager
from typing import Optional, Generator
import logging
import time
import uuid

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .lock_manager import LockManager


logger = logging.getLogger(__name__)


class RedisLockManager(LockManager):
    """
    Distributed lock manager using Redis.

    Features:
    - Process-safe (works across multiple processes/machines)
    - Automatic lock expiration (prevents stuck locks)
    - Unique lock identifiers (prevents accidental release by other processes)
    - Timeout support
    - Health checking

    Implementation based on Redis SET NX pattern:
    https://redis.io/docs/manual/patterns/distributed-locks/
    """

    def __init__(self, redis_client: 'redis.Redis', key_prefix: str = 'givtcp:lock',
                 default_ttl: int = 30):
        """
        Initialize Redis lock manager.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for all lock keys in Redis
            default_ttl: Default lock TTL in seconds (prevents stuck locks)
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis-py is required for RedisLockManager")

        self.redis = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

        # Verify Redis connection
        try:
            self.redis.ping()
            logger.info("RedisLockManager initialized successfully")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def _get_lock_key(self, resource_name: str) -> str:
        """Generate Redis key for a resource lock."""
        return f"{self.key_prefix}:{resource_name}"

    @contextmanager
    def acquire(self, resource_name: str, timeout: Optional[float] = None,
                ttl: Optional[int] = None) -> Generator[bool, None, None]:
        """
        Acquire a distributed lock using Redis.

        Args:
            resource_name: Unique identifier for the resource
            timeout: Maximum time to wait for lock (seconds). None = wait forever
            ttl: Lock time-to-live (seconds). If not specified, uses default_ttl

        Yields:
            bool: True if lock acquired

        Raises:
            TimeoutError: If lock cannot be acquired within timeout

        Example:
            with lock_manager.acquire('inverter_write', timeout=10.0, ttl=30):
                # Critical section - only one process at a time across all nodes
                write_to_inverter()
        """
        lock_key = self._get_lock_key(resource_name)
        lock_value = str(uuid.uuid4())  # Unique identifier for this lock
        lock_ttl = ttl if ttl is not None else self.default_ttl

        start_time = time.time()
        acquired = False

        try:
            # Try to acquire lock
            if timeout is None:
                # Wait forever
                while True:
                    # SET key value NX EX ttl
                    # NX = only set if not exists
                    # EX = expiration time in seconds
                    if self.redis.set(lock_key, lock_value, nx=True, ex=lock_ttl):
                        acquired = True
                        logger.debug(f"Redis lock acquired: {resource_name}")
                        break
                    time.sleep(0.1)  # Brief sleep before retry
            else:
                # Try with timeout
                end_time = start_time + timeout
                while time.time() < end_time:
                    if self.redis.set(lock_key, lock_value, nx=True, ex=lock_ttl):
                        acquired = True
                        elapsed = time.time() - start_time
                        logger.debug(f"Redis lock acquired: {resource_name} (waited {elapsed:.3f}s)")
                        break
                    time.sleep(0.1)  # Brief sleep before retry

                if not acquired:
                    elapsed = time.time() - start_time
                    logger.error(f"Timeout acquiring Redis lock: {resource_name} (waited {elapsed:.3f}s)")
                    raise TimeoutError(f"Could not acquire lock for '{resource_name}' within {timeout}s")

            yield True

        finally:
            if acquired:
                # Only release if we own the lock (check value matches)
                # Use Lua script for atomic check-and-delete
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                try:
                    result = self.redis.eval(lua_script, 1, lock_key, lock_value)
                    if result == 1:
                        logger.debug(f"Redis lock released: {resource_name}")
                    else:
                        logger.warning(f"Lock already released or expired: {resource_name}")
                except Exception as e:
                    logger.error(f"Error releasing Redis lock {resource_name}: {e}")

    def is_locked(self, resource_name: str) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource_name: Resource identifier

        Returns:
            bool: True if locked, False otherwise
        """
        lock_key = self._get_lock_key(resource_name)
        try:
            return self.redis.exists(lock_key) > 0
        except Exception as e:
            logger.error(f"Error checking lock status for {resource_name}: {e}")
            return False

    def get_ttl(self, resource_name: str) -> Optional[int]:
        """
        Get remaining TTL for a lock.

        Args:
            resource_name: Resource identifier

        Returns:
            int: Remaining TTL in seconds, or None if lock doesn't exist
        """
        lock_key = self._get_lock_key(resource_name)
        try:
            ttl = self.redis.ttl(lock_key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"Error getting TTL for {resource_name}: {e}")
            return None

    def force_release(self, resource_name: str):
        """
        Force release a lock (use with caution).

        Warning: This releases the lock regardless of who owns it.
        Only use for administrative/cleanup purposes.

        Args:
            resource_name: Resource identifier
        """
        lock_key = self._get_lock_key(resource_name)
        try:
            deleted = self.redis.delete(lock_key)
            if deleted:
                logger.warning(f"Force released lock: {resource_name}")
            else:
                logger.debug(f"No lock to force release: {resource_name}")
        except Exception as e:
            logger.error(f"Error force releasing lock {resource_name}: {e}")

    def clear_all(self):
        """
        Clear all locks with this prefix (use with extreme caution).

        Warning: This clears ALL locks managed by this instance.
        Only use for testing or administrative cleanup.
        """
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.warning(f"Cleared {deleted} locks with pattern: {pattern}")
            else:
                logger.debug("No locks to clear")
        except Exception as e:
            logger.error(f"Error clearing all locks: {e}")
