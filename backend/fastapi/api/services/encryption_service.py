import base64
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

# Re-export context variables for backward compatibility
# These are now defined in encrypted_type.py to break circular imports (Issue #1190)
from ..utils.encrypted_type import current_dek, current_user_id

logger = logging.getLogger(__name__)

# In production, this MUST come from a secure vault (KMS / HashiCorp Vault)
MASTER_KEY_STR = os.getenv("ENCRYPTION_MASTER_KEY", "b33945de21b7ebd25e171542fba861f22e70eade98aa80ce79015c7ee2f27bf2")
# Ensure 32 bytes
MASTER_KEY = MASTER_KEY_STR.encode('utf-8')[:32].ljust(32, b'\0')

class EncryptionService:
    @staticmethod
    def generate_dek() -> bytes:
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def wrap_dek(dek: bytes) -> str:
        aesgcm = AESGCM(MASTER_KEY)
        nonce = os.urandom(12)
        wrapped = aesgcm.encrypt(nonce, dek, None)
        return base64.b64encode(nonce + wrapped).decode('utf-8')

    @staticmethod
    def unwrap_dek(wrapped_dek_str: str) -> bytes:
        aesgcm = AESGCM(MASTER_KEY)
        raw = base64.b64decode(wrapped_dek_str)
        nonce, wrapped = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, wrapped, None)

    @staticmethod
    def encrypt_data(plaintext: str, dek: bytes) -> str:
        if not plaintext:
            return plaintext
        aesgcm = AESGCM(dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return "ENC:" + base64.b64encode(nonce + ciphertext).decode('utf-8')

    @staticmethod
    def decrypt_data(ciphertext_str: str, dek: bytes, log_audit: bool = True) -> str:
        if not ciphertext_str or not str(ciphertext_str).startswith("ENC:"):
            return ciphertext_str
        
        try:
            raw = base64.b64decode(ciphertext_str[4:])
            nonce, ciphertext = raw[:12], raw[12:]
            aesgcm = AESGCM(dek)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
            
            # Application-Level Audit Logging (#1105)
            if log_audit:
                user_id = current_user_id.get()
                if user_id:
                    try:
                        from .kafka_producer import get_kafka_producer
                        from datetime import datetime, timezone
                        UTC = timezone.utc
                        producer = get_kafka_producer()
                        producer.queue_event({
                            "type": "DATA_ACCESS",
                            "entity": "JournalEntry",
                            "entity_id": str(user_id),
                            "payload": {"action": "decrypted_sensitive_content"},
                            "user_id": user_id,
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Audit log push failed on decryption: {e}")
                        
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return "<DECRYPTION_FAILED>"

    @staticmethod
    async def get_or_create_user_dek(user_id: int, db: AsyncSession) -> bytes:
        from ..models import UserEncryptionKey
        stmt = select(UserEncryptionKey).filter_by(user_id=user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record:
            return EncryptionService.unwrap_dek(record.wrapped_dek)
        
        # Create new DEK
        dek = EncryptionService.generate_dek()
        wrapped = EncryptionService.wrap_dek(dek)
        new_record = UserEncryptionKey(user_id=user_id, wrapped_dek=wrapped)
        db.add(new_record)
        await db.commit()
        return dek


# EncryptedString class has been moved to ../utils/encrypted_type.py
# to avoid circular import deadlock (Issue #1190).
# Re-export for backward compatibility
from ..utils.encrypted_type import EncryptedString  # noqa: F401, E402
