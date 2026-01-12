# migrations/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your models
try:
    from app.models import Base
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
from app.config import DATABASE_URL

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = DATABASE_URL # Use app config
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
    DEFAULT_INI_URL = "sqlite:///db/soulsense.db"
    
    if ini_url != DEFAULT_INI_URL:
        # It's an override (Test)
        target_url = ini_url
    else:
        # It's the default, so use App Config
        target_url = DATABASE_URL
        
    from sqlalchemy import create_engine
    connectable = create_engine(target_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()