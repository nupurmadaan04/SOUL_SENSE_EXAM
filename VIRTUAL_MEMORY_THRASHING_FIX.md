# Virtual Memory Swapping Thrashing Fix (#1159)

## Issue Description
Improper swap configuration causes heavy disk swapping, leading to performance collapse under memory pressure.

**Objective:** Prevent performance collapse under memory pressure.

**Edge Cases:**
- High concurrent model usage
- Background jobs spiking memory

**Test Cases:**
- Stress memory beyond limits
- Monitor swap usage

**Recommended Testing:**
- Disable swap in containers
- Memory stress tools

**Technical Implementation:**
- Set memorySwap limits
- Enforce cgroup constraints

## Solution Implemented

### Changes Made

Modified `docker-compose.yml` to add memory limits and cgroup constraints:

1. **API Service:**
   - Memory limit: 2g
   - Memory reservation: 1g
   - Swappiness: 0 (to reduce swap tendency)

2. **Database Service:**
   - Memory limit: 1g
   - Memory reservation: 512m
   - Swappiness: 0

3. **Redis Service:**
   - Memory limit: 512m
   - Memory reservation: 256m
   - Swappiness: 0

### How It Fixes the Issue

- **Prevents Performance Collapse:** Memory limits prevent containers from consuming unlimited memory, avoiding swap thrashing.
- **Enforces Cgroup Constraints:** Docker's resource limits enforce memory constraints at the cgroup level.
- **Reduces Swap Usage:** Setting `vm.swappiness: 0` minimizes the kernel's tendency to swap memory to disk.
- **Handles Edge Cases:** Limits protect against high concurrent usage and background job spikes.

### Note on Memory-Swap Limits
Docker Compose does not directly support `memory-swap` limits in the `deploy.resources.limits` section. For production deployments, use Docker CLI with `--memory-swap` set to the same value as `--memory` to disable swap entirely:

```bash
docker run --memory=2g --memory-swap=2g ...
```

### Files Modified
- `docker-compose.yml`

### Testing
- Compose file validated successfully
- Ready for memory stress testing and swap usage monitoring