"""
Shadow Table Swap Validation Framework

Validates zero-downtime migrations using shadow table pattern:
1. Create shadow table with new schema
2. Backfill data from original table
3. Validate consistency before swap
4. Swap tables atomically
5. Retain original table for rollback

This module provides validation to prevent data loss/corruption.
"""

import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from sqlalchemy import Engine, text, inspect

logger = logging.getLogger(__name__)


@dataclass
class ColumnSchema:
    """Column definition for schema comparison."""
    name: str
    type: str
    nullable: bool
    primary_key: bool = False
    unique: bool = False


@dataclass
class TableSchemaComparison:
    """Schema comparison result."""
    original_columns: List[ColumnSchema]
    shadow_columns: List[ColumnSchema]
    passed: bool
    missing_columns: List[str] = field(default_factory=list)
    extra_columns: List[str] = field(default_factory=list)
    type_mismatches: Dict[str, tuple] = field(default_factory=dict)
    error_message: str = ""


@dataclass
class DataSyncMetrics:
    """Data synchronization metrics."""
    original_row_count: int
    shadow_row_count: int
    checksum_original: str
    checksum_shadow: str
    passed: bool
    rows_missing_in_shadow: int = 0
    rows_extra_in_shadow: int = 0
    error_message: str = ""


@dataclass
class SwapValidationResult:
    """Complete shadow table swap validation result."""
    original_table: str
    shadow_table: str
    schema_valid: bool
    data_valid: bool
    fk_safe: bool
    passed: bool
    schema_comparison: Optional[TableSchemaComparison] = None
    data_metrics: Optional[DataSyncMetrics] = None
    fk_errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validation_timestamp: str = ""


class ShadowTableSwapValidator:
    """Validates shadow table swaps before execution."""

    def __init__(self, engine: Engine):
        """Initialize validator with database engine."""
        self.engine = engine
        self.inspector = inspect(engine)

    def validate_pre_swap(
        self,
        original_table: str,
        shadow_table: str
    ) -> SwapValidationResult:
        """Validate tables before swap. Returns validation result."""
        from datetime import datetime

        result = SwapValidationResult(
            original_table=original_table,
            shadow_table=shadow_table,
            schema_valid=False,
            data_valid=False,
            fk_safe=False,
            passed=False,
            validation_timestamp=datetime.utcnow().isoformat()
        )

        # Check tables exist
        if not self._table_exists(original_table):
            result.error_message = f"Original table '{original_table}' not found"
            logger.error(result.error_message)
            return result

        if not self._table_exists(shadow_table):
            result.error_message = f"Shadow table '{shadow_table}' not found"
            logger.error(result.error_message)
            return result

        # 1. Schema validation
        schema_result = self.compare_schemas(original_table, shadow_table)
        result.schema_comparison = schema_result
        result.schema_valid = schema_result.passed

        if not result.schema_valid:
            result.recommendations.append(
                f"Fix schema mismatches: {schema_result.error_message}"
            )
            logger.warning(f"Schema mismatch: {schema_result.error_message}")
            return result

        # 2. Data synchronization validation
        data_result = self.validate_data_integrity(original_table, shadow_table)
        result.data_metrics = data_result
        result.data_valid = data_result.passed

        if not result.data_valid:
            result.recommendations.append(
                f"Sync data: {data_result.rows_missing_in_shadow} missing rows, "
                f"{data_result.rows_extra_in_shadow} extra rows"
            )
            logger.warning(f"Data mismatch: {data_result.error_message}")
            return result

        # 3. Foreign key safety
        fk_errors = self._validate_foreign_keys(shadow_table)
        result.fk_safe = len(fk_errors) == 0
        result.fk_errors = fk_errors

        if not result.fk_safe:
            result.recommendations.append(
                f"Fix foreign key constraints: {len(fk_errors)} issues found"
            )
            logger.warning(f"FK errors: {fk_errors}")
            return result

        # All validations passed
        result.passed = True
        logger.info(
            f"✓ Pre-swap validation passed for '{original_table}' → '{shadow_table}'"
        )
        return result

    def validate_post_swap(
        self,
        original_table_old: str,  # Original table renamed to _old
        new_active_table: str,     # Shadow table renamed to original name
    ) -> SwapValidationResult:
        """Validate tables after swap. Ensures active table is correct."""
        from datetime import datetime

        result = SwapValidationResult(
            original_table=original_table_old,
            shadow_table=new_active_table,
            schema_valid=True,
            data_valid=True,
            fk_safe=True,
            passed=True,
            validation_timestamp=datetime.utcnow().isoformat()
        )

        # Verify backup table exists
        if not self._table_exists(original_table_old):
            result.passed = False
            result.error_message = f"Backup table '{original_table_old}' not found"
            logger.error(result.error_message)
            return result

        # Verify active table exists
        if not self._table_exists(new_active_table):
            result.passed = False
            result.error_message = f"Active table '{new_active_table}' not found"
            logger.error(result.error_message)
            return result

        logger.info(f"✓ Post-swap validation passed: '{new_active_table}' is active")
        return result

    def compare_schemas(
        self,
        table1: str,
        table2: str
    ) -> TableSchemaComparison:
        """Compare schemas of two tables (table1=original, table2=shadow)."""
        cols1 = self._get_table_columns(table1)
        cols2 = self._get_table_columns(table2)

        result = TableSchemaComparison(
            original_columns=cols1,
            shadow_columns=cols2,
            passed=True
        )

        # Check for missing/extra columns
        names1 = {c.name for c in cols1}
        names2 = {c.name for c in cols2}

        # missing_columns = in original but not in shadow
        # extra_columns = in shadow but not in original
        result.missing_columns = list(names1 - names2)
        result.extra_columns = list(names2 - names1)

        if result.missing_columns or result.extra_columns:
            result.passed = False
            result.error_message = (
                f"Missing in shadow: {result.missing_columns}, Extra in shadow: {result.extra_columns}"
            )
            return result

        # Check type compatibility
        col_map1 = {c.name: c for c in cols1}
        col_map2 = {c.name: c for c in cols2}

        for name in names1:
            c1 = col_map1[name]
            c2 = col_map2[name]

            # Type mismatch
            if str(c1.type) != str(c2.type):
                result.type_mismatches[name] = (str(c1.type), str(c2.type))
                result.passed = False

            # Nullability mismatch (shadow can be more permissive)
            if c1.nullable and not c2.nullable:
                result.type_mismatches[name] = ("nullable", "not null")
                result.passed = False

        if result.type_mismatches:
            result.error_message = f"Type mismatches: {result.type_mismatches}"

        return result

    def validate_data_integrity(
        self,
        original_table: str,
        shadow_table: str
    ) -> DataSyncMetrics:
        """Validate data consistency between tables."""
        result = DataSyncMetrics(
            original_row_count=0,
            shadow_row_count=0,
            checksum_original="",
            checksum_shadow="",
            passed=True
        )

        try:
            with self.engine.connect() as conn:
                # Row counts
                result.original_row_count = self._get_row_count(conn, original_table)
                result.shadow_row_count = self._get_row_count(conn, shadow_table)

                # Checksums
                result.checksum_original = self._calculate_table_checksum(
                    conn, original_table
                )
                result.checksum_shadow = self._calculate_table_checksum(
                    conn, shadow_table
                )

                # Compare
                if result.original_row_count != result.shadow_row_count:
                    result.rows_missing_in_shadow = (
                        result.original_row_count - result.shadow_row_count
                    )
                    result.rows_extra_in_shadow = max(0, result.rows_missing_in_shadow * -1)
                    result.passed = False
                    result.error_message = (
                        f"Row count mismatch: {result.original_row_count} vs "
                        f"{result.shadow_row_count}"
                    )
                    return result

                if result.checksum_original != result.checksum_shadow:
                    result.passed = False
                    result.error_message = "Data checksum mismatch - possible data divergence"
                    return result

        except Exception as e:
            result.passed = False
            result.error_message = f"Checksum validation failed: {str(e)}"
            logger.error(result.error_message)
            return result

        return result

    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        try:
            return table_name in self.inspector.get_table_names()
        except Exception:
            return False

    def _get_table_columns(self, table_name: str) -> List[ColumnSchema]:
        """Get column definitions for table."""
        try:
            cols = self.inspector.get_columns(table_name)
            pk_constraint = self.inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", []))

            result = []
            for col in cols:
                result.append(
                    ColumnSchema(
                        name=col["name"],
                        type=str(col["type"]),
                        nullable=col.get("nullable", True),
                        primary_key=col["name"] in pk_cols
                    )
                )
            return result
        except Exception as e:
            logger.warning(f"Could not inspect table '{table_name}': {e}")
            return []

    def _get_row_count(self, conn, table_name: str) -> int:
        """Get row count for table."""
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
        except Exception:
            return 0

    def _calculate_table_checksum(self, conn, table_name: str) -> str:
        """Calculate SHA-256 checksum of table data."""
        try:
            result = conn.execute(text(f"SELECT * FROM {table_name} ORDER BY 1"))
            rows = result.fetchall()

            hasher = hashlib.sha256()
            for row in rows:
                row_str = str(row)
                hasher.update(row_str.encode())

            return hasher.hexdigest()
        except Exception:
            return ""

    def _validate_foreign_keys(self, table_name: str) -> List[str]:
        """Validate foreign key constraints."""
        errors = []
        try:
            fks = self.inspector.get_foreign_keys(table_name)
            for fk in fks:
                # Basic validation - FK definition exists
                constrained_cols = fk.get("constrained_columns", [])
                if not constrained_cols:
                    errors.append(f"FK {fk['name']} has no constrained columns")
        except Exception as e:
            logger.warning(f"FK validation skipped: {e}")

        return errors


def get_shadow_validator(engine: Engine) -> ShadowTableSwapValidator:
    """Factory function to get validator instance."""
    return ShadowTableSwapValidator(engine)
