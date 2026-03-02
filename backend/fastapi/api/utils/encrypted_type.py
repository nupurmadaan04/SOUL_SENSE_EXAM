"""
Encrypted String Type Decorator and Context Variables.

This module provides the EncryptedString SQLAlchemy type decorator that handles
transparent encryption/decryption of string fields in the database. It's separated
from encryption_service.py to break circular import dependencies with models.

Related: Issue #1190 (Circular Import Deadlock)
"""

import contextvars
import logging
from sqlalchemy.types import TypeDecorator, Text

logger = logging.getLogger(__name__)

# Context variables to hold current user's DEK and ID globally for the current async task
current_dek = contextvars.ContextVar('current_dek', default=None)
current_user_id = contextvars.ContextVar('current_user_id', default=None)


class EncryptedString(TypeDecorator):
    """
    Custom SQLAlchemy TypeDecorator (Issue #1105).
    Transparently handles AEAD encryption on write and decryption on read.
    Requires `current_dek` ContextVar to be set by Auth Middleware.
    
    This class is kept minimal to avoid circular imports. Heavy encryption
    logic is delegated to EncryptionService via lazy imports.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt data before writing to database."""
        if value is None:
            return value
            
        dek = current_dek.get()
        if not dek:
            logger.warning("No User DEK found in ContextVar. Aborting encryption.")
            raise ValueError("Application-level encryption requires active User DEK context.")
            
        if isinstance(value, str) and value.startswith("ENC:"):
            return value
        
        # Lazy import to avoid circular dependency with encryption_service
        from .encryption_service import EncryptionService
        return EncryptionService.encrypt_data(str(value), dek)

    def process_result_value(self, value, dialect):
        """Decrypt data after reading from database."""
        if value is None:
            return value
            
        if not value.startswith("ENC:"):
            return value
            
        dek = current_dek.get()
        if not dek:
            # Mask data to prevent plaintext leakage in insecure contexts
            return "<ENCRYPTED_DATA: DEK Context Required>"
        
        # Lazy import to avoid circular dependency with encryption_service
        from .encryption_service import EncryptionService
        return EncryptionService.decrypt_data(value, dek)
