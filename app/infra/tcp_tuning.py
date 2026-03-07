import os
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    PASSED = "passed"
    MISMATCH = "mismatch"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"

@dataclass
class TCPParameter:
    name: str  # sysctl parameter name (e.g., 'net.ipv4.tcp_rmem')
    expected_value: Any
    description: str
    impact: str

@dataclass
class ValidationResult:
    parameter: str
    status: ValidationStatus
    expected: Any
    actual: Optional[Any] = None
    message: str = ""

# Approved TCP Tuning Profiles
# Values based on high-concurrency Linux server best practices
TCP_TUNING_PROFILES = {
    "default": [
        TCPParameter("net.core.somaxconn", 1024, "Max backlog connections", "Reduces connection drops under load"),
        TCPParameter("net.ipv4.tcp_max_syn_backlog", 2048, "Max pending TCP connections", "Protects against SYN flood and slow starts"),
        TCPParameter("net.ipv4.tcp_fin_timeout", 15, "Seconds to wait for FIN packet", "Quickly frees up resources from closed connections"),
        TCPParameter("net.ipv4.tcp_keepalive_time", 300, "Keepalive interval", "Detects dead connections early"),
        TCPParameter("net.ipv4.tcp_tw_reuse", 1, "Allow reuse of TIME-WAIT sockets", "Efficiently handles high connection churn"),
    ],
    "high_performance": [
        TCPParameter("net.core.somaxconn", 4096, "Max backlog connections", "Supports very high concurrency"),
        TCPParameter("net.ipv4.tcp_max_syn_backlog", 8192, "Max pending TCP connections", "Supports very high concurrency"),
        TCPParameter("net.ipv4.tcp_rmem", "4096 87380 6291456", "TCP receive buffer sizes", "Optimized memory for large receive windows"),
        TCPParameter("net.ipv4.tcp_wmem", "4096 16384 4194304", "TCP send buffer sizes", "Optimized memory for large send windows"),
        TCPParameter("net.ipv4.tcp_tw_reuse", 1, "Allow reuse of TIME-WAIT sockets", "Prevents socket exhaustion"),
    ]
}

class TCPTuningValidator:
    def __init__(self, profile_name: str = "default"):
        self.profile_name = profile_name
        self.parameters = TCP_TUNING_PROFILES.get(profile_name, TCP_TUNING_PROFILES["default"])

    def get_sysctl_value(self, name: str) -> Optional[str]:
        """Reads a sysctl value from the filesystem."""
        try:
            # Convert net.ipv4.tcp_rmem to /proc/sys/net/ipv4/tcp_rmem
            path = os.path.join("/proc/sys", name.replace(".", "/"))
            if not os.path.exists(path):
                return None
            with open(path, "r") as f:
                return f.read().strip()
        except (PermissionError, IOError) as e:
            logger.error(f"Failed to read sysctl {name}: {e}")
            return None

    def validate_all(self) -> List[ValidationResult]:
        """Validates all parameters in the current profile."""
        results = []
        if os.name != "posix":
            logger.warning("TCP tuning validation skipped on non-Linux OS")
            return [ValidationResult("os_check", ValidationStatus.NOT_APPLICABLE, "Linux", os.name, "Only supported on Linux")]

        for param in self.parameters:
            actual = self.get_sysctl_value(param.name)
            if actual is None:
                results.append(ValidationResult(param.name, ValidationStatus.ERROR, param.expected_value, None, "Could not read parameter"))
                continue
            
            # Simple string comparison for now; might need smarter parsing for ranged types like tcp_rmem
            is_match = str(actual) == str(param.expected_value)
            status = ValidationStatus.PASSED if is_match else ValidationStatus.MISMATCH
            
            results.append(ValidationResult(
                param.name, 
                status, 
                param.expected_value, 
                actual,
                "" if is_match else f"Expected {param.expected_value}, got {actual}"
            ))
        return results

    def generate_rollback_script(self) -> str:
        """Generates a shell script to restore current values before changes."""
        lines = ["#!/bin/bash", "# Auto-generated rollback script for TCP tuning", ""]
        for param in self.parameters:
            current = self.get_sysctl_value(param.name)
            if current:
                lines.append(f"sysctl -w {param.name}='{current}'")
        return "\n".join(lines)

    def export_metrics(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Exports metrics for observability."""
        total = len(results)
        passed = sum(1 for r in results if r.status == ValidationStatus.PASSED)
        mismatches = sum(1 for r in results if r.status == ValidationStatus.MISMATCH)
        errors = sum(1 for r in results if r.status == ValidationStatus.ERROR)
        
        return {
            "tcp_tuning_profile": self.profile_name,
            "tcp_tuning_total_params": total,
            "tcp_tuning_passed": passed,
            "tcp_tuning_mismatches": mismatches,
            "tcp_tuning_errors": errors,
            "tcp_tuning_status": "healthy" if mismatches == 0 and errors == 0 else "unhealthy"
        }
