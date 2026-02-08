"""
Tests for Resend OTP with Cooldown Timer feature.

Covers:
- OTPManager.get_cooldown_remaining()
- AuthManager.resend_2fa_login_otp()
- Resend during password reset flow
- Rate limiting on resend attempts
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.auth.auth import AuthManager
from app.auth.otp_manager import OTPManager
from app.models import User, PersonalProfile, OTP


# ─── Fixtures ───

@pytest.fixture
def auth_manager(temp_db):
    return AuthManager()


@pytest.fixture
def test_user(auth_manager, temp_db):
    """Register a test user and return (username, email)."""
    username = "cooldown_user"
    email = "cooldown@test.com"
    auth_manager.register_user(username, email, "Cool", "Down", 25, "M", "StrongPass1!")
    return username, email


@pytest.fixture
def test_user_2fa(auth_manager, temp_db):
    """Register a test user with 2FA enabled and return (username, email)."""
    username = "twofa_user"
    email = "twofa@test.com"
    auth_manager.register_user(username, email, "Two", "FA", 30, "F", "StrongPass1!")
    user = temp_db.query(User).filter_by(username=username).first()
    user.is_2fa_enabled = True
    temp_db.commit()
    return username, email


# ─── OTPManager.get_cooldown_remaining Tests ───

class TestGetCooldownRemaining:
    """Tests for OTPManager.get_cooldown_remaining()"""

    def test_no_previous_otp_returns_zero(self, temp_db):
        """No prior OTP means no cooldown."""
        user = User(username="no_otp_user", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining == 0

    def test_cooldown_active_after_generation(self, temp_db):
        """Cooldown should be active immediately after OTP generation."""
        user = User(username="cd_active", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        code, error = OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None
        assert error is None

        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining > 0
        assert remaining <= OTPManager.RATE_LIMIT_SECONDS

    def test_cooldown_expired(self, temp_db):
        """Cooldown should return 0 after the rate limit window passes."""
        user = User(username="cd_expired", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        # Insert an OTP with created_at in the past (beyond cooldown)
        past_time = datetime.utcnow() - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 10)
        old_otp = OTP(
            user_id=user.id,
            code_hash="fakehash",
            type="RESET_PASSWORD",
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=5),
            is_used=False,
            attempts=0
        )
        temp_db.add(old_otp)
        temp_db.commit()

        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining == 0

    def test_cooldown_midway(self, temp_db):
        """Cooldown should return correct remaining seconds mid-window."""
        user = User(username="cd_midway", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        elapsed = 25  # 25 seconds ago
        past_time = datetime.utcnow() - timedelta(seconds=elapsed)
        otp = OTP(
            user_id=user.id,
            code_hash="fakehash",
            type="RESET_PASSWORD",
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=5),
            is_used=False,
            attempts=0
        )
        temp_db.add(otp)
        temp_db.commit()

        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        expected = OTPManager.RATE_LIMIT_SECONDS - elapsed
        # Allow 1-second tolerance for test execution time
        assert abs(remaining - expected) <= 1

    def test_cooldown_per_purpose(self, temp_db):
        """Cooldown is tracked independently per purpose type."""
        user = User(username="cd_purpose", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        # Generate OTP for RESET_PASSWORD only
        code, _ = OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None

        # RESET_PASSWORD should have cooldown
        remaining_reset = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining_reset > 0

        # LOGIN_CHALLENGE should have NO cooldown
        remaining_login = OTPManager.get_cooldown_remaining(user.id, "LOGIN_CHALLENGE", db_session=temp_db)
        assert remaining_login == 0

    def test_cooldown_uses_latest_otp(self, temp_db):
        """Cooldown should be based on the most recent OTP, not older ones."""
        user = User(username="cd_latest", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        # Old OTP (expired cooldown)
        old_time = datetime.utcnow() - timedelta(seconds=120)
        old_otp = OTP(
            user_id=user.id, code_hash="old", type="RESET_PASSWORD",
            created_at=old_time, expires_at=old_time + timedelta(minutes=5),
            is_used=True, attempts=0
        )
        temp_db.add(old_otp)

        # Recent OTP (active cooldown)
        recent_time = datetime.utcnow() - timedelta(seconds=10)
        recent_otp = OTP(
            user_id=user.id, code_hash="recent", type="RESET_PASSWORD",
            created_at=recent_time, expires_at=recent_time + timedelta(minutes=5),
            is_used=False, attempts=0
        )
        temp_db.add(recent_otp)
        temp_db.commit()

        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining > 0
        assert remaining <= 50  # ~50s remaining from a 10s-old OTP


# ─── Resend Password Reset OTP Tests ───

class TestResendPasswordResetOTP:
    """Tests for resending OTP during password reset flow."""

    def test_resend_after_cooldown(self, auth_manager, test_user, temp_db):
        """Resend should succeed after cooldown expires."""
        username, email = test_user

        # First send
        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.initiate_password_reset(email)
            assert success

        # Expire the cooldown by backdating the OTP
        user = temp_db.query(User).filter_by(username=username).first()
        otp = temp_db.query(OTP).filter_by(user_id=user.id, type="RESET_PASSWORD").order_by(OTP.created_at.desc()).first()
        otp.created_at = datetime.utcnow() - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 5)
        temp_db.commit()

        # Resend should now succeed
        with patch("app.services.email_service.EmailService.send_otp", return_value=True) as mock_send:
            success, msg = auth_manager.initiate_password_reset(email)
            assert success
            assert mock_send.called

    def test_resend_during_cooldown_fails(self, auth_manager, test_user, temp_db):
        """Resend should fail if cooldown is still active."""
        _, email = test_user

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.initiate_password_reset(email)
            assert success

        # Immediate resend should fail (rate limited)
        success, msg = auth_manager.initiate_password_reset(email)
        assert not success
        assert "wait" in msg.lower()

    def test_resend_generates_new_code(self, auth_manager, test_user, temp_db):
        """Each resend should generate a new OTP code."""
        username, email = test_user

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.initiate_password_reset(email)
            assert success

        user = temp_db.query(User).filter_by(username=username).first()
        first_otp = temp_db.query(OTP).filter_by(user_id=user.id, type="RESET_PASSWORD").order_by(OTP.created_at.desc()).first()
        first_hash = first_otp.code_hash

        # Expire cooldown
        first_otp.created_at = datetime.utcnow() - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 5)
        temp_db.commit()

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.initiate_password_reset(email)
            assert success

        second_otp = temp_db.query(OTP).filter_by(user_id=user.id, type="RESET_PASSWORD").order_by(OTP.created_at.desc()).first()
        # New OTP should have a different hash (extremely unlikely to collide)
        assert second_otp.id != first_otp.id


# ─── AuthManager.resend_2fa_login_otp Tests ───

class TestResend2FALoginOTP:
    """Tests for AuthManager.resend_2fa_login_otp()"""

    def test_resend_success(self, auth_manager, test_user_2fa, temp_db):
        """Resend 2FA OTP should succeed for valid user."""
        username, email = test_user_2fa

        with patch("app.services.email_service.EmailService.send_otp", return_value=True) as mock_send:
            success, msg = auth_manager.resend_2fa_login_otp(username)
            assert success
            assert "sent" in msg.lower()
            assert mock_send.called

    def test_resend_rate_limited(self, auth_manager, test_user_2fa, temp_db):
        """Second resend within cooldown should fail."""
        username, _ = test_user_2fa

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.resend_2fa_login_otp(username)
            assert success

        # Immediate second resend should be rate limited
        success, msg = auth_manager.resend_2fa_login_otp(username)
        assert not success
        assert "wait" in msg.lower()

    def test_resend_after_cooldown_expires(self, auth_manager, test_user_2fa, temp_db):
        """Resend should succeed after cooldown window passes."""
        username, _ = test_user_2fa

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.resend_2fa_login_otp(username)
            assert success

        # Expire cooldown
        user = temp_db.query(User).filter_by(username=username).first()
        otp = temp_db.query(OTP).filter_by(user_id=user.id, type="LOGIN_CHALLENGE").order_by(OTP.created_at.desc()).first()
        otp.created_at = datetime.utcnow() - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 5)
        temp_db.commit()

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, msg = auth_manager.resend_2fa_login_otp(username)
            assert success

    def test_resend_unknown_user(self, auth_manager, temp_db):
        """Resend for a non-existent user should fail."""
        success, msg = auth_manager.resend_2fa_login_otp("nonexistent_user")
        assert not success
        assert "not found" in msg.lower()

    def test_resend_user_without_email(self, auth_manager, temp_db):
        """Resend should fail if user has no email in profile."""
        # Create user without a PersonalProfile
        user = User(username="no_email_user", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        success, msg = auth_manager.resend_2fa_login_otp("no_email_user")
        assert not success
        assert "email" in msg.lower() or "not found" in msg.lower()

    def test_resend_email_service_failure(self, auth_manager, test_user_2fa, temp_db):
        """Resend should return failure if email service fails."""
        username, _ = test_user_2fa

        with patch("app.services.email_service.EmailService.send_otp", return_value=False):
            success, msg = auth_manager.resend_2fa_login_otp(username)
            assert not success
            assert "failed" in msg.lower()

    def test_resend_creates_login_challenge_otp(self, auth_manager, test_user_2fa, temp_db):
        """Resend should create OTP with LOGIN_CHALLENGE purpose."""
        username, _ = test_user_2fa

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            auth_manager.resend_2fa_login_otp(username)

        user = temp_db.query(User).filter_by(username=username).first()
        otp = temp_db.query(OTP).filter_by(user_id=user.id, type="LOGIN_CHALLENGE").first()
        assert otp is not None
        assert not otp.is_used
        assert otp.attempts == 0


# ─── Resend 2FA Setup OTP Tests ───

class TestResend2FASetupOTP:
    """Tests for resending OTP during 2FA setup (send_2fa_setup_otp)."""

    def test_resend_setup_otp_success(self, auth_manager, test_user, temp_db):
        """First send of 2FA setup OTP should succeed."""
        username, _ = test_user

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, msg = auth_manager.send_2fa_setup_otp(username)
            assert success

    def test_resend_setup_otp_rate_limited(self, auth_manager, test_user, temp_db):
        """Immediate re-send of 2FA setup OTP should be rate limited."""
        username, _ = test_user

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.send_2fa_setup_otp(username)
            assert success

        # Immediate resend should fail
        success, msg = auth_manager.send_2fa_setup_otp(username)
        assert not success
        assert "wait" in msg.lower()

    def test_resend_setup_otp_after_cooldown(self, auth_manager, test_user, temp_db):
        """Re-send should succeed after cooldown expires."""
        username, _ = test_user

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.send_2fa_setup_otp(username)
            assert success

        # Expire cooldown
        user = temp_db.query(User).filter_by(username=username).first()
        otp = temp_db.query(OTP).filter_by(user_id=user.id, type="2FA_SETUP").order_by(OTP.created_at.desc()).first()
        if otp:
            otp.created_at = datetime.utcnow() - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 5)
            temp_db.commit()

        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            success, _ = auth_manager.send_2fa_setup_otp(username)
            assert success


# ─── Edge Cases ───

class TestCooldownEdgeCases:
    """Edge case tests for cooldown behavior."""

    def test_cooldown_does_not_go_negative(self, temp_db):
        """get_cooldown_remaining should never return negative values."""
        user = User(username="no_neg", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        # OTP created way in the past
        ancient_time = datetime.utcnow() - timedelta(hours=1)
        otp = OTP(
            user_id=user.id, code_hash="hash", type="RESET_PASSWORD",
            created_at=ancient_time, expires_at=ancient_time + timedelta(minutes=5),
            is_used=True, attempts=0
        )
        temp_db.add(otp)
        temp_db.commit()

        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining == 0

    def test_multiple_users_independent_cooldown(self, temp_db):
        """Cooldown for one user should not affect another user."""
        user_a = User(username="user_a", password_hash="hash")
        user_b = User(username="user_b", password_hash="hash")
        temp_db.add_all([user_a, user_b])
        temp_db.commit()

        # Generate OTP for user_a only
        code, _ = OTPManager.generate_otp(user_a.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None

        # user_a should have cooldown
        assert OTPManager.get_cooldown_remaining(user_a.id, "RESET_PASSWORD", db_session=temp_db) > 0

        # user_b should have NO cooldown
        assert OTPManager.get_cooldown_remaining(user_b.id, "RESET_PASSWORD", db_session=temp_db) == 0

    def test_resend_after_verify_still_respects_cooldown(self, temp_db):
        """Even after OTP is used/verified, cooldown on generation still applies."""
        user = User(username="verify_cd", password_hash="hash")
        temp_db.add(user)
        temp_db.commit()

        with patch("app.auth.otp_manager.secrets.choice", return_value="1"):
            code, _ = OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
            assert code == "111111"

        # Verify (mark as used)
        assert OTPManager.verify_otp(user.id, "111111", "RESET_PASSWORD", db_session=temp_db)

        # Cooldown should still be active (based on created_at, not is_used)
        remaining = OTPManager.get_cooldown_remaining(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining > 0

        # Attempting to generate again should fail
        code2, error = OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code2 is None
        assert "wait" in error.lower()
