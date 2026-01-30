import signal
import atexit
import tkinter as tk
from tkinter import messagebox
import logging
from app.ui.app_initializer import AppInitializer
from app.ui.view_manager import ViewManager
from app.auth.app_auth import AppAuth
from app.shutdown_handler import ShutdownHandler
from app.ui.styles import UIStyles
from app.startup_checks import run_all_checks, get_check_summary, CheckStatus
from app.exceptions import IntegrityError
from app.logger import setup_logging
from app.error_handler import setup_global_exception_handlers
from app.questions import initialize_questions
from typing import Optional, Dict, Any
from app.error_handler import get_error_handler, ErrorSeverity
from app.logger import get_logger
from app.i18n_manager import get_i18n
from app.auth import AuthManager
from app.questions import load_questions
from app.ui.sidebar import SidebarNav
from app.ui.assessments import AssessmentHub
from app.ui.exam import ExamManager
from app.ui.dashboard import AnalyticsDashboard
from app.ui.journal import JournalFeature

class SoulSenseApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        # Initialize modules
        self.initializer = AppInitializer(self)
        self.view_manager = ViewManager(self)
        self.auth_handler = AppAuth(self)
        self.shutdown_handler = ShutdownHandler(self)

    def switch_view(self, view_id):
        """Delegate view switching to ViewManager"""
        self.view_manager.switch_view(view_id)

    def apply_theme(self, theme_name: str):
        """Delegate theme application to UIStyles"""
        self.ui_styles.apply_theme(theme_name)
        # Refresh current view
        if hasattr(self, 'current_view') and self.current_view:
            self.switch_view(self.current_view)
        elif hasattr(self, 'sidebar') and self.sidebar.active_id:
            self.switch_view(self.sidebar.active_id)

    def show_home(self):
        """Delegate to ViewManager"""
        self.view_manager.show_home()

    def start_exam(self):
        """Delegate to ViewManager"""
        self.view_manager.start_exam()

    def show_dashboard(self):
        """Delegate to ViewManager"""
        self.view_manager.show_dashboard()

    def show_journal(self):
        """Delegate to ViewManager"""
        self.view_manager.show_journal()

    def show_profile(self):
        """Delegate to ViewManager"""
        self.view_manager.show_profile()

    def show_history(self):
        """Delegate to ViewManager"""
        self.view_manager.show_history()

    def show_assessments(self):
        """Delegate to ViewManager"""
        self.view_manager.show_assessments()

    def clear_screen(self):
        """Delegate to ViewManager"""
        self.view_manager.clear_screen()

    def graceful_shutdown(self):
        """Delegate to ShutdownHandler"""
        self.shutdown_handler.graceful_shutdown()

# --- Global Error Handlers ---

def show_error(title, message, exception=None):
    """Global error display function"""
    if exception:
        logging.error(f"{title}: {message} - {exception}")
    else:
        logging.error(f"{title}: {message}")

    try:
        messagebox.showerror(title, message)
    except:
        print(f"CRITICAL ERROR (No GUI): {title} - {message}")

def global_exception_handler(self, exc_type, exc_value, traceback_obj):
    """Handle uncaught exceptions"""
    import traceback
    traceback_str = "".join(traceback.format_exception(exc_type, exc_value, traceback_obj))
    logging.critical(f"Uncaught Exception: {traceback_str}")
    show_error("Unexpected Error", f"An unexpected error occurred:\n{exc_value}", exception=traceback_str)


if __name__ == "__main__":
    # Setup centralized logging and error handling
    setup_logging()
    setup_global_exception_handlers()

    try:
        # Run startup integrity checks before initializing the app
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            results = run_all_checks(raise_on_critical=True)
            summary = get_check_summary(results)
            logger.info(summary)

            # Show warning dialog if there were any warnings
            warnings = [r for r in results if r.status == CheckStatus.WARNING]
            if warnings:
                # Create a temporary root for the warning dialog
                temp_root = tk.Tk()
                temp_root.withdraw()
                warning_msg = "\n".join([f"• {r.name}: {r.message}" for r in warnings])
                messagebox.showwarning(
                    "Startup Warnings",
                    f"The application started with the following warnings:\n\n{warning_msg}\n\nThe application will continue with default settings."
                )
                temp_root.destroy()

        except IntegrityError as e:
            # Critical failure - show error and exit
            temp_root = tk.Tk()
            temp_root.withdraw()
            messagebox.showerror(
                "Startup Failed",
                f"Critical integrity check failed:\n\n{str(e)}\n\nThe application cannot start."
            )
            temp_root.destroy()
            raise SystemExit(1)

        # All checks passed, start the application

        # Initialize Questions Cache (Preload)
        from app.questions import initialize_questions
        logger.info("Preloading questions into memory...")
        if not initialize_questions():
            logger.warning("Initial question preload failed. Application will attempt lazy-loading.")

        root = tk.Tk()

        # Register tkinter-specific exception handler
        def tk_report_callback_exception(exc_type, exc_value, exc_tb):
            """Handle exceptions in tkinter callbacks."""
            handler = get_error_handler()
            handler.log_error(
                exc_value,
                module="tkinter",
                operation="callback",
                severity=ErrorSeverity.HIGH
            )
            user_msg = handler.get_user_message(exc_value)
            show_error("Interface Error", user_msg, exc_value)

        root.report_callback_exception = tk_report_callback_exception

        app = SoulSenseApp(root)

        # Set up graceful shutdown handlers
        root.protocol("WM_DELETE_WINDOW", app.graceful_shutdown)

        # Signal handlers for SIGINT (Ctrl+C) and SIGTERM
        def signal_handler(signum, frame):
            app.logger.info(f"Received signal {signum}, initiating shutdown")
            app.graceful_shutdown()

        signal.signal(signal.SIGINT, signal_handler)

        # Try to register SIGTERM handler, but don't fail if it's not available
        try:
            signal.signal(signal.SIGTERM, signal_handler)
        except (AttributeError, ValueError, OSError):
            # SIGTERM may not be available on some platforms (e.g., older Windows)
            app.logger.debug("SIGTERM not available on this platform, skipping registration")

        # Register atexit handler as backup
        atexit.register(app.graceful_shutdown)

        root.mainloop()

    except SystemExit:
        pass  # Clean exit from integrity failure
    except Exception as e:
        import traceback
        handler = get_error_handler()
        handler.log_error(e, module="main", operation="startup", severity=ErrorSeverity.CRITICAL)
        traceback.print_exc()
