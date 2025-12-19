# Testing Rules

> Standards for writing and maintaining tests.

## Test Commands

```bash
# Backend
cd backend
pytest                          # All tests
pytest tests/unit/              # Unit tests only
pytest -v --cov=src             # With coverage
pytest tests/unit/test_file.py::test_function  # Single test

# Frontend
cd frontend
npm run test                    # Run tests
npm run test:coverage           # With coverage
```

## Test Organization

```
tests/
├── unit/                       # Unit tests (fast, isolated)
│   ├── domain/                 # Business logic tests
│   ├── api/                    # API route tests
│   └── infrastructure/         # Infrastructure tests
├── integration/                # Integration tests
└── conftest.py                 # Shared fixtures
```

## Test Naming Convention

```python
# Pattern: test_{action}_{scenario}_{expected_result}
def test_create_agent_with_valid_data_returns_agent():
    ...

def test_create_agent_without_name_raises_validation_error():
    ...
```

## Requirements

### Must Have
- Unit tests for all public functions
- Integration tests for API endpoints
- Edge case coverage
- Error condition testing

### Forbidden
- ❌ Skipping tests to make CI pass
- ❌ Deleting tests to "fix" failures
- ❌ Tests with hardcoded sleep()
- ❌ Tests that depend on execution order

## Mocking Guidelines

```python
# Use pytest fixtures for common mocks
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# Use patch for external services
@patch('src.integrations.llm.client.call_api')
def test_with_mocked_llm(mock_api):
    mock_api.return_value = {"response": "test"}
    ...
```

## Coverage Requirements

| Category | Minimum |
|----------|---------|
| Overall | 80% |
| Domain Layer | 90% |
| API Layer | 85% |
| Infrastructure | 70% |
