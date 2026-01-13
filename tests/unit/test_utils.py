"""
Unit tests for GivTCP utility functions.

Tests for functions extracted from read.py as part of Phase 1 refactoring.
"""

import pytest
from datetime import datetime, time, timezone
from unittest.mock import Mock
from GivTCP.utils import dicttoList, iterate_dict, dataSmoother2


class TestDictToList:
    """Tests for the dicttoList function."""

    def test_flat_dict(self):
        """Test conversion of a flat dictionary."""
        input_dict = {'a': 1, 'b': 2, 'c': 3}
        result = dicttoList(input_dict)
        assert set(result) == {'a', 'b', 'c'}

    def test_nested_dict(self):
        """Test conversion of a nested dictionary."""
        input_dict = {
            'level1': 1,
            'nested': {
                'level2': 2,
                'deeper': {
                    'level3': 3
                }
            }
        }
        result = dicttoList(input_dict)
        assert 'level1' in result
        assert 'nested' in result
        assert 'level2' in result
        assert 'deeper' in result
        assert 'level3' in result

    def test_empty_dict(self):
        """Test conversion of an empty dictionary."""
        result = dicttoList({})
        assert result == []

    def test_dict_with_non_dict_values(self):
        """Test that non-dict values don't cause issues."""
        input_dict = {
            'string': 'value',
            'int': 42,
            'list': [1, 2, 3],
            'nested': {'key': 'value'}
        }
        result = dicttoList(input_dict)
        # Should contain all top-level keys and nested keys
        assert 'string' in result
        assert 'int' in result
        assert 'list' in result
        assert 'nested' in result
        assert 'key' in result


class TestIterateDict:
    """Tests for the iterate_dict function."""

    def test_string_values_passthrough(self, mock_logger):
        """Test that string values pass through unchanged."""
        input_dict = {'key': 'value'}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {'key': 'value'}

    def test_int_values_passthrough(self, mock_logger):
        """Test that integer values pass through unchanged."""
        input_dict = {'key': 42}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {'key': 42}

    def test_float_rounding(self, mock_logger):
        """Test that float values are rounded to 3 decimal places."""
        input_dict = {'key': 3.14159265}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {'key': 3.142}

    def test_datetime_conversion(self, mock_logger):
        """Test that datetime objects are converted to strings."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        input_dict = {'timestamp': dt}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {'timestamp': '15-01-2024 14:30:45'}

    def test_time_conversion(self, mock_logger):
        """Test that time objects are converted to strings."""
        t = time(14, 30)
        input_dict = {'time': t}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {'time': '14:30'}

    def test_tuple_with_slot_conversion(self, mock_logger):
        """Test that tuples with 'slot' in key name are split into start/end."""
        t1 = time(9, 0)
        t2 = time(17, 0)
        input_dict = {'charge_slot_1': (t1, t2)}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {
            'charge_slot_1_start': '09:00',
            'charge_slot_1_end': '17:00'
        }

    def test_tuple_without_slot_conversion(self, mock_logger):
        """Test that regular tuples are split into indexed items."""
        input_dict = {'values': ('a', 'b', 'c')}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {
            'values_0': 'a',
            'values_1': 'b',
            'values_2': 'c'
        }

    def test_nested_dict_recursion(self, mock_logger):
        """Test that nested dictionaries are processed recursively."""
        input_dict = {
            'level1': 'value1',
            'nested': {
                'level2': 'value2'
            }
        }
        result = iterate_dict(input_dict, mock_logger)
        assert result == {
            'level1': 'value1',
            'nested': {
                'level2': 'value2'
            }
        }

    def test_model_conversion(self, mock_logger):
        """Test that Model objects are converted to their name."""
        from givenergy_modbus.model.inverter import Model
        input_dict = {'model': Model.AC}
        result = iterate_dict(input_dict, mock_logger)
        assert result == {'model': 'AC'}

    def test_without_logger(self):
        """Test that function works without explicit logger."""
        input_dict = {'key': 'value'}
        result = iterate_dict(input_dict)
        assert result == {'key': 'value'}


class TestDataSmoother2:
    """Tests for the dataSmoother2 function."""

    def setup_method(self):
        """Set up common test data."""
        self.mock_lookup = Mock()
        self.mock_lookup.min = 0
        self.mock_lookup.max = 100
        self.mock_lookup.allowZero = False
        self.mock_lookup.smooth = True
        self.mock_lookup.onlyIncrease = False

        self.givLUT = {'test_value': self.mock_lookup}
        self.timezone = timezone.utc

    def test_none_smoother_returns_new_value(self):
        """Test that 'none' smoothing returns new value immediately."""
        dataNew = ['test_value', 50.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'none'
        )
        assert result == 50.0

    def test_value_below_min_rejected(self):
        """Test that values below minimum are rejected."""
        dataNew = ['test_value', -10.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 40.0  # Old value returned

    def test_value_above_max_rejected(self):
        """Test that values above maximum are rejected."""
        dataNew = ['test_value', 150.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 40.0  # Old value returned

    def test_zero_not_allowed_rejected(self):
        """Test that zero values are rejected when not allowed."""
        self.mock_lookup.allowZero = False
        dataNew = ['test_value', 0.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 40.0  # Old value returned

    def test_zero_allowed_accepted(self):
        """Test that zero values are accepted when allowed and smoothing permits."""
        self.mock_lookup.allowZero = True
        self.mock_lookup.smooth = False  # Disable smoothing to allow the change
        dataNew = ['test_value', 0.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 0.0  # New value accepted

    def test_small_change_accepted(self):
        """Test that small changes within threshold are accepted."""
        dataNew = ['test_value', 42.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 42.0  # New value accepted (5% change)

    def test_large_spike_rejected(self):
        """Test that large sudden spikes are rejected."""
        from datetime import timedelta

        # Set lastUpdate to 30 seconds ago (within 60 second threshold)
        lastUpdate = (datetime.now(self.timezone) - timedelta(seconds=30)).isoformat()

        # 100% spike (40 -> 80)
        dataNew = ['test_value', 80.0]
        dataOld = ['test_value', 40.0]

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'  # 35% threshold
        )
        assert result == 40.0  # Old value returned due to spike

    def test_old_update_spike_accepted(self):
        """Test that spikes are accepted if enough time has passed."""
        from datetime import timedelta

        # Set lastUpdate to 120 seconds ago (beyond 60 second threshold)
        lastUpdate = (datetime.now(self.timezone) - timedelta(seconds=120)).isoformat()

        # Large change but enough time has passed
        dataNew = ['test_value', 80.0]
        dataOld = ['test_value', 40.0]

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 80.0  # New value accepted

    def test_only_increase_enforced(self):
        """Test that values that should only increase are enforced."""
        self.mock_lookup.onlyIncrease = True

        dataNew = ['test_value', 35.0]
        dataOld = ['test_value', 40.0]
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 40.0  # Old value kept as new value decreased

    def test_smoothing_levels(self):
        """Test different smoothing level thresholds."""
        from datetime import timedelta

        lastUpdate = (datetime.now(self.timezone) - timedelta(seconds=30)).isoformat()

        # Test data: 40 -> 60 (50% increase) - definitely over threshold for high/medium
        dataNew_large = ['test_value', 60.0]
        dataOld = ['test_value', 40.0]

        # High smoothing (25% threshold) - should reject large spike
        result_high = dataSmoother2(
            dataNew_large, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'high'
        )
        assert result_high == 40.0  # Rejected (50% > 25%)

        # Medium smoothing (35% threshold) - should reject large spike
        result_medium = dataSmoother2(
            dataNew_large, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result_medium == 40.0  # Rejected (50% > 35%)

        # Low smoothing (50% threshold) - should still accept at boundary
        result_low = dataSmoother2(
            dataNew_large, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'low'
        )
        assert result_low == 60.0  # Accepted (50% not > 50%)

    def test_non_numeric_passthrough(self):
        """Test that non-numeric values pass through."""
        dataNew = ['test_value', 'string_value']
        dataOld = ['test_value', 'old_string']
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 'string_value'  # New value returned

    def test_old_data_zero_passthrough(self):
        """Test that new data is accepted when old data is zero."""
        dataNew = ['test_value', 50.0]
        dataOld = ['test_value', 0]  # Old data is zero
        lastUpdate = datetime.now(self.timezone).isoformat()

        result = dataSmoother2(
            dataNew, dataOld, lastUpdate,
            self.givLUT, self.timezone, 'medium'
        )
        assert result == 50.0  # New value accepted
