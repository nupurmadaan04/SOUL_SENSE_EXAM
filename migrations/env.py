# migrations/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, event, text
from alembic import context
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import migration checksum registry
try:
    from app.infra.migration_checksum_registry import ChecksumRegistry
    CHECKSUM_REGISTRY_AVAILABLE = True
except ImportError:
    CHECKSUM_REGISTRY_AVAILABLE = False

# Import online index policy guard
try:
    from app.infra.online_index_policy import validate_index_in_migration
    INDEX_POLICY_AVAILABLE = True
except ImportError:
    INDEX_POLICY_AVAILABLE = False

# Import backfill job registry
try:
    from app.infra.backfill_job_registry import get_backfill_registry
    BACKFILL_REGISTRY_AVAILABLE = True
except ImportError:
    BACKFILL_REGISTRY_AVAILABLE = False

# Import shadow table swap validator
try:
    from app.infra.shadow_table_swap_validator import ShadowTableSwapValidator
    SHADOW_VALIDATOR_AVAILABLE = True
except ImportError:
    SHADOW_VALIDATOR_AVAILABLE = False

# Import your models
try:
    from backend.fastapi.api.models import Base
    target_metadata = Base.metadata
except ImportError:
    # Create an empty metadata if models can't be imported
    from sqlalchemy import MetaData
    target_metadata = MetaData()

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import app config for DB URL
from backend.fastapi.api.config import get_settings_instance
settings = get_settings_instance()
DATABASE_URL = settings.database_url


def verify_migration_integrity() -> None:
    """Verify migration file integrity before running migrations."""
    if not CHECKSUM_REGISTRY_AVAILABLE:
        return

    try:
        migrations_dir = os.path.dirname(os.path.abspath(__file__))
        registry = ChecksumRegistry(migrations_dir=migrations_dir)
        result = registry.verify_all_migrations()

        if not result.passed:
            raise RuntimeError(
                f"Migration integrity check failed: "
                f"{result.modified_count} modified, {result.missing_count} missing. "
                f"Details: {result.error_message}"
            )

        if result.total_migrations > 0:
            import logging
            log = logging.getLogger(__name__)
            log.info(f"✓ Migration integrity verified: {result.valid_count}/{result.total_migrations}")
    except RuntimeError:
        raise
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.warning(f"Migration integrity check skipped: {e}")


def log_index_policy_info(database_url: str) -> None:
    """Log index policy information for the target database."""
    if not INDEX_POLICY_AVAILABLE:
        return
    
    try:
        import logging
        log = logging.getLogger(__name__)
        
        # Detect database type from URL
        if 'postgresql' in database_url or 'postgres' in database_url:
            db_type = 'postgresql'
            msg = "Index Policy: PostgreSQL - using CREATE INDEX CONCURRENTLY for online creation"
        elif 'mysql' in database_url:
            db_type = 'mysql'
            msg = "Index Policy: MySQL - using ALGORITHM=INPLACE, LOCK=NONE for online creation"
        elif 'sqlite' in database_url:
            db_type = 'sqlite'
            msg = "Index Policy: SQLite - full table lock during CREATE INDEX (schedule maintenance window)"
        else:
            return
        
        log.info(f"✓ {msg}")
    except Exception:
        pass  # Graceful degradation


def log_backfill_registry_status() -> None:
    """Log backfill job registry availability and recent jobs."""
    if not BACKFILL_REGISTRY_AVAILABLE:
        return
    
    try:
        import logging
        log = logging.getLogger(__name__)
        
        registry = get_backfill_registry()
        log.info("✓ Backfill Job Registry: Available for migration observability")
    except Exception:
        pass  # Graceful degradation


def log_shadow_table_validator_status() -> None:
    """Log shadow table swap validator availability."""
    if not SHADOW_VALIDATOR_AVAILABLE:
        return
    
    try:
        import logging
        log = logging.getLogger(__name__)
        log.info("✓ Shadow Table Swap Validator: Available for zero-downtime migrations")
    except Exception:
        pass  # Graceful degradation




def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    verify_migration_integrity()
    
    url = DATABASE_URL # Use app config
    log_index_policy_info(url)
    log_backfill_registry_status()
    log_shadow_table_validator_status()
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    verify_migration_integrity()
    
    # Logic to support both Tests (overridden config) and App (app.config)
    # Check if we are running in a test environment
    # The test runner sets the URL in the config object.
    # Default Alembic command uses the .ini file value.
    
    ini_url = config.get_main_option("sqlalchemy.url")
    
    # If the URL in config is different from the hardcoded default in .ini, 
    # it means it was overridden (e.g. by Test), so we trust it.
    # Otherwise, we prefer the App's DATABASE_URL source of truth.
    
    # Hardcoded check for the default value in alembic.ini
    # This is safer than checking for 'pytest' in modules
    DEFAULT_INI_URL = "sqlite:///data/soulsense.db"
    
    if ini_url != DEFAULT_INI_URL:
        # It's an override (Test)
        target_url = ini_url
    else:
        # It's the default, so use App Config
        target_url = DATABASE_URL
    
    # Log index policy and backfill registry information
    log_index_policy_info(target_url)
    log_backfill_registry_status()
    log_shadow_table_validator_status()
        
    from sqlalchemy import create_engine
    connect_args = {}
    if 'sqlite' in target_url:
        connect_args = {'timeout': 60}
        
    connectable = create_engine(target_url, connect_args=connect_args)

    @event.listens_for(connectable, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # Using DELETE mode instead of WAL for better compatibility with virtual/network drives
        cursor.execute("PRAGMA journal_mode=DELETE")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.close()

    with connectable.connect() as connection:
        # PR 1 Fix: Disable foreign keys for SQLite batch migrations
        from sqlalchemy import text
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            render_as_batch=True  # Fix for SQLite ALTER limitation
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()