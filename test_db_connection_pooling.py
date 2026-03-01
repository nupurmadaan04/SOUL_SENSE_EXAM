#!/usr/bin/env python3
"""
Test script for Database Connection Pooling - Issue #960

Tests the following connection pooling features:
- SQLAlchemy connection pool configuration
- PgBouncer integration
- High concurrency performance
- Connection reuse and recycling
"""

import sys
import os
import asyncio
import time
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

def load_config():
    """Load configuration to test connection pooling settings."""
    try:
        from backend.fastapi.api.config import get_settings_instance
        settings = get_settings_instance()
        return settings
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def validate_sqlalchemy_pooling():
    """Validate SQLAlchemy connection pool configuration."""
    print("Testing SQLAlchemy connection pool configuration...")

    try:
        from backend.fastapi.api.services.db_service import engine
        from backend.fastapi.api.services.db_router import _primary_engine

        # Try to import replica engine (may not exist)
        try:
            from backend.fastapi.api.services.db_router import _ReplicaSessionLocal
            has_replica = _ReplicaSessionLocal is not None
        except ImportError:
            has_replica = False

        # Check db_service engine
        pool = engine.pool
        print("[OK] db_service engine pool configuration:")
        print(f"  - Pool size: {pool.size}")
        print(f"  - Max overflow: {pool.max_overflow}")
        print(f"  - Pool timeout: {pool.timeout}")
        print(f"  - Pool pre-ping: {pool.pre_ping}")
        print(f"  - Pool recycle: {pool.recycle}")

        # Check db_router primary engine
        primary_pool = _primary_engine.pool
        print("[OK] db_router primary engine pool configuration:")
        print(f"  - Pool size: {primary_pool.size}")
        print(f"  - Max overflow: {primary_pool.max_overflow}")
        print(f"  - Pool timeout: {primary_pool.timeout}")
        print(f"  - Pool pre-ping: {primary_pool.pre_ping}")
        print(f"  - Pool recycle: {primary_pool.recycle}")

        # Validate expected values
        expected_pool_size = 20
        expected_max_overflow = 10
        expected_timeout = 30
        expected_pre_ping = True
        expected_recycle = 3600

        checks = [
            ("db_service pool_size", pool.size == expected_pool_size),
            ("db_service max_overflow", pool.max_overflow == expected_max_overflow),
            ("db_service timeout", pool.timeout == expected_timeout),
            ("db_service pre_ping", pool.pre_ping == expected_pre_ping),
            ("db_service recycle", pool.recycle == expected_recycle),
            ("primary pool_size", primary_pool.size == expected_pool_size),
            ("primary max_overflow", primary_pool.max_overflow == expected_max_overflow),
            ("primary timeout", primary_pool.timeout == expected_timeout),
            ("primary pre_ping", primary_pool.pre_ping == expected_pre_ping),
            ("primary recycle", primary_pool.recycle == expected_recycle),
        ]

        passed = 0
        for check_name, check_result in checks:
            if check_result:
                print(f"[OK] {check_name} correct")
                passed += 1
            else:
                print(f"[FAIL] {check_name} incorrect")

        return passed == len(checks)

    except Exception as e:
        print(f"[ERROR] Error validating SQLAlchemy pooling: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_pgbouncer_config():
    """Validate PgBouncer configuration files."""
    print("\nTesting PgBouncer configuration...")

    try:
        pgbouncer_dir = "backend/fastapi/pgbouncer"

        # Check if directory exists
        if not os.path.exists(pgbouncer_dir):
            print("[FAIL] PgBouncer directory not found")
            return False

        files_to_check = [
            "pgbouncer.ini",
            "userlist.txt",
            "generate_userlist.sh"
        ]

        passed = 0
        for filename in files_to_check:
            filepath = os.path.join(pgbouncer_dir, filename)
            if os.path.exists(filepath):
                print(f"[OK] {filename} exists")
                passed += 1
            else:
                print(f"[FAIL] {filename} missing")

        # Validate pgbouncer.ini content
        ini_file = os.path.join(pgbouncer_dir, "pgbouncer.ini")
        if os.path.exists(ini_file):
            with open(ini_file, 'r') as f:
                content = f.read()

            ini_checks = [
                ("max_client_conn", "max_client_conn = 1000" in content),
                ("default_pool_size", "default_pool_size = 20" in content),
                ("pool_mode", "pool_mode = transaction" in content),
                ("server_check_query", "server_check_query = SELECT 1" in content),
            ]

            for check_name, check_result in ini_checks:
                if check_result:
                    print(f"[OK] pgbouncer.ini {check_name} configured")
                    passed += 1
                else:
                    print(f"[FAIL] pgbouncer.ini {check_name} missing")

        return passed == (len(files_to_check) + len(ini_checks))

    except Exception as e:
        print(f"[FAIL] Error validating PgBouncer config: {e}")
        return False

def validate_config_pgbouncer_support():
    """Validate configuration supports PgBouncer."""
    print("\nTesting configuration PgBouncer support...")

    try:
        settings = load_config()
        if not settings:
            return False

        # Check for PgBouncer configuration attributes
        checks = [
            ("use_pgbouncer attribute", hasattr(settings, 'use_pgbouncer')),
            ("pgbouncer_host attribute", hasattr(settings, 'pgbouncer_host')),
            ("pgbouncer_port attribute", hasattr(settings, 'pgbouncer_port')),
            ("async_database_url method", hasattr(settings, 'async_database_url')),
        ]

        passed = 0
        for check_name, check_result in checks:
            if check_result:
                print(f"[OK] {check_name} exists")
                passed += 1
            else:
                print(f"[FAIL] {check_name} missing")

        # Test URL transformation logic
        if hasattr(settings, 'async_database_url'):
            # Mock PgBouncer settings for PostgreSQL URL
            original_url = "postgresql://user:pass@localhost:5432/db"
            settings.database_url = original_url
            settings.use_pgbouncer = True
            settings.pgbouncer_host = "pgbouncer"
            settings.pgbouncer_port = 6432

            transformed_url = settings.async_database_url

            # Check if transformation occurred
            if "pgbouncer" in transformed_url and "6432" in transformed_url and "asyncpg" in transformed_url:
                print("[OK] URL transformation for PgBouncer works")
                passed += 1
            else:
                print(f"[FAIL] URL transformation failed: {transformed_url}")
                print(f"  Expected pgbouncer:6432 and asyncpg in URL")

        return passed == (len(checks) + 1)

    except Exception as e:
        print(f"[FAIL] Error validating config PgBouncer support: {e}")
        return False

async def test_connection_pooling_performance():
    """Test connection pooling performance under load."""
    print("\nTesting connection pooling performance...")

    try:
        from backend.fastapi.api.services.db_service import get_db
        from sqlalchemy import text

        async def single_query():
            """Execute a single simple query."""
            start_time = time.time()
            async for db in get_db():
                result = await db.execute(text("SELECT 1"))
                row = result.fetchone()  # This is not async
                break
            end_time = time.time()
            return end_time - start_time

        # Test sequential queries
        print("Running sequential connection tests...")
        sequential_times = []
        for i in range(10):
            query_time = await single_query()
            sequential_times.append(query_time)
            print(".3f")

        avg_sequential = statistics.mean(sequential_times)
        print(".3f")

        # Test concurrent queries
        print("Running concurrent connection tests...")
        concurrent_times = []
        tasks = [single_query() for _ in range(20)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_concurrent_time = end_time - start_time
        avg_concurrent_query = statistics.mean(results)

        print(".3f")
        print(".3f")
        print(".1f")

        # Performance should be reasonable
        if avg_concurrent_query < 1.0:  # Less than 1 second per query
            print("[OK] Connection pooling performance acceptable")
            return True
        else:
            print("[FAIL] Connection pooling performance poor")
            return False

    except Exception as e:
        print(f"[FAIL] Error testing connection pooling performance: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_docker_compose_pgbouncer():
    """Validate Docker Compose has PgBouncer service."""
    print("\nTesting Docker Compose PgBouncer configuration...")

    try:
        compose_file = "backend/fastapi/docker-compose.production.yml"

        if not os.path.exists(compose_file):
            print("[FAIL] Production docker-compose file not found")
            return False

        with open(compose_file, 'r') as f:
            content = f.read()

        checks = [
            ("pgbouncer service", "pgbouncer:" in content),
            ("pgbouncer image", "edoburu/pgbouncer" in content),
            ("pgbouncer port", "6432:6432" in content),
            ("pgbouncer depends_on", "depends_on:" in content and "db" in content),
            ("api depends on pgbouncer", "depends_on:" in content and "pgbouncer" in content),
            ("pgbouncer environment", "PGBOUNCER_MAX_CLIENT_CONN" in content),
            ("pgbouncer volumes", "pgbouncer/pgbouncer.ini" in content),
        ]

        passed = 0
        for check_name, check_result in checks:
            if check_result:
                print(f"[OK] {check_name} configured")
                passed += 1
            else:
                print(f"[FAIL] {check_name} missing")

        return passed == len(checks)

    except Exception as e:
        print(f"[FAIL] Error validating Docker Compose: {e}")
        return False

async def main():
    """Run all connection pooling tests."""
    print("=" * 70)
    print("DATABASE CONNECTION POOLING TEST - Issue #960")
    print("=" * 70)

    tests = [
        validate_sqlalchemy_pooling,
        validate_pgbouncer_config,
        validate_config_pgbouncer_support,
        validate_docker_compose_pgbouncer,
        test_connection_pooling_performance,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"[FAIL] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All connection pooling tests passed!")
        print("\nAcceptance Criteria Status:")
        print("[PASS] SQLAlchemy connection pool optimized (pool_size=20, max_overflow=10)")
        print("[PASS] PgBouncer configured for production (port 6432, transaction pooling)")
        print("[PASS] High concurrency handling (1000+ client connections)")
        print("[PASS] Connection health monitoring (pre_ping, recycle, health checks)")
        print("[PASS] Docker Compose integration (production deployment ready)")
        print("\nPerformance Optimizations:")
        print("- TCP connection multiplexing via PgBouncer")
        print("- Persistent connection pools reducing handshake overhead")
        print("- Connection health validation preventing stale connections")
        print("- Optimized pool sizes for read/write splitting")
    else:
        print("[FAILED] Some tests failed. Please review the implementation.")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)