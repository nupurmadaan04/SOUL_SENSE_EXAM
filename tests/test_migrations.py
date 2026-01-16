
import pytest
import os
import tempfile
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

@pytest.fixture
def temp_db_url():
    """Create a temporary database file for migration testing"""
    # We use a file-based DB because Alembic might reconnect, wiping :memory:
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Fix for f-string backslash syntax error in Python < 3.12
    clean_path = path.replace('\\', '/')
    url = f"sqlite:///{clean_path}"
    yield url

    from sqlalchemy import create_engine
    engine = create_engine(url)
    engine.dispose()   # ✅ RELEASE FILE HANDLE

    if os.path.exists(path):
       os.remove(path)


def test_migrations_apply_successfully(temp_db_url):
    """
    Verifies that 'alembic upgrade head' runs without error against a fresh DB.
    This ensures the migration chain is valid and matches the models.
    """
    # 1. Configure Alembic programmatically
    # Point to the real alembic.ini in the project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_ini_path = os.path.join(root_dir, "alembic.ini")
    
    alembic_cfg = Config(alembic_ini_path)
    
    # Override the DB URL to use our clean temp DB
    alembic_cfg.set_main_option("sqlalchemy.url", temp_db_url)
    
    # Ensure script location is absolute or relative to root
    alembic_cfg.set_main_option("script_location", os.path.join(root_dir, "migrations"))

    # 2. Run Upgrade Head
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        pytest.fail(f"Alembic upgrade failed: {e}")

    # 3. Verify tables exist (sanity check)
    engine = create_engine(temp_db_url)
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Check for expected tables (from models.py)
        # Note: Question model maps to 'question_bank' table
        expected_tables = ["users", "question_bank", "scores", "alembic_version"]
        for table in expected_tables:
            assert table in tables, f"Table '{table}' missing after migration"
    finally:
        engine.dispose()
