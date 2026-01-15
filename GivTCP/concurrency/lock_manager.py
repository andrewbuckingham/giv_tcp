"""
Lock manager implementations for thread-safe and process-safe operations.

Phase 5 Refactoring: Replace File Locks with Proper Synchronization

This module provides:
- Abstract LockManager interface
- ThreadLockManager for single-process thread-safe locking
- Context manager support for automatic lock release
- Timeout handling to prevent deadlocks
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from threading import RLock
from typing import Optional, Generator
import logging
import time


logger = logging.getLogger(__name__)


class LockManager(ABC):
    """Abstract base class for lock management."""

    @abstractmethod
    @contextmanager
    def acquire(self, resource_name: str, timeout: Optional[float] = None) -> Generator[bool, None, None]:
        """
        Acquire a lock for the specified resource.

        Args:
            resource_name: Unique identifier for the resource to lock
            timeout: Maximum time to wait for lock (None = wait forever)

        Yields:
            bool: True if lock acquired successfully

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        pass

    @abstractmethod
    def is_locked(self, resource_name: str) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource_name: Resource identifier

        Returns:
            bool: True if locked, False otherwise
        """
        pass


class ThreadLockManager(LockManager):
    """
    Thread-safe lock manager using threading.RLock.

    Provides per-resource locking with reentrant locks to prevent deadlocks.
    Suitable for single-process multi-threaded applications.

    Features:
    - Reentrant locks (same thread can acquire multiple times)
    - Per-resource locking (different resources don't block each other)
    - Timeout support
    - Automatic cleanup
    """

    def __init__(self):
        """Initialize the thread lock manager."""
        self._locks = {}  # resource_name -> RLock
        self._global_lock = RLock()  # Protects _locks dictionary
        logger.debug("ThreadLockManager initialized")

    @contextmanager
    def acquire(self, resource_name: str, timeout: Optional[float] = None) -> Generator[bool, None, None]:
        """
        Acquire a reentrant lock for the specified resource.

        Args:
            resource_name: Unique identifier for the resource
            timeout: Maximum time to wait (seconds). None = wait forever

        Yields:
            bool: Always True (lock acquired)

        Raises:
            TimeoutError: If lock cannot be acquired within timeout

        Example:
            with lock_manager.acquire('inverter_read', timeout=10.0):
                # Critical section - only one thread at a time
                read_inverter_data()
        """
        # Get or create lock for this resource
        with self._global_lock:
            if resource_name not in self._locks:
                self._locks[resource_name] = RLock()
                logger.debug(f"Created new lock for resource: {resource_name}")
            resource_lock = self._locks[resource_name]

        # Try to acquire the resource lock
        start_time = time.time()
        acquired = False

        try:
            if timeout is None:
                # Wait forever
                resource_lock.acquire()
                acquired = True
                logger.debug(f"Lock acquired for resource: {resource_name}")
            else:
                # Try to acquire with timeout
                end_time = start_time + timeout
                while time.time() < end_time:
                    if resource_lock.acquire(blocking=False):
                        acquired = True
                        elapsed = time.time() - start_time
                        logger.debug(f"Lock acquired for resource: {resource_name} (waited {elapsed:.3f}s)")
                        break
                    time.sleep(0.01)  # Brief sleep to avoid busy-waiting

                if not acquired:
                    elapsed = time.time() - start_time
                    logger.error(f"Timeout acquiring lock for resource: {resource_name} (waited {elapsed:.3f}s)")
                    raise TimeoutError(f"Could not acquire lock for '{resource_name}' within {timeout}s")

            yield True

        finally:
            if acquired:
                resource_lock.release()
                logger.debug(f"Lock released for resource: {resource_name}")

    def is_locked(self, resource_name: str) -> bool:
        """
        Check if a resource is currently locked by another thread.

        IMPORTANT: Due to reentrant lock behavior (RLock), this method will
        return False if called from the thread that currently holds the lock,
        since that thread can re-acquire its own lock. To check if ANY thread
        holds the lock, call this from a different thread.

        Note: This is a best-effort check. The lock state may change
        immediately after this method returns.

        Args:
            resource_name: Resource identifier

        Returns:
            bool: True if locked by another thread, False if not locked or
                  locked by current thread
        """
        with self._global_lock:
            if resource_name not in self._locks:
                return False  # No lock exists = not locked
            resource_lock = self._locks[resource_name]

        # Try to acquire without blocking
        acquired = resource_lock.acquire(blocking=False)
        if acquired:
            resource_lock.release()
            return False  # Was able to acquire = not locked
        return True  # Unable to acquire = locked

    def clear(self):
        """
        Clear all locks. Only call when you're sure no locks are held.

        Warning: This is mainly for testing. In production, locks should
        be released naturally via context manager.
        """
        with self._global_lock:
            count = len(self._locks)
            self._locks.clear()
            logger.debug(f"Cleared {count} locks")
