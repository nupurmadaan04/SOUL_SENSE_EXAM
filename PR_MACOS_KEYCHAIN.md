# Pull Request: macOS Keychain Integration for Local Secrets

## Description
This initiative addresses a structural quality gap within the OS domain. It reduces regression risk and strengthens engineering guardrails by moving local secrets (master encryption keys) from plain-text or local file storage into secure, OS-managed credential stores.

## Objective
Deliver measurable improvement in OS quality with defined ownership, observability, rollout strategy, and verification mechanisms.

## Technical Implementation
- **Keychain Service**: Created `app/services/keychain_service.py` as a cross-platform wrapper for OS-level credential storage.
- **Crypto Integration**: Updated `app/auth/crypto.py` to prefer the Keychain for the master key when the feature flag is enabled.
- **Feature Flag**: Added `macos_keychain_integration` flag to `app/feature_flags.py` for safe rollout.
- **Observability**: Added structured logging and a diagnostic script (`scripts/keychain_diagnostics.py`) to track metrics and signals.

## Verification Results
- **Automated Tests**: 9/9 tests passed (Unit & Integration).
- **Environment Support**: Verified on Windows (using Credential Manager) and architected for macOS (using Keychain).
- **Fallback**: Verified graceful fallback to legacy derivation when the feature is disabled or unavailable.

## Screenshots
### Test Output
- 9 passed in 0.43s.

### Metrics Dashboard
- Success/Failure tracking implemented in diagnostics.

### API Responses / Logs
- `INFO: Using master key from OS keychain.`
- `SUCCESS: 'SoulSense' secret found in Windows Credential Manager.`
