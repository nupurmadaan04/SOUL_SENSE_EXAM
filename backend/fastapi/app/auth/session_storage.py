"""
Session Storage Utilities for Remember Me Feature
=================================================
Manages persistent session storage for auto-login functionality.
"""

import os
import json
import time
import hmac
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
import logging

SESSION_FILE = (
    Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    / "app_data"
    / "session.json"
)
SECRET_KEY_FILE = (
    Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    / "app_data"
    / ".session_key"
)
SESSION_MAX_AGE_DAYS = 30


def _get_or_create_secret_key() -> bytes:
    secret = os.environ.get("SOUL_SENSE_SESSION_SECRET")
    if secret:
        return secret.encode("utf-8")

    if SECRET_KEY_FILE.exists():
        try:
            with open(SECRET_KEY_FILE, "r") as f:
                return f.read().strip().encode("utf-8")
        except Exception:
            pass

    new_key = secrets.token_hex(32)
    try:
        SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SECRET_KEY_FILE, "w") as f:
            f.write(new_key)
        os.chmod(SECRET_KEY_FILE, 0o600)
    except Exception as e:
        logging.error(f"Failed to store session secret key: {e}")

    return new_key.encode("utf-8")


def _compute_signature(data: Dict[str, Any], secret: bytes) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _ensure_session_dir():
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_session(username: str, remember_me: bool = False) -> bool:
    if not remember_me:
        clear_session()
        return True

    try:
        _ensure_session_dir()
        secret = _get_or_create_secret_key()

        session_data = {
            "username": username,
            "login_time": time.time(),
            "expires_at": time.time() + (SESSION_MAX_AGE_DAYS * 24 * 60 * 60),
        }

        signature = _compute_signature(session_data, secret)
        signed_session = {"data": session_data, "signature": signature}

        with open(SESSION_FILE, "w") as f:
            json.dump(signed_session, f, indent=2)

        logging.info(f"Session saved for user: {username}")
        return True
    except Exception as e:
        logging.error(f"Failed to save session: {e}")
        return False


def get_session() -> Optional[Dict[str, Any]]:
    try:
        if not SESSION_FILE.exists():
            return None

        secret = _get_or_create_secret_key()

        with open(SESSION_FILE, "r") as f:
            signed_session = json.load(f)

        if not all(k in signed_session for k in ["data", "signature"]):
            clear_session()
            return None

        session_data = signed_session["data"]
        stored_signature = signed_session["signature"]

        if not all(k in session_data for k in ["username", "login_time", "expires_at"]):
            clear_session()
            return None

        expected_signature = _compute_signature(session_data, secret)

        if not hmac.compare_digest(stored_signature, expected_signature):
            logging.warning(
                "Session signature verification failed - possible tampering detected"
            )
            clear_session()
            return None

        return session_data
    except Exception as e:
        logging.error(f"Failed to read session: {e}")
        return None


def is_session_valid() -> bool:
    session = get_session()
    if not session:
        return False

    if time.time() > session.get("expires_at", 0):
        clear_session()
        return False

    return True


def get_saved_username() -> Optional[str]:
    if is_session_valid():
        session = get_session()
        return session.get("username") if session else None
    return None


def clear_session() -> bool:
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
            logging.info("Session cleared")
        return True
    except Exception as e:
        logging.error(f"Failed to clear session: {e}")
        return False
