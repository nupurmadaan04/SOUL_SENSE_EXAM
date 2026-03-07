"""
Comprehensive test suite for Shadow Table Swap Validator.

Tests cover:
- Schema compatibility validation
- Data integrity validation
- Foreign key safety
- Edge cases: empty tables, NULLs, large datasets
- Pre/post swap validation
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, text
from sqlalchemy.orm import declarative_base, relationship
from app.infra.shadow_table_swap_validator import (
    ShadowTableSwapValidator,
    ColumnSchema,
    TableSchemaComparison,
    DataSyncMetrics,
    SwapValidationResult,
)

Base = declarative_base()


class User(Base):
    """Test user model."""
    __tablename__ = "test_users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255))


class UserNew(Base):
    """Shadow table with same schema."""
    __tablename__ = "test_users_shadow"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255))


class UserModified(Base):
    """Shadow table with modified schema."""
    __tablename__ = "test_users_modified"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    phone = Column(String(20))  # Extra column


@pytest.fixture
def sqlite_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def validator(sqlite_engine):
    """Create validator instance."""
    return ShadowTableSwapValidator(sqlite_engine)


@pytest.fixture
def populated_engine():
    """Create engine with test data."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO test_users (id, email, name) VALUES (1, 'alice@test.com', 'Alice')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO test_users (id, email, name) VALUES (2, 'bob@test.com', 'Bob')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO test_users_shadow (id, email, name) VALUES (1, 'alice@test.com', 'Alice')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO test_users_shadow (id, email, name) VALUES (2, 'bob@test.com', 'Bob')"
            )
        )
        conn.commit()

    yield engine
    engine.dispose()


# ============================================================================
# SCHEMA VALIDATION TESTS
# ============================================================================


def test_schema_comparison_identical_tables(sqlite_engine):
    """Test schema comparison with identical tables."""
    validator = ShadowTableSwapValidator(sqlite_engine)

    result = validator.compare_schemas("test_users", "test_users_shadow")

    assert result.passed is True
    assert len(result.missing_columns) == 0
    assert len(result.extra_columns) == 0
    assert len(result.type_mismatches) == 0


def test_schema_comparison_extra_column(sqlite_engine):
    """Test schema comparison when shadow has extra column."""
    engine = sqlite_engine
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE test_extra (id INTEGER PRIMARY KEY, email TEXT NOT NULL, extra_col TEXT)"
            )
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.compare_schemas("test_users", "test_extra")

    assert result.passed is False
    assert "extra_col" in result.extra_columns


def test_schema_comparison_missing_column(sqlite_engine):
    """Test schema comparison when shadow is missing column."""
    engine = sqlite_engine
    with engine.connect() as conn:
        conn.execute(
            text("CREATE TABLE test_missing (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.compare_schemas("test_users", "test_missing")

    assert result.passed is False
    assert "name" in result.missing_columns


def test_schema_comparison_type_mismatch(sqlite_engine):
    """Test schema comparison with type mismatch."""
    engine = sqlite_engine
    with engine.connect() as conn:
        conn.execute(
            text("CREATE TABLE test_type_mismatch (id INTEGER PRIMARY KEY, email INTEGER, name TEXT)")
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.compare_schemas("test_users", "test_type_mismatch")

    assert result.passed is False
    assert "email" in result.type_mismatches


# ============================================================================
# DATA INTEGRITY TESTS
# ============================================================================


def test_data_integrity_matching_data(populated_engine):
    """Test data integrity with matching row counts and checksums."""
    validator = ShadowTableSwapValidator(populated_engine)

    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is True
    assert result.original_row_count == 2
    assert result.shadow_row_count == 2
    assert result.checksum_original == result.checksum_shadow


def test_data_integrity_row_count_mismatch(populated_engine):
    """Test data integrity when row counts differ."""
    engine = populated_engine
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO test_users_shadow (id, email, name) VALUES (3, 'carol@test.com', 'Carol')"
            )
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is False
    assert result.original_row_count == 2
    assert result.shadow_row_count == 3


def test_data_integrity_empty_tables(sqlite_engine):
    """Test data integrity with empty tables."""
    validator = ShadowTableSwapValidator(sqlite_engine)

    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is True
    assert result.original_row_count == 0
    assert result.shadow_row_count == 0


def test_data_integrity_checksum_mismatch(populated_engine):
    """Test data integrity when checksums differ."""
    engine = populated_engine
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE test_users_shadow SET email = 'different@test.com' WHERE id = 1")
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is False
    assert result.checksum_original != result.checksum_shadow


# ============================================================================
# PRE-SWAP VALIDATION TESTS
# ============================================================================


def test_pre_swap_all_validations_pass(populated_engine):
    """Test pre-swap validation when all checks pass."""
    validator = ShadowTableSwapValidator(populated_engine)

    result = validator.validate_pre_swap("test_users", "test_users_shadow")

    assert result.passed is True
    assert result.schema_valid is True
    assert result.data_valid is True
    assert result.fk_safe is True


def test_pre_swap_original_table_missing(sqlite_engine):
    """Test pre-swap when original table doesn't exist."""
    validator = ShadowTableSwapValidator(sqlite_engine)

    result = validator.validate_pre_swap("nonexistent", "test_users_shadow")

    assert result.passed is False
    assert "not found" in result.error_message


def test_pre_swap_shadow_table_missing(sqlite_engine):
    """Test pre-swap when shadow table doesn't exist."""
    validator = ShadowTableSwapValidator(sqlite_engine)

    result = validator.validate_pre_swap("test_users", "nonexistent")

    assert result.passed is False
    assert "not found" in result.error_message


def test_pre_swap_schema_mismatch_blocks_swap(sqlite_engine):
    """Test pre-swap blocked by schema mismatch."""
    engine = sqlite_engine
    with engine.connect() as conn:
        conn.execute(
            text("CREATE TABLE test_users_bad (id INTEGER PRIMARY KEY, email INTEGER)")
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_pre_swap("test_users", "test_users_bad")

    assert result.passed is False
    assert result.schema_valid is False


def test_pre_swap_data_mismatch_blocks_swap(populated_engine):
    """Test pre-swap blocked by data mismatch."""
    engine = populated_engine
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM test_users_shadow WHERE id = 2")
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_pre_swap("test_users", "test_users_shadow")

    assert result.passed is False
    assert result.data_valid is False


# ============================================================================
# POST-SWAP VALIDATION TESTS
# ============================================================================


def test_post_swap_validation_success(populated_engine):
    """Test post-swap validation when swap was successful."""
    engine = populated_engine
    validator = ShadowTableSwapValidator(engine)

    # Simulate swap by creating backup table
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE test_users RENAME TO test_users_backup"))
        conn.execute(text("ALTER TABLE test_users_shadow RENAME TO test_users"))
        conn.commit()

    result = validator.validate_post_swap("test_users_backup", "test_users")

    assert result.passed is True


def test_post_swap_backup_table_missing(populated_engine):
    """Test post-swap fails when backup table missing."""
    validator = ShadowTableSwapValidator(populated_engine)

    result = validator.validate_post_swap("nonexistent_backup", "test_users_shadow")

    assert result.passed is False
    assert "not found" in result.error_message


def test_post_swap_active_table_missing(populated_engine):
    """Test post-swap fails when active table missing."""
    validator = ShadowTableSwapValidator(populated_engine)

    result = validator.validate_post_swap("test_users", "nonexistent_active")

    assert result.passed is False
    assert "not found" in result.error_message


# ============================================================================
# DATACLASS SERIALIZATION TESTS
# ============================================================================


def test_dataclass_result_serializable(populated_engine):
    """Test that validation results are serializable."""
    import json
    from dataclasses import asdict

    validator = ShadowTableSwapValidator(populated_engine)
    result = validator.validate_pre_swap("test_users", "test_users_shadow")

    result_dict = asdict(result)
    json_str = json.dumps(result_dict, default=str)

    assert "test_users" in json_str
    assert result.passed is True


def test_column_schema_dataclass(sqlite_engine):
    """Test ColumnSchema dataclass."""
    col = ColumnSchema(
        name="email",
        type="VARCHAR(255)",
        nullable=False,
        primary_key=False
    )

    assert col.name == "email"
    assert col.type == "VARCHAR(255)"
    assert col.nullable is False


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_validator_handles_large_row_count(sqlite_engine):
    """Test validator with large number of rows."""
    engine = sqlite_engine
    with engine.connect() as conn:
        for i in range(100):
            conn.execute(
                text(
                    f"INSERT INTO test_users (id, email, name) VALUES ({i}, 'user{i}@test.com', 'User{i}')"
                )
            )
        for i in range(100):
            conn.execute(
                text(
                    f"INSERT INTO test_users_shadow (id, email, name) VALUES ({i}, 'user{i}@test.com', 'User{i}')"
                )
            )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is True
    assert result.original_row_count == 100
    assert result.shadow_row_count == 100


def test_validator_handles_null_values(sqlite_engine):
    """Test validator with NULL values in columns."""
    engine = sqlite_engine
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO test_users (id, email, name) VALUES (1, 'user1@test.com', NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO test_users_shadow (id, email, name) VALUES (1, 'user1@test.com', NULL)"
            )
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is True


def test_validator_with_special_characters(sqlite_engine):
    """Test validator with special characters in data."""
    engine = sqlite_engine
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO test_users (id, email, name) VALUES (1, 'user+test@example.com', 'Müller')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO test_users_shadow (id, email, name) VALUES (1, 'user+test@example.com', 'Müller')"
            )
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_data_integrity("test_users", "test_users_shadow")

    assert result.passed is True


# ============================================================================
# VALIDATION RESULT STRUCTURE TESTS
# ============================================================================


def test_swap_validation_result_structure(populated_engine):
    """Test SwapValidationResult has all required fields."""
    validator = ShadowTableSwapValidator(populated_engine)
    result = validator.validate_pre_swap("test_users", "test_users_shadow")

    assert result.original_table == "test_users"
    assert result.shadow_table == "test_users_shadow"
    assert isinstance(result.schema_valid, bool)
    assert isinstance(result.data_valid, bool)
    assert isinstance(result.fk_safe, bool)
    assert isinstance(result.passed, bool)
    assert result.schema_comparison is not None
    assert result.data_metrics is not None
    assert isinstance(result.recommendations, list)


def test_validation_adds_recommendations(populated_engine):
    """Test that validation adds helpful recommendations on failure."""
    engine = populated_engine
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM test_users_shadow WHERE id = 1")
        )
        conn.commit()

    validator = ShadowTableSwapValidator(engine)
    result = validator.validate_pre_swap("test_users", "test_users_shadow")

    assert result.passed is False
    assert len(result.recommendations) > 0


# ============================================================================
# LOGGING TESTS
# ============================================================================


def test_validation_logs_success(populated_engine, caplog):
    """Test that validation logs success."""
    validator = ShadowTableSwapValidator(populated_engine)

    result = validator.validate_pre_swap("test_users", "test_users_shadow")

    assert result.passed is True
    assert any("Pre-swap validation passed" in record.message for record in caplog.records)


def test_validation_logs_errors(sqlite_engine, caplog):
    """Test that validation logs errors."""
    validator = ShadowTableSwapValidator(sqlite_engine)

    result = validator.validate_pre_swap("nonexistent", "test_users_shadow")

    assert result.passed is False
    assert any("not found" in record.message for record in caplog.records)
