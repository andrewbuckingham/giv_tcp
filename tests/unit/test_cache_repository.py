"""
Unit tests for cache repository implementations.

Tests for Phase 2 refactoring: Fix Race Conditions with Repository Pattern

Critical tests:
- Thread-safety of PickleCacheRepository
- Atomic write operations
- Concurrent read/write scenarios
- Error handling and recovery
"""

import pytest
import os
import tempfile
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier
from GivTCP.repositories import PickleCacheRepository


class TestPickleCacheRepository:
    """Tests for PickleCacheRepository implementation."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache_repo(self, temp_cache_dir):
        """Create a PickleCacheRepository instance."""
        return PickleCacheRepository(temp_cache_dir)

    def test_initialization(self, temp_cache_dir):
        """Test repository initialization."""
        repo = PickleCacheRepository(temp_cache_dir)
        assert repo.cache_location == temp_cache_dir
        assert os.path.exists(temp_cache_dir)

    def test_initialization_creates_directory(self):
        """Test that initialization creates cache directory if missing."""
        temp_dir = tempfile.mkdtemp()
        cache_dir = os.path.join(temp_dir, 'nonexistent', 'cache')

        try:
            repo = PickleCacheRepository(cache_dir)
            assert os.path.exists(cache_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_set_and_get(self, cache_repo):
        """Test basic set and get operations."""
        data = {'key': 'value', 'number': 42}
        cache_repo.set('test_key', data)

        retrieved = cache_repo.get('test_key')
        assert retrieved == data

    def test_get_nonexistent_key(self, cache_repo):
        """Test getting a key that doesn't exist returns None."""
        result = cache_repo.get('nonexistent')
        assert result is None

    def test_exists(self, cache_repo):
        """Test exists method."""
        assert not cache_repo.exists('test_key')

        cache_repo.set('test_key', 'value')
        assert cache_repo.exists('test_key')

    def test_delete(self, cache_repo):
        """Test delete operation."""
        cache_repo.set('test_key', 'value')
        assert cache_repo.exists('test_key')

        cache_repo.delete('test_key')
        assert not cache_repo.exists('test_key')

    def test_delete_nonexistent_key(self, cache_repo):
        """Test deleting a nonexistent key doesn't raise error."""
        # Should not raise exception
        cache_repo.delete('nonexistent')

    def test_overwrite_existing_key(self, cache_repo):
        """Test overwriting an existing key."""
        cache_repo.set('test_key', 'old_value')
        cache_repo.set('test_key', 'new_value')

        result = cache_repo.get('test_key')
        assert result == 'new_value'

    def test_multiple_keys(self, cache_repo):
        """Test storing and retrieving multiple keys."""
        data = {
            'key1': {'data': 1},
            'key2': {'data': 2},
            'key3': {'data': 3}
        }

        for key, value in data.items():
            cache_repo.set(key, value)

        for key, expected_value in data.items():
            retrieved = cache_repo.get(key)
            assert retrieved == expected_value

    def test_complex_data_structures(self, cache_repo):
        """Test storing complex nested data structures."""
        complex_data = {
            'nested': {
                'level1': {
                    'level2': {
                        'level3': 'deep_value'
                    }
                }
            },
            'list': [1, 2, 3, [4, 5, 6]],
            'tuple': (1, 2, 3),
            'mixed': {
                'string': 'text',
                'number': 42,
                'float': 3.14,
                'boolean': True,
                'none': None
            }
        }

        cache_repo.set('complex', complex_data)
        retrieved = cache_repo.get('complex')

        assert retrieved == complex_data
        assert retrieved['nested']['level1']['level2']['level3'] == 'deep_value'

    def test_clear(self, cache_repo):
        """Test clearing all cache files."""
        # Create multiple cache entries
        for i in range(5):
            cache_repo.set(f'key_{i}', f'value_{i}')

        # Verify they exist
        assert all(cache_repo.exists(f'key_{i}') for i in range(5))

        # Clear cache
        cache_repo.clear()

        # Verify they're gone
        assert not any(cache_repo.exists(f'key_{i}') for i in range(5))

    def test_atomic_write(self, cache_repo, temp_cache_dir):
        """Test that writes are atomic (no partial writes visible)."""
        key = 'atomic_test'
        large_data = {'data': 'x' * 10000}  # Large enough to take time to write

        cache_repo.set(key, large_data)

        # Verify complete data was written
        retrieved = cache_repo.get(key)
        assert retrieved == large_data

        # Verify no .tmp file left behind
        temp_file = os.path.join(temp_cache_dir, f'{key}.pkl.tmp')
        assert not os.path.exists(temp_file)

    def test_concurrent_reads(self, cache_repo):
        """Test multiple threads reading the same key simultaneously."""
        data = {'value': 'test_data'}
        cache_repo.set('shared_key', data)

        def read_cache():
            return cache_repo.get('shared_key')

        # Run 20 concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_cache) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should succeed and return the same data
        assert all(result == data for result in results)
        assert len(results) == 20

    def test_concurrent_writes_same_key(self, cache_repo):
        """Test multiple threads writing to the same key."""
        key = 'concurrent_key'
        num_writes = 50

        def write_cache(value):
            cache_repo.set(key, {'thread_value': value})
            return value

        # Run concurrent writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_cache, i) for i in range(num_writes)]
            completed = [f.result() for f in as_completed(futures)]

        # Verify final value exists and is valid
        final_value = cache_repo.get(key)
        assert final_value is not None
        assert 'thread_value' in final_value
        assert final_value['thread_value'] in range(num_writes)
        assert len(completed) == num_writes

    def test_concurrent_writes_different_keys(self, cache_repo):
        """Test multiple threads writing to different keys."""
        num_keys = 100

        def write_cache(key_num):
            key = f'key_{key_num}'
            value = {'data': key_num}
            cache_repo.set(key, value)
            return (key, value)

        # Run concurrent writes to different keys
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(write_cache, i) for i in range(num_keys)]
            results = [f.result() for f in as_completed(futures)]

        # Verify all writes succeeded
        assert len(results) == num_keys

        # Verify all keys exist with correct values
        for key, expected_value in results:
            retrieved = cache_repo.get(key)
            assert retrieved == expected_value

    def test_concurrent_read_write(self, cache_repo):
        """Test simultaneous reads and writes to the same key."""
        key = 'rw_key'
        cache_repo.set(key, {'counter': 0})

        reads = []
        writes_completed = []

        def reader():
            # Read 10 times
            for _ in range(10):
                value = cache_repo.get(key)
                if value:
                    reads.append(value)
                time.sleep(0.001)

        def writer(value):
            cache_repo.set(key, {'counter': value})
            writes_completed.append(value)
            time.sleep(0.001)

        # Run readers and writers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Start 3 readers
            reader_futures = [executor.submit(reader) for _ in range(3)]

            # Start 5 writers
            writer_futures = [executor.submit(writer, i) for i in range(1, 6)]

            # Wait for all to complete
            for f in reader_futures + writer_futures:
                f.result()

        # Verify reads succeeded (no corruption)
        assert len(reads) > 0
        assert all(isinstance(r, dict) and 'counter' in r for r in reads)

        # Verify all writes completed
        assert len(writes_completed) == 5

    def test_synchronized_concurrent_writes(self, cache_repo):
        """Test that concurrent writes don't corrupt data."""
        key = 'sync_key'
        num_threads = 10
        barrier = Barrier(num_threads)

        def synchronized_write(thread_id):
            # Wait for all threads to be ready
            barrier.wait()

            # All threads write simultaneously
            data = {
                'thread_id': thread_id,
                'data': 'x' * 1000,  # Some data
                'timestamp': time.time()
            }
            cache_repo.set(key, data)
            return thread_id

        # Run synchronized writes
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(synchronized_write, i)
                      for i in range(num_threads)]
            completed = [f.result() for f in as_completed(futures)]

        # Verify final value is valid (not corrupted)
        final_value = cache_repo.get(key)
        assert final_value is not None
        assert 'thread_id' in final_value
        assert 'data' in final_value
        assert len(final_value['data']) == 1000
        assert final_value['thread_id'] in range(num_threads)
        assert len(completed) == num_threads

    def test_error_recovery_corrupted_file(self, cache_repo, temp_cache_dir):
        """Test that corrupted cache files are handled gracefully."""
        key = 'corrupted_key'
        filepath = os.path.join(temp_cache_dir, f'{key}.pkl')

        # Create a corrupted pickle file
        with open(filepath, 'wb') as f:
            f.write(b'not_valid_pickle_data')

        # Should return None, not raise exception
        result = cache_repo.get(key)
        assert result is None

    def test_per_file_locking(self, cache_repo):
        """Test that different files can be accessed concurrently."""
        num_keys = 10
        start_barrier = Barrier(num_keys)

        def write_and_read(key_num):
            key = f'parallel_key_{key_num}'

            # Wait for all threads to be ready
            start_barrier.wait()

            # Write to this key
            cache_repo.set(key, {'value': key_num})

            # Read back immediately
            result = cache_repo.get(key)

            return (key, result)

        # All threads should complete quickly since they access different files
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_keys) as executor:
            futures = [executor.submit(write_and_read, i) for i in range(num_keys)]
            results = [f.result() for f in as_completed(futures)]

        elapsed = time.time() - start_time

        # Verify all operations succeeded
        assert len(results) == num_keys
        for key, value in results:
            assert value is not None
            assert value['value'] == int(key.split('_')[-1])

        # Should complete relatively quickly (parallel access)
        # This is a loose check - mainly ensures no deadlocks
        assert elapsed < 5.0  # Should be much faster, but give headroom

    def test_get_filepath(self, cache_repo, temp_cache_dir):
        """Test internal _get_filepath method."""
        key = 'test_key'
        expected_path = os.path.join(temp_cache_dir, 'test_key.pkl')
        actual_path = cache_repo._get_filepath(key)
        assert actual_path == expected_path


# Only run Redis tests if redis is available
try:
    import redis
    from GivTCP.repositories import RedisCacheRepository

    class TestRedisCacheRepository:
        """Tests for RedisCacheRepository implementation."""

        @pytest.fixture
        def redis_client(self):
            """Create a Redis client for testing."""
            try:
                client = redis.Redis(host='localhost', port=6379, db=15)
                client.ping()
                yield client
                # Cleanup
                client.flushdb()
            except redis.ConnectionError:
                pytest.skip("Redis not available for testing")

        @pytest.fixture
        def cache_repo(self, redis_client):
            """Create a RedisCacheRepository instance."""
            return RedisCacheRepository(redis_client, prefix='test_givtcp')

        def test_initialization(self, redis_client):
            """Test repository initialization."""
            repo = RedisCacheRepository(redis_client, prefix='test')
            assert repo.key_prefix == 'test'

        def test_set_and_get(self, cache_repo):
            """Test basic set and get operations."""
            data = {'key': 'value', 'number': 42}
            cache_repo.set('test_key', data)

            retrieved = cache_repo.get('test_key')
            assert retrieved == data

        def test_get_nonexistent_key(self, cache_repo):
            """Test getting a key that doesn't exist."""
            result = cache_repo.get('nonexistent')
            assert result is None

        def test_exists(self, cache_repo):
            """Test exists method."""
            assert not cache_repo.exists('test_key')

            cache_repo.set('test_key', 'value')
            assert cache_repo.exists('test_key')

        def test_delete(self, cache_repo):
            """Test delete operation."""
            cache_repo.set('test_key', 'value')
            assert cache_repo.exists('test_key')

            cache_repo.delete('test_key')
            assert not cache_repo.exists('test_key')

        def test_ttl(self, cache_repo):
            """Test TTL functionality."""
            cache_repo.set('ttl_key', 'value', ttl=10)

            # Key should exist
            assert cache_repo.exists('ttl_key')

            # Should have TTL
            ttl = cache_repo.get_ttl('ttl_key')
            assert ttl is not None
            assert 0 < ttl <= 10

        def test_concurrent_access(self, cache_repo):
            """Test concurrent Redis access."""
            def write_read(i):
                key = f'concurrent_{i}'
                cache_repo.set(key, {'value': i})
                return cache_repo.get(key)

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(write_read, i) for i in range(50)]
                results = [f.result() for f in as_completed(futures)]

            assert len(results) == 50
            assert all(r is not None for r in results)

except ImportError:
    # Redis not available, skip tests
    pass
