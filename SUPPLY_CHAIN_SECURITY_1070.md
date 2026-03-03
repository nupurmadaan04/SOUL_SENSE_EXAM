# Supply Chain Security Hardening #1070

## Overview

This document describes the comprehensive supply chain security hardening implementation for the Soul Sense Exam platform. The implementation addresses Issue #1070 and provides robust protection against supply chain attacks, compromised dependencies, and transitive vulnerability exploitation.

## Objectives

- **Dependency Pinning**: All dependencies are pinned to exact versions
- **Hash Verification**: Cryptographic hash verification for all packages
- **Automated Alerts**: Real-time vulnerability monitoring via Dependabot
- **CI/CD Integration**: Automated security gates in the pipeline

## Architecture

### Components

1. **Pinned Requirements** (`requirements-pinned.txt`)
   - Exact version pinning with `==`
   - SHA256 hash verification
   - Protection against package tampering

2. **Dependabot Configuration** (`.github/dependabot.yml`)
   - Automated vulnerability alerts
   - Daily dependency scanning
   - Automatic PR creation for security updates

3. **Supply Chain Security Script** (`scripts/supply_chain_security.py`)
   - Dependency parsing and validation
   - Hash verification
   - Security gate for CI/CD
   - Comprehensive reporting

4. **GitHub Actions Workflow** (`.github/workflows/supply-chain-security.yml`)
   - Automated security scanning
   - Dependency review
   - SBOM generation
   - Security gate enforcement

## Implementation Details

### Dependency Pinning and Hash Verification

#### File Structure

```
requirements.txt          # High-level dependencies
requirements-pinned.txt   # Pinned with hashes (auto-generated)
requirements-security.txt # Security-specific tools
```

#### Example Pinned Dependency

```
package==1.0.0 \
    --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f \
    --hash=sha256:b8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
```

### Automated Alert Configuration

#### Dependabot Settings

- **Scan Frequency**: Daily at 09:00 UTC
- **Vulnerability Alerts**: Enabled for all ecosystems
- **Auto-PRs**: Limited to 10 open PRs
- **Labels**: `dependencies`, `security`, `ECWoC26`

#### Supported Ecosystems

- Python (pip) - Root and backend directories
- GitHub Actions
- npm (frontend)

### Security Gate Workflow

The security gate runs on:
- Every push to `main` or `feature/*` branches
- Every pull request to `main`
- Daily scheduled runs (cron)
- Manual trigger via workflow_dispatch

#### Gate Steps

1. **Dependency Hash Verification**
   - Validates all dependencies in `requirements-pinned.txt`
   - Checks hash coverage percentage
   - Fails if any dependency lacks hash

2. **Vulnerability Scan**
   - pip-audit scan
   - Safety vulnerability check
   - Bandit security linting

3. **SBOM Generation**
   - CycloneDX format
   - Artifact upload with 365-day retention
   - Dependency graph submission

4. **Dependency Review** (PR only)
   - License compliance check
   - New dependency analysis
   - Inline PR comments

## Usage

### Running Security Checks Locally

```bash
# Run full security check
python scripts/supply_chain_security.py --check

# Run as CI gate (fails on issues)
python scripts/supply_chain_security.py --gate --fail-on-issues

# Check specific requirements file
python scripts/supply_chain_security.py --requirements requirements-pinned.txt

# Generate security report
python scripts/supply_chain_security.py --report security-report.json
```

### Installing with Hash Verification

```bash
# Install with strict hash verification
pip install --require-hashes -r requirements-pinned.txt

# This will fail if:
# - Any package hash doesn't match
# - Any package lacks a hash
# - Package content has been tampered with
```

### Updating Pinned Requirements

```bash
# Install pip-tools
pip install pip-tools

# Generate pinned requirements with hashes
pip-compile --generate-hashes requirements.txt -o requirements-pinned.txt

# Verify the generated file
python scripts/supply_chain_security.py --requirements requirements-pinned.txt
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPPLY_CHAIN_GATE_ENABLED` | `true` | Enable/disable security gate |
| `HASH_VERIFICATION_ENABLED` | `true` | Enable hash verification |
| `VULNERABILITY_THRESHOLD` | `high` | Minimum severity to fail build |

### Severity Thresholds

- `critical`: Only critical vulnerabilities block builds
- `high`: High and critical vulnerabilities block builds (default)
- `medium`: Medium, high, and critical block builds
- `low`: All vulnerabilities except info block builds
- `info`: All vulnerabilities block builds

## Security Features

### Hash Verification Modes

1. **Strict Mode** (CI/CD)
   ```bash
   pip install --require-hashes -r requirements-pinned.txt
   ```
   - All packages must have hashes
   - Hash must match downloaded package
   - No network fallback

2. **Audit Mode** (Local development)
   ```bash
   python scripts/supply_chain_security.py --check
   ```
   - Validates hash coverage
   - Warns about missing hashes
   - Doesn't block installation

### Protection Against Supply Chain Attacks

| Attack Vector | Mitigation |
|---------------|------------|
| Compromised upstream packages | SHA256 hash verification |
| Typosquatting | Pinned versions in vetted requirements |
| Dependency confusion | Explicit index configuration |
| Transitive vulnerabilities | Dependabot alerts + Safety scans |
| Malicious version bumps | Review required for all updates |

## Testing

### Running Tests

```bash
# Run all supply chain security tests
pytest tests/test_supply_chain_security_1070.py -v

# Run specific test class
pytest tests/test_supply_chain_security_1070.py::TestSupplyChainSecurityChecker -v

# Run with coverage
pytest tests/test_supply_chain_security_1070.py --cov=scripts.supply_chain_security
```

### Test Coverage

- ✅ Dependency parsing with various formats
- ✅ Hash validation (valid, invalid, missing)
- ✅ Requirements file structure validation
- ✅ Transitive dependency checking
- ✅ Security report generation
- ✅ CLI argument parsing
- ✅ Edge cases (empty files, malformed entries)
- ✅ Integration workflows

## Monitoring and Alerting

### Metrics Collected

- Hash coverage percentage
- Vulnerability detection count by severity
- Dependency update frequency
- Security gate pass/fail rate

### Alert Channels

- GitHub Security tab
- Dependabot alerts
- Workflow notifications
- Slack/Email (via GitHub Actions)

### Dashboard

Access the security dashboard at:
- GitHub → Security → Dependabot alerts
- GitHub → Security → Code scanning alerts
- GitHub → Actions → Supply Chain Security workflow

## Troubleshooting

### Common Issues

#### Hash Verification Failed
```
ERROR: Hashes don't match for package==1.0.0
```
**Solution**: 
1. Verify the package hasn't been tampered with
2. Update the hash if it's a legitimate new release
3. Run `pip-compile --generate-hashes` to refresh

#### Missing Hash for Dependency
```
ERROR: Dependency 'package==1.0.0' is missing SHA256 hash
```
**Solution**:
1. Add the hash using `hashin package==1.0.0`
2. Or regenerate with `pip-compile --generate-hashes`

#### Vulnerability Gate Blocking Build
```
❌ Security gate FAILED
```
**Solution**:
1. Check the vulnerability report in workflow artifacts
2. Update the vulnerable dependency
3. Or create a temporary exception (with justification)

### Debug Commands

```bash
# Debug requirements parsing
python scripts/supply_chain_security.py --check --project-root .

# List all installed packages with versions
pip list --format=json

# Check specific package hash
pip hash package-1.0.0-py3-none-any.whl

# Verify installed packages against requirements
pip check
```

## Compliance

### Standards Compliance

- **NTIA SBOM**: CycloneDX format meets requirements
- **OWASP SCVS**: Software Component Verification Standard
- **SLSA**: Supply-chain Levels for Software Artifacts (Level 1)

### Audit Trail

All supply chain security events are logged:
- Dependency updates
- Hash verification failures
- Vulnerability discoveries
- Gate bypass events

## Future Enhancements

### Planned Features

- **SLSA Level 2**: Build provenance attestation
- **Sigstore Integration**: Cosign for package signing
- **SLSA Provenance**: GitHub Actions provenance generation
- **Container Scanning**: Docker image vulnerability scanning
- **License Compliance**: Automated license compatibility checking

### Integration Roadmap

- [ ] Trivy integration for container scanning
- [ ] Snyk alternative vulnerability database
- [ ] Automated dependency update PRs
- [ ] Security scorecards integration

## Migration Guide

### From Unpinned Dependencies

1. **Install pip-tools**
   ```bash
   pip install pip-tools
   ```

2. **Create requirements.txt**
   ```
   fastapi>=0.100.0
   uvicorn>=0.23.0
   ```

3. **Generate Pinned Requirements**
   ```bash
   pip-compile --generate-hashes requirements.txt -o requirements-pinned.txt
   ```

4. **Verify Installation**
   ```bash
   pip install --require-hashes -r requirements-pinned.txt
   ```

5. **Update CI/CD**
   - Add `supply-chain-security.yml` workflow
   - Enable Dependabot in repository settings

### Rollback Plan

If issues arise:

1. **Disable Hash Verification**
   ```bash
   # Use regular requirements.txt instead
   pip install -r requirements.txt
   ```

2. **Disable Security Gate**
   Set `SUPPLY_CHAIN_GATE_ENABLED=false` in workflow

3. **Revert to Previous Versions**
   ```bash
   git checkout HEAD~1 -- requirements-pinned.txt
   ```

## Support and Maintenance

### Maintenance Tasks

- **Weekly**: Review Dependabot alerts
- **Monthly**: Update pinned requirements
- **Quarterly**: Review and update severity thresholds
- **Annually**: Full supply chain security audit

### Team Responsibilities

| Role | Responsibilities |
|------|------------------|
| Security Team | Review exceptions, update thresholds |
| DevOps | Maintain CI/CD workflows |
| Developers | Update dependencies, fix vulnerabilities |
| Maintainers | Approve security PRs |

## References

- [pip Hash-Checking Mode](https://pip.pypa.io/en/stable/cli/pip_install/#hash-checking-mode)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [CycloneDX Specification](https://cyclonedx.org/specification/overview/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)
- [SLSA Framework](https://slsa.dev/)

## Acceptance Criteria Verification

- ✅ **Dependencies pinned**: All packages use `==` version pinning
- ✅ **Vulnerabilities monitored**: Dependabot enabled for all ecosystems
- ✅ **Alerts enabled**: Automated PRs and notifications configured
- ✅ **Hash verification**: SHA256 hashes required for all packages
- ✅ **CI/CD integration**: Security gate in GitHub Actions
- ✅ **SBOM generation**: CycloneDX format with artifact retention
- ✅ **Test coverage**: Comprehensive test suite implemented
- ✅ **Documentation**: Complete implementation guide provided

---

## Appendix: Quick Reference

### One-Line Commands

```bash
# Verify all security checks pass
python scripts/supply_chain_security.py --gate

# Update all pinned dependencies
pip-compile --generate-hashes --upgrade requirements.txt -o requirements-pinned.txt

# Check for vulnerable packages
safety check -r requirements-pinned.txt

# Generate SBOM
cyclonedx-py -r -o sbom.json
```

### File Checklist

- [ ] `requirements-pinned.txt` exists with hashes
- [ ] `.github/dependabot.yml` configured
- [ ] `.github/workflows/supply-chain-security.yml` active
- [ ] `scripts/supply_chain_security.py` executable
- [ ] `tests/test_supply_chain_security_1070.py` passing

### Contact

For questions or issues related to supply chain security:
- Create an issue: [GitHub Issues](https://github.com/nupurmadaan04/SOUL_SENSE_EXAM/issues)
- Security issues: Use responsible disclosure via GitHub Security Advisories
