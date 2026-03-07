# PR: Dependency Update Batching with Risk Tiers

**Issue:** #1472  
**Branch:** `fix/dependency-update-batching-risk-tiers-1472`

## Overview

This PR implements dependency update batching with risk tier classification to intelligently manage and deploy dependency updates. The system assesses update risk, batches related updates, and provides safe rollout controls with rollback capabilities.

## Features Implemented

### Dependency Management
- **6 Update Types**: Security, Bugfix, Feature, Performance, Breaking, Deprecated
- **5 Risk Tiers**: Critical, High, Medium, Low, Info
- **9 Update Statuses**: Pending, Analyzing, Approved, Rejected, Scheduled, Deploying, Deployed, Rolled Back, Failed
- **6 Batching Strategies**: Security-only, Patch-only, Minor-only, All-except-major, All, Custom

### Risk Assessment
- CVSS score-based vulnerability assessment
- Version change analysis (major/minor/patch)
- Update type risk weighting
- Customizable risk assessment rules
- Automated risk score calculation (0-10 scale)

### Batching System
- Group updates by risk level and type
- Batch approval workflows
- Deployment scheduling
- Rollback window management (24 hours default)

### Deployment Management
- Controlled deployment with approval gates
- Deployment result tracking
- Rollback capabilities
- Deployment history

### API Endpoints (17 endpoints)

**Dependency Management:**
- `POST /dependency-updates/dependencies` - Register dependency (Admin only)
- `GET /dependency-updates/dependencies` - List dependencies
- `GET /dependency-updates/dependencies/{name}` - Get specific dependency

**Update Management:**
- `POST /dependency-updates/updates` - Register available update (Admin only)
- `GET /dependency-updates/updates` - List available updates
- `GET /dependency-updates/updates/{update_id}` - Get specific update

**Batch Management:**
- `POST /dependency-updates/batches` - Create batch (Admin only)
- `GET /dependency-updates/batches` - List batches
- `GET /dependency-updates/batches/{batch_id}` - Get specific batch
- `POST /dependency-updates/batches/{batch_id}/approve` - Approve batch (Admin only)
- `POST /dependency-updates/batches/{batch_id}/schedule` - Schedule batch (Admin only)
- `POST /dependency-updates/batches/{batch_id}/deploy` - Deploy batch (Admin only)
- `POST /dependency-updates/batches/{batch_id}/rollback` - Rollback batch (Admin only)

**Deployment Tracking:**
- `GET /dependency-updates/deployments/{deployment_id}` - Get deployment result

**Analytics:**
- `GET /dependency-updates/statistics` - Get statistics
- `GET /dependency-updates/health` - Health check

## Implementation Details

### Risk Assessment Algorithm
1. **Security Check**: CVSS >= 9.0 → CRITICAL, CVSS >= 7.0 → HIGH
2. **Update Type**: Breaking → HIGH, Security → HIGH, Feature → MEDIUM
3. **Version Change**: Major → HIGH, Minor → MEDIUM, Patch → LOW
4. **Score Calculation**: Sum of risk modifiers (capped at 10)

### Default Risk Rules
| Rule | Criteria | Risk Tier | Score Modifier |
|------|----------|-----------|----------------|
| Critical Security | CVSS >= 9.0 | CRITICAL | +10 |
| High Security | CVSS >= 7.0 | HIGH | +7 |
| Breaking Change | Major version | HIGH | +6 |
| Minor Update | Minor version | MEDIUM | +3 |
| Patch Update | Patch version | LOW | +1 |

### Batching Strategy
- Updates are grouped based on selected strategy
- Batch risk is calculated as the highest individual risk
- Total risk score is the sum of all update scores
- Approval required for HIGH/CRITICAL batches

## Testing

**25 comprehensive tests covering:**
- Enum validation (4 tests)
- Dependency management (4 tests)
- Risk assessment (3 tests)
- Update management (3 tests)
- Batch operations (6 tests)
- Deployment operations (3 tests)
- Statistics (1 test)
- Global manager lifecycle (2 tests)

## Usage Example

```python
# Register dependencies
await update_manager.register_dependency(
    name="requests",
    current_version="2.28.0",
    ecosystem="pypi"
)

# Register available updates
update1 = await update_manager.register_available_update(
    dependency_name="requests",
    new_version="2.31.0",
    update_type=UpdateType.SECURITY,
    vulnerabilities=[{"cvss_score": 8.5, "cve_id": "CVE-2023-1234"}]
)

# Risk is automatically assessed as HIGH

# Create a batch
batch = await update_manager.create_batch(
    name="Security Updates March 2026",
    description="Critical security patches",
    strategy=BatchingStrategy.SECURITY_ONLY,
    update_ids=[update1.update_id]
)

# Approve the batch
await update_manager.approve_batch(batch.batch_id, "security@example.com")

# Schedule for maintenance window
await update_manager.schedule_batch(
    batch.batch_id,
    scheduled_at=datetime(2026, 3, 15, 2, 0)  # 2 AM
)

# Deploy
result = await update_manager.deploy_batch(batch.batch_id)

if result.status == UpdateStatus.DEPLOYED:
    print(f"Successfully deployed {len(result.successful_updates)} updates")
    
# Rollback if needed (within 24 hours)
rollback_result = await update_manager.rollback_batch(batch.batch_id)
```

## Files Changed

1. `backend/fastapi/api/utils/dependency_update_batching.py` - Core implementation (550+ lines)
2. `backend/fastapi/api/routers/dependency_updates.py` - API routes (400+ lines)
3. `tests/test_dependency_update_batching.py` - Comprehensive tests (400+ lines)
4. `PR_1472_DEPENDENCY_UPDATE_BATCHING.md` - Documentation

## Security Considerations

- All batch operations require admin privileges
- Approval gates for high-risk updates
- Rollback capability within time window
- Audit trail for all deployments
- Vulnerability data is tracked per dependency

## Future Enhancements

- Integration with vulnerability databases (NVD, OSV)
- Automatic PR creation for updates
- CI/CD pipeline integration
- Dependency graph analysis
- License compliance checking
- Automated compatibility testing
