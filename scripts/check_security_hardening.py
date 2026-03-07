#!/usr/bin/env python3
"""
Security Hardening Status Checker for SoulSense
================================================

Scans the codebase for implemented security controls and emits a summary.
Maps directly to docs/SECURITY_HARDENING_CHECKLIST.md.

Usage:
    python scripts/check_security_hardening.py          # coloured terminal output
    python scripts/check_security_hardening.py --json    # machine-readable JSON
    python scripts/check_security_hardening.py --ci      # exit 1 if any required check fails
"""

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

# Resolve project root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Check:
    id: str
    category: str
    description: str
    required: bool
    files: List[str]          # relative paths to inspect
    pattern: str              # regex pattern to search for
    status: Optional[str] = None   # PASS / FAIL / PARTIAL
    detail: str = ""


@dataclass
class Report:
    passed: int = 0
    failed: int = 0
    partial: int = 0
    total: int = 0
    checks: List[Check] = field(default_factory=list)

    @property
    def all_required_pass(self) -> bool:
        return all(c.status == "PASS" for c in self.checks if c.required)


# ---------------------------------------------------------------------------
# Check definitions — mirrors the checklist doc sections
# ---------------------------------------------------------------------------

CHECKS: List[Check] = [
    # 1. Authentication
    Check("A-1", "Authentication", "bcrypt password hashing (>=12 rounds)", True,
          ["app/auth/auth.py", "app/security_config.py"],
          r"bcrypt\.gensalt\(rounds=|PASSWORD_HASH_ROUNDS\s*=\s*(?:1[2-9]|[2-9]\d)"),
    Check("A-2", "Authentication", "Password complexity validation", True,
          ["app/validation.py"],
          r"def validate_password_security|validate_password"),
    Check("A-3", "Authentication", "Account lockout after failed attempts", True,
          ["app/auth/auth.py", "app/security_config.py"],
          r"MAX_LOGIN_ATTEMPTS|failed_attempts|lockout"),
    Check("A-4", "Authentication", "Cryptographic session tokens (256-bit)", True,
          ["app/auth/auth.py"],
          r"secrets\.token_urlsafe\(32\)"),
    Check("A-5", "Authentication", "Session expiry enforced", True,
          ["app/security_config.py"],
          r"SESSION_TIMEOUT_HOURS\s*="),
    Check("A-6", "Authentication", "Idle-timeout auto-logout", True,
          ["app/auth/idle_watcher.py"],
          r"class IdleWatcher|timeout_seconds"),
    Check("A-7", "Authentication", "Timing-safe login (dummy verify on missing user)", False,
          ["app/auth/auth.py"],
          r"dummy|constant_time|timing|bcrypt.*fake"),
    Check("A-8", "Authentication", "Reserved usernames blocked", True,
          ["app/validation.py"],
          r"RESERVED_USERNAMES"),

    # 2. Two-Factor Authentication
    Check("2FA-1", "2FA / OTP", "OTP hashed before storage (SHA-256)", True,
          ["app/auth/otp_manager.py"],
          r"hashlib\.sha256|_hash_code"),
    Check("2FA-2", "2FA / OTP", "OTP rate limit (60s)", True,
          ["app/auth/otp_manager.py"],
          r"RATE_LIMIT_SECONDS\s*=\s*60"),
    Check("2FA-3", "2FA / OTP", "Max OTP verification attempts", True,
          ["app/auth/otp_manager.py"],
          r"MAX_VERIFY_ATTEMPTS\s*=\s*3"),

    # 3. Rate Limiting
    Check("RL-1", "Rate Limiting", "Global API rate limit configured", True,
          ["app/security_config.py"],
          r"MAX_REQUESTS_PER_MINUTE\s*="),
    Check("RL-2", "Rate Limiting", "Analytics API rate limiter", True,
          ["backend/fastapi/api/middleware/rate_limiter.py"],
          r"analytics_rate_limiter|requests_per_minute"),
    Check("RL-3", "Rate Limiting", "Login attempt throttling", True,
          ["app/auth/auth.py"],
          r"failed_attempts|lockout_duration|LOCKOUT_DURATION"),

    # 4. Input Validation
    Check("IV-1", "Input Validation", "SQL injection detection patterns", True,
          ["app/validation.py"],
          r"SQL_INJECTION_PATTERNS"),
    Check("IV-2", "Input Validation", "XSS detection patterns", True,
          ["app/validation.py"],
          r"XSS_PATTERNS"),
    Check("IV-3", "Input Validation", "HTML entity escaping (sanitize_text)", True,
          ["app/validation.py"],
          r"html\.escape|sanitize_text"),
    Check("IV-4", "Input Validation", "Max input length enforcement", True,
          ["app/security_config.py"],
          r"MAX_INPUT_LENGTH\s*="),
    Check("IV-5", "Input Validation", "Email strict validation", True,
          ["app/validation.py"],
          r"validate_email_strict|EMAIL_REGEX_STRICT"),

    # 5. File Security
    Check("FS-1", "File Security", "File extension whitelist", True,
          ["app/security_config.py"],
          r"ALLOWED_FILE_EXTENSIONS"),
    Check("FS-2", "File Security", "File size limit", True,
          ["app/security_config.py"],
          r"MAX_FILE_SIZE_MB\s*="),
    Check("FS-3", "File Security", "Path traversal prevention", True,
          ["app/utils/file_validation.py"],
          r"traversal|\.\."),

    # 6. RBAC / Access Control
    Check("AC-1", "Access Control", "Reserved username protection", True,
          ["app/validation.py"],
          r"RESERVED_USERNAMES"),
    Check("AC-2", "Access Control", "Formal RBAC role model", False,
          ["app/models.py"],
          r"class Role|role_id|user_role"),

    # 7. Secrets Management
    Check("S-1", "Secrets Management", ".env excluded from version control", True,
          [".gitignore"],
          r"\.env"),
    Check("S-2", "Secrets Management", "dotenv loaded at startup", True,
          ["app/config.py"],
          r"load_dotenv"),
    Check("S-3", "Secrets Management", "Environment validator for required secrets", True,
          ["backend/core/validators.py"],
          r"class EnvironmentValidator|validate_required"),
    Check("S-4", "Secrets Management", "No hardcoded master key in production", False,
          ["app/auth/crypto.py"],
          r"os\.environ|env_var|getenv.*key"),

    # 8. PII Redaction
    Check("PII-1", "PII Redaction", "Audit log detail-field allowlist", True,
          ["app/services/audit_service.py"],
          r"ALLOWED_DETAIL_FIELDS"),
    Check("PII-2", "PII Redaction", "User-agent truncation in audit logs", True,
          ["app/services/audit_service.py"],
          r"safe_ua|truncat|250"),
    Check("PII-3", "PII Redaction", "Data-at-rest encryption (Fernet)", True,
          ["app/auth/crypto.py"],
          r"Fernet|PBKDF2HMAC"),
    Check("PII-4", "PII Redaction", "PII masking in log files", False,
          ["app/logger.py"],
          r"mask|redact|pii"),

    # 9. Security Headers
    Check("H-1", "Security Headers", "X-Content-Type-Options: nosniff", True,
          ["app/security_config.py"],
          r"X-Content-Type-Options.*nosniff"),
    Check("H-2", "Security Headers", "X-Frame-Options: DENY", True,
          ["app/security_config.py"],
          r"X-Frame-Options.*DENY"),
    Check("H-3", "Security Headers", "HSTS header configured", True,
          ["app/security_config.py"],
          r"Strict-Transport-Security"),
    Check("H-4", "Security Headers", "SecurityHeadersMiddleware on all responses", True,
          ["backend/fastapi/api/middleware/security.py"],
          r"SecurityHeaders|security_headers"),

    # 10. Audit Logging
    Check("L-1", "Audit Logging", "Centralized audit service", True,
          ["app/services/audit_service.py"],
          r"class AuditService"),
    Check("L-2", "Audit Logging", "Rotating log files (10 MB / 5 backups)", True,
          ["app/logger.py"],
          r"RotatingFileHandler|MAX_BYTES|BACKUP_COUNT"),
    Check("L-3", "Audit Logging", "Separate error log stream", True,
          ["app/logger.py"],
          r"ERROR_LOG_FILE|soulsense_errors"),
    Check("L-4", "Audit Logging", "DB-failure fallback logging", True,
          ["app/services/audit_service.py"],
          r"logger\.critical|AUDIT LOG FAILURE"),

    # 11. Database Security
    Check("DB-1", "Database Security", "Connection timeout configured", True,
          ["app/security_config.py"],
          r"DB_CONNECTION_TIMEOUT\s*="),
    Check("DB-2", "Database Security", "Connection pool bounded", True,
          ["app/security_config.py"],
          r"DB_POOL_SIZE\s*="),
    Check("DB-3", "Database Security", "ORM parameterised queries (SQLAlchemy)", True,
          ["app/db.py"],
          r"sqlalchemy|create_engine|Session"),

    # 12. Error Handling
    Check("EH-1", "Error Handling", "Custom exception hierarchy", True,
          ["app/exceptions.py"],
          r"class SoulSenseError|class.*Error.*Exception"),
    Check("EH-2", "Error Handling", "safe_operation decorator", True,
          ["app/error_handler.py"],
          r"safe_operation|def safe_"),
]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _read_file(rel_path: str) -> str:
    """Read a project file by relative path. Return empty string if missing."""
    full = ROOT / rel_path
    if not full.is_file():
        return ""
    return full.read_text(encoding="utf-8", errors="replace")


def run_checks() -> Report:
    """Execute every check and return a Report."""
    report = Report(total=len(CHECKS))

    for chk in CHECKS:
        found = False
        for rel in chk.files:
            content = _read_file(rel)
            if not content:
                continue
            if re.search(chk.pattern, content, re.IGNORECASE):
                found = True
                break

        if found:
            chk.status = "PASS"
            report.passed += 1
        else:
            # Check if file exists but pattern not found → PARTIAL
            any_file_exists = any((ROOT / r).is_file() for r in chk.files)
            if any_file_exists:
                chk.status = "PARTIAL"
                chk.detail = "File exists but pattern not matched"
                report.partial += 1
            else:
                chk.status = "FAIL"
                chk.detail = "Implementation file(s) not found"
                report.failed += 1

        report.checks.append(chk)

    return report


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

_ICONS = {"PASS": "\u2705", "FAIL": "\u274c", "PARTIAL": "\u26a0\ufe0f"}


def print_terminal(report: Report) -> None:
    """Pretty-print the report to stdout."""
    print()
    print("=" * 68)
    print("   SoulSense — Security Hardening Status")
    print("=" * 68)

    current_cat = ""
    for chk in report.checks:
        if chk.category != current_cat:
            current_cat = chk.category
            print(f"\n  [{current_cat}]")

        icon = _ICONS.get(chk.status, "?")
        req = "REQ" if chk.required else "OPT"
        line = f"    {icon} {chk.id:<8} [{req}] {chk.description}"
        if chk.detail:
            line += f"  ({chk.detail})"
        print(line)

    print()
    print("-" * 68)
    print(f"  TOTAL: {report.total}   "
          f"PASS: {report.passed}   "
          f"PARTIAL: {report.partial}   "
          f"FAIL: {report.failed}")

    req_pass = sum(1 for c in report.checks if c.required and c.status == "PASS")
    req_total = sum(1 for c in report.checks if c.required)
    req_fail = req_total - req_pass

    if req_fail:
        print(f"  REQUIRED checks failing: {req_fail}/{req_total}")
    else:
        print(f"  All {req_total} REQUIRED checks passing.")

    print("-" * 68)
    print("  Checklist: docs/SECURITY_HARDENING_CHECKLIST.md")
    print("=" * 68)
    print()


def print_json(report: Report) -> None:
    """Emit the report as JSON for CI integration."""
    out = {
        "summary": {
            "total": report.total,
            "passed": report.passed,
            "partial": report.partial,
            "failed": report.failed,
            "all_required_pass": report.all_required_pass,
        },
        "checks": [
            {
                "id": c.id,
                "category": c.category,
                "description": c.description,
                "required": c.required,
                "status": c.status,
                "detail": c.detail,
                "files": c.files,
            }
            for c in report.checks
        ],
    }
    print(json.dumps(out, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    report = run_checks()

    if "--json" in args:
        print_json(report)
    else:
        print_terminal(report)

    # In --ci mode, exit 1 when any required check is not PASS
    if "--ci" in args and not report.all_required_pass:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
