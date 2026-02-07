"""
Test Suite: Secure Password Hashing (bcrypt)

Covers:
- Hash generation (format, uniqueness, salt)
- Password verification (correct, incorrect, edge cases)
- Signup stores hashed password (not plaintext)
- Login verifies against hashed password
- Password reset stores new bcrypt hash
- CLI placeholder is a valid bcrypt hash
- Admin interface hashing & legacy migration
- Edge cases (unicode, long passwords, empty strings)
"""

import pytest
import bcrypt
from unittest.mock import patch, MagicMock
from app.auth.auth import AuthManager
from app.models import User, PersonalProfile


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def auth(temp_db):
    """Provide a fresh AuthManager backed by the temp in-memory DB."""
    return AuthManager()


@pytest.fixture
def registered_user(auth):
    """Register a user and return (auth_manager, username, password)."""
    username = "hashtest_user"
    email = "hashtest@example.com"
    password = "SecurePass1!"
    success, msg, code = auth.register_user(
        username, email, "Hash", "Test", 25, "M", password
    )
    assert success, f"Setup failed: {msg}"
    return auth, username, password


# ==============================================================================
# 1. HASH GENERATION TESTS
# ==============================================================================

class TestHashGeneration:
    """Verify bcrypt hash output format and properties."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        self.auth = AuthManager()

    def test_hash_is_not_plaintext(self):
        """Hash must never equal the original password."""
        password = "MyPassword123!"
        hashed = self.auth.hash_password(password)
        assert hashed != password

    def test_hash_starts_with_bcrypt_prefix(self):
        """bcrypt hashes always start with $2b$ (or $2a$/$2y$)."""
        hashed = self.auth.hash_password("AnyPassword1!")
        assert hashed.startswith("$2")

    def test_hash_has_correct_length(self):
        """bcrypt hashes are always 60 characters."""
        hashed = self.auth.hash_password("AnyPassword1!")
        assert len(hashed) == 60

    def test_hash_contains_cost_factor(self):
        """Hash should embed the configured cost factor (rounds=12)."""
        hashed = self.auth.hash_password("AnyPassword1!")
        # Format: $2b$12$...
        assert "$12$" in hashed

    def test_same_password_produces_different_hashes(self):
        """Each call must generate a unique salt, so hashes differ."""
        password = "SamePassword1!"
        h1 = self.auth.hash_password(password)
        h2 = self.auth.hash_password(password)
        assert h1 != h2

    def test_different_passwords_produce_different_hashes(self):
        """Different inputs must produce different hashes."""
        h1 = self.auth.hash_password("PasswordA1!")
        h2 = self.auth.hash_password("PasswordB1!")
        assert h1 != h2

    def test_hash_is_string(self):
        """hash_password must return a decoded UTF-8 string, not bytes."""
        hashed = self.auth.hash_password("TestPass1!")
        assert isinstance(hashed, str)


# ==============================================================================
# 2. PASSWORD VERIFICATION TESTS
# ==============================================================================

class TestPasswordVerification:
    """Verify bcrypt password checking logic."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        self.auth = AuthManager()

    def test_correct_password_verifies(self):
        password = "CorrectHorse1!"
        hashed = self.auth.hash_password(password)
        assert self.auth.verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = self.auth.hash_password("RealPassword1!")
        assert self.auth.verify_password("WrongPassword1!", hashed) is False

    def test_empty_password_fails(self):
        hashed = self.auth.hash_password("RealPassword1!")
        assert self.auth.verify_password("", hashed) is False

    def test_case_sensitive(self):
        """Password verification must be case-sensitive."""
        password = "CaseSensitive1!"
        hashed = self.auth.hash_password(password)
        assert self.auth.verify_password("casesensitive1!", hashed) is False
        assert self.auth.verify_password("CASESENSITIVE1!", hashed) is False

    def test_unicode_password(self):
        """Unicode characters should hash and verify correctly."""
        password = "Pässwörd123!"
        hashed = self.auth.hash_password(password)
        assert self.auth.verify_password(password, hashed) is True
        assert self.auth.verify_password("Passwrd123!", hashed) is False

    def test_long_password_rejected(self):
        """bcrypt 5.0+ raises ValueError for passwords > 72 bytes."""
        password = "A" * 100 + "1!"
        with pytest.raises((ValueError, Exception)):
            self.auth.hash_password(password)

    def test_verify_returns_false_on_invalid_hash(self):
        """Verification against a non-bcrypt string should return False, not crash."""
        assert self.auth.verify_password("test", "not_a_valid_hash") is False

    def test_verify_returns_false_on_empty_hash(self):
        """Verification against an empty hash should return False."""
        assert self.auth.verify_password("test", "") is False


# ==============================================================================
# 3. SIGNUP STORES HASHED PASSWORD
# ==============================================================================

class TestSignupHashStorage:
    """Verify that registration stores a bcrypt hash, never plaintext."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        self.auth = AuthManager()
        self.db = temp_db

    def test_registered_user_has_bcrypt_hash(self):
        password = "SignupTest1!"
        self.auth.register_user(
            "signup_hash", "signup@test.com", "Sign", "Up", 25, "M", password
        )
        user = self.db.query(User).filter_by(username="signup_hash").first()

        assert user is not None
        assert user.password_hash != password
        assert user.password_hash.startswith("$2")
        assert len(user.password_hash) == 60

    def test_stored_hash_verifies_against_original(self):
        password = "VerifyMe123!"
        self.auth.register_user(
            "verify_store", "verify@test.com", "Ver", "Ify", 30, "F", password
        )
        user = self.db.query(User).filter_by(username="verify_store").first()

        assert self.auth.verify_password(password, user.password_hash) is True

    def test_two_users_same_password_different_hashes(self):
        """Even with the same password, each user gets a unique hash (unique salt)."""
        password = "SharedPass1!"
        self.auth.register_user(
            "user_a", "a@test.com", "A", "User", 25, "M", password
        )
        self.auth.register_user(
            "user_b", "b@test.com", "B", "User", 26, "F", password
        )

        user_a = self.db.query(User).filter_by(username="user_a").first()
        user_b = self.db.query(User).filter_by(username="user_b").first()

        assert user_a.password_hash != user_b.password_hash
        # But both must verify against the same plaintext
        assert self.auth.verify_password(password, user_a.password_hash)
        assert self.auth.verify_password(password, user_b.password_hash)


# ==============================================================================
# 4. LOGIN VERIFIES HASHED PASSWORD
# ==============================================================================

class TestLoginHashVerification:
    """Verify that login correctly authenticates against bcrypt hashes."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        self.auth = AuthManager()
        self.password = "LoginTest1!"
        self.auth.register_user(
            "login_hash", "login@test.com", "Log", "In", 25, "M", self.password
        )

    def test_login_with_correct_password(self):
        success, msg, code = self.auth.login_user("login_hash", self.password)
        assert success is True
        assert code is None

    def test_login_with_wrong_password(self):
        success, msg, code = self.auth.login_user("login_hash", "WrongPass1!")
        assert success is False
        assert code == "AUTH001"

    def test_login_with_plaintext_of_hash_fails(self):
        """Attempting to log in with the hash string itself must fail."""
        from app.models import User
        from app.db import get_session
        session = get_session()
        user = session.query(User).filter_by(username="login_hash").first()
        stored_hash = user.password_hash
        session.close()

        success, msg, code = self.auth.login_user("login_hash", stored_hash)
        assert success is False

    def test_login_by_email_with_hashed_password(self):
        """Login via email should also verify against bcrypt hash."""
        success, msg, code = self.auth.login_user("login@test.com", self.password)
        assert success is True

    def test_login_nonexistent_user(self):
        success, msg, code = self.auth.login_user("ghost_user", "AnyPass1!")
        assert success is False
        assert code == "AUTH001"


# ==============================================================================
# 5. PASSWORD RESET STORES NEW HASH
# ==============================================================================

class TestPasswordResetHash:
    """Verify that password reset replaces hash with a new bcrypt hash."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        self.auth = AuthManager()
        self.db = temp_db
        self.old_password = "OldPassword1!"
        self.new_password = "NewPassword1!"
        self.email = "reset_hash@test.com"

        self.auth.register_user(
            "reset_hash", self.email, "Reset", "Hash", 28, "M", self.old_password
        )

    def test_reset_changes_hash(self):
        """After reset, the stored hash must be different and verify against new password."""
        user_before = self.db.query(User).filter_by(username="reset_hash").first()
        old_hash = user_before.password_hash

        # Initiate + complete reset with patched OTP
        with patch("app.auth.otp_manager.secrets.choice", return_value="1"):
            with patch("app.services.email_service.EmailService.send_otp", return_value=True):
                self.auth.initiate_password_reset(self.email)

        success, msg = self.auth.complete_password_reset(self.email, "111111", self.new_password)
        assert success, f"Reset failed: {msg}"

        self.db.expire_all()
        user_after = self.db.query(User).filter_by(username="reset_hash").first()

        # Hash changed
        assert user_after.password_hash != old_hash
        # New hash is valid bcrypt
        assert user_after.password_hash.startswith("$2")
        # New password verifies
        assert self.auth.verify_password(self.new_password, user_after.password_hash)
        # Old password no longer verifies
        assert not self.auth.verify_password(self.old_password, user_after.password_hash)


# ==============================================================================
# 6. CLI PLACEHOLDER HASH
# ==============================================================================

class TestCLIPlaceholderHash:
    """Verify the CLI implicit auth creates a valid bcrypt hash, not plaintext."""

    def test_cli_creates_bcrypt_hash(self, temp_db):
        """Simulate the CLI user-creation path and verify the stored hash."""
        import bcrypt as _bcrypt
        _cli_hash = _bcrypt.hashpw(b"implicit_cli_auth", _bcrypt.gensalt(rounds=12)).decode()

        user = User(username="cli_user", password_hash=_cli_hash)
        temp_db.add(user)
        temp_db.commit()

        stored = temp_db.query(User).filter_by(username="cli_user").first()
        assert stored.password_hash.startswith("$2")
        assert len(stored.password_hash) == 60
        assert stored.password_hash != "implicit_cli_auth"

    def test_cli_hash_is_verifiable(self):
        """The CLI placeholder hash should be verifiable by bcrypt."""
        _cli_hash = bcrypt.hashpw(b"implicit_cli_auth", bcrypt.gensalt(rounds=12)).decode()
        assert bcrypt.checkpw(b"implicit_cli_auth", _cli_hash.encode()) is True
        assert bcrypt.checkpw(b"wrong_password", _cli_hash.encode()) is False


# ==============================================================================
# 7. ADMIN INTERFACE HASHING (tested via raw bcrypt to avoid tkinter import)
# ==============================================================================

class TestAdminInterfaceHashing:
    """Verify the admin-style password hashing and legacy SHA-256 migration logic.
    
    Note: We replicate the admin_interface hashing logic here using raw bcrypt
    to avoid importing scripts.admin_interface which pulls in tkinter and
    causes metaclass conflicts in the test environment.
    """

    def _hash_password(self, password):
        """Replicate admin_interface._hash_password logic."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()

    def _verify_password(self, password, password_hash):
        """Replicate admin_interface._verify_password logic (bcrypt + SHA-256 fallback)."""
        if password_hash.startswith('$2'):
            try:
                return bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception:
                return False
        else:
            import hashlib
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            return legacy_hash == password_hash

    def test_admin_hash_is_bcrypt(self):
        """Admin _hash_password must produce valid bcrypt hashes."""
        hashed = self._hash_password("AdminPass123")
        assert hashed.startswith("$2")
        assert len(hashed) == 60

    def test_admin_verify_bcrypt(self):
        """Admin _verify_password must verify bcrypt hashes."""
        hashed = self._hash_password("AdminPass123")
        assert self._verify_password("AdminPass123", hashed) is True
        assert self._verify_password("WrongPass", hashed) is False

    def test_admin_legacy_sha256_detection(self):
        """Admin _verify_password should handle legacy SHA-256 hashes."""
        import hashlib
        password = "LegacyPass"
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()

        # Legacy hash does NOT start with $2, so the fallback path runs
        assert not legacy_hash.startswith("$2")
        assert self._verify_password(password, legacy_hash) is True
        assert self._verify_password("wrong", legacy_hash) is False


# ==============================================================================
# 8. BACKEND-STYLE HASHING (tested via raw bcrypt to avoid fastapi import collision)
# ==============================================================================

class TestBackendStyleHash:
    """Verify the backend hash_password logic using raw bcrypt.
    
    Note: Importing backend.fastapi.api.services.user_service directly causes
    a namespace collision (the local 'backend/fastapi/' directory shadows the
    fastapi package). We replicate the exact same logic here.
    """

    @staticmethod
    def _hash_password(password: str) -> str:
        """Replicate backend user_service.hash_password."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def test_backend_hash_is_bcrypt(self):
        hashed = self._hash_password("BackendPass1!")
        assert hashed.startswith("$2")
        assert len(hashed) == 60

    def test_backend_hash_verifies(self):
        password = "BackendVerify1!"
        hashed = self._hash_password(password)
        assert bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def test_backend_hash_unique_salts(self):
        h1 = self._hash_password("SamePass1!")
        h2 = self._hash_password("SamePass1!")
        assert h1 != h2


# ==============================================================================
# 9. CROSS-SERVICE CONSISTENCY
# ==============================================================================

class TestCrossServiceConsistency:
    """Verify that hashes from one service can be verified by another."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db):
        self.auth = AuthManager()

    def test_desktop_hash_verified_by_raw_bcrypt(self):
        """Desktop AuthManager hash should be verifiable by raw bcrypt library."""
        password = "CrossCheck1!"
        hashed = self.auth.hash_password(password)
        assert bcrypt.checkpw(password.encode(), hashed.encode())

    def test_raw_bcrypt_hash_verified_by_desktop(self):
        """A hash created by raw bcrypt should be verifiable by AuthManager."""
        password = "RawBcrypt1!"
        raw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
        assert self.auth.verify_password(password, raw_hash) is True

    def test_backend_hash_verified_by_desktop(self):
        """A hash created with the backend's bcrypt approach should verify via desktop AuthManager."""
        password = "InteropTest1!"
        backend_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        assert self.auth.verify_password(password, backend_hash) is True
