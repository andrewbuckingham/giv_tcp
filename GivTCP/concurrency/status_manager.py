"""
Status manager for tracking operation states across processes.

Phase 5 Refactoring: Replace File-Based Status Flags

Provides a clean interface for setting/checking operation status flags
that can work with either files (legacy) or Redis (distributed).
"""

from abc import ABC, abstractmethod
import os
from os.path import exists
import logging

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


logger = logging.getLogger(__name__)


class StatusManager(ABC):
    """Abstract base class for status management."""

    @abstractmethod
    def set_status(self, status_name: str) -> None:
        """
        Set a status flag to indicate an operation is active.

        Args:
            status_name: Name of the status flag (e.g., 'FCRunning', 'FERunning')
        """
        pass

    @abstractmethod
    def clear_status(self, status_name: str) -> None:
        """
        Clear a status flag to indicate an operation has completed.

        Args:
            status_name: Name of the status flag
        """
        pass

    @abstractmethod
    def is_status_set(self, status_name: str) -> bool:
        """
        Check if a status flag is currently set.

        Args:
            status_name: Name of the status flag

        Returns:
            bool: True if status is set, False otherwise
        """
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Clear all status flags (cleanup on startup)."""
        pass


class FileStatusManager(StatusManager):
    """
    File-based status manager (legacy implementation).

    Uses hidden files as status flags. Compatible with existing code.
    """

    def __init__(self, base_path: str = "."):
        """
        Initialize file status manager.

        Args:
            base_path: Base directory for status files
        """
        self.base_path = base_path
        logger.debug(f"FileStatusManager initialized with base_path: {base_path}")

    def _get_status_file(self, status_name: str) -> str:
        """Get full path to status file."""
        return os.path.join(self.base_path, f".{status_name}")

    def set_status(self, status_name: str) -> None:
        """Create a status file to indicate operation is active."""
        filepath = self._get_status_file(status_name)
        try:
            open(filepath, 'w').close()
            logger.debug(f"Status set: {status_name}")
        except Exception as e:
            logger.error(f"Error setting status {status_name}: {e}")

    def clear_status(self, status_name: str) -> None:
        """Remove a status file to indicate operation completed."""
        filepath = self._get_status_file(status_name)
        try:
            if exists(filepath):
                os.remove(filepath)
                logger.debug(f"Status cleared: {status_name}")
        except Exception as e:
            logger.error(f"Error clearing status {status_name}: {e}")

    def is_status_set(self, status_name: str) -> bool:
        """Check if status file exists."""
        filepath = self._get_status_file(status_name)
        return exists(filepath)

    def clear_all(self) -> None:
        """Clear all known status files."""
        known_statuses = ['FCRunning', 'FERunning', 'lockfile']
        for status in known_statuses:
            self.clear_status(status)
        logger.debug("All status files cleared")


class RedisStatusManager(StatusManager):
    """
    Redis-based status manager (distributed implementation).

    Uses Redis keys as status flags. Better for multi-process/multi-machine deployments.
    """

    def __init__(self, redis_client: 'redis.Redis', key_prefix: str = 'givtcp:status',
                 default_ttl: int = 3600):
        """
        Initialize Redis status manager.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for all status keys
            default_ttl: Default TTL for status keys (prevents stuck statuses)
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis-py is required for RedisStatusManager")

        self.redis = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

        # Verify Redis connection
        try:
            self.redis.ping()
            logger.info("RedisStatusManager initialized successfully")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def _get_status_key(self, status_name: str) -> str:
        """Generate Redis key for a status flag."""
        return f"{self.key_prefix}:{status_name}"

    def set_status(self, status_name: str, ttl: int = None) -> None:
        """
        Set a status flag in Redis.

        Args:
            status_name: Name of the status flag
            ttl: Time-to-live in seconds (prevents stuck statuses). Uses default_ttl if not specified
        """
        key = self._get_status_key(status_name)
        ttl = ttl if ttl is not None else self.default_ttl

        try:
            self.redis.setex(key, ttl, '1')
            logger.debug(f"Redis status set: {status_name} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Error setting Redis status {status_name}: {e}")

    def clear_status(self, status_name: str) -> None:
        """Clear a status flag from Redis."""
        key = self._get_status_key(status_name)
        try:
            self.redis.delete(key)
            logger.debug(f"Redis status cleared: {status_name}")
        except Exception as e:
            logger.error(f"Error clearing Redis status {status_name}: {e}")

    def is_status_set(self, status_name: str) -> bool:
        """Check if a status flag is set in Redis."""
        key = self._get_status_key(status_name)
        try:
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking Redis status {status_name}: {e}")
            return False

    def get_ttl(self, status_name: str) -> int:
        """
        Get remaining TTL for a status flag.

        Args:
            status_name: Name of the status flag

        Returns:
            int: Remaining TTL in seconds, or -1 if no TTL, or -2 if key doesn't exist
        """
        key = self._get_status_key(status_name)
        try:
            return self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for {status_name}: {e}")
            return -2

    def clear_all(self) -> None:
        """Clear all status flags with this prefix."""
        try:
            pattern = f"{self.key_prefix}:*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} Redis status flags")
            else:
                logger.debug("No Redis status flags to clear")
        except Exception as e:
            logger.error(f"Error clearing all Redis statuses: {e}")
