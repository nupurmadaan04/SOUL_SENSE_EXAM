"""
Tests for Online Index Creation Policy Guard

Coverage:
- Policy validation for all supported databases
- Edge cases: invalid inputs, timeouts, long durations
- Database-specific checks: PostgreSQL, MySQL, SQLite
- Policy enforcement and recommendations
"""

import pytest
from app.infra.online_index_policy import (
    IndexDefinition,
    OnlineIndexPolicyValidator,
    DatabaseType,
    IndexPolicy,
    validate_index_in_migration,
)


class TestIndexDefinition:
    """Test index definition validation."""
    
    def test_valid_index_definition(self):
        """Valid index definition should pass validation."""
        index = IndexDefinition(
            name="ix_users_email",
            table="users",
            columns=["email"]
        )
        is_valid, msg = index.validate()
        assert is_valid
        assert msg == ""
    
    def test_index_missing_name(self):
        """Index without name should fail validation."""
        index = IndexDefinition(name="", table="users", columns=["email"])
        is_valid, msg = index.validate()
        assert not is_valid
        assert "required" in msg.lower()
    
    def test_index_missing_table(self):
        """Index without table should fail validation."""
        index = IndexDefinition(name="ix_test", table="", columns=["email"])
        is_valid, msg = index.validate()
        assert not is_valid
    
    def test_index_missing_columns(self):
        """Index without columns should fail validation."""
        index = IndexDefinition(name="ix_test", table="users", columns=[])
        is_valid, msg = index.validate()
        assert not is_valid
    
    def test_index_negative_duration(self):
        """Index with negative duration should fail validation."""
        index = IndexDefinition(
            name="ix_test",
            table="users",
            columns=["email"],
            estimated_duration_seconds=-1
        )
        is_valid, msg = index.validate()
        assert not is_valid


class TestPostgreSQLValidation:
    """Test PostgreSQL index policy validation."""
    
    def test_postgresql_supports_online_creation(self):
        """PostgreSQL should support online index creation."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert result.passed
        assert result.database_type == "postgresql"
        assert len(result.checks) >= 2
    
    def test_postgresql_concurrent_keywords(self):
        """PostgreSQL validation should recommend CONCURRENT keyword."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        concurrent_check = next(
            (c for c in result.checks if c.policy == IndexPolicy.MUST_BE_CONCURRENT),
            None
        )
        assert concurrent_check is not None
        assert concurrent_check.passed
        assert "CONCURRENTLY" in concurrent_check.recommendation
    
    def test_postgresql_long_duration_warning(self):
        """PostgreSQL index with long duration should show warning."""
        index = IndexDefinition(
            name="ix_large_table",
            table="huge_users",
            columns=["email"],
            estimated_duration_seconds=400
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert result.passed
        assert len(result.warnings) > 0
        assert any("long" in w.lower() for w in result.warnings)
    
    def test_postgresql_rollback_plan_check(self):
        """PostgreSQL should check for rollback plan."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        rollback_check = next(
            (c for c in result.checks if c.policy == IndexPolicy.MUST_HAVE_ROLLBACK),
            None
        )
        assert rollback_check is not None
        assert rollback_check.passed


class TestMySQLValidation:
    """Test MySQL index policy validation."""
    
    def test_mysql_supports_online_creation(self):
        """MySQL should support online index creation."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        assert result.passed
        assert result.database_type == "mysql"
    
    def test_mysql_inplace_lock_none_recommendation(self):
        """MySQL should recommend ALGORITHM=INPLACE, LOCK=NONE."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        inplace_check = next(
            (c for c in result.checks if c.policy == IndexPolicy.MUST_BE_INPLACE),
            None
        )
        assert inplace_check is not None
        assert inplace_check.passed
        assert "INPLACE" in inplace_check.recommendation
        assert "LOCK=NONE" in inplace_check.recommendation
    
    def test_mysql_long_duration_warning(self):
        """MySQL index with long duration should show warning."""
        index = IndexDefinition(
            name="ix_large_table",
            table="orders",
            columns=["price"],
            estimated_duration_seconds=500
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        assert result.passed
        assert len(result.warnings) > 0


class TestSQLiteValidation:
    """Test SQLite index policy validation."""
    
    def test_sqlite_requires_maintenance_window(self):
        """SQLite should warn about table lock requirement."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.SQLITE)
        result = validator.validate(index)
        
        # SQLite doesn't support online index creation
        assert len(result.warnings) > 0
        assert any("lock" in w.lower() or "maintenance" in w.lower() 
                   for w in result.warnings)
    
    def test_sqlite_no_online_mode(self):
        """SQLite should not support online index creation."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.SQLITE)
        result = validator.validate(index)
        
        requires_maint_check = next(
            (c for c in result.checks if c.policy == IndexPolicy.REQUIRES_MAINTENANCE),
            None
        )
        assert requires_maint_check is not None
        # Not blocking, just a warning
        assert not requires_maint_check.blocking
    
    def test_sqlite_long_duration_blocking(self):
        """SQLite with very long duration should warn (non-blocking)."""
        index = IndexDefinition(
            name="ix_large_table",
            table="huge_data",
            columns=["id"],
            estimated_duration_seconds=600
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.SQLITE)
        result = validator.validate(index)
        
        # Still passes but with warnings
        assert len(result.warnings) >= 2  # Lock + duration


class TestUniqueIndexes:
    """Test validation of unique indexes."""
    
    def test_postgresql_unique_index(self):
        """PostgreSQL should support unique indexes."""
        index = IndexDefinition(
            name="ix_email_unique",
            table="users",
            columns=["email"],
            is_unique=True
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert result.passed
        assert result.metrics["is_unique"] is True
    
    def test_mysql_unique_index(self):
        """MySQL should support unique indexes."""
        index = IndexDefinition(
            name="ix_code_unique",
            table="vouchers",
            columns=["code"],
            is_unique=True
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        assert result.passed
        assert result.metrics["is_unique"] is True


class TestMultiColumnIndexes:
    """Test validation of composite indexes."""
    
    def test_postgresql_multi_column_index(self):
        """PostgreSQL should support multi-column indexes."""
        index = IndexDefinition(
            name="ix_user_date",
            table="events",
            columns=["user_id", "created_at"]
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert result.passed
        assert result.metrics["columns"] == 2
    
    def test_mysql_multi_column_index(self):
        """MySQL should support multi-column indexes."""
        index = IndexDefinition(
            name="ix_order_user_date",
            table="orders",
            columns=["user_id", "order_date", "status"]
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        assert result.passed
        assert result.metrics["columns"] == 3


class TestConvenienceFunction:
    """Test the convenience validation function."""
    
    def test_validate_index_in_migration_postgresql(self):
        """Test convenience function with PostgreSQL."""
        result = validate_index_in_migration(
            db_type="postgresql",
            index_name="ix_test",
            table_name="users",
            columns=["email"]
        )
        
        assert result.passed
        assert result.database_type == "postgresql"
    
    def test_validate_index_in_migration_mysql(self):
        """Test convenience function with MySQL."""
        result = validate_index_in_migration(
            db_type="mysql",
            index_name="ix_test",
            table_name="users",
            columns=["email"]
        )
        
        assert result.passed
        assert result.database_type == "mysql"
    
    def test_validate_index_in_migration_sqlite(self):
        """Test convenience function with SQLite."""
        result = validate_index_in_migration(
            db_type="sqlite",
            index_name="ix_test",
            table_name="users",
            columns=["email"]
        )
        
        # Warnings but passes
        assert len(result.warnings) > 0
        assert result.database_type == "sqlite"
    
    def test_validate_index_with_duration(self):
        """Test convenience function with custom duration."""
        result = validate_index_in_migration(
            db_type="postgresql",
            index_name="ix_large",
            table_name="massive_table",
            columns=["data"],
            estimated_duration_seconds=500
        )
        
        assert result.metrics["estimated_duration_seconds"] == 500
    
    def test_validate_index_with_unique(self):
        """Test convenience function with unique constraint."""
        result = validate_index_in_migration(
            db_type="mysql",
            index_name="ix_unique",
            table_name="accounts",
            columns=["username"],
            is_unique=True
        )
        
        assert result.metrics["is_unique"] is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_database_type_in_function(self):
        """Invalid database type should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_index_in_migration(
                db_type="oracle",
                index_name="ix_test",
                table_name="users",
                columns=["email"]
            )
        assert "Unsupported database type" in str(exc_info.value)
    
    def test_empty_index_name_in_function(self):
        """Empty index name should result in failed validation."""
        result = validate_index_in_migration(
            db_type="postgresql",
            index_name="",
            table_name="users",
            columns=["email"]
        )
        
        assert not result.passed
        assert len(result.errors) > 0
    
    def test_empty_columns_in_function(self):
        """Empty columns list should result in failed validation."""
        result = validate_index_in_migration(
            db_type="postgresql",
            index_name="ix_test",
            table_name="users",
            columns=[]
        )
        
        assert not result.passed
        assert len(result.errors) > 0
    
    def test_very_long_index_duration(self):
        """Very long index duration should generate warnings."""
        result = validate_index_in_migration(
            db_type="postgresql",
            index_name="ix_huge",
            table_name="enormous_table",
            columns=["data"],
            estimated_duration_seconds=3600  # 1 hour
        )
        
        assert len(result.warnings) > 0


class TestResultSerialization:
    """Test that validation results can be serialized."""
    
    def test_result_to_dict_postgresql(self):
        """Result should convert to dictionary for logging."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["passed"] == result.passed
        assert result_dict["index"] == result.index_name
        assert result_dict["database"] == result.database_type
        assert "checks" in result_dict
        assert "timestamp" in result_dict
    
    def test_result_to_dict_contains_all_fields(self):
        """Result dictionary should contain all expected fields."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        result_dict = result.to_dict()
        
        expected_keys = ["passed", "index", "database", "checks", 
                        "errors", "warnings", "recommendations", 
                        "metrics", "timestamp"]
        for key in expected_keys:
            assert key in result_dict


class TestRecommendations:
    """Test that recommendations are helpful and actionable."""
    
    def test_postgresql_recommendations_are_actionable(self):
        """PostgreSQL recommendations should have SQL syntax."""
        index = IndexDefinition(name="ix_email", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert len(result.recommendations) > 0
        assert any("CREATE INDEX" in rec for rec in result.recommendations)
    
    def test_mysql_recommendations_are_actionable(self):
        """MySQL recommendations should have SQL syntax."""
        index = IndexDefinition(name="ix_code", table="orders", columns=["order_code"])
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        assert len(result.recommendations) > 0
        assert any("ALTER TABLE" in rec or "ALGORITHM" in rec 
                   for rec in result.recommendations)
    
    def test_sqlite_recommendations_mention_maintenance(self):
        """SQLite recommendations should mention maintenance window."""
        index = IndexDefinition(name="ix_test", table="users", columns=["email"])
        validator = OnlineIndexPolicyValidator(DatabaseType.SQLITE)
        result = validator.validate(index)
        
        assert len(result.recommendations) > 0
        assert any("maintenance" in rec.lower() 
                   for rec in result.recommendations)


class TestMetrics:
    """Test that metrics are captured correctly."""
    
    def test_metrics_include_table_and_columns(self):
        """Metrics should include table name and column count."""
        index = IndexDefinition(
            name="ix_test",
            table="orders",
            columns=["user_id", "status"]
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert result.metrics["table"] == "orders"
        assert result.metrics["columns"] == 2
    
    def test_metrics_include_duration(self):
        """Metrics should include estimated duration."""
        index = IndexDefinition(
            name="ix_test",
            table="users",
            columns=["email"],
            estimated_duration_seconds=45
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
        result = validator.validate(index)
        
        assert result.metrics["estimated_duration_seconds"] == 45
    
    def test_metrics_include_is_unique(self):
        """Metrics should include unique constraint flag."""
        index = IndexDefinition(
            name="ix_email_unique",
            table="users",
            columns=["email"],
            is_unique=True
        )
        validator = OnlineIndexPolicyValidator(DatabaseType.MYSQL)
        result = validator.validate(index)
        
        assert result.metrics["is_unique"] is True
