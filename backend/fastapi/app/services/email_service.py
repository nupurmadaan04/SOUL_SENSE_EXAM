import logging
import tkinter as tk
from tkinter import messagebox

logger = logging.getLogger(__name__)


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
            # In a real implementation:
            # msg = MIMEText(f"Your code is {code}")
            # server.sendmail(...)

            logger.info(f"Mock email sent to {to_email} for {purpose}")
            return True

        except Exception as e:
            logger.error(f"Failed to send mock email: {e}")
            return False
