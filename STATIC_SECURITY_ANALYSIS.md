# Static Security Analysis Implementation

## Overview

This document describes the implementation of automated static security analysis in the CI pipeline for issue #1059. The implementation integrates Bandit for Python code security scanning and Safety for dependency vulnerability checking.

## Tools Used

### Bandit
- **Purpose**: Static security analysis for Python code
- **Version**: >= 1.7.0
- **Target**: `backend/` directory
- **Configuration**: `.bandit` config file
- **Severity Threshold**: High (blocks CI on High/Critical vulnerabilities)

### Safety
- **Purpose**: Dependency vulnerability scanning
- **Version**: >= 2.3.0
- **Targets**: `requirements.txt` and `backend/fastapi/requirements.txt`
- **Severity Threshold**: High (blocks CI on High/Critical vulnerabilities)

### OWASP ZAP
- **Purpose**: Dynamic security testing for APIs
- **Mode**: Baseline scanning
- **Target**: Running backend server in CI (http://host.docker.internal:8000)
- **Configuration**: `.zap/rules.tsv` for suppressing false positives
- **Severity Threshold**: Medium (blocks CI on Medium/High vulnerabilities)
- **Output**: HTML report uploaded as artifact

## Configuration Files

### `.bandit`
```ini
[bandit]
exclude_dirs = tests, __pycache__, .pytest_cache
skips = B101,B601,B603  # Skip assert checks, shell usage, subprocess without shell
```

### `requirements-security.txt`
```
bandit>=1.7.0
safety>=2.3.0
```

### `.zap/rules.tsv`
```tsv
# OWASP ZAP Rules File for Suppressing False Positives
# Format: URL	Alert	Evidence	CWE	Other
# Use this file to suppress known false positive alerts from ZAP baseline scans
# Example entries (uncomment and modify as needed):
# http://example.com/api/.*	X-Frame-Options Header Not Set		X-Frame-Options	Known false positive for API endpoints
# http://example.com/.*	Content Security Policy (CSP) Header Not Set		CSP	Not applicable for API responses
```

## CI Integration

The security scans are integrated into the GitHub Actions workflow (`python-app.yml`) and run on every pull request to the `main` branch.

### Workflow Steps Added

1. **Install Security Tools**
   ```yaml
   - name: Install security tools
     run: pip install bandit safety
   ```

2. **Bandit Security Scan**
   ```yaml
   - name: Run Bandit security scan
     run: bandit -r backend/ --severity-level high
   ```

3. **Dependency Vulnerability Scan**
   ```yaml
   - name: Run dependency vulnerability scan
     run: |
       safety check -r requirements.txt --severity-threshold high
       if [ -f backend/fastapi/requirements.txt ]; then safety check -r backend/fastapi/requirements.txt --severity-threshold high; fi
   ```

4. **OWASP ZAP Dynamic Scan**
   ```yaml
   - name: Test Backend App
     run: |
       # ... server startup and pytest ...
       echo "Running OWASP ZAP baseline scan..."
       docker run --rm -v $(pwd):/zap/wrk -t zaproxy/zap-baseline:latest -t http://host.docker.internal:8000 -r zap_report.html --alert-level Medium -z "-config rules.file=/zap/wrk/.zap/rules.tsv"
     working-directory: ./backend/fastapi

   - name: Upload ZAP Scan Report
     uses: actions/upload-artifact@v4
     with:
       name: zap-scan-report
       path: backend/fastapi/zap_report.html
   ```

### Security Regression Tests

The security regression test suite (`tests/security/`) is automatically executed as part of the standard pytest run in CI:

```yaml
- name: Test Root App
  run: pytest tests/ -n 2 --maxfail=5 -m "not serial" --timeout=120 -v
```

All security regression tests run on every PR and fail the build if any security vulnerability is reintroduced.

## Acceptance Criteria

- ✅ Bandit runs on every PR
- ✅ Dependency scan runs on every PR
- ✅ CI fails on High severity vulnerabilities (static)
- ✅ CI passes when vulnerabilities are resolved
- ✅ Security reports visible in CI logs
- ✅ ZAP runs on staging environment (CI test environment)
- ✅ Scan report uploaded as artifact
- ✅ CI fails on medium/high vulnerabilities (dynamic)
- ✅ False positives documented and suppressed
- ✅ Expired JWT returns 401
- ✅ Tampered JWT returns 401
- ✅ Unauthorized role access returns 403
- ✅ Replay refresh token blocked
- ✅ All tests run in CI

## Security Issues Detected

Bandit scans for common security vulnerabilities including:

- Hardcoded secrets and passwords
- Use of insecure cryptographic functions
- SQL injection vulnerabilities
- Cross-site scripting (XSS) issues
- Command injection risks
- Unsafe deserialization

Safety checks for known vulnerabilities in Python packages from the Python Package Index (PyPI).

ZAP baseline scanning detects runtime security issues including:

- Missing security headers (X-Frame-Options, CSP, HSTS)
- CORS misconfigurations
- Authentication and authorization weaknesses
- IDOR (Insecure Direct Object References)
- Injection vulnerabilities
- Sensitive data exposure
- Broken access control

## Handling False Positives

If Bandit reports false positives:

1. Review the specific issue in the CI logs
2. Add appropriate skip rules to `.bandit` configuration
3. Use `# nosec` comments in code for specific lines (as last resort)
4. Update this document with the rationale

If ZAP reports false positives:

1. Review the alert in the HTML report artifact
2. Add suppression rules to `.zap/rules.tsv` using the format: URL<TAB>Alert<TAB>Evidence<TAB>CWE<TAB>Other
3. Use regex patterns for URLs when applicable
4. Document the rationale in comments
5. Re-run CI to verify suppression

## Maintenance

- Regularly update Bandit and Safety versions in `requirements-security.txt`
- Review and update `.bandit` configuration as needed
- Monitor CI logs for new vulnerability patterns
- Update dependencies to address reported vulnerabilities

## Security Regression Tests

Automated pytest test suite located in `tests/security/` to prevent reintroduction of known vulnerabilities:

### JWT Security Tests (`test_jwt_security.py`)
- Expired JWT rejection (returns 401)
- Tampered JWT rejection (returns 401)
- Missing required claims validation
- Invalid algorithm detection
- Blacklisted token rejection

### Role-Based Access Control Tests (`test_rbac_security.py`)
- Regular user cannot access admin endpoints (returns 403)
- Admin user can access admin endpoints
- Data isolation between users
- Role persistence validation

### Refresh Token Security Tests (`test_refresh_token_security.py`)
- Refresh token replay prevention
- Token rotation after use
- Expired refresh token rejection
- Invalid hash detection
- Concurrent usage handling

### Comprehensive Test Suite (`test_security_regression_suite.py`)
- All acceptance criteria validation
- CI integration verification
- Test isolation confirmation

## References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://safetycli.readthedocs.io/)
- [OWASP ZAP Documentation](https://www.zaproxy.org/)
- [ZAP Baseline Scan](https://www.zaproxy.org/docs/docker/baseline-scan/)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides)