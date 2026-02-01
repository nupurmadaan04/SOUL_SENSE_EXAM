"""
Startup integrity checks for the SoulSense application.
Validates database schema and required files at application startup.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from sqlalchemy import inspect

from app.config import (
    BASE_DIR, DATA_DIR, LOG_DIR, MODELS_DIR, 
    DB_PATH, CONFIG_PATH, DEFAULT_CONFIG
)
from app.exceptions import IntegrityError, DatabaseError, ConfigurationError

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    """Status of an integrity check."""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class IntegrityCheckResult:
    """Result of a single integrity check."""
    name: str
    status: CheckStatus
    message: str
    recovery_action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


# Required files for the application to function
REQUIRED_FILES: List[Dict[str, Any]] = [
    {"path": "data", "type": "directory", "critical": True, "auto_create": True},
    {"path": "logs", "type": "directory", "critical": False, "auto_create": True},
    {"path": "models", "type": "directory", "critical": False, "auto_create": True},
]

# Required database tables
REQUIRED_TABLES: List[str] = [
    "users",
    "scores", 
    "responses",
    "journal_entries",
    "user_settings",
    "personal_profiles",
    "medical_profiles",
    "user_strengths",
    "user_emotional_patterns",
    "login_attempts",
    "user_sync_settings",
    "question_bank",
    "question_category"
]


def check_database_schema() -> IntegrityCheckResult:
    """
    Validate that the database exists and has the required tables.
    Attempts to create missing tables if possible.
    """
    from app.db import engine, check_db_state
    
    try:
        # Check if database file exists
        if not os.path.exists(DB_PATH):
            logger.warning(f"Database file not found at {DB_PATH}")
            # Try to create it
            try:
                check_db_state()
                return IntegrityCheckResult(
                    name="database_schema",
                    status=CheckStatus.WARNING,
                    message="Database was missing but has been created.",
                    recovery_action="Created database with default schema"
                )
            except Exception as e:
                return IntegrityCheckResult(
                    name="database_schema",
                    status=CheckStatus.FAILED,
                    message=f"Failed to create database: {str(e)}",
                    details={"error": str(e)}
                )
        
        # Check tables using SQLAlchemy inspector
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        missing_tables = [t for t in REQUIRED_TABLES if t not in existing_tables]
        
        if missing_tables:
            logger.warning(f"Missing database tables: {missing_tables}")
            # Try to create missing tables
            try:
                check_db_state()
                # Re-check after creation attempt
                inspector = inspect(engine)
                still_missing = [t for t in REQUIRED_TABLES if t not in inspector.get_table_names()]
                
                if still_missing:
                    return IntegrityCheckResult(
                        name="database_schema",
                        status=CheckStatus.FAILED,
                        message=f"Could not create tables: {still_missing}",
                        details={"missing_tables": still_missing}
                    )
                
                return IntegrityCheckResult(
                    name="database_schema",
                    status=CheckStatus.WARNING,
                    message=f"Created missing tables: {missing_tables}",
                    recovery_action=f"Created tables: {', '.join(missing_tables)}"
                )
            except Exception as e:
                return IntegrityCheckResult(
                    name="database_schema",
                    status=CheckStatus.FAILED,
                    message=f"Failed to create missing tables: {str(e)}",
                    details={"missing_tables": missing_tables, "error": str(e)}
                )
        
        logger.info("Database schema check passed")
        return IntegrityCheckResult(
            name="database_schema",
            status=CheckStatus.PASSED,
            message="All required tables present",
            details={"tables_found": list(existing_tables)}
        )
        
    except Exception as e:
        logger.error(f"Database schema check failed: {e}", exc_info=True)
        return IntegrityCheckResult(
            name="database_schema",
            status=CheckStatus.FAILED,
            message=f"Database check error: {str(e)}",
            details={"error": str(e)}
        )


def check_required_files() -> IntegrityCheckResult:
    """
    Verify that required directories and files exist.
    Creates missing directories if auto_create is True.
    """
    missing_critical: List[str] = []
    missing_optional: List[str] = []
    created: List[str] = []
    
    for file_info in REQUIRED_FILES:
        path = os.path.join(BASE_DIR, file_info["path"])
        exists = os.path.exists(path)
        
        if not exists:
            if file_info.get("auto_create") and file_info["type"] == "directory":
                try:
                    os.makedirs(path, exist_ok=True)
                    created.append(file_info["path"])
                    logger.info(f"Created missing directory: {path}")
                except OSError as e:
                    logger.error(f"Failed to create directory {path}: {e}")
                    if file_info.get("critical"):
                        missing_critical.append(file_info["path"])
                    else:
                        missing_optional.append(file_info["path"])
            elif file_info.get("critical"):
                missing_critical.append(file_info["path"])
            else:
                missing_optional.append(file_info["path"])
    
    if missing_critical:
        return IntegrityCheckResult(
            name="required_files",
            status=CheckStatus.FAILED,
            message=f"Critical files/directories missing: {missing_critical}",
            details={"missing_critical": missing_critical, "missing_optional": missing_optional}
        )
    
    if missing_optional:
        return IntegrityCheckResult(
            name="required_files",
            status=CheckStatus.WARNING,
            message=f"Optional files/directories missing: {missing_optional}",
            recovery_action=f"Created: {created}" if created else None,
            details={"missing_optional": missing_optional, "created": created}
        )
    
    if created:
        return IntegrityCheckResult(
            name="required_files",
            status=CheckStatus.WARNING,
            message="Some directories were created",
            recovery_action=f"Created: {', '.join(created)}",
            details={"created": created}
        )
    
    logger.info("Required files check passed")
    return IntegrityCheckResult(
        name="required_files",
        status=CheckStatus.PASSED,
        message="All required files and directories present"
    )


def check_config_integrity() -> IntegrityCheckResult:
    """
    Validate that the configuration file is valid and contains expected keys.
    Creates default config if missing.
    """
    try:
        if not os.path.exists(CONFIG_PATH):
            # Config missing - create default
            try:
                from app.utils.atomic import atomic_write
                
                with atomic_write(CONFIG_PATH, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info(f"Created default config at {CONFIG_PATH}")
                return IntegrityCheckResult(
                    name="config_integrity",
                    status=CheckStatus.WARNING,
                    message="Config file was missing, created with defaults",
                    recovery_action="Created config.json with default values"
                )
            except Exception as e:
                return IntegrityCheckResult(
                    name="config_integrity",
                    status=CheckStatus.WARNING,
                    message=f"Could not create config file: {str(e)}. Using in-memory defaults.",
                    details={"error": str(e)}
                )
        
        # Validate JSON structure
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            # Corrupt config - attempt recovery by backing up and creating new
            backup_path = CONFIG_PATH + ".corrupt.bak"
            try:
                from app.utils.atomic import atomic_write
                
                os.rename(CONFIG_PATH, backup_path)
                with atomic_write(CONFIG_PATH, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.warning(f"Corrupt config backed up to {backup_path}, created new default")
                return IntegrityCheckResult(
                    name="config_integrity",
                    status=CheckStatus.WARNING,
                    message="Config was corrupt, restored to defaults",
                    recovery_action=f"Backed up corrupt config and created new default",
                    details={"backup_path": backup_path}
                )
            except Exception as recovery_error:
                return IntegrityCheckResult(
                    name="config_integrity",
                    status=CheckStatus.FAILED,
                    message=f"Config is corrupt and recovery failed: {str(e)}",
                    details={"parse_error": str(e), "recovery_error": str(recovery_error)}
                )
        
        # Verify required sections exist
        required_sections = ["database", "ui", "features"]
        missing_sections = [s for s in required_sections if s not in config]
        
        if missing_sections:
            return IntegrityCheckResult(
                name="config_integrity",
                status=CheckStatus.WARNING,
                message=f"Config missing sections: {missing_sections}. Using defaults for these.",
                details={"missing_sections": missing_sections}
            )
        
        logger.info("Config integrity check passed")
        return IntegrityCheckResult(
            name="config_integrity",
            status=CheckStatus.PASSED,
            message="Configuration is valid"
        )
        
    except Exception as e:
        logger.error(f"Config integrity check failed: {e}", exc_info=True)
        return IntegrityCheckResult(
            name="config_integrity",
            status=CheckStatus.FAILED,
            message=f"Config check error: {str(e)}",
            details={"error": str(e)}
        )


def run_all_checks(raise_on_critical: bool = True) -> List[IntegrityCheckResult]:
    """
    Run all startup integrity checks.
    
    Args:
        raise_on_critical: If True, raises IntegrityError on any FAILED check
        
    Returns:
        List of IntegrityCheckResult for all checks
        
    Raises:
        IntegrityError: If any check fails and raise_on_critical is True
    """
    logger.info("Running startup integrity checks...")
    
    checks: List[Callable[[], IntegrityCheckResult]] = [
        check_config_integrity,  # Config first, as others may depend on it
        check_required_files,
        check_database_schema,
    ]
    
    results: List[IntegrityCheckResult] = []
    failed_checks: List[str] = []
    
    for check_func in checks:
        try:
            result = check_func()
            results.append(result)
            
            # Log result
            if result.status == CheckStatus.PASSED:
                logger.info(f"✓ {result.name}: {result.message}")
            elif result.status == CheckStatus.WARNING:
                logger.warning(f"⚠ {result.name}: {result.message}")
                if result.recovery_action:
                    logger.info(f"  Recovery: {result.recovery_action}")
            else:
                logger.error(f"✗ {result.name}: {result.message}")
                failed_checks.append(result.name)
                
        except Exception as e:
            logger.error(f"Check {check_func.__name__} crashed: {e}", exc_info=True)
            result = IntegrityCheckResult(
                name=check_func.__name__,
                status=CheckStatus.FAILED,
                message=f"Check crashed: {str(e)}",
                details={"exception": str(e)}
            )
            results.append(result)
            failed_checks.append(check_func.__name__)
    
    # Summary
    passed = sum(1 for r in results if r.status == CheckStatus.PASSED)
    warnings = sum(1 for r in results if r.status == CheckStatus.WARNING)
    failed = sum(1 for r in results if r.status == CheckStatus.FAILED)
    
    logger.info(f"Integrity checks complete: {passed} passed, {warnings} warnings, {failed} failed")
    
    if failed_checks and raise_on_critical:
        raise IntegrityError(
            f"Critical startup checks failed: {', '.join(failed_checks)}. "
            "The application cannot start safely."
        )
    
    return results


def get_check_summary(results: List[IntegrityCheckResult]) -> str:
    """Generate a human-readable summary of check results."""
    lines = ["Startup Integrity Check Results:", "=" * 40]
    
    for result in results:
        status_symbol = {
            CheckStatus.PASSED: "✓",
            CheckStatus.WARNING: "⚠",
            CheckStatus.FAILED: "✗"
        }.get(result.status, "?")
        
        lines.append(f"{status_symbol} {result.name}: {result.message}")
        if result.recovery_action:
            lines.append(f"   → Recovery: {result.recovery_action}")
    
    lines.append("=" * 40)
    return "\n".join(lines)
