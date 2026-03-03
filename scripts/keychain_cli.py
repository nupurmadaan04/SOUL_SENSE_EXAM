#!/usr/bin/env python3
"""
CLI tool for managing secrets in macOS Keychain or encrypted storage.

Usage:
    python scripts/keychain_cli.py store <service> <account> <secret>
    python scripts/keychain_cli.py get <service> <account>
    python scripts/keychain_cli.py delete <service> <account>
    python scripts/keychain_cli.py migrate
"""

import sys
import os
import argparse
import getpass
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.keychain_manager import get_keychain_manager


def store_secret(args):
    """Store a secret."""
    manager = get_keychain_manager()
    
    # Get secret from stdin if not provided
    secret = args.secret
    if not secret:
        secret = getpass.getpass(f"Enter secret for {args.service}:{args.account}: ")
    
    if manager.store_secret(args.service, args.account, secret):
        print(f"✓ Stored secret for {args.service}:{args.account}")
        return 0
    else:
        print(f"✗ Failed to store secret", file=sys.stderr)
        return 1


def get_secret(args):
    """Retrieve a secret."""
    manager = get_keychain_manager()
    
    secret = manager.get_secret(args.service, args.account)
    if secret:
        if args.quiet:
            print(secret)
        else:
            print(f"Secret for {args.service}:{args.account}:")
            print(secret)
        return 0
    else:
        print(f"✗ Secret not found for {args.service}:{args.account}", file=sys.stderr)
        return 1


def delete_secret(args):
    """Delete a secret."""
    manager = get_keychain_manager()
    
    if not args.yes:
        confirm = input(f"Delete secret for {args.service}:{args.account}? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled")
            return 0
    
    if manager.delete_secret(args.service, args.account):
        print(f"✓ Deleted secret for {args.service}:{args.account}")
        return 0
    else:
        print(f"✗ Failed to delete secret", file=sys.stderr)
        return 1


def migrate_secrets(args):
    """Migrate secrets from environment variables."""
    manager = get_keychain_manager()
    
    # Default migration map for SoulSense
    env_vars = {
        'db_password': 'DATABASE_PASSWORD',
        'jwt_secret': 'JWT_SECRET_KEY',
        'encryption_key': 'ENCRYPTION_KEY',
        'redis_password': 'REDIS_PASSWORD',
        'smtp_password': 'SMTP_PASSWORD',
    }
    
    print(f"Migrating secrets from environment to secure storage...")
    migrated = manager.migrate_from_env("soulsense", env_vars)
    
    print(f"✓ Migrated {migrated} secrets")
    
    if migrated > 0:
        print("\nRecommendation: Remove these environment variables from .env file:")
        for account, env_var in env_vars.items():
            if os.getenv(env_var):
                print(f"  - {env_var}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage secrets in macOS Keychain or encrypted storage"
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Store command
    store_parser = subparsers.add_parser('store', help='Store a secret')
    store_parser.add_argument('service', help='Service name (e.g., soulsense)')
    store_parser.add_argument('account', help='Account/key name (e.g., db_password)')
    store_parser.add_argument('secret', nargs='?', help='Secret value (prompted if not provided)')
    store_parser.set_defaults(func=store_secret)
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Retrieve a secret')
    get_parser.add_argument('service', help='Service name')
    get_parser.add_argument('account', help='Account/key name')
    get_parser.add_argument('-q', '--quiet', action='store_true', help='Output only the secret value')
    get_parser.set_defaults(func=get_secret)
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a secret')
    delete_parser.add_argument('service', help='Service name')
    delete_parser.add_argument('account', help='Account/key name')
    delete_parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')
    delete_parser.set_defaults(func=delete_secret)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate secrets from environment variables')
    migrate_parser.set_defaults(func=migrate_secrets)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
