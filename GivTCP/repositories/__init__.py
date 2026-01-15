"""
Repository pattern implementations for GivTCP cache management.

This module provides thread-safe and atomic cache operations to eliminate
race conditions in the multi-process GivTCP architecture.

Phase 2 Refactoring: Fix Race Conditions with Repository Pattern
"""

from .cache_repository import CacheRepository, PickleCacheRepository

# RedisCacheRepository requires redis-py (optional dependency)
try:
    from .redis_cache_repository import RedisCacheRepository
    __all__ = ['CacheRepository', 'PickleCacheRepository', 'RedisCacheRepository']
except ImportError:
    __all__ = ['CacheRepository', 'PickleCacheRepository']
