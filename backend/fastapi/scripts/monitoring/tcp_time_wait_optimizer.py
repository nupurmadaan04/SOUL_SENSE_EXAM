#!/usr/bin/env python3
"""
TCP TIME_WAIT Socket Exhaustion Prevention - Kernel Parameter Tuning

Optimizes system TCP settings to prevent TIME_WAIT socket table overflow
from rapid database reconnections. Implements connection reuse and tuning
for high-concurrency database access.
"""

import os
import sys
import platform
import subprocess
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class TCPTuner:
    """
    TCP kernel parameter tuner for TIME_WAIT socket exhaustion prevention.

    Optimizes system settings for high-frequency database connections.
    """

    def __init__(self):
        self.system = platform.system().lower()
        self.is_admin = self._check_admin_privileges()

    def _check_admin_privileges(self) -> bool:
        """Check if running with administrative privileges."""
        try:
            if self.system == "windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False

    def get_current_settings(self) -> Dict[str, str]:
        """Get current TCP kernel parameters."""
        settings = {}

        if self.system == "linux":
            settings.update(self._get_linux_tcp_settings())
        elif self.system == "darwin":  # macOS
            settings.update(self._get_macos_tcp_settings())
        elif self.system == "windows":
            settings.update(self._get_windows_tcp_settings())

        return settings

    def _get_linux_tcp_settings(self) -> Dict[str, str]:
        """Get Linux TCP settings."""
        settings = {}
        tcp_params = [
            "net.ipv4.tcp_tw_reuse",
            "net.ipv4.tcp_tw_recycle",
            "net.ipv4.tcp_fin_timeout",
            "net.ipv4.tcp_max_tw_buckets",
            "net.ipv4.ip_local_port_range",
            "net.core.somaxconn",
            "net.ipv4.tcp_keepalive_time",
            "net.ipv4.tcp_keepalive_intvl",
            "net.ipv4.tcp_keepalive_probes"
        ]

        for param in tcp_params:
            try:
                result = subprocess.run(
                    ["sysctl", "-n", param],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    settings[param] = result.stdout.strip()
            except:
                settings[param] = "unknown"

        return settings

    def _get_macos_tcp_settings(self) -> Dict[str, str]:
        """Get macOS TCP settings."""
        settings = {}
        tcp_params = [
            "net.inet.tcp.twreusetimeout",
            "net.inet.tcp.keepidle",
            "net.inet.tcp.keepintvl",
            "net.inet.tcp.keepcnt",
            "kern.ipc.somaxconn"
        ]

        for param in tcp_params:
            try:
                result = subprocess.run(
                    ["sysctl", "-n", param],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    settings[param] = result.stdout.strip()
            except:
                settings[param] = "unknown"

        return settings

    def _get_windows_tcp_settings(self) -> Dict[str, str]:
        """Get Windows TCP settings."""
        settings = {}

        # Use netsh to get TCP settings
        try:
            result = subprocess.run(
                ["netsh", "int", "tcp", "show", "global"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                settings["netsh_tcp_global"] = result.stdout
        except:
            settings["netsh_tcp_global"] = "unknown"

        return settings

    def apply_optimizations(self) -> List[str]:
        """
        Apply TCP optimizations for TIME_WAIT prevention.

        Returns:
            List of applied changes
        """
        if not self.is_admin:
            logger.warning("Administrative privileges required for TCP tuning")
            return []

        applied = []

        if self.system == "linux":
            applied.extend(self._apply_linux_optimizations())
        elif self.system == "darwin":
            applied.extend(self._apply_macos_optimizations())
        elif self.system == "windows":
            applied.extend(self._apply_windows_optimizations())

        return applied

    def _apply_linux_optimizations(self) -> List[str]:
        """Apply Linux TCP optimizations."""
        optimizations = [
            ("net.ipv4.tcp_tw_reuse", "1"),  # Reuse TIME_WAIT sockets
            ("net.ipv4.tcp_tw_recycle", "1"),  # Recycle TIME_WAIT sockets (deprecated but still useful)
            ("net.ipv4.tcp_fin_timeout", "30"),  # Reduce TIME_WAIT timeout
            ("net.ipv4.tcp_max_tw_buckets", "65536"),  # Increase max TIME_WAIT sockets
            ("net.ipv4.ip_local_port_range", "1024 65535"),  # Maximize local port range
            ("net.core.somaxconn", "4096"),  # Increase listen backlog
            ("net.ipv4.tcp_keepalive_time", "600"),  # Keepalive timing
            ("net.ipv4.tcp_keepalive_intvl", "60"),
            ("net.ipv4.tcp_keepalive_probes", "3")
        ]

        applied = []
        for param, value in optimizations:
            try:
                result = subprocess.run(
                    ["sysctl", "-w", f"{param}={value}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    applied.append(f"{param}={value}")
                    logger.info(f"Applied: {param}={value}")
                else:
                    logger.warning(f"Failed to apply {param}={value}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error applying {param}={value}: {e}")

        return applied

    def _apply_macos_optimizations(self) -> List[str]:
        """Apply macOS TCP optimizations."""
        optimizations = [
            ("net.inet.tcp.twreusetimeout", "30000"),  # 30 seconds
            ("net.inet.tcp.keepidle", "600000"),  # 10 minutes
            ("net.inet.tcp.keepintvl", "75000"),  # 75 seconds
            ("net.inet.tcp.keepcnt", "8"),
            ("kern.ipc.somaxconn", "4096")
        ]

        applied = []
        for param, value in optimizations:
            try:
                result = subprocess.run(
                    ["sudo", "sysctl", "-w", f"{param}={value}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    applied.append(f"{param}={value}")
                    logger.info(f"Applied: {param}={value}")
                else:
                    logger.warning(f"Failed to apply {param}={value}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error applying {param}={value}: {e}")

        return applied

    def _apply_windows_optimizations(self) -> List[str]:
        """Apply Windows TCP optimizations."""
        applied = []

        # Windows optimizations via netsh
        optimizations = [
            ["netsh", "int", "tcp", "set", "global", "timestamps=enabled"],
            ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
            ["netsh", "int", "tcp", "set", "global", "chimney=disabled"],
            ["netsh", "int", "tcp", "set", "global", "netdma=disabled"],
            ["netsh", "int", "tcp", "set", "global", "dca=disabled"],
            ["netsh", "int", "tcp", "set", "global", "congestionprovider=ctcp"]
        ]

        for cmd in optimizations:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    applied.append(" ".join(cmd))
                    logger.info(f"Applied: {' '.join(cmd)}")
                else:
                    logger.warning(f"Failed to apply {' '.join(cmd)}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error applying {' '.join(cmd)}: {e}")

        return applied

    def make_persistent(self) -> bool:
        """
        Make TCP optimizations persistent across reboots.

        Returns:
            True if successful
        """
        if not self.is_admin:
            return False

        try:
            if self.system == "linux":
                return self._make_linux_persistent()
            elif self.system == "darwin":
                return self._make_macos_persistent()
            elif self.system == "windows":
                return self._make_windows_persistent()
        except Exception as e:
            logger.error(f"Failed to make optimizations persistent: {e}")

        return False

    def _make_linux_persistent(self) -> bool:
        """Make Linux optimizations persistent."""
        sysctl_conf = "/etc/sysctl.conf"
        optimizations = [
            "net.ipv4.tcp_tw_reuse = 1",
            "net.ipv4.tcp_tw_recycle = 1",
            "net.ipv4.tcp_fin_timeout = 30",
            "net.ipv4.tcp_max_tw_buckets = 65536",
            "net.ipv4.ip_local_port_range = 1024 65535",
            "net.core.somaxconn = 4096"
        ]

        try:
            with open(sysctl_conf, 'a') as f:
                f.write("\n# TCP TIME_WAIT optimizations for Soul Sense\n")
                for opt in optimizations:
                    f.write(f"{opt}\n")

            # Apply immediately
            subprocess.run(["sysctl", "-p"], check=True)
            logger.info("Linux TCP optimizations made persistent")
            return True
        except Exception as e:
            logger.error(f"Failed to make Linux optimizations persistent: {e}")
            return False

    def _make_macos_persistent(self) -> bool:
        """Make macOS optimizations persistent."""
        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.soulsense.tcp-tuning</string>
    <key>ProgramArguments</key>
    <array>
        <string>sysctl</string>
        <string>-w</string>
        <string>net.inet.tcp.twreusetimeout=30000</string>
        <string>net.inet.tcp.keepidle=600000</string>
        <string>net.inet.tcp.keepintvl=75000</string>
        <string>net.inet.tcp.keepcnt=8</string>
        <string>kern.ipc.somaxconn=4096</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""

        plist_path = "/Library/LaunchDaemons/com.soulsense.tcp-tuning.plist"

        try:
            with open(plist_path, 'w') as f:
                f.write(plist_content)

            subprocess.run(["chmod", "644", plist_path], check=True)
            subprocess.run(["launchctl", "load", plist_path], check=True)

            logger.info("macOS TCP optimizations made persistent")
            return True
        except Exception as e:
            logger.error(f"Failed to make macOS optimizations persistent: {e}")
            return False

    def _make_windows_persistent(self) -> bool:
        """Make Windows optimizations persistent."""
        # Windows optimizations are typically persistent by default
        # We could create a scheduled task or registry entries, but for now
        # just log that manual persistence may be needed
        logger.info("Windows TCP optimizations applied (may require manual persistence)")
        return True


def optimize_tcp_settings(make_persistent: bool = False) -> Dict:
    """
    Optimize TCP settings for TIME_WAIT prevention.

    Args:
        make_persistent: Whether to make changes persistent across reboots

    Returns:
        Dictionary with optimization results
    """
    tuner = TCPTuner()

    result = {
        "system": tuner.system,
        "is_admin": tuner.is_admin,
        "current_settings": tuner.get_current_settings(),
        "applied_optimizations": [],
        "persistent": False,
        "success": False
    }

    if not tuner.is_admin:
        logger.warning("TCP tuning requires administrative privileges")
        return result

    logger.info(f"Optimizing TCP settings for {tuner.system}")

    # Apply optimizations
    result["applied_optimizations"] = tuner.apply_optimizations()

    if make_persistent:
        result["persistent"] = tuner.make_persistent()

    result["success"] = len(result["applied_optimizations"]) > 0

    if result["success"]:
        logger.info(f"Successfully applied {len(result['applied_optimizations'])} TCP optimizations")
    else:
        logger.warning("No TCP optimizations were applied")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TCP TIME_WAIT Socket Exhaustion Prevention")
    parser.add_argument("--persistent", action="store_true",
                       help="Make optimizations persistent across reboots")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show current settings without applying changes")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')

    if args.dry_run:
        tuner = TCPTuner()
        print("Current TCP Settings:")
        for key, value in tuner.get_current_settings().items():
            print(f"  {key}: {value}")
    else:
        result = optimize_tcp_settings(make_persistent=args.persistent)

        print(f"System: {result['system']}")
        print(f"Admin privileges: {result['is_admin']}")
        print(f"Optimizations applied: {len(result['applied_optimizations'])}")
        print(f"Persistent: {result['persistent']}")
        print(f"Success: {result['success']}")

        if result['applied_optimizations']:
            print("\nApplied optimizations:")
            for opt in result['applied_optimizations']:
                print(f"  ✓ {opt}")