# PR: Infrastructure Drift Detection between IaC and Runtime

**Issue:** #1463  
**Branch:** `fix/infra-drift-detection-iac-runtime-1463`

## Overview

This PR implements comprehensive infrastructure drift detection capabilities to identify and report differences between Infrastructure as Code (IaC) definitions and actual runtime state. The system supports multiple IaC providers (Terraform, CloudFormation, Pulumi, Ansible) and provides automated remediation suggestions.

## Features Implemented

### Core Drift Detection
- **8 Drift Statuses**: PENDING, SCANNING, DETECTED, NO_DRIFT, REMEDIATING, REMEDIATED, FAILED, IGNORED
- **5 Severity Levels**: CRITICAL, HIGH, MEDIUM, LOW, INFO
- **5 IaC Providers**: Terraform, CloudFormation, Pulumi, Ansible, Custom
- **9 Resource Types**: Compute, Storage, Network, Database, Security, IAM, Load Balancer, Container, Serverless

### State Management
- IaC state snapshot capture with Git metadata integration
- Runtime state scanning with cloud provider support (AWS, Azure, GCP)
- Historical state tracking and comparison

### Drift Analysis
- Deep resource attribute comparison
- Nested dictionary flattening for comprehensive comparison
- Case-insensitive string comparison
- Numeric tolerance for floating-point values
- List comparison with sorting
- Ignored attributes (timestamps, version IDs, etc.)

### Alerting & Remediation
- Automatic alert generation for critical/high drift
- Alert acknowledgment workflow
- Remediation script generation
- Manual step tracking

### API Endpoints (14 endpoints)

**IaC State Management:**
- `POST /drift-detection/iac-state` - Capture IaC state (Admin only)
- `GET /drift-detection/iac-state` - List IaC states
- `GET /drift-detection/iac-state/{state_id}` - Get specific state

**Runtime State Management:**
- `POST /drift-detection/runtime-state` - Capture runtime state (Admin only)

**Drift Detection:**
- `POST /drift-detection/detect` - Run drift detection (Admin only)
- `GET /drift-detection/scans` - List scan results
- `GET /drift-detection/scans/{scan_id}` - Get specific scan
- `GET /drift-detection/scans/{scan_id}/drifted-resources` - Get drifted resources
- `POST /drift-detection/scans/{scan_id}/resources/{resource_id}/remediate` - Generate remediation (Admin only)

**Alerting:**
- `GET /drift-detection/alerts` - List alerts
- `POST /drift-detection/alerts/{alert_id}/acknowledge` - Acknowledge alert (Admin only)

**Analytics:**
- `GET /drift-detection/statistics` - Get drift statistics
- `GET /drift-detection/health` - Health check

## Implementation Details

### Architecture
- `DriftDetectionManager`: Central orchestrator for drift detection operations
- `ResourceComparator`: Handles resource comparison logic with multiple strategies
- Dataclasses for type-safe state and result representation

### Key Design Decisions
1. **Async-first design** for non-blocking operations
2. **In-memory storage** with structured dataclasses
3. **Flexible resource type mapping** for cloud-specific types
4. **Automatic severity calculation** based on change characteristics

### Severity Calculation Logic
- **CRITICAL**: Security-related changes (password, secret, key, token)
- **HIGH**: Infrastructure-critical changes (instance_type, size, version)
- **MEDIUM**: Multiple changes (>5 attribute changes)
- **LOW**: Minor changes

## Testing

**37 comprehensive tests covering:**
- Enum validation (4 tests)
- Resource comparison logic (10 tests)
- Drift detection manager operations (13 tests)
- Global manager lifecycle (2 tests)
- Edge cases and error handling (4 tests)
- Alert management (3 tests)
- Remediation generation (2 tests)

**Test coverage areas:**
- Identical resource comparison
- Added/modified/removed attribute detection
- Nested dictionary handling
- List comparison
- Case-insensitive comparison
- Numeric tolerance
- Severity calculation
- Empty state handling
- Null value handling

## Usage Example

```python
# Capture IaC state
iac_state = await drift_manager.capture_iac_state(
    provider=IaCProvider.TERRAFORM,
    environment="production",
    state_data=terraform_state,
    git_commit="abc123",
    git_branch="main"
)

# Capture runtime state
runtime_state = await drift_manager.capture_runtime_state(
    provider="aws",
    environment="production",
    resources=aws_resources
)

# Run drift detection
result = await drift_manager.detect_drift(
    iac_state_id=iac_state.state_id,
    runtime_state_id=runtime_state.state_id,
    scan_name="Daily Drift Check"
)

# Check results
if result.status == DriftStatus.DETECTED:
    print(f"Found {len(result.drifted_resources)} drifted resources")
    print(f"Critical: {result.critical_count}, High: {result.high_count}")
```

## Files Changed

1. `backend/fastapi/api/utils/infra_drift_detection.py` - Core implementation (550+ lines)
2. `backend/fastapi/api/routers/infra_drift_detection.py` - API routes (400+ lines)
3. `tests/test_infra_drift_detection.py` - Comprehensive tests (700+ lines)
4. `PR_1463_INFRA_DRIFT_DETECTION.md` - Documentation

## Future Enhancements

- Scheduled drift detection jobs
- Integration with notification systems (Slack, PagerDuty)
- Automated remediation execution
- Drift trend analysis
- Multi-region drift correlation
- Custom policy rule engine

## Security Considerations

- All drift detection operations require admin privileges
- Sensitive attribute masking in drift reports
- Alert acknowledgment audit trail
- Remediation script validation before execution
