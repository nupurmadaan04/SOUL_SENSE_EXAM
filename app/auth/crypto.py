import base64
import logging
import secrets
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import BASE_DIR
from app.feature_flags import feature_flags
from app.services.keychain_service import KeychainService

logger = logging.getLogger(__name__)

class EncryptionManager:
    _key = None
    _cipher = None

    @classmethod
    def _get_key(cls):
        """
        Get or derive the encryption key.
        In production, this should come from a secure env var.
        For standalone, we'll attempt to use the OS Keychain if enabled,
        falling back to deterministic derivation.
        """
        if cls._key:
            return cls._key

        # Try Keychain integration if flag is enabled
        if feature_flags.is_enabled("macos_keychain_integration"):
            try:
                key_from_keychain = KeychainService.get_secret("master_key")
                if key_from_keychain:
                    cls._key = key_from_keychain.encode('utf-8')
                    logger.info("Using master key from OS keychain.")
                    return cls._key
                
                # Generate and store if not exists
                new_key = Fernet.generate_key()
                if KeychainService.set_secret("master_key", new_key.decode('utf-8')):
                    cls._key = new_key
                    logger.info("Generated and stored new master key in OS keychain.")
                    return cls._key
            except Exception as e:
                logger.warning(f"Keychain access failed, falling back to legacy derivation: {e}")

        # Fallback to deterministic derivation (Legacy)
        master_password = b"SOULSENSE_INTERNAL_MASTER_KEY_CHANGE_ME_IN_PROD"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'static_salt_for_dev_simplicity', 
            iterations=100000,
        )
        cls._key = base64.urlsafe_b64encode(kdf.derive(master_password))
        logger.debug("Using legacy deterministic derivation for master key.")
        return cls._key

    @classmethod
    def _get_cipher(cls):
        if not cls._cipher:
            key = cls._get_key()
            cls._cipher = Fernet(key)
        return cls._cipher

    @classmethod
    def encrypt(cls, plaintext: str) -> Optional[str]:
        """Encrypt string value"""
        if not plaintext:
            return None
        try:
            cipher = cls._get_cipher()
            return cipher.encrypt(plaintext.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @classmethod
    def decrypt(cls, ciphertext: str) -> Optional[str]:
        """Decrypt string value"""
        if not ciphertext:
            return None
        try:
            cipher = cls._get_cipher()
            return cipher.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
