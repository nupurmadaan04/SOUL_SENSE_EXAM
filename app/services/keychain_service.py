import logging
import platform
from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    keyring = None  # type: ignore
    KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)

class KeychainService:
    """
    Service for interacting with the OS-level credential store.
    On macOS, this uses the Keychain.
    On Windows, this uses Credential Manager.
    On Linux, this uses Secret Service or KWallet.
    """
    
    SERVICE_NAME = "SoulSense"
    
    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if keychain integration is supported on the current platform.
        We prioritize macOS for this implementation.
        """
        if not KEYRING_AVAILABLE:
            logger.warning("keyring library is not installed. Keychain integration disabled.")
            return False
            
        # Optional: strictly limit to macOS if requested, 
        # but keyring is cross-platform by default.
        # current_os = platform.system()
        # if current_os != "Darwin":
        #    return False
            
        return True

    @classmethod
    def set_secret(cls, account: str, secret: str) -> bool:
        """
        Store a secret in the keychain.
        
        Args:
            account: The account name/identifier for the secret.
            secret: The secret string to store.
            
        Returns:
            True if successful, False otherwise.
        """
        if not cls.is_supported():
            return False
            
        try:
            keyring.set_password(cls.SERVICE_NAME, account, secret)
            logger.info(f"Successfully stored secret for {account} in keychain.")
            return True
        except Exception as e:
            logger.error(f"Failed to set secret in keychain for {account}: {e}")
            return False

    @classmethod
    def get_secret(cls, account: str) -> Optional[str]:
        """
        Retrieve a secret from the keychain.
        
        Args:
            account: The account name/identifier for the secret.
            
        Returns:
            The secret string if found, None otherwise.
        """
        if not cls.is_supported():
            return None
            
        try:
            secret = keyring.get_password(cls.SERVICE_NAME, account)
            if secret:
                logger.debug(f"Successfully retrieved secret for {account} from keychain.")
            else:
                logger.debug(f"No secret found for {account} in keychain.")
            return secret
        except Exception as e:
            logger.error(f"Failed to get secret from keychain for {account}: {e}")
            return None

    @classmethod
    def delete_secret(cls, account: str) -> bool:
        """
        Delete a secret from the keychain.
        
        Args:
            account: The account name/identifier for the secret.
            
        Returns:
            True if successful, False otherwise.
        """
        if not cls.is_supported():
            return False
            
        try:
            keyring.delete_password(cls.SERVICE_NAME, account)
            logger.info(f"Successfully deleted secret for {account} from keychain.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret from keychain for {account}: {e}")
            return False
