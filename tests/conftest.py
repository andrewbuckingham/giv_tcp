"""
Pytest configuration and shared fixtures for GivTCP tests.

This file contains common fixtures that can be used across all test files.
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

# Add the GivTCP module to the path so tests can import it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    logger = Mock()
    logger.info = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def sample_timezone():
    """Provide a sample timezone for testing."""
    return timezone.utc


@pytest.fixture
def mock_givlut_entry():
    """Provide a mock GivLUT entry for data validation testing."""
    entry = Mock()
    entry.min = 0
    entry.max = 100
    entry.allowZero = False
    entry.smooth = True
    entry.onlyIncrease = False
    return entry


@pytest.fixture
def sample_nested_dict():
    """Provide a sample nested dictionary for testing."""
    return {
        'level1_a': 'value1',
        'level1_b': {
            'level2_a': 'value2',
            'level2_b': {
                'level3': 'value3'
            }
        },
        'level1_c': 'value4'
    }


@pytest.fixture
def sample_datetime_dict():
    """Provide a dictionary with various data types for testing iterate_dict."""
    from datetime import datetime, time
    return {
        'string_value': 'test',
        'int_value': 42,
        'float_value': 3.14159,
        'datetime_value': datetime(2024, 1, 1, 12, 30, 45),
        'time_value': time(14, 30),
        'tuple_slot': (time(9, 0), time(17, 0)),
        'nested_dict': {
            'nested_value': 100
        }
    }
