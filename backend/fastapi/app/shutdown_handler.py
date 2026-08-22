import signal
import atexit
from app.logger import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.main import SoulSenseApp

class ShutdownHandler:
    def __init__(self, app: 'SoulSenseApp'):
        self.app = app
        self.logger = get_logger(__name__)
        self.setup_shutdown_handlers()

    def setup_shutdown_handlers(self):
        """Set up signal handlers and atexit registration"""
        # Register tkinter-specific exception handler
        def tk_report_callback_exception(exc_type, exc_value, exc_tb):
            """Handle exceptions in tkinter callbacks."""
            from app.error_handler import get_error_handler, ErrorSeverity
            handler = get_error_handler()
            handler.log_error(
                exc_value,
                module="tkinter",
                operation="callback",
                severity=ErrorSeverity.HIGH
            )
            import tkinter.messagebox as messagebox
            user_msg = handler.get_user_message(exc_value)
            messagebox.showerror("Interface Error", user_msg)

        self.app.root.report_callback_exception = tk_report_callback_exception

        # Set up graceful shutdown handlers
        self.app.root.protocol("WM_DELETE_WINDOW", self.graceful_shutdown)

        # Signal handlers for SIGINT (Ctrl+C) and SIGTERM
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            # Defer shutdown to avoid subprocess cleanup issues in signal handler (race condition fix #1185)
            self.app.root.after(0, self.graceful_shutdown)

        signal.signal(signal.SIGINT, signal_handler)

        # Try to register SIGTERM handler, but don't fail if it's not available
        try:
            signal.signal(signal.SIGTERM, signal_handler)
        except (AttributeError, ValueError, OSError):
            # SIGTERM may not be available on some platforms (e.g., older Windows)
            self.logger.debug("SIGTERM not available on this platform, skipping registration")

        # Register atexit handler as backup
        atexit.register(self.graceful_shutdown)

    def graceful_shutdown(self):
        """Perform graceful shutdown operations"""
        self.logger.info("Initiating graceful application shutdown...")

        try:
            # Clean up ML subprocesses first
            try:
                from app.ml.subprocess_manager import get_ml_subprocess_manager
                ml_manager = get_ml_subprocess_manager()
                ml_manager.cleanup_all()
                self.logger.info("ML subprocesses cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error during ML subprocess cleanup: {e}")

            # Commit any pending database operations from the scoped session
            from app.db import SessionLocal
            session = SessionLocal()
            if session:
                session.commit()
                SessionLocal.remove()  # Remove the session from the scoped registry
                self.logger.info("Database session committed and removed successfully")
        except Exception as e:
            self.logger.error(f"Error during database shutdown: {e}")

        # Log shutdown
        self.logger.info("Application shutdown complete")

        # Destroy the root window to exit
        if hasattr(self.app, 'root') and self.app.root:
            try:
                self.app.root.destroy()
            except Exception:
                pass  # Window already destroyed
