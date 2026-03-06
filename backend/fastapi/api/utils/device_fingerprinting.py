"""
Device Fingerprinting Utility for Session Binding

This module provides device fingerprinting capabilities to bind user sessions
to specific devices, preventing token theft and misuse while allowing for
controlled drift tolerance.

Key Features:
- Captures comprehensive device metadata hash
- Implements configurable drift tolerance
- Logs fingerprint mismatch attempts
- Supports various device attributes for fingerprinting
"""

import hashlib
import json
import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
UTC = timezone.utc

logger = logging.getLogger(__name__)


@dataclass
class DeviceFingerprint:
    """Represents a device fingerprint with metadata."""
    fingerprint_hash: str
    user_agent: str
    ip_address: str
    accept_language: str
    accept_encoding: str
    screen_resolution: Optional[str] = None
    timezone_offset: Optional[int] = None
    platform: Optional[str] = None
    do_not_track: Optional[str] = None
    cookie_enabled: Optional[bool] = None
    plugins: Optional[str] = None
    canvas_fingerprint: Optional[str] = None
    webgl_fingerprint: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


class DeviceFingerprinting:
    """Handles device fingerprinting and drift tolerance validation."""

    # Drift tolerance thresholds (configurable)
    DRIFT_THRESHOLDS = {
        'user_agent_minor': 0.1,  # Allow minor user agent changes (browser updates)
        'ip_address_change': 0.3,  # Allow IP changes (VPN, mobile networks)
        'language_change': 0.2,   # Allow language preference changes
        'timezone_change': 0.1,   # Allow timezone changes
        'platform_change': 0.0,   # Platform changes not allowed (OS changes)
        'screen_resolution_change': 0.1,  # Allow resolution changes
    }

    @staticmethod
    def extract_fingerprint_from_request(request) -> DeviceFingerprint:
        """
        Extract device fingerprint from FastAPI request object.

        Captures comprehensive device metadata for fingerprinting.
        """
        headers = dict(request.headers)

        # Extract key fingerprinting attributes
        user_agent = headers.get('user-agent', '')
        ip_address = getattr(request.client, 'host', '') if request.client else ''
        accept_language = headers.get('accept-language', '')
        accept_encoding = headers.get('accept-encoding', '')

        # Extract additional fingerprinting data
        screen_resolution = headers.get('x-screen-resolution', None)
        timezone_offset = headers.get('x-timezone-offset', None)
        platform = headers.get('sec-ch-ua-platform', headers.get('x-platform', None))
        do_not_track = headers.get('dnt', None)
        cookie_enabled = headers.get('x-cookie-enabled', None)

        # Extract plugin and hardware fingerprints (if available)
        plugins = headers.get('x-plugins-hash', None)
        canvas_fingerprint = headers.get('x-canvas-fingerprint', None)
        webgl_fingerprint = headers.get('x-webgl-fingerprint', None)

        # Create fingerprint object
        fingerprint = DeviceFingerprint(
            fingerprint_hash="",  # Will be calculated
            user_agent=user_agent,
            ip_address=ip_address,
            accept_language=accept_language,
            accept_encoding=accept_encoding,
            screen_resolution=screen_resolution,
            timezone_offset=int(timezone_offset) if timezone_offset else None,
            platform=platform,
            do_not_track=do_not_track,
            cookie_enabled=cookie_enabled.lower() == 'true' if cookie_enabled else None,
            plugins=plugins,
            canvas_fingerprint=canvas_fingerprint,
            webgl_fingerprint=webgl_fingerprint
        )

        # Calculate fingerprint hash
        fingerprint.fingerprint_hash = DeviceFingerprinting.calculate_fingerprint_hash(fingerprint)

        return fingerprint

    @staticmethod
    def calculate_fingerprint_hash(fingerprint: DeviceFingerprint) -> str:
        """
        Calculate a stable hash of the device fingerprint.

        Uses SHA-256 with selected attributes for consistent fingerprinting.
        """
        # Select stable fingerprinting attributes
        fingerprint_data = {
            'user_agent': fingerprint.user_agent,
            'accept_language': fingerprint.accept_language,
            'accept_encoding': fingerprint.accept_encoding,
            'platform': fingerprint.platform,
            'screen_resolution': fingerprint.screen_resolution,
            'timezone_offset': fingerprint.timezone_offset,
            'plugins': fingerprint.plugins,
            'canvas_fingerprint': fingerprint.canvas_fingerprint,
            'webgl_fingerprint': fingerprint.webgl_fingerprint,
        }

        # Remove None values and sort for consistency
        clean_data = {k: v for k, v in fingerprint_data.items() if v is not None}
        sorted_data = json.dumps(clean_data, sort_keys=True)

        # Calculate hash
        return hashlib.sha256(sorted_data.encode('utf-8')).hexdigest()

    @staticmethod
    def calculate_drift_score(old_fingerprint: DeviceFingerprint, new_fingerprint: DeviceFingerprint) -> float:
        """
        Calculate drift score between two fingerprints.

        Returns a score from 0.0 (identical) to 1.0 (completely different).
        """
        differences = 0
        total_attributes = 0

        # Compare each attribute
        attributes_to_compare = [
            ('user_agent', 'user_agent_minor'),
            ('ip_address', 'ip_address_change'),
            ('accept_language', 'language_change'),
            ('platform', 'platform_change'),
            ('screen_resolution', 'screen_resolution_change'),
        ]

        for attr, threshold_key in attributes_to_compare:
            old_value = getattr(old_fingerprint, attr)
            new_value = getattr(new_fingerprint, attr)

            if old_value is not None or new_value is not None:
                total_attributes += 1
                if old_value != new_value:
                    differences += 1

        # Compare timezone offset
        if old_fingerprint.timezone_offset is not None or new_fingerprint.timezone_offset is not None:
            total_attributes += 1
            if old_fingerprint.timezone_offset != new_fingerprint.timezone_offset:
                differences += 1

        # Calculate drift score
        if total_attributes == 0:
            return 0.0

        return min(differences / total_attributes, 1.0)

    @staticmethod
    def is_drift_acceptable(old_fingerprint: DeviceFingerprint, new_fingerprint: DeviceFingerprint) -> Tuple[bool, float, str]:
        """
        Determine if fingerprint drift is acceptable.

        Returns (is_acceptable, drift_score, reason)
        """
        drift_score = DeviceFingerprinting.calculate_drift_score(old_fingerprint, new_fingerprint)

        # Check against thresholds
        if drift_score <= DeviceFingerprinting.DRIFT_THRESHOLDS['user_agent_minor']:
            return True, drift_score, "Minor drift within acceptable range"

        if drift_score <= DeviceFingerprinting.DRIFT_THRESHOLDS['ip_address_change']:
            return True, drift_score, "IP address change (VPN/mobile network)"

        if drift_score <= DeviceFingerprinting.DRIFT_THRESHOLDS['language_change']:
            return True, drift_score, "Language preference change"

        if drift_score <= DeviceFingerprinting.DRIFT_THRESHOLDS['timezone_change']:
            return True, drift_score, "Timezone change"

        # Major changes not allowed
        if drift_score > DeviceFingerprinting.DRIFT_THRESHOLDS['platform_change']:
            return False, drift_score, "Platform/OS change detected"

        return False, drift_score, f"Drift score {drift_score:.2f} exceeds acceptable threshold"

    @staticmethod
    def normalize_fingerprint_data(fingerprint_data: Dict[str, Any]) -> DeviceFingerprint:
        """
        Normalize fingerprint data from database into DeviceFingerprint object.
        """
        return DeviceFingerprint(
            fingerprint_hash=fingerprint_data.get('fingerprint_hash', ''),
            user_agent=fingerprint_data.get('user_agent', ''),
            ip_address=fingerprint_data.get('ip_address', ''),
            accept_language=fingerprint_data.get('accept_language', ''),
            accept_encoding=fingerprint_data.get('accept_encoding', ''),
            screen_resolution=fingerprint_data.get('screen_resolution'),
            timezone_offset=fingerprint_data.get('timezone_offset'),
            platform=fingerprint_data.get('platform'),
            do_not_track=fingerprint_data.get('do_not_track'),
            cookie_enabled=fingerprint_data.get('cookie_enabled'),
            plugins=fingerprint_data.get('plugins'),
            canvas_fingerprint=fingerprint_data.get('canvas_fingerprint'),
            webgl_fingerprint=fingerprint_data.get('webgl_fingerprint'),
            created_at=fingerprint_data.get('created_at')
        )