from typing import Optional
import os
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BASE_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)

logger = logging.getLogger(__name__)

class EncryptionManager:
    _key = None
    _cipher = None

    @classmethod
    def _get_key(cls):
        """
        Get or derive the encryption key.
        In production, this should come from a secure env var.
        For standalone, we'll derive it from a local secret or create one.
        """
        if cls._key:
            return cls._key
            
        secret_path = os.path.join(BASE_DIR, '.app_secret')
        master_password = b"SOULSENSE_INTERNAL_MASTER_KEY_CHANGE_ME_IN_PROD"
        
        # In a real scenario, use a proper key management system
        # Here we use a deterministic derivation for local consistency without external vault
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'static_salt_for_dev_simplicity', 
            iterations=100000,
        )
        cls._key = base64.urlsafe_b64encode(kdf.derive(master_password))
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