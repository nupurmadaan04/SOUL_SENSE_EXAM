#!/usr/bin/env python3
"""
Demo script for macOS Keychain integration.

Demonstrates:
1. Storing secrets
2. Retrieving secrets
3. Fallback chain
4. Migration from environment
5. Platform detection
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.keychain_manager import get_keychain_manager
from app.utils.secure_config import SecureConfig, get_database_password


def print_section(title):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo_basic_operations():
    """Demonstrate basic keychain operations."""
    print_section("1. Basic Keychain Operations")
    
    manager = get_keychain_manager()
    print(f"✓ Initialized KeychainManager")
    print(f"  Backend: {manager.backend.__class__.__name__}")
    
    # Store
    print("\n→ Storing secret...")
    success = manager.store_secret("demo", "api_key", "demo_secret_123")
    print(f"  {'✓' if success else '✗'} Store operation")
    
    # Retrieve
    print("\n→ Retrieving secret...")
    secret = manager.get_secret("demo", "api_key")
    print(f"  {'✓' if secret else '✗'} Retrieved: {secret}")
    
    # Delete
    print("\n→ Deleting secret...")
    success = manager.delete_secret("demo", "api_key")
    print(f"  {'✓' if success else '✗'} Delete operation")
    
    # Verify deleted
    print("\n→ Verifying deletion...")
    secret = manager.get_secret("demo", "api_key")
    print(f"  {'✓' if secret is None else '✗'} Secret deleted: {secret is None}")


def demo_fallback_chain():
    """Demonstrate fallback chain."""
    print_section("2. Fallback Chain (Keychain → Environment → Default)")
    
    config = SecureConfig("demo")
    
    # Test 1: Not in keychain, not in env, use default
    print("→ Test 1: Missing secret with default")
    value = config.get("missing_key", "MISSING_ENV", default="fallback_value")
    print(f"  Result: {value}")
    print(f"  {'✓' if value == 'fallback_value' else '✗'} Used default value")
    
    # Test 2: Set in environment
    print("\n→ Test 2: Secret in environment variable")
    os.environ["TEST_ENV_VAR"] = "env_value_123"
    value = config.get("test_key", "TEST_ENV_VAR", default="fallback")
    print(f"  Result: {value}")
    print(f"  {'✓' if value == 'env_value_123' else '✗'} Used environment value")
    
    # Test 3: Set in keychain (overrides environment)
    print("\n→ Test 3: Secret in keychain (overrides environment)")
    config.set("test_key", "keychain_value_456")
    config.clear_cache()  # Clear cache to re-check
    value = config.get("test_key", "TEST_ENV_VAR", default="fallback")
    print(f"  Result: {value}")
    print(f"  {'✓' if value == 'keychain_value_456' else '✗'} Used keychain value")
    
    # Cleanup
    manager = get_keychain_manager()
    manager.delete_secret("demo", "test_key")
    del os.environ["TEST_ENV_VAR"]


def demo_migration():
    """Demonstrate migration from environment variables."""
    print_section("3. Migration from Environment Variables")
    
    # Set up test environment variables
    test_env = {
        "TEST_DB_PASSWORD": "db_pass_123",
        "TEST_API_KEY": "api_key_456",
        "TEST_SECRET": "secret_789"
    }
    
    print("→ Setting up test environment variables...")
    for key, value in test_env.items():
        os.environ[key] = value
        print(f"  {key} = {value}")
    
    # Migrate
    print("\n→ Migrating to secure storage...")
    manager = get_keychain_manager()
    
    migration_map = {
        "db_password": "TEST_DB_PASSWORD",
        "api_key": "TEST_API_KEY",
        "secret": "TEST_SECRET"
    }
    
    migrated = manager.migrate_from_env("demo_migration", migration_map)
    print(f"  ✓ Migrated {migrated} secrets")
    
    # Verify migration
    print("\n→ Verifying migrated secrets...")
    for account, env_var in migration_map.items():
        secret = manager.get_secret("demo_migration", account)
        expected = os.environ.get(env_var)
        match = secret == expected
        print(f"  {'✓' if match else '✗'} {account}: {secret}")
    
    # Cleanup
    print("\n→ Cleaning up...")
    for account in migration_map.keys():
        manager.delete_secret("demo_migration", account)
    for key in test_env.keys():
        del os.environ[key]
    print("  ✓ Cleanup complete")


def demo_secure_config():
    """Demonstrate SecureConfig convenience functions."""
    print_section("4. SecureConfig Convenience Functions")
    
    manager = get_keychain_manager()
    
    # Store test secrets
    print("→ Storing test secrets...")
    manager.store_secret("soulsense", "db_password", "postgres_pass_123")
    print("  ✓ Stored db_password")
    
    # Retrieve using convenience function
    print("\n→ Retrieving using convenience function...")
    password = get_database_password()
    print(f"  Result: {password}")
    print(f"  {'✓' if password == 'postgres_pass_123' else '✗'} Retrieved correctly")
    
    # Cleanup
    print("\n→ Cleaning up...")
    manager.delete_secret("soulsense", "db_password")
    print("  ✓ Cleanup complete")


def demo_platform_detection():
    """Demonstrate platform detection."""
    print_section("5. Platform Detection")
    
    import platform
    
    print(f"→ Current platform: {platform.system()}")
    
    manager = get_keychain_manager()
    backend_name = manager.backend.__class__.__name__
    
    print(f"→ Selected backend: {backend_name}")
    
    if platform.system() == "Darwin":
        expected = "MacOSKeychainBackend"
    else:
        expected = "EncryptedFileBackend"
    
    print(f"  {'✓' if backend_name == expected else '✗'} Correct backend for platform")


def demo_error_handling():
    """Demonstrate error handling."""
    print_section("6. Error Handling & Edge Cases")
    
    manager = get_keychain_manager()
    
    # Test 1: Retrieve non-existent secret
    print("→ Test 1: Retrieve non-existent secret")
    secret = manager.get_secret("demo", "nonexistent")
    print(f"  Result: {secret}")
    print(f"  {'✓' if secret is None else '✗'} Returns None for missing secret")
    
    # Test 2: Get with default
    print("\n→ Test 2: Get with default value")
    secret = manager.get_secret("demo", "nonexistent", default="fallback")
    print(f"  Result: {secret}")
    print(f"  {'✓' if secret == 'fallback' else '✗'} Returns default value")
    
    # Test 3: Delete non-existent secret
    print("\n→ Test 3: Delete non-existent secret")
    success = manager.delete_secret("demo", "nonexistent")
    print(f"  Result: {success}")
    print(f"  {'✓' if success else '✗'} Handles gracefully")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("  macOS Keychain Integration - Demo")
    print("="*60)
    
    try:
        demo_basic_operations()
        demo_fallback_chain()
        demo_migration()
        demo_secure_config()
        demo_platform_detection()
        demo_error_handling()
        
        print("\n" + "="*60)
        print("  ✓ All demos completed successfully!")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
