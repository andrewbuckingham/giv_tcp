# GivTCP Test Suite

This directory contains tests for the GivTCP application, created as part of Phase 1 refactoring.

## Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── unit/                    # Unit tests
│   ├── test_utils.py        # Tests for utility functions
│   └── ...
├── integration/             # Integration tests (future)
└── fixtures/                # Test data and fixtures
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/unit/test_utils.py
```

### Run with coverage
```bash
pytest --cov=GivTCP --cov-report=html
```

### Run specific test class or function
```bash
pytest tests/unit/test_utils.py::TestDictToList
pytest tests/unit/test_utils.py::TestDictToList::test_flat_dict
```

## Current Coverage

As of Phase 1 completion:
- **utils.py**: 98% coverage (26 tests)
- **Overall project**: ~20% coverage (baseline established)

## Test Guidelines

### Writing Tests

1. **Use descriptive names**: Test names should clearly describe what they test
2. **One assertion per test**: When possible, test one thing at a time
3. **Use fixtures**: Leverage pytest fixtures from conftest.py for common setup
4. **Mock external dependencies**: Use pytest-mock for external services

### Test Organization

- **Unit tests** (`tests/unit/`): Test individual functions/classes in isolation
- **Integration tests** (`tests/integration/`): Test interaction between components
- **Fixtures** (`tests/fixtures/`): Sample data, mock objects, test utilities

## Dependencies

Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Key dependencies:
- pytest: Test framework
- pytest-cov: Coverage reporting
- pytest-mock: Mocking support
- freezegun: Time manipulation for tests

## Phase 1 Accomplishments

### Extracted Functions (from read.py to utils.py)

1. **dicttoList**: Converts nested dictionaries to flat key lists
   - Pure function, no side effects
   - 4 test cases covering edge cases

2. **iterate_dict**: Converts data types to publish-safe formats
   - Handles datetime, time, tuples, Model objects, floats
   - 10 test cases covering all data types

3. **dataSmoother2**: Data validation and spike filtering
   - Complex business logic with multiple validation rules
   - 12 test cases covering validation scenarios

### Benefits Achieved

- ✅ Established testing infrastructure
- ✅ 98% coverage on extracted utilities
- ✅ Enabled refactoring with confidence
- ✅ Documented function behavior through tests
- ✅ Made functions independently testable
- ✅ Backward compatibility maintained

## Next Steps (Phase 2)

- Add Repository pattern tests
- Test thread-safety of cache operations
- Integration tests for Modbus communication
- Increase overall project coverage to 40%

## Continuous Integration

To set up CI (GitHub Actions example):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest --cov=GivTCP --cov-report=xml
      - uses: codecov/codecov-action@v2
```
