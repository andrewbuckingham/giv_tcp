"""
Unit tests for HardwareCommunicationService.

Tests for Phase 3 refactoring: Extract Service Layer

Critical tests:
- Lock acquisition and release (both new and legacy)
- Inverter data retrieval via GivClient
- Timestamp tracking and calculation
- Error handling (timeouts, communication failures)
- Feature flag support (use_new_locks, use_new_cache)
"""

import pytest
import datetime
import pickle
import tempfile
from unittest.mock import Mock, patch, mock_open, MagicMock
from GivTCP.services import HardwareCommunicationService
from GivTCP.services.hardware_service import InverterReadResult


class TestHardwareCommunicationService:
    """Tests for HardwareCommunicationService."""

    @pytest.fixture
    def mock_giv_client(self):
        """Create a mock GivClient."""
        client = Mock()
        plant = Mock()
        plant.inverter = Mock()
        plant.inverter.battery_percent = 75
        plant.batteries = [Mock()]
        client.getData = Mock(return_value=plant)
        return client

    @pytest.fixture
    def mock_lock_manager(self):
        """Create a mock ThreadLockManager."""
        lock_manager = Mock()
        lock_manager.acquire = MagicMock()
        lock_manager.acquire.return_value.__enter__ = Mock()
        lock_manager.acquire.return_value.__exit__ = Mock()
        return lock_manager

    @pytest.fixture
    def mock_cache_repo(self):
        """Create a mock CacheRepository."""
        cache_repo = Mock()
        cache_repo.get = Mock(return_value=None)
        cache_repo.set = Mock()
        return cache_repo

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary file paths for testing."""
        return {
            'lock_file': str(tmp_path / "inverter.lock"),
            'last_update': str(tmp_path / "lastUpdate.pkl")
        }

    def test_initialization(self, mock_giv_client):
        """Test service initialization."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            inverter_ip="192.168.1.100",
            instance_id="1"
        )

        assert service.giv_client == mock_giv_client
        assert service.inverter_ip == "192.168.1.100"
        assert service.instance_id == "1"
        assert service.use_new_locks == False
        assert service.use_new_cache == False

    def test_read_with_lock_manager_success(
        self, mock_giv_client, mock_lock_manager, mock_cache_repo
    ):
        """Test successful read with new lock manager."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=mock_lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Verify lock was acquired
        mock_lock_manager.acquire.assert_called_once_with('inverter_read', timeout=30.0)

        # Verify GivClient was called
        mock_giv_client.getData.assert_called_once_with(False)

        # Verify result structure
        assert isinstance(result, InverterReadResult)
        assert result.inverter is not None
        assert isinstance(result.batteries, list)
        assert isinstance(result.timestamp, str)
        assert isinstance(result.time_since_last, float)
        assert result.status == "online"

    def test_read_with_lock_manager_timeout(
        self, mock_giv_client, mock_cache_repo
    ):
        """Test lock timeout with new lock manager."""
        lock_manager = Mock()
        lock_manager.acquire = Mock(side_effect=TimeoutError("Lock timeout"))

        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        with pytest.raises(TimeoutError):
            service.read_inverter_data(fullrefresh=False)

    def test_read_with_file_lock_success(
        self, mock_giv_client, temp_files
    ):
        """Test successful read with legacy file lock."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_file_path=temp_files['lock_file'],
            last_update_path=temp_files['last_update'],
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=False,
            use_new_cache=False
        )

        result = service.read_inverter_data(fullrefresh=True)

        # Verify GivClient was called
        mock_giv_client.getData.assert_called_once_with(True)

        # Verify lock file was removed
        import os
        assert not os.path.exists(temp_files['lock_file'])

        # Verify result structure
        assert isinstance(result, InverterReadResult)
        assert result.status == "online"

    def test_read_with_file_lock_existing_lock(
        self, mock_giv_client, temp_files
    ):
        """Test read fails when lockfile already exists."""
        # Create existing lock file
        open(temp_files['lock_file'], 'w').close()

        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_file_path=temp_files['lock_file'],
            last_update_path=temp_files['last_update'],
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=False,
            use_new_cache=False
        )

        with pytest.raises(RuntimeError, match="Lockfile set"):
            service.read_inverter_data(fullrefresh=False)

    def test_read_with_file_lock_removes_on_error(
        self, mock_giv_client, temp_files
    ):
        """Test lock file is removed even when inverter read fails."""
        mock_giv_client.getData = Mock(side_effect=Exception("Connection failed"))

        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_file_path=temp_files['lock_file'],
            last_update_path=temp_files['last_update'],
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=False,
            use_new_cache=False
        )

        with pytest.raises(Exception, match="Connection failed"):
            service.read_inverter_data(fullrefresh=False)

        # Verify lock file was removed despite error
        import os
        assert not os.path.exists(temp_files['lock_file'])

    def test_timestamp_calculation_with_cache_repo(
        self, mock_giv_client, mock_lock_manager, mock_cache_repo
    ):
        """Test timestamp calculation using cache repository."""
        # Set up previous timestamp (1 second ago)
        current_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        previous_time = current_time - datetime.timedelta(seconds=1)
        mock_cache_repo.get = Mock(return_value=previous_time.isoformat())

        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=mock_lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Verify cache was accessed
        mock_cache_repo.get.assert_called_once_with('lastUpdate_1')
        mock_cache_repo.set.assert_called_once()

        # Verify time since last is approximately 1 second
        assert result.time_since_last >= 0.9
        assert result.time_since_last <= 1.5

    def test_timestamp_calculation_with_pickle(
        self, mock_giv_client, temp_files
    ):
        """Test timestamp calculation using legacy pickle file."""
        # Create previous timestamp pickle (2 seconds ago)
        current_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        previous_time = current_time - datetime.timedelta(seconds=2)

        with open(temp_files['last_update'], 'wb') as f:
            pickle.dump(previous_time.isoformat(), f, pickle.HIGHEST_PROTOCOL)

        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_file_path=temp_files['lock_file'],
            last_update_path=temp_files['last_update'],
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=False,
            use_new_cache=False
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Verify time since last is approximately 2 seconds
        assert result.time_since_last >= 1.9
        assert result.time_since_last <= 2.5

        # Verify new timestamp was saved to pickle
        with open(temp_files['last_update'], 'rb') as f:
            saved_timestamp = pickle.load(f)
        assert isinstance(saved_timestamp, str)

    def test_timestamp_no_previous_update_cache(
        self, mock_giv_client, mock_lock_manager, mock_cache_repo
    ):
        """Test timestamp calculation when no previous update in cache."""
        mock_cache_repo.get = Mock(return_value=None)

        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=mock_lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Time since last should be 0 when no previous update
        assert result.time_since_last == 0.0

    def test_timestamp_no_previous_update_pickle(
        self, mock_giv_client, temp_files
    ):
        """Test timestamp calculation when no previous pickle file."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_file_path=temp_files['lock_file'],
            last_update_path=temp_files['last_update'],
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=False,
            use_new_cache=False
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Time since last should be 0 when no previous file
        assert result.time_since_last == 0.0

        # Verify pickle file was created
        import os
        assert os.path.exists(temp_files['last_update'])

    def test_fullrefresh_parameter_passed(
        self, mock_giv_client, mock_lock_manager, mock_cache_repo
    ):
        """Test that fullrefresh parameter is passed to GivClient."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=mock_lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        # Test with fullrefresh=True
        service.read_inverter_data(fullrefresh=True)
        mock_giv_client.getData.assert_called_with(True)

        # Test with fullrefresh=False
        service.read_inverter_data(fullrefresh=False)
        mock_giv_client.getData.assert_called_with(False)

    def test_timestamp_format_iso8601(
        self, mock_giv_client, mock_lock_manager, mock_cache_repo
    ):
        """Test that timestamp is in ISO 8601 format with UTC timezone."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=mock_lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Verify timestamp can be parsed as ISO format
        timestamp = datetime.datetime.fromisoformat(result.timestamp)
        assert timestamp.tzinfo is not None

    def test_inverter_result_contains_all_fields(
        self, mock_giv_client, mock_lock_manager, mock_cache_repo
    ):
        """Test that InverterReadResult contains all expected fields."""
        service = HardwareCommunicationService(
            giv_client=mock_giv_client,
            lock_manager=mock_lock_manager,
            cache_repo=mock_cache_repo,
            inverter_ip="192.168.1.100",
            instance_id="1",
            use_new_locks=True,
            use_new_cache=True
        )

        result = service.read_inverter_data(fullrefresh=False)

        # Verify all fields present
        assert hasattr(result, 'inverter')
        assert hasattr(result, 'batteries')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'time_since_last')
        assert hasattr(result, 'status')
