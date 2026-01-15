"""
Concurrency control implementations for GivTCP.

This module provides thread-safe and process-safe locking mechanisms to eliminate
TOCTOU (Time-of-Check-Time-of-Use) vulnerabilities in the multi-process architecture.

Phase 5 Refactoring: Replace File Locks with Proper Synchronization
"""

from .lock_manager import LockManager, ThreadLockManager
from .status_manager import StatusManager, FileStatusManager

# RedisLockManager and RedisStatusManager require redis-py
try:
    from .redis_lock_manager import RedisLockManager
    from .status_manager import RedisStatusManager
    __all__ = ['LockManager', 'ThreadLockManager', 'RedisLockManager',
               'StatusManager', 'FileStatusManager', 'RedisStatusManager']
except ImportError:
    __all__ = ['LockManager', 'ThreadLockManager',
               'StatusManager', 'FileStatusManager']
