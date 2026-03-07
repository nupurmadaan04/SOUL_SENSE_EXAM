# Test Suite Documentation

## Overview

This directory contains the complete test suite for SOUL_SENSE_EXAM. All tests are mandatory on every push and PR to ensure code quality and prevent regressions.

## Test Categories

The test suite is organized into several categories using pytest markers:

### Unit Tests (`@pytest.mark.unit`)
- Isolated component tests
- No external dependencies
- Run in parallel for speed
- Execute: `pytest tests/ -m unit -v`

### Integration Tests (`@pytest.mark.integration`)
- Cross-module and API integration tests
- Test component interactions
- Location: `tests/integration/`
- Execute: `pytest tests/ -m integration -v`

### Security Tests (`@pytest.mark.security`)
- Security-focused tests
- Supply chain, auth, CORS tests
- Location: `tests/security/`
- Execute: `pytest tests/ -m security -v`

### Performance Tests (`@pytest.mark.performance`)
- Latency budgets and performance validation
- Location: `tests/performance/`
- Execute: `pytest tests/ -m performance -v`

### Serial Tests (`@pytest.mark.serial`)
- Tests requiring sequential execution
- GUI and threading tests
- Execute: `pytest tests/ -m serial -v`

### Smoke Tests (`@pytest.mark.smoke`)
- Quick validation tests
- Execute: `pytest tests/ -m smoke -v`

## Running Tests Locally

### Prerequisites

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-mock pytest-cov pytest-xdist pytest-timeout
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Tests with Coverage
```bash
pytest tests/ -v --cov=app --cov=backend --cov-report=html --cov-report=term-missing
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/ -m unit -v

# Integration tests only
pytest tests/integration/ -v

# Security tests only
pytest tests/security/ -v

# Performance tests only
pytest tests/performance/ -v

# Exclude serial tests (run in parallel)
pytest tests/ -m "not serial" -n 2 -v

# Run serial tests only
pytest tests/ -m serial -v
```

### Run Single Test File
```bash
pytest tests/test_auth.py -v
```

### Run with Timeout
```bash
pytest tests/ -v --timeout=180
```

## CI/CD Pipeline

### Automated Test Execution

The GitHub Actions workflow (`python-app.yml`) automatically runs:

1. **Pre-commit checks** - Code style and formatting
2. **Type checking** - mypy validation
3. **Linting** - flake8 style checks
4. **Security scans** - bandit, safety, SBOM, vulnerability gate
5. **Unit + Integration tests** - Parallel execution with coverage
6. **Serial tests** - Sequential execution
7. **Backend API tests** - FastAPI validation with ZAP security scan
8. **Environment fidelity** - Test environment validation
9. **Coverage reporting** - HTML coverage report upload
10. **Artifact uploads** - Reports, coverage, fidelity scorecard

### Test Requirements

✅ **All tests must pass** before merge to main  
✅ **Coverage reporting** is generated and uploaded  
✅ **Fidelity score** must be ≥ 75/100  
✅ **Security scans** must pass with no high-severity issues  

## Coverage Standards

- **Target Coverage**: Maintain 80%+ code coverage
- **Coverage Reports**: HTML reports generated in `htmlcov/`
- **View Report**: Open `htmlcov/index.html` in browser

## Test Configuration

### pytest.ini Settings

```ini
[pytest]
pythonpath = .
testpaths = tests
timeout = 180           # Per-test timeout in seconds
timeout_method = thread # Timeout enforcement method
```

### Markers Configuration

See `pytest.ini` for complete marker definitions.

## Common Issues & Solutions

### Flaky Tests
If tests fail intermittently:
1. Check for race conditions
2. Mark with `@pytest.mark.serial` if needed
3. Review timeout values
4. Check for external dependencies

### Timeout Errors
If tests timeout:
1. Increase timeout: `pytest --timeout=300`
2. Mark with `@pytest.mark.serial` instead of parallel
3. Profile the test to identify bottlenecks

### Coverage Not Generating
```bash
# Ensure coverage is installed
pip install pytest-cov coverage

# Run with coverage flags
pytest tests/ --cov=app --cov=backend --cov-report=html
```

## Adding New Tests

### Test Naming Convention
- Unit test: `test_<component>_<scenario>.py`
- Integration test: `tests/integration/test_<feature>_integration.py`
- Security test: `tests/security/test_<area>_security.py`

### Adding Test Markers

```python
@pytest.mark.unit
def test_component_behavior():
    """Test description."""
    assert result == expected

@pytest.mark.integration
def test_api_workflow():
    """Test API integration workflow."""
    response = api.call()
    assert response.status == 200

@pytest.mark.serial
def test_gui_interaction():
    """GUI tests must run serially."""
    gui.interact()
```

### Coverage Requirements

```python
# Good - testable code
def calculate_score(answers):
    """Calculate exam score from answers."""
    return sum(a.points for a in answers if a.is_correct)

# Test it
def test_calculate_score():
    """Test score calculation."""
    answers = [Answer(points=10, is_correct=True)]
    assert calculate_score(answers) == 10
```

## Test Artifacts

The CI pipeline uploads these artifacts for each build:

- `coverage-report-<sha>` - HTML coverage report
- `fidelity-scorecard-<sha>` - Environment fidelity metrics
- `sbom-<sha>` - Software Bill of Materials
- `vulnerability-report-<sha>` - Security vulnerability scan
- `zap-scan-report` - OWASP ZAP security scan

Access artifacts in GitHub Actions: **Artifacts** tab in workflow run.

## Continuous Improvement

Regular areas to monitor:
- Test execution time trends
- Coverage by module
- Flake/failure rates
- Performance regression
- Security scan results

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [pytest-xdist (Parallel Testing)](https://pytest-xdist.readthedocs.io/)
- [Issue #1422: Required Test Suite](https://github.com/nupurmadaan04/SOUL_SENSE_EXAM/issues/1422)
