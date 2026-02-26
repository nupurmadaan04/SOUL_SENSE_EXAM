"""
Tests for OTP Verification Attempt Limiting feature.

Covers:
- OTP wrong attempts tracking
- OTP locking after max attempts
- Remaining attempts calculation
- Lock status checking
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.auth.auth import AuthManager
from app.auth.otp_manager import OTPManager
from backend.fastapi.api.root_models import User, PersonalProfile, OTP

pytestmark = pytest.mark.asyncio

# ─── Fixtures ───

@pytest.fixture
async def auth_manager(temp_db):
    return AuthManager()


@pytest.fixture
async def test_user(auth_manager, temp_db):
    """Register a test user and return (username, email)."""
    username = "otp_lock_user"
    email = "otp_lock@test.com"
    success, msg, code = await auth_manager.register_user(username, email, "OTP", "Lock", 25, "M", "StrongPass1!")
    assert success, f"Registration failed: {msg}"
    return username, email


@pytest.fixture
async def test_user_2fa(auth_manager, temp_db):
    """Register a test user with 2FA enabled and return (username, email)."""
    username = "twofa_lock_user"
    email = "twofa_lock@test.com"
    success, msg, code = await auth_manager.register_user(username, email, "Two", "FALock", 30, "F", "StrongPass1!")
    assert success, f"Registration failed: {msg}"
    
    stmt = select(User).where(User.username == username)
    result = await temp_db.execute(stmt)
    user = result.scalars().first()
    assert user is not None, f"User {username} not found in DB after registration"
    user.is_2fa_enabled = True
    await temp_db.commit()
    return username, email


# ─── OTP Attempts Tracking Tests ───

class TestOTPAttemptsTracking:
    """Tests for tracking OTP wrong attempts."""

    async def test_attempts_increment_on_wrong_code(self, test_user, temp_db):
        """Wrong OTP entry should increment attempt counter."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        # Generate OTP
        code, error = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None

        # Verify with wrong code
        success, msg = await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)
        assert not success

        # Check attempts incremented
        stmt = select(OTP).where(OTP.user_id == user.id, OTP.type == "RESET_PASSWORD").order_by(OTP.created_at.desc())
        result = await temp_db.execute(stmt)
        otp = result.scalars().first()
        assert otp.attempts == 1

    async def test_attempts_increment_multiple_times(self, test_user, temp_db):
        """Multiple wrong attempts should keep incrementing."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None

        # Try wrong codes multiple times
        for i in range(3):
            success, msg = await OTPManager.verify_otp(user.id, f"00000{i}", "RESET_PASSWORD", db_session=temp_db)
            assert not success

        # Check attempts = 3
        stmt = select(OTP).where(OTP.user_id == user.id, OTP.type == "RESET_PASSWORD").order_by(OTP.created_at.desc())
        result = await temp_db.execute(stmt)
        otp = result.scalars().first()
        assert otp.attempts == 3


# ─── OTP Locking Tests ───

class TestOTPLocking:
    """Tests for OTP locking after max attempts."""

    async def test_otp_locks_after_max_attempts(self, test_user, temp_db):
        """OTP should lock after MAX_VERIFY_ATTEMPTS failed attempts."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None

        # Fail MAX_VERIFY_ATTEMPTS times
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            success, msg = await OTPManager.verify_otp(user.id, f"00000{i}", "RESET_PASSWORD", db_session=temp_db)
            assert not success

        # OTP should now be locked
        stmt = select(OTP).where(OTP.user_id == user.id, OTP.type == "RESET_PASSWORD").order_by(OTP.created_at.desc())
        result = await temp_db.execute(stmt)
        otp = result.scalars().first()
        assert otp.is_locked is True

    async def test_locked_otp_rejects_verification(self, test_user, temp_db):
        """Locked OTP should reject even correct code."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert code is not None

        # Lock the OTP by maxing out attempts
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        # Try with correct code - should fail
        success, msg = await OTPManager.verify_otp(user.id, code, "RESET_PASSWORD", db_session=temp_db)
        assert not success
        assert "locked" in msg.lower() or "too many failed attempts" in msg.lower()

    async def test_lock_message_includes_resend_instruction(self, test_user, temp_db):
        """Lock message should instruct user to request new code."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)

        # Max out attempts
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            success, msg = await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        assert "request a new code" in msg.lower()


# ─── Remaining Attempts Tests ───

class TestRemainingAttempts:
    """Tests for get_remaining_attempts method."""

    async def test_get_remaining_attempts_initial(self, test_user, temp_db):
        """Initially should return MAX_VERIFY_ATTEMPTS."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)

        remaining = await OTPManager.get_remaining_attempts(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining == OTPManager.MAX_VERIFY_ATTEMPTS

    async def test_get_remaining_attempts_after_failures(self, test_user, temp_db):
        """Remaining attempts should decrease after failures."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)

        # Fail once
        await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        remaining = await OTPManager.get_remaining_attempts(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining == OTPManager.MAX_VERIFY_ATTEMPTS - 1

    async def test_get_remaining_attempts_returns_zero_when_locked(self, test_user, temp_db):
        """Should return 0 when OTP is locked."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)

        # Lock the OTP
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        remaining = await OTPManager.get_remaining_attempts(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert remaining == 0


# ─── Lock Status Check Tests ───

class TestLockStatusCheck:
    """Tests for is_otp_locked method."""

    async def test_is_otp_locked_returns_false_initially(self, test_user, temp_db):
        """Should return False when OTP is fresh."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)

        is_locked, msg = await OTPManager.is_otp_locked(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert is_locked is False
        assert "attempts remaining" in msg.lower()

    async def test_is_otp_locked_returns_true_when_locked(self, test_user, temp_db):
        """Should return True when OTP is locked."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        code, _ = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=temp_db)

        # Lock the OTP
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        is_locked, msg = await OTPManager.is_otp_locked(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert is_locked is True
        assert "too many failed attempts" in msg.lower()

    async def test_is_otp_locked_returns_false_no_otp(self, test_user, temp_db):
        """Should return False with message when no active OTP."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        is_locked, msg = await OTPManager.is_otp_locked(user.id, "RESET_PASSWORD", db_session=temp_db)
        assert is_locked is False
        assert "no active otp" in msg.lower()


# ─── Integration Tests with AuthManager ───

class TestOTPLockIntegration:
    """Integration tests with AuthManager methods."""

    async def test_verify_2fa_login_returns_lock_message(self, auth_manager, test_user_2fa, temp_db):
        """verify_2fa_login should return lock message after max attempts."""
        username, email = test_user_2fa
        
        # Generate initial OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            await auth_manager.resend_2fa_login_otp(username)

        # Fail MAX_VERIFY_ATTEMPTS times
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            success, msg, token = await auth_manager.verify_2fa_login(username, "000000")
            assert not success

        # Next attempt should indicate locked
        success, msg, token = await auth_manager.verify_2fa_login(username, "000000")
        assert not success
        assert "request a new code" in msg.lower()

    async def test_complete_password_reset_returns_lock_message(self, auth_manager, test_user, temp_db):
        """complete_password_reset should return lock message after max attempts."""
        username, email = test_user
        
        # Generate initial OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            await auth_manager.initiate_password_reset(email)

        # Fail MAX_VERIFY_ATTEMPTS times by calling complete_password_reset with wrong codes
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            success, msg = await auth_manager.complete_password_reset(email, "000000", "NewStrongPass2!")
            assert not success

        # Next attempt should indicate locked
        success, msg = await auth_manager.complete_password_reset(email, "000000", "NewStrongPass2!")
        assert not success
        assert "request a new code" in msg.lower()

    async def test_enable_2fa_returns_lock_message(self, auth_manager, test_user, temp_db):
        """enable_2fa should return lock message after max attempts."""
        username, email = test_user

        # Generate initial OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            await auth_manager.send_2fa_setup_otp(username)

        # Fail MAX_VERIFY_ATTEMPTS times
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            success, msg = await auth_manager.enable_2fa(username, "000000")
            assert not success

        # Next attempt should indicate locked
        success, msg = await auth_manager.enable_2fa(username, "000000")
        assert not success
        assert "request a new code" in msg.lower()


# ─── Regenerate After Lock Tests ───

class TestRegenerateAfterLock:
    """Tests for regenerating OTP after lock."""

    async def test_new_otp_after_resend_unlocks(self, auth_manager, test_user, temp_db):
        """Resending OTP should create a new unlocked OTP."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        # Generate and lock first OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True):
            await auth_manager.initiate_password_reset(email)

        stmt = select(OTP).where(OTP.user_id == user.id, OTP.type == "RESET_PASSWORD").order_by(OTP.created_at.desc())
        result = await temp_db.execute(stmt)
        first_otp = result.scalars().first()

        # Lock it
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        # Expire cooldown
        first_otp.created_at = datetime.now(timezone.utc) - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 5)
        await temp_db.commit()

        # Resend should create new OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True) as mock_send:
            success, msg = await auth_manager.initiate_password_reset(email)
            assert success

        # Check new OTP exists and is not locked
        stmt = select(OTP).where(OTP.user_id == user.id, OTP.type == "RESET_PASSWORD").order_by(OTP.created_at.desc())
        result = await temp_db.execute(stmt)
        new_otp = result.scalars().first()
        assert new_otp.id != first_otp.id
        assert new_otp.is_locked is False
        assert new_otp.attempts == 0

    async def test_correct_code_works_after_regenerate(self, auth_manager, test_user, temp_db):
        """Correct code should work on the new OTP after resend."""
        username, email = test_user
        stmt = select(User).where(User.username == username)
        result = await temp_db.execute(stmt)
        user = result.scalars().first()

        # Generate and lock first OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True) as mock_send:
            await auth_manager.initiate_password_reset(email)
            first_code = mock_send.call_args[0][1]  # Get the code that was "sent"

        # Lock it with wrong attempts
        for i in range(OTPManager.MAX_VERIFY_ATTEMPTS):
            await OTPManager.verify_otp(user.id, "000000", "RESET_PASSWORD", db_session=temp_db)

        # Expire cooldown
        stmt = select(OTP).where(OTP.user_id == user.id, OTP.type == "RESET_PASSWORD").order_by(OTP.created_at.desc())
        result = await temp_db.execute(stmt)
        first_otp = result.scalars().first()
        first_otp.created_at = datetime.now(timezone.utc) - timedelta(seconds=OTPManager.RATE_LIMIT_SECONDS + 5)
        await temp_db.commit()

        # Generate new OTP
        with patch("app.services.email_service.EmailService.send_otp", return_value=True) as mock_send:
            await auth_manager.initiate_password_reset(email)
            new_code = mock_send.call_args[0][1]

        # Correct code should work now
        success, msg = await OTPManager.verify_otp(user.id, new_code, "RESET_PASSWORD", db_session=temp_db)
        assert success is True
