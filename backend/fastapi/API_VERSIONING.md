# API Versioning Strategy

**Version 1.0 (Current)**

## Overview

SoulSense API follows a URL path-based versioning strategy. All versioned endpoints are accessible under the `/api/v1` prefix.

## API Structure

- **Base URL**: `/api/v1`
- **Discovery Endpoint**: `GET /` - Returns a list of available API versions.

### Versioning Policy

- **Breaking Changes**: Any change that breaks backward compatibility will trigger a new major version (e.g., v2).
- **Non-Breaking Changes**: Additions (new fields, new endpoints) may be added to the current version without incrementing the major version.

## Client Usage

### Headers

Every API response includes the `X-API-Version` header indicating the API version used.

```http
X-API-Version: 1.0
```

### Authentication

The OAuth2 token authentication endpoint is now versioned:

- **POST** `/api/v1/auth/login`

## Migration Guide (v1)

All previous non-versioned endpoints are deprecated and removed. Clients must update their base URLs.

| Resource  | Old Path            | New Path                           |
| --------- | ------------------- | ---------------------------------- |
| Users     | `/api/users/*`      | `/api/v1/users/*`                  |
| Auth      | `/auth/login`       | `/api/v1/auth/login`               |
| Analytics | `/api/v1/analytics` | `/api/v1/analytics` (Standardized) |
| Health    | `/health`           | `/api/v1/health`                   |
| Journal   | `/api`              | `/api/v1/journal`                  |

## Future Deprecation Model

When a new version (v2) is released:

1. **Coexistence**: v1 and v2 will run in parallel for at least 6 months.
2. **Deprecation**: After 6 months, v1 will be marked deprecated. `Deprecation` and `Sunset` headers will be added to v1 responses.
3. **Sunset**: v1 will be removed after the sunset date.

## Edge Cases & Error Handling

- **404 Not Found**: Accessing removed legacy paths (e.g., `/auth/login`) will return a standard 404 error.
- **Trailing Slashes**: The API handles trailing slashes automatically (e.g., `/api/v1/users/` redirects to `/api/v1/users`).
- **Root Discovery**: If you are unsure of the version, query the root `/` to see active versions.
