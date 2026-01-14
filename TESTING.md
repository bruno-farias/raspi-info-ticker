## Testing Guide

This project maintains **80%+ test coverage** to ensure reliability and code quality.

## Quick Start

### Run All Tests
```bash
./run_tests.sh
```

Or manually:
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html
```

### Run Specific Tests
```bash
# Run unit tests only
pytest -m unit

# Run integration tests
pytest -m integration

# Run tests for specific module
pytest tests/test_weather_plugin.py

# Run specific test
pytest tests/test_plugins.py::TestPluginRegistry::test_create_plugin
```

### Watch Mode
```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                  # Shared fixtures
├── test_plugins.py              # Plugin system tests
├── test_weather_plugin.py       # Weather plugin tests
├── test_currency_plugin.py      # Currency plugin tests
├── test_crypto_plugin.py        # Crypto plugin tests
├── test_clock_plugin.py         # Clock plugin tests
├── test_config.py               # Configuration tests
├── test_scheduler.py            # Display scheduler tests
├── test_renderer.py             # Display renderer tests
└── test_runner.py               # Display runner tests
```

## Writing Tests

### Test Markers
```python
@pytest.mark.unit           # Unit test
@pytest.mark.integration    # Integration test
@pytest.mark.slow           # Slow running test
@pytest.mark.network        # Requires network access
```

### Async Tests
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Using Fixtures
```python
def test_with_mock_config(mock_config):
    """Use shared mock config."""
    assert mock_config["app_name"] == "Test Ticker"

def test_with_fresh_registry(fresh_plugin_registry):
    """Use fresh plugin registry."""
    registry = fresh_plugin_registry
    # Registry is clean for this test
```

### Mocking HTTP Requests
```python
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_api_call():
    with aioresponses() as mock:
        mock.get("https://api.example.com/data", payload={"key": "value"})

        result = await fetch_from_api()
        assert result["key"] == "value"
```

## Coverage Requirements

- **Minimum coverage**: 80%
- **CI fails** if coverage drops below threshold
- View detailed coverage: `open htmlcov/index.html`

### Exclude from Coverage
```python
# Use pragma to exclude specific lines
def debug_function():  # pragma: no cover
    print("Debug info")
```

## Continuous Integration

Tests run automatically on:
- **Push** to master/main/develop
- **Pull requests**
- **Multiple Python versions**: 3.9, 3.10, 3.11

View results: [GitHub Actions](https://github.com/your-username/raspi-info-ticker/actions)

## Test Categories

### Unit Tests
- Test individual functions/classes in isolation
- Fast execution
- No external dependencies

### Integration Tests
- Test component interactions
- May use real services (with mocking)
- Slower execution

### Fixture-based Tests
- Use shared test data and mocks
- Defined in `conftest.py`

## Troubleshooting

### Tests fail with import errors
```bash
# Ensure you're in project root
cd /path/to/raspi-info-ticker

# Install in development mode
pip install -e .
```

### Async test warnings
```bash
# Install pytest-asyncio
pip install pytest-asyncio
```

### Coverage not tracking correctly
```bash
# Clear cache and rerun
pytest --cache-clear --cov=src
```

## Best Practices

1. **Write tests first** (TDD when possible)
2. **Keep tests isolated** - no shared state
3. **Use descriptive names** - test_should_do_something_when_condition
4. **Mock external dependencies** - APIs, databases, hardware
5. **Test edge cases** - None, empty, invalid input
6. **Maintain 80%+ coverage** - aim higher for critical code

## Example Test

```python
"""Example test module."""

import pytest
from src.plugins import BasePlugin

class TestExamplePlugin:
    """Test example plugin."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plugin_initialization(self):
        """Test plugin initializes correctly."""
        plugin = ExamplePlugin()
        await plugin.initialize()

        assert plugin.name == "example"
        assert plugin.config.enabled is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_plugin_fetches_data(self, mock_api_response):
        """Test plugin fetches and processes data."""
        plugin = ExamplePlugin()

        with aioresponses() as mock:
            mock.get("https://api.example.com", payload=mock_api_response)

            data = await plugin.fetch_data()

            assert data is not None
            assert "key" in data
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [aioresponses](https://github.com/pnuckowski/aioresponses)
- [Coverage.py](https://coverage.readthedocs.io/)
