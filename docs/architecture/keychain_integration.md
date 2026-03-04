# Architecture: macOS Keychain Integration

## Overview
This document describes the integration of the macOS Keychain (and equivalent OS-level credential stores on other platforms) into the Soul Sense application for secure storage of local secrets.

## Goals
- Move away from hardcoded or local file-based secrets.
- Use OS-native secure storage for master encryption keys.
- Provide a cross-platform fallback for environments where secure storage is unavailable.

## Components

### 1. `KeychainService` (`app/services/keychain_service.py`)
A wrapper around the `keyring` library. It provides a simple API for:
- `set_secret(account, secret)`
- `get_secret(account)`
- `delete_secret(account)`

It uses `SERVICE_NAME = "SoulSense"` as the service identifier in the OS credential store.

### 2. `EncryptionManager` (`app/auth/crypto.py`)
Modified to use `KeychainService` for managing the "master key".
- **Activation**: Gated by the `macos_keychain_integration` feature flag.
- **Workflow**:
    1. Check if feature flag is enabled.
    2. Attempt to retrieve `master_key` from `KeychainService`.
    3. If found, use it as the Fernet key.
    4. If not found, generate a new Fernet key, store it in the Keychain, and use it.
    5. **Fallback**: If the flag is disabled or if any error occurs during Keychain access, it falls back to the legacy deterministic key derivation (PBKDF2HMAC).

## Security Model
- **Isolation**: Each secret is stored under a specific account name within the "SoulSense" service.
- **Encryption at Rest**: The OS manages the actual encryption of the secrets in its secure store.
- **Access Control**: Only the Soul Sense application (or user with appropriate permissions) can access the secrets.

## Configuration
The integration can be controlled via:
- **Feature Flag**: `macos_keychain_integration` (enabled via environment variable `SOULSENSE_FF_MACOS_KEYCHAIN_INTEGRATION=true` or `config.json`).
- **Backend Setting**: `macos_keychain_enabled` in `BaseAppSettings`.

## Observability
- **Logs**:
    - `INFO`: Successful storage/deletion of secrets.
    - `WARNING`: Failures during keychain access with fallback notifications.
    - `DEBUG`: Secret retrieval attempts.
- **Metrics**: Log messages are structured to allow aggregators to track counts of "Successfully stored secret" vs "Keychain access failed".

## Rollback Plan
If issues arise (e.g., keychain corruption, permission issues):
1. Set `SOULSENSE_FF_MACOS_KEYCHAIN_INTEGRATION=false`.
2. The application will immediately fall back to the legacy key derivation.
3. *Note*: Data encrypted with the keychain-stored key will be inaccessible until the flag is re-enabled or the key is manually moved to the legacy derivation (requires migration).
