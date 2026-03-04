# Supply Chain Security Testing Guide

## Quick Test Commands

### Run All Tests
```bash
# Run complete test suite
pytest tests/test_supply_chain_security_1070.py -v

# Run with coverage report
pytest tests/test_supply_chain_security_1070.py --cov=scripts.supply_chain_security --cov-report=html
```

### Manual Script Testing

#### 1. Basic Check
```bash
python scripts/supply_chain_security.py --check
```
**Expected Output:**
- Shows requirements_validation status
- Shows transitive_dependencies warnings
- Shows hash_coverage percentage
- Overall PASS/FAIL status

#### 2. CI Gate Mode
```bash
python scripts/supply_chain_security.py --gate --fail-on-issues
echo "Exit code: $?"
```
**Expected Output:**
- Exit code 0 if all checks pass
- Exit code 1 if any check fails

#### 3. Generate Report
```bash
python scripts/supply_chain_security.py --report report.json
cat report.json | python -m json.tool
```
**Expected Output:**
- Valid JSON file with all check results
- Timestamp, project_root, severity_threshold
- Detailed check results with passed/failed status

#### 4. Check Specific File
```bash
python scripts/supply_chain_security.py --requirements requirements-pinned.txt
```
**Expected Output:**
- Validates the specified file only
- Reports on hash coverage for that file

## Test Scenarios

### Scenario 1: All Checks Pass
**Setup:**
- requirements.txt exists
- requirements-pinned.txt exists with all hashed dependencies
- All installed packages are pinned

**Command:**
```bash
python scripts/supply_chain_security.py --gate
```

**Expected:** Exit code 0 with "✅ Supply chain security gate PASSED"

### Scenario 2: Missing requirements.txt
**Setup:**
- Temporarily rename requirements.txt

**Command:**
```bash
mv requirements.txt requirements.txt.bak
python scripts/supply_chain_security.py --gate --no-fail-on-issues
mv requirements.txt.bak requirements.txt
```

**Expected:** Shows error "requirements.txt not found", gate fails

### Scenario 3: Dependency Without Hash
**Setup:**
Create test file with missing hash:
```bash
echo "package-without-hash==1.0.0" > /tmp/test-req.txt
python scripts/supply_chain_security.py --requirements /tmp/test-req.txt
```

**Expected:** Reports missing hash for package

### Scenario 4: Invalid Hash Format
**Setup:**
Create test file with invalid hash:
```bash
echo "package==1.0.0 --hash=sha256:invalid" > /tmp/test-req.txt
python scripts/supply_chain_security.py --requirements /tmp/test-req.txt
```

**Expected:** Reports invalid hash format

## CI/CD Testing

### Test GitHub Actions Workflow (Local)

Use [act](https://github.com/nektos/act) to test workflows locally:

```bash
# Install act
brew install act

# Run supply chain security workflow
act -W .github/workflows/supply-chain-security.yml
```

### Test Dependabot Configuration

```bash
# Validate dependabot.yml
pip install dependabot-core  # or use GitHub's validator

# Check for syntax errors
cat .github/dependabot.yml | python -c "import yaml; yaml.safe_load(open(0))"
```

## Integration Testing

### Test with Real Vulnerabilities

1. Install a known vulnerable package:
```bash
pip install urllib3==1.26.0  # Example vulnerable version
```

2. Run security check:
```bash
python scripts/supply_chain_security.py --check
```

3. Check if transitive dependency detection works

### Test Hash Verification

1. Create test requirements with valid hash:
```bash
echo "requests==2.31.0 --hash=sha256:9f5e8b7c6d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e1f2a" > /tmp/test-valid.txt
python scripts/supply_chain_security.py --requirements /tmp/test-valid.txt
```

2. Test with mismatched hash (should fail verification in real pip install)

## Performance Testing

### Large Requirements File

```bash
# Generate large requirements file
for i in {1..100}; do
  echo "package$i==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f" >> /tmp/large-req.txt
done

# Time the parsing
time python scripts/supply_chain_security.py --requirements /tmp/large-req.txt
```

## Debugging Failed Tests

### If tests fail:

1. **Check imports:**
```bash
python -c "from scripts.supply_chain_security import SupplyChainSecurityChecker; print('OK')"
```

2. **Run single test with verbose output:**
```bash
pytest tests/test_supply_chain_security_1070.py::TestSupplyChainSecurityChecker::test_parse_requirements_file_with_hashes -v -s
```

3. **Check Python version:**
```bash
python --version  # Should be 3.8+
```

## Acceptance Criteria Verification

| Criteria | Test Command | Expected Result |
|----------|--------------|-----------------|
| Dependencies pinned | `python scripts/supply_chain_security.py --check` | Shows hash coverage 100% |
| Vulnerabilities monitored | Check `.github/dependabot.yml` exists | File exists and is valid YAML |
| Alerts enabled | `cat .github/dependabot.yml` | Shows vulnerability-alerts: enabled |
| Hash verification | `python scripts/supply_chain_security.py --requirements requirements-pinned.txt` | All packages have hashes |
| CI/CD integration | `ls .github/workflows/supply-chain-security.yml` | File exists |

## Troubleshooting Common Issues

### Issue 1: "ModuleNotFoundError"
**Fix:** Add project root to Python path
```bash
export PYTHONPATH="${PYTHONPATH}:."
```

### Issue 2: "Permission denied" on script
**Fix:** Make script executable
```bash
chmod +x scripts/supply_chain_security.py
```

### Issue 3: Tests fail on Windows
**Fix:** Use forward slashes in paths or Path objects
```python
from pathlib import Path
path = Path("requirements.txt")
```

### Issue 4: Subprocess errors in tests
**Fix:** Ensure pip is available in test environment
```bash
which pip
python -m pip --version
```

## Continuous Testing

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: supply-chain-check
      name: Supply Chain Security Check
      entry: python scripts/supply_chain_security.py --check
      language: system
      pass_filenames: false
      always_run: true
```

### GitHub Actions Test Matrix

Test across multiple Python versions:

```yaml
strategy:
  matrix:
    python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']
```

## Summary

After running all tests, you should see:
- ✅ 35 unit tests passing
- ✅ Security check runs without errors
- ✅ Report generates valid JSON
- ✅ Gate mode returns appropriate exit codes
- ✅ All acceptance criteria met
