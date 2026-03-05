import logging
import datetime
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class EmailService:
    """
    Service for handling email communications.
    Currently a MOCK implementation that logs to console/file.
    """

    @staticmethod
    def send_otp(to_email: str, code: str, purpose: str = "Password Reset") -> bool:
        """
        Send an OTP to the specified email address.

        Args:
            to_email: Recipient email
            code: The 6-digit OTP code
            purpose: The reason for the OTP (displayed in subject/body)

        Returns:
            bool: True if sent successfully (always True for Mock)
        """
        try:
            # Mask the code for logging
            masked_code = "******"
            
            log_msg = f"""
            --------------------------------------------------------
            [MOCK EMAIL SENT]
            To: {to_email}
            Subject: SoulSense Code: {purpose}

            Hello,

            Your One-Time Password (OTP) for {purpose} is:

            >>> {code if settings.debug else masked_code} <<<

            This code is valid for 5 minutes.
            If you did not request this, please ignore this email.
            --------------------------------------------------------
            """

            # Use logger instead of print for the main message
            if settings.debug:
                 print(log_msg)
            
            logger.info(f"Mock email sent to {to_email} with code {masked_code}")

            # Write to a debug file only in debug mode
            if settings.debug:
                try:
                    with open("otp_debug.txt", "a") as f:
                        f.write(f"To: {to_email} | Code: {code} | Time: {datetime.datetime.now()}\n")
                except Exception as file_err:
                    logger.error(f"Failed to write to otp_debug.txt: {file_err}")

            return True

        except Exception as e:
            logger.error(f"Failed to send mock email: {e}")
            # Try to log to file even on error
            try:
                with open("otp_debug.txt", "a") as f:
                    f.write(f"ERROR Sending to {to_email}: {e}\n")
            except:
                pass
            return False