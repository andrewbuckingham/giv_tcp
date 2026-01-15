"""
Unit tests for DataProcessingService.

Tests for Phase 3 refactoring: Extract Service Layer

Critical tests:
- Post-processing pipeline (rate calcs, battery value, data cleansing)
- Cache stack management (FIFO)
- Cache persistence (repository and pickle)
- Consistency checking (missing keys)
- Function composition with external functions
"""

import pytest
import pickle
import tempfile
from unittest.mock import Mock
from GivTCP.services import DataProcessingService


class TestDataProcessingService:
    """Tests for DataProcessingService."""

    @pytest.fixture
    def mock_cache_repo(self):
        """Create a mock CacheRepository."""
        cache_repo = Mock()
        cache_repo.get = Mock(return_value=None)
        cache_repo.set = Mock()
        return cache_repo

    @pytest.fixture
    def mock_functions(self):
        """Create mock processing functions."""
        rate_calc = Mock(side_effect=lambda data, old: {**data, 'rates_applied': True})
        battery_value = Mock(side_effect=lambda data: {**data, 'battery_value': 123.45})
        data_cleansing = Mock(side_effect=lambda data, old: {**data, 'cleansed': True})
        dict_to_list = Mock(side_effect=lambda d: list(d.keys()))
        return {
            'rate_calc': rate_calc,
            'battery_value': battery_value,
            'data_cleansing': data_cleansing,
            'dict_to_list': dict_to_list
        }

    @pytest.fixture
    def sample_data(self):
        """Create sample multi_output data."""
        return {
            'Power': {'Power': {'PV_Power': 4000, 'Load_Power': 3000}},
            'Energy': {'Today': {'PV_Energy_Today_kWh': 25.5}},
            'SOC': 75,
            'status': 'online'
        }

    @pytest.fixture
    def sample_cache_stack(self, sample_data):
        """Create sample cache stack."""
        return [
            sample_data.copy(),
            sample_data.copy(),
            sample_data.copy(),
            sample_data.copy(),
            sample_data.copy()
        ]

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary file paths for testing."""
        return {
            'cache_file': str(tmp_path / "regCache.pkl")
        }

    def test_initialization(self, mock_cache_repo, mock_functions):
        """Test service initialization."""
        service = DataProcessingService(
            cache_repo=mock_cache_repo,
            instance_id="1",
            use_new_cache=True,
            rate_calc_func=mock_functions['rate_calc']
        )

        assert service.cache_repo == mock_cache_repo
        assert service.instance_id == "1"
        assert service.use_new_cache == True
        assert service.rate_calc_func == mock_functions['rate_calc']

    def test_process_output_applies_all_functions(
        self, mock_functions, sample_data, sample_cache_stack
    ):
        """Test that process_output applies all processing functions."""
        service = DataProcessingService(
            rate_calc_func=mock_functions['rate_calc'],
            battery_value_func=mock_functions['battery_value'],
            data_cleansing_func=mock_functions['data_cleansing'],
            use_new_cache=True
        )

        result = service.process_output(sample_data, sample_cache_stack)

        # Verify all functions were called
        mock_functions['rate_calc'].assert_called_once()
        mock_functions['battery_value'].assert_called_once()
        mock_functions['data_cleansing'].assert_called_once()

        # Verify transformations were applied
        assert result['rates_applied'] == True
        assert result['battery_value'] == 123.45
        assert result['cleansed'] == True

    def test_process_output_with_empty_cache_stack(
        self, mock_functions, sample_data
    ):
        """Test process_output with empty cache stack."""
        service = DataProcessingService(
            rate_calc_func=mock_functions['rate_calc'],
            battery_value_func=mock_functions['battery_value'],
            use_new_cache=True
        )

        result = service.process_output(sample_data, [])

        # Should still work, using sample_data as fallback for old data
        mock_functions['rate_calc'].assert_called_once()
        mock_functions['battery_value'].assert_called_once()

    def test_process_output_skips_missing_functions(
        self, sample_data, sample_cache_stack
    ):
        """Test that missing functions are skipped gracefully."""
        service = DataProcessingService(
            rate_calc_func=None,
            battery_value_func=None,
            data_cleansing_func=None,
            use_new_cache=True
        )

        # Should not raise error
        result = service.process_output(sample_data, sample_cache_stack)

        # Data should be unchanged
        assert result == sample_data

    def test_update_cache_stack_fifo_behavior(self, sample_data):
        """Test cache stack FIFO behavior."""
        service = DataProcessingService(use_new_cache=True)

        # Start with full stack
        cache_stack = [
            {'id': 1},
            {'id': 2},
            {'id': 3},
            {'id': 4},
            {'id': 5}
        ]

        # Add new data
        new_data = {'id': 6}
        updated_stack = service.update_cache_stack(cache_stack, new_data)

        # Verify FIFO: oldest (id=1) removed, newest (id=6) added
        assert len(updated_stack) == 5
        assert updated_stack[0]['id'] == 2
        assert updated_stack[4]['id'] == 6

    def test_update_cache_stack_with_less_than_5(self, sample_data):
        """Test cache stack update when stack has less than 5 elements."""
        service = DataProcessingService(use_new_cache=True)

        cache_stack = [{'id': 1}, {'id': 2}, {'id': 3}]
        new_data = {'id': 4}

        updated_stack = service.update_cache_stack(cache_stack, new_data)

        # Should just append without removing
        assert len(updated_stack) == 4
        assert updated_stack[3]['id'] == 4

    def test_save_cache_stack_with_repository(self, mock_cache_repo):
        """Test saving cache stack using cache repository."""
        service = DataProcessingService(
            cache_repo=mock_cache_repo,
            instance_id="1",
            use_new_cache=True
        )

        cache_stack = [{'id': 1}, {'id': 2}]
        service.save_cache_stack(cache_stack)

        # Verify repository was called
        mock_cache_repo.set.assert_called_once_with('regCache_1', cache_stack)

    def test_save_cache_stack_with_pickle(self, temp_files):
        """Test saving cache stack using pickle file."""
        service = DataProcessingService(
            cache_file_path=temp_files['cache_file'],
            instance_id="1",
            use_new_cache=False
        )

        cache_stack = [{'id': 1}, {'id': 2}, {'id': 3}]
        service.save_cache_stack(cache_stack)

        # Verify pickle file was created
        import os
        assert os.path.exists(temp_files['cache_file'])

        # Verify contents
        with open(temp_files['cache_file'], 'rb') as f:
            loaded_stack = pickle.load(f)
        assert loaded_stack == cache_stack

    def test_load_cache_stack_with_repository(self, mock_cache_repo):
        """Test loading cache stack from cache repository."""
        cache_stack = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}, {'id': 5}]
        mock_cache_repo.get = Mock(return_value=cache_stack)

        service = DataProcessingService(
            cache_repo=mock_cache_repo,
            instance_id="1",
            use_new_cache=True
        )

        result = service.load_cache_stack()

        # Verify repository was called
        mock_cache_repo.get.assert_called_once_with('regCache_1')
        assert result == cache_stack

    def test_load_cache_stack_with_pickle(self, temp_files):
        """Test loading cache stack from pickle file."""
        cache_stack = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}, {'id': 5}]

        # Create pickle file
        with open(temp_files['cache_file'], 'wb') as f:
            pickle.dump(cache_stack, f, pickle.HIGHEST_PROTOCOL)

        service = DataProcessingService(
            cache_file_path=temp_files['cache_file'],
            instance_id="1",
            use_new_cache=False
        )

        result = service.load_cache_stack()

        assert result == cache_stack

    def test_load_cache_stack_not_found_repository(self, mock_cache_repo):
        """Test loading cache stack when not found in repository."""
        mock_cache_repo.get = Mock(return_value=None)

        service = DataProcessingService(
            cache_repo=mock_cache_repo,
            instance_id="1",
            use_new_cache=True
        )

        result = service.load_cache_stack()

        # Should return empty 5-element stack
        assert result == [0, 0, 0, 0, 0]

    def test_load_cache_stack_not_found_pickle(self, temp_files):
        """Test loading cache stack when pickle file doesn't exist."""
        service = DataProcessingService(
            cache_file_path=temp_files['cache_file'],
            instance_id="1",
            use_new_cache=False
        )

        result = service.load_cache_stack()

        # Should return empty 5-element stack
        assert result == [0, 0, 0, 0, 0]

    def test_check_consistency_no_missing_keys(self, mock_functions):
        """Test consistency check when no keys are missing."""
        service = DataProcessingService(
            dict_to_list_func=mock_functions['dict_to_list'],
            use_new_cache=True
        )

        new_data = {'key1': 1, 'key2': 2, 'key3': 3}
        old_data = {'key1': 10, 'key2': 20, 'key3': 30}

        # Should not raise or log critical
        service._check_consistency(new_data, old_data)

    def test_check_consistency_with_missing_keys(self, mock_functions, caplog):
        """Test consistency check logs warning when keys are missing."""
        import logging
        caplog.set_level(logging.CRITICAL)

        service = DataProcessingService(
            dict_to_list_func=mock_functions['dict_to_list'],
            use_new_cache=True
        )

        new_data = {'key1': 1, 'key2': 2}
        old_data = {'key1': 10, 'key2': 20, 'key3': 30}

        service._check_consistency(new_data, old_data)

        # Verify critical log was created for missing key
        assert 'key3' in caplog.text
        assert 'missing from new data' in caplog.text

    def test_check_consistency_without_dict_to_list(self):
        """Test consistency check does nothing without dict_to_list function."""
        service = DataProcessingService(
            dict_to_list_func=None,
            use_new_cache=True
        )

        new_data = {'key1': 1}
        old_data = {'key1': 10, 'key2': 20}

        # Should not raise error
        service._check_consistency(new_data, old_data)

    def test_process_output_uses_most_recent_cache(
        self, mock_functions, sample_data
    ):
        """Test that process_output uses index 4 (most recent) from cache stack."""
        service = DataProcessingService(
            rate_calc_func=mock_functions['rate_calc'],
            use_new_cache=True
        )

        cache_stack = [
            {'timestamp': '2025-01-01'},
            {'timestamp': '2025-01-02'},
            {'timestamp': '2025-01-03'},
            {'timestamp': '2025-01-04'},
            {'timestamp': '2025-01-05'}  # Most recent
        ]

        service.process_output(sample_data, cache_stack)

        # Verify rate_calc was called with most recent cache data
        call_args = mock_functions['rate_calc'].call_args[0]
        assert call_args[1]['timestamp'] == '2025-01-05'

    def test_complete_pipeline_integration(
        self, mock_cache_repo, mock_functions, sample_data, temp_files
    ):
        """Test complete pipeline: load, process, update, save."""
        service = DataProcessingService(
            cache_repo=mock_cache_repo,
            instance_id="1",
            use_new_cache=True,
            rate_calc_func=mock_functions['rate_calc'],
            battery_value_func=mock_functions['battery_value'],
            data_cleansing_func=mock_functions['data_cleansing'],
            dict_to_list_func=mock_functions['dict_to_list']
        )

        # 1. Load cache stack
        initial_stack = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}, {'id': 5}]
        mock_cache_repo.get = Mock(return_value=initial_stack)
        cache_stack = service.load_cache_stack()

        # 2. Process output
        processed = service.process_output(sample_data, cache_stack)

        # 3. Update cache stack
        updated_stack = service.update_cache_stack(cache_stack, processed)

        # 4. Save cache stack
        service.save_cache_stack(updated_stack)

        # Verify stack was updated correctly
        assert len(updated_stack) == 5
        assert updated_stack[4] == processed

        # Verify save was called
        mock_cache_repo.set.assert_called_once()
