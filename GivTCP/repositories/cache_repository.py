# -*- coding: utf-8 -*-
"""
Cache repository implementations with thread-safe operations.

This module provides the Repository pattern for cache management, eliminating
race conditions caused by direct pickle file access in a multi-process environment.

Phase 2 Refactoring: Fix Race Conditions with Repository Pattern

Key improvements:
- Thread-safe read/write using threading.RLock()
- Atomic writes using temp file + os.replace()
- Per-file locking to prevent deadlocks
- Proper error handling and cleanup
"""

from abc import ABC, abstractmethod
from threading import RLock
from typing import Any, Optional
import pickle
import os
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class CacheRepository(ABC):
    """
    Abstract base class for cache operations.

    Defines the interface that all cache implementations must follow.
    This allows easy switching between pickle-based and Redis-based caching.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data by key.

        Args:
            key: Cache key identifier

        Returns:
            Cached data if exists, None otherwise
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Store data in cache.

        Args:
            key: Cache key identifier
            value: Data to cache (must be picklable)
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key identifier

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Remove cached data.

        Args:
            key: Cache key identifier
        """
        pass


class PickleCacheRepository(CacheRepository):
    """
    Thread-safe pickle-based cache implementation.

    This implementation fixes the race conditions in the original code by:
    1. Using per-file RLock for thread-safe access
    2. Atomic writes via temp file + os.replace()
    3. Proper exception handling
    4. Automatic cleanup on errors

    Example:
        >>> cache = PickleCacheRepository('/path/to/cache')
        >>> cache.set('regCache_1', {'data': 'value'})
        >>> data = cache.get('regCache_1')
        >>> if cache.exists('regCache_1'):
        ...     cache.delete('regCache_1')
    """

    def __init__(self, cache_location: str):
        """
        Initialize the pickle cache repository.

        Args:
            cache_location: Directory path where cache files are stored
        """
        self.cache_location = cache_location
        self._locks = {}  # Per-file locks: {filepath: RLock}
        self._global_lock = RLock()  # Lock for _locks dict access

        # Ensure cache directory exists
        os.makedirs(cache_location, exist_ok=True)

        logger.info(f"PickleCacheRepository initialized at {cache_location}")

    @contextmanager
    def _file_lock(self, filepath: str):
        """
        Context manager for per-file locking.

        This prevents deadlocks by locking only the specific file being accessed,
        rather than a global lock for all cache operations.

        Args:
            filepath: Full path to the file to lock

        Yields:
            None (lock is held within context)
        """
        # Get or create lock for this specific file
        with self._global_lock:
            if filepath not in self._locks:
                self._locks[filepath] = RLock()
            file_lock = self._locks[filepath]

        # Acquire the file-specific lock
        with file_lock:
            yield

    def _get_filepath(self, key: str) -> str:
        """
        Generate full file path for a cache key.

        Args:
            key: Cache key identifier

        Returns:
            Full path to cache file
        """
        return os.path.join(self.cache_location, f"{key}.pkl")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data with thread-safe read.

        Args:
            key: Cache key identifier

        Returns:
            Cached data if exists and readable, None otherwise
        """
        filepath = self._get_filepath(key)

        if not os.path.exists(filepath):
            return None

        with self._file_lock(filepath):
            try:
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
                logger.debug(f"Cache hit: {key}")
                return data
            except (EOFError, pickle.UnpicklingError) as e:
                logger.error(f"Failed to read cache {key}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error reading cache {key}: {e}")
                return None

    def set(self, key: str, value: Any) -> None:
        """
        Store data with thread-safe atomic write.

        Uses temp file + os.replace() to ensure atomicity:
        1. Write to temporary file
        2. Atomically replace original file
        3. Clean up temp file on error

        This prevents corruption from concurrent writes or crashes mid-write.

        Args:
            key: Cache key identifier
            value: Data to cache (must be picklable)

        Raises:
            Exception: If write fails (after cleanup)
        """
        filepath = self._get_filepath(key)
        temp_filepath = filepath + '.tmp'

        with self._file_lock(filepath):
            try:
                # Write to temp file first
                with open(temp_filepath, 'wb') as f:
                    pickle.dump(value, f, pickle.HIGHEST_PROTOCOL)

                # Atomic rename (works on Windows and Unix)
                # os.replace() is atomic on both platforms
                os.replace(temp_filepath, filepath)

                logger.debug(f"Cache written: {key}")

            except Exception as e:
                logger.error(f"Failed to write cache {key}: {e}")

                # Clean up temp file if it exists
                if os.path.exists(temp_filepath):
                    try:
                        os.remove(temp_filepath)
                    except:
                        pass  # Best effort cleanup

                raise  # Re-raise the original exception

    def exists(self, key: str) -> bool:
        """
        Check if cache key exists.

        Args:
            key: Cache key identifier

        Returns:
            True if cache file exists, False otherwise
        """
        filepath = self._get_filepath(key)
        return os.path.exists(filepath)

    def delete(self, key: str) -> None:
        """
        Remove cached data with thread-safe deletion.

        Args:
            key: Cache key identifier
        """
        filepath = self._get_filepath(key)

        if not os.path.exists(filepath):
            return

        with self._file_lock(filepath):
            try:
                os.remove(filepath)
                logger.debug(f"Cache deleted: {key}")
            except FileNotFoundError:
                # Race condition: another process deleted it
                # This is fine, the file is gone
                pass
            except Exception as e:
                logger.error(f"Failed to delete cache {key}: {e}")
                raise

    def clear(self) -> None:
        """
        Clear all cache files in the cache location.

        WARNING: This removes ALL .pkl files in the cache directory.
        """
        for filename in os.listdir(self.cache_location):
            if filename.endswith('.pkl'):
                filepath = os.path.join(self.cache_location, filename)
                try:
                    os.remove(filepath)
                    logger.debug(f"Cleared cache file: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to clear cache file {filename}: {e}")
