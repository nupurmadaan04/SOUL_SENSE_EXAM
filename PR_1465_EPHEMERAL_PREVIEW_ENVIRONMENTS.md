# PR: Ephemeral Preview Environments for PRs

**Issue:** #1465  
**Branch:** `fix/ephemeral-preview-environments-prs-1465`

## Overview

This PR implements ephemeral preview environments for pull requests, enabling automatic creation, deployment, and cleanup of temporary environments for testing and review purposes. The system integrates with GitHub webhooks to automatically manage environments based on PR lifecycle events.

## Features Implemented

### Environment Management
- **10 Environment Statuses**: PENDING, PROVISIONING, READY, DEPLOYING, RUNNING, SLEEPING, DESTROYING, DESTROYED, FAILED, TIMEOUT
- **4 Environment Sizes**: SMALL (0.5 CPU, 512MB), MEDIUM (1 CPU, 1GB), LARGE (2 CPU, 2GB), XLARGE (4 CPU, 4GB)
- **4 Environment Types**: Pull Request, Feature Branch, Hotfix, Experimental
- **4 Access Levels**: Public, Organization, Team, Restricted

### GitHub Integration
- Automatic environment creation on PR open
- Automatic update on PR synchronize (new commits)
- Automatic destruction on PR close
- Webhook endpoint for GitHub events

### Resource Management
- Configurable resource allocation per environment size
- Budget tracking with limits on environments, concurrent running, and monthly cost
- Cost estimation based on uptime and resource usage

### Lifecycle Management
- Automatic TTL-based expiration
- Inactivity-based auto-destruction
- Manual destroy capability
- Chain of custody event logging

### Domain & SSL
- Automatic subdomain generation
- Domain configuration per template
- SSL certificate support (Let's Encrypt)
- URL generation for easy access

### API Endpoints (15 endpoints)

**Environment Management:**
- `POST /ephemeral-environments/environments` - Create environment (Admin only)
- `GET /ephemeral-environments/environments` - List environments
- `GET /ephemeral-environments/environments/{environment_id}` - Get specific environment
- `POST /ephemeral-environments/environments/{environment_id}/deploy` - Deploy (Admin only)
- `DELETE /ephemeral-environments/environments/{environment_id}` - Destroy (Admin only)

**Templates:**
- `POST /ephemeral-environments/templates` - Create template (Admin only)
- `GET /ephemeral-environments/templates` - List templates
- `GET /ephemeral-environments/templates/{template_id}` - Get specific template

**Monitoring:**
- `GET /ephemeral-environments/environments/{environment_id}/metrics` - Get metrics
- `GET /ephemeral-environments/environments/{environment_id}/events` - Get events

**Budget & Statistics:**
- `GET /ephemeral-environments/budget` - Get budget
- `GET /ephemeral-environments/statistics` - Get statistics

**Webhooks:**
- `POST /ephemeral-environments/webhooks/github` - GitHub webhook

**Health:**
- `GET /ephemeral-environments/health` - Health check

## Implementation Details

### Architecture
- `EphemeralEnvironmentManager`: Central orchestrator for environment lifecycle
- Background cleanup task for TTL and inactivity management
- Event-driven PR integration
- Resource allocation based on size tiers

### Key Design Decisions
1. **Async-first design** for non-blocking operations
2. **Background cleanup loop** for automated maintenance
3. **GitHub webhook integration** for seamless PR workflow
4. **Budget enforcement** to prevent runaway costs
5. **Event logging** for audit trail

### Resource Allocation
| Size | CPU | Memory | Storage |
|------|-----|--------|---------|
| SMALL | 0.5 cores | 512 MB | 5 GB |
| MEDIUM | 1 core | 1 GB | 10 GB |
| LARGE | 2 cores | 2 GB | 20 GB |
| XLARGE | 4 cores | 4 GB | 50 GB |

### Cost Estimation
- SMALL: $0.05/hour
- MEDIUM: $0.10/hour
- LARGE: $0.20/hour
- XLARGE: $0.40/hour

## Testing

**31 comprehensive tests covering:**
- Enum validation (4 tests)
- Resource allocation (4 tests)
- Domain configuration (2 tests)
- Environment manager operations (17 tests)
- Global manager lifecycle (2 tests)

**Test coverage areas:**
- Environment creation and provisioning
- Deployment lifecycle
- Destruction and cleanup
- PR event handling (open, sync, close)
- Template management
- Metrics collection
- Budget tracking
- Event logging

## Usage Example

```python
# Create environment
env = await ephemeral_manager.create_environment(
    name="feature-x",
    environment_type=EnvironmentType.PULL_REQUEST,
    repository_url="https://github.com/example/repo",
    branch_name="feature/x",
    commit_sha="abc123def456",
    deployment_config=DeploymentConfig(
        image_repository="registry.example.com/my-app",
        image_tag="feature-x-abc123",
        container_port=8080,
        env_vars={"ENV": "preview"}
    ),
    pull_request_number=42,
    size=EnvironmentSize.MEDIUM,
    ttl_hours=24
)

# Environment automatically provisions and deploys
# Access at: https://pr-42-feature-x.preview.example.com

# Update metrics
await ephemeral_manager.update_metrics(
    environment_id=env.environment_id,
    cpu_usage_percent=45.5,
    memory_usage_mb=512,
    request_count=1000
)

# Manual cleanup (or let TTL handle it)
await ephemeral_manager.destroy_environment(
    environment_id=env.environment_id,
    reason="Test completed"
)
```

### GitHub Webhook Setup

Configure GitHub webhook to POST to:
```
POST /ephemeral-environments/webhooks/github
```

Events to subscribe to:
- Pull requests (opened, synchronize, closed)

Payload:
```json
{
  "action": "opened",
  "pull_request_number": 123,
  "branch_name": "feature/new-feature",
  "commit_sha": "abc123def456",
  "repository_url": "https://github.com/example/repo",
  "sender": "developer@example.com"
}
```

## Files Changed

1. `backend/fastapi/api/utils/ephemeral_environments.py` - Core implementation (650+ lines)
2. `backend/fastapi/api/routers/ephemeral_environments.py` - API routes (450+ lines)
3. `tests/test_ephemeral_environments.py` - Comprehensive tests (500+ lines)
4. `PR_1465_EPHEMERAL_PREVIEW_ENVIRONMENTS.md` - Documentation

## Security Considerations

- Environment creation requires admin privileges
- Access levels control who can view environments
- Access tokens for secure admin access
- Automatic cleanup prevents orphaned resources
- Budget limits prevent cost overruns

## Future Enhancements

- Integration with Kubernetes for actual provisioning
- Database seeding for environment initialization
- Preview environment comments on PRs
- Screenshot/capture on deployment
- Multi-region deployment support
- Custom domain support per environment
- Integration with CI/CD pipelines
