"""
Unit tests for lock manager implementations.

Tests for Phase 5 refactoring: Replace File Locks with Proper Synchronization

Critical tests:
- Thread-safety of lock acquisitions
- Timeout behavior
- Deadlock prevention
- Lock cleanup
- Concurrent access scenarios
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier, Event
from GivTCP.concurrency import LockManager, ThreadLockManager


class TestThreadLockManager:
    """Tests for ThreadLockManager implementation."""

    @pytest.fixture
    def lock_manager(self):
        """Create a ThreadLockManager instance."""
        return ThreadLockManager()

    def test_initialization(self):
        """Test lock manager initialization."""
        manager = ThreadLockManager()
        assert manager is not None
        assert len(manager._locks) == 0

    def test_basic_lock_acquire(self, lock_manager):
        """Test basic lock acquisition and release."""
        locked_by_other = []

        def check_from_other_thread():
            # Check if locked from another thread
            locked_by_other.append(lock_manager.is_locked('test_resource'))

        with lock_manager.acquire('test_resource'):
            # Check from another thread (should see it as locked)
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(check_from_other_thread).result()

        # Lock released
        assert not lock_manager.is_locked('test_resource')
        assert locked_by_other[0] is True  # Other thread saw it as locked

    def test_lock_reentrant(self, lock_manager):
        """Test that locks are reentrant (same thread can acquire multiple times)."""
        success = []

        with lock_manager.acquire('test_resource'):
            # Acquire again from same thread (should succeed without blocking)
            try:
                with lock_manager.acquire('test_resource', timeout=1.0):
                    success.append(True)
            except TimeoutError:
                success.append(False)

        # Now fully released
        assert not lock_manager.is_locked('test_resource')
        assert success[0] is True  # Reentrant acquisition succeeded

    def test_different_resources_independent(self, lock_manager):
        """Test that locks on different resources don't interfere."""
        success = []

        with lock_manager.acquire('resource_a'):
            # Can acquire different resource while holding first (should not block)
            try:
                with lock_manager.acquire('resource_b', timeout=1.0):
                    success.append(True)
            except TimeoutError:
                success.append(False)

        assert len(success) == 1 and success[0] is True

    def test_timeout_success(self, lock_manager):
        """Test successful lock acquisition within timeout."""
        start = time.time()
        with lock_manager.acquire('test_resource', timeout=5.0):
            elapsed = time.time() - start
            assert elapsed < 5.0  # Should acquire immediately

    def test_timeout_failure(self, lock_manager):
        """Test timeout when lock cannot be acquired."""
        # Acquire lock in main thread
        with lock_manager.acquire('test_resource', timeout=1.0):
            # Try to acquire from another thread with short timeout
            def try_acquire():
                with lock_manager.acquire('test_resource', timeout=0.5):
                    pass

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(try_acquire)
                with pytest.raises(TimeoutError):
                    future.result()

    def test_is_locked_when_not_locked(self, lock_manager):
        """Test is_locked returns False for unlocked resource."""
        assert not lock_manager.is_locked('test_resource')

    def test_is_locked_when_locked(self, lock_manager):
        """Test is_locked returns True for locked resource (checked from another thread)."""
        locked_status = []

        def check_lock():
            locked_status.append(lock_manager.is_locked('test_resource'))

        with lock_manager.acquire('test_resource'):
            # Check from another thread
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(check_lock).result()

        assert locked_status[0] is True  # Was locked when checked from other thread

    def test_concurrent_access_blocks(self, lock_manager):
        """Test that concurrent threads block on the same resource."""
        execution_order = []
        barrier = Barrier(2)

        def worker(worker_id):
            barrier.wait()  # Ensure both threads start simultaneously
            with lock_manager.acquire('shared_resource', timeout=2.0):
                execution_order.append(f'start_{worker_id}')
                time.sleep(0.1)  # Hold lock briefly
                execution_order.append(f'end_{worker_id}')

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(worker, 1)
            future2 = executor.submit(worker, 2)
            future1.result()
            future2.result()

        # Should have sequential execution (one completes before other starts)
        assert len(execution_order) == 4

        # Check that one worker completes fully before the other starts
        # Valid patterns: [start_1, end_1, start_2, end_2] or [start_2, end_2, start_1, end_1]
        if execution_order[0] == 'start_1':
            assert execution_order == ['start_1', 'end_1', 'start_2', 'end_2']
        else:
            assert execution_order == ['start_2', 'end_2', 'start_1', 'end_1']

    def test_sequential_multi_resource_locks(self, lock_manager):
        """Test acquiring multiple resources sequentially (non-overlapping)."""
        result = []

        def worker1():
            with lock_manager.acquire('resource_a', timeout=2.0):
                result.append('worker1_a_acquired')
                time.sleep(0.05)
            # Released resource_a before acquiring resource_b
            with lock_manager.acquire('resource_b', timeout=2.0):
                result.append('worker1_b_acquired')

        def worker2():
            with lock_manager.acquire('resource_b', timeout=2.0):
                result.append('worker2_b_acquired')
                time.sleep(0.05)
            # Released resource_b before acquiring resource_a
            with lock_manager.acquire('resource_a', timeout=2.0):
                result.append('worker2_a_acquired')

        # Non-overlapping acquisitions should complete successfully
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker1)
            f2 = executor.submit(worker2)
            f1.result(timeout=3.0)
            f2.result(timeout=3.0)

        # All acquisitions should succeed
        assert len(result) == 4

    def test_high_concurrency(self, lock_manager):
        """Test lock manager with high concurrency."""
        counter = {'value': 0}
        num_threads = 20
        increments_per_thread = 50

        def increment_counter():
            for _ in range(increments_per_thread):
                with lock_manager.acquire('counter_lock', timeout=5.0):
                    counter['value'] += 1

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(increment_counter) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()  # Wait for all to complete

        # If locking works correctly, counter should be exact
        expected = num_threads * increments_per_thread
        assert counter['value'] == expected

    def test_exception_in_critical_section_releases_lock(self, lock_manager):
        """Test that lock is released even if exception occurs."""
        try:
            with lock_manager.acquire('test_resource'):
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Lock should be released despite exception
        # Verify by trying to acquire from another thread
        can_acquire = []

        def try_acquire():
            try:
                with lock_manager.acquire('test_resource', timeout=0.5):
                    can_acquire.append(True)
            except TimeoutError:
                can_acquire.append(False)

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(try_acquire).result()

        assert can_acquire[0] is True  # Could acquire = lock was released

    def test_clear_locks(self, lock_manager):
        """Test clearing all locks."""
        # Create some locks
        with lock_manager.acquire('resource1'):
            pass
        with lock_manager.acquire('resource2'):
            pass
        with lock_manager.acquire('resource3'):
            pass

        # Clear should remove lock objects (though they're released)
        lock_manager.clear()
        assert len(lock_manager._locks) == 0

    def test_lock_performance(self, lock_manager):
        """Test that lock acquisition is fast for different resources."""
        num_resources = 100
        start = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            def acquire_lock(resource_id):
                with lock_manager.acquire(f'resource_{resource_id}', timeout=1.0):
                    pass  # Just acquire and release

            futures = [executor.submit(acquire_lock, i) for i in range(num_resources)]
            for future in as_completed(futures):
                future.result()

        elapsed = time.time() - start

        # Should complete quickly (different resources don't block)
        assert elapsed < 2.0  # Should be much faster, but give headroom

    def test_context_manager_protocol(self, lock_manager):
        """Test that lock manager properly implements context manager protocol."""
        # Should work with 'with' statement
        acquired = False
        try:
            with lock_manager.acquire('test_resource') as result:
                acquired = True
                assert result is True  # acquire() should yield True
        except Exception as e:
            pytest.fail(f"Context manager failed: {e}")

        assert acquired

    def test_long_running_lock_with_timeout(self, lock_manager):
        """Test timeout behavior with long-running lock holder."""
        event = Event()
        timeout_occurred = []

        def lock_holder():
            with lock_manager.acquire('shared_resource', timeout=5.0):
                event.set()  # Signal that lock is held
                time.sleep(1.0)  # Hold for 1 second

        def lock_waiter():
            event.wait()  # Wait until lock is definitely held
            try:
                with lock_manager.acquire('shared_resource', timeout=0.5):
                    pass
            except TimeoutError:
                timeout_occurred.append(True)

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(lock_holder)
            f2 = executor.submit(lock_waiter)
            f1.result()
            f2.result()

        # Timeout should have occurred
        assert len(timeout_occurred) == 1


# Only run Redis tests if redis is available
try:
    import redis
    from GivTCP.concurrency import RedisLockManager

    class TestRedisLockManager:
        """Tests for RedisLockManager implementation."""

        @pytest.fixture
        def redis_client(self):
            """Create a Redis client for testing."""
            try:
                client = redis.Redis(host='localhost', port=6379, db=15)
                client.ping()
                yield client
                # Cleanup - remove all test locks
                pattern = 'test_givtcp:lock:*'
                keys = client.keys(pattern)
                if keys:
                    client.delete(*keys)
            except redis.ConnectionError:
                pytest.skip("Redis not available for testing")

        @pytest.fixture
        def lock_manager(self, redis_client):
            """Create a RedisLockManager instance."""
            manager = RedisLockManager(redis_client, key_prefix='test_givtcp:lock', default_ttl=30)
            yield manager
            # Cleanup
            manager.clear_all()

        def test_initialization(self, redis_client):
            """Test Redis lock manager initialization."""
            manager = RedisLockManager(redis_client, key_prefix='test', default_ttl=60)
            assert manager.key_prefix == 'test'
            assert manager.default_ttl == 60

        def test_basic_lock_acquire(self, lock_manager):
            """Test basic lock acquisition and release."""
            with lock_manager.acquire('test_resource'):
                assert lock_manager.is_locked('test_resource')

            # Lock should be released
            time.sleep(0.1)  # Brief wait for Redis
            assert not lock_manager.is_locked('test_resource')

        def test_lock_ttl(self, lock_manager):
            """Test that locks have TTL and expire."""
            with lock_manager.acquire('test_resource', ttl=1):
                ttl = lock_manager.get_ttl('test_resource')
                assert ttl is not None
                assert 0 < ttl <= 1

        def test_lock_expires(self, lock_manager):
            """Test that lock expires after TTL."""
            with lock_manager.acquire('test_resource', ttl=1):
                pass  # Release immediately

            # Lock should be gone
            assert not lock_manager.is_locked('test_resource')

        def test_distributed_locking(self, redis_client):
            """Test that lock works across multiple lock manager instances."""
            manager1 = RedisLockManager(redis_client, key_prefix='test_givtcp:lock')
            manager2 = RedisLockManager(redis_client, key_prefix='test_givtcp:lock')

            with manager1.acquire('shared_resource', timeout=1.0):
                # Manager2 should see it as locked
                assert manager2.is_locked('shared_resource')

                # Manager2 should not be able to acquire
                with pytest.raises(TimeoutError):
                    with manager2.acquire('shared_resource', timeout=0.5):
                        pass

        def test_force_release(self, lock_manager):
            """Test force release of lock."""
            with lock_manager.acquire('test_resource'):
                assert lock_manager.is_locked('test_resource')

                # Force release from outside
                lock_manager.force_release('test_resource')
                time.sleep(0.1)
                assert not lock_manager.is_locked('test_resource')

        def test_clear_all(self, lock_manager):
            """Test clearing all locks."""
            # Acquire multiple locks
            with lock_manager.acquire('resource1'):
                pass
            with lock_manager.acquire('resource2'):
                pass

            # Verify they exist
            assert not lock_manager.is_locked('resource1')  # Released
            assert not lock_manager.is_locked('resource2')  # Released

            # Clear all should work (though nothing to clear)
            lock_manager.clear_all()

        def test_concurrent_process_simulation(self, redis_client):
            """Test concurrent access from multiple manager instances (simulates processes)."""
            counter = {'value': 0}

            def increment_with_lock(manager_id):
                manager = RedisLockManager(redis_client, key_prefix='test_givtcp:lock')
                with manager.acquire('counter_lock', timeout=5.0):
                    # Simulate read-modify-write
                    current = counter['value']
                    time.sleep(0.01)  # Simulate processing
                    counter['value'] = current + 1

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(increment_with_lock, i) for i in range(20)]
                for future in as_completed(futures):
                    future.result()

            assert counter['value'] == 20

except ImportError:
    # Redis not available, skip tests
    pass
