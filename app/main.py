"""
SoulSense Main Application Entry Point

This module serves as the central entry point for the SoulSense EQ assessment application.
It orchestrates the complete application lifecycle from startup validation through
graceful shutdown, coordinating all major subsystems and ensuring proper initialization order.
"""

# === CORE UI FRAMEWORK ===
import tkinter as tk
from tkinter import messagebox

# === LOGGING AND ERROR HANDLING ===
import logging
from app.logger import setup_logging
from app.error_handler import setup_global_exception_handlers

# === APPLICATION MODULES ===
# Core application initialization and state management
from app.ui.app_initializer import AppInitializer
# View switching and UI navigation management
from app.ui.view_manager import ViewManager
# User authentication and session management
from app.auth.app_auth import AppAuth
# Graceful shutdown and cleanup coordination
from app.shutdown_handler import ShutdownHandler

# === UTILITY MODULES ===
from app.ui.styles import UIStyles  # UI theming and styling
from app.startup_checks import run_all_checks, get_check_summary, CheckStatus  # System validation
from app.exceptions import IntegrityError  # Startup validation errors
from app.questions import initialize_questions  # Question data preloading

# === TYPE HINTS ===
from typing import Optional, Dict, Any

class SoulSenseApp:
    """
    Main application class coordinating all SoulSense functionality.
    
    This class serves as the central hub that initializes and manages all
    application modules, handles view switching, and coordinates between
    different components of the EQ assessment system.
    """
    
    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the SoulSense application with all core modules.
        
        The initialization order is critical:
        1. AppInitializer first (sets up core app state and configuration)
        2. ViewManager (depends on initialized app state)
        3. Auth handler (needs app state for user management)
        4. Shutdown handler (needs all components for cleanup)
        """
        self.root = root

        # === CORE MODULE INITIALIZATION ===
        # Order matters: AppInitializer must come first as other modules depend on it
        
        # Initialize core application state, configuration, and UI framework
        # This creates the foundational app object that other modules will use
        self.initializer = AppInitializer(self)
        
        # Initialize view management system (depends on app state being ready)
        # Handles switching between different application screens/views
        self.view_manager = ViewManager(self)
        
        # Initialize authentication system (needs app state for user sessions)
        # Manages user login, logout, and session state
        self.auth_handler = AppAuth(self)
        
        # Initialize shutdown handling (needs all components for proper cleanup)
        # Manages graceful application termination and resource cleanup
        self.shutdown_handler = ShutdownHandler(self)
        
        # === APPLICATION STATE ===
        # Track animation state for UI optimization
        self.is_animating = False

        # === BACKWARD COMPATIBILITY EXPOSURE ===
        # Expose commonly used attributes directly on the main app object
        # This maintains API compatibility while using the modular architecture
        # Core UI and state attributes
        self.colors = self.initializer.app.colors
        self.fonts = self.initializer.app.fonts
        self.username = self.initializer.app.username
        self.current_user_id = self.initializer.app.current_user_id
        self.settings = self.initializer.app.settings
        
        # Application data and content
        self.questions = self.initializer.app.questions
        
        # UI component references
        self.main_container = self.initializer.app.main_container
        self.sidebar = self.initializer.app.sidebar
        self.content_area = self.initializer.app.content_area
        
        # Functional managers
        self.exam_manager = self.initializer.app.exam_manager
        self.ui_styles = self.initializer.app.ui_styles
        
        # System services
        self.logger = self.initializer.app.logger
        self.i18n = self.initializer.app.i18n
        
        # User profile data
        self.age = self.initializer.app.age
        self.age_group = self.initializer.app.age_group

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

    def logout(self):
        """
        Handle user logout with confirmation dialog.
        
        This method ensures users don't accidentally lose unsaved work by:
        1. Showing a confirmation dialog before proceeding
        2. Only proceeding with logout if user confirms
        3. Delegating actual logout logic to the initializer
        """
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out? Any unsaved changes will be lost."):
            self.initializer.logout_user()

# --- Global Error Handlers ---

# === GLOBAL ERROR HANDLING ===
# These functions provide application-wide error handling and user notification
# They ensure errors are properly logged and displayed to users in a user-friendly way

def show_error(title, message, exception=None):
    """
    Global error display function that handles both logging and user notification.
    
    This function serves as the centralized error reporting mechanism that:
    1. Logs errors with appropriate severity levels
    2. Displays user-friendly error dialogs
    3. Falls back to console output if GUI is unavailable
    """
    # Log the error with full context for debugging
    if exception:
        logging.error(f"{title}: {message} - {exception}")
    else:
        logging.error(f"{title}: {message}")

    # Attempt GUI error display, fallback to console if GUI unavailable
    try:
        messagebox.showerror(title, message)
    except:
        print(f"CRITICAL ERROR (No GUI): {title} - {message}")

def global_exception_handler(self, exc_type, exc_value, traceback_obj):
    """
    Handle uncaught exceptions that bubble up to the top level.
    
    This is the final safety net for exceptions that aren't caught elsewhere.
    It ensures critical errors are logged and the application fails gracefully.
    """
    import traceback
    # Generate full traceback for debugging
    traceback_str = "".join(traceback.format_exception(exc_type, exc_value, traceback_obj))
    logging.critical(f"Uncaught Exception: {traceback_str}")
    show_error("Unexpected Error", f"An unexpected error occurred:\n{exc_value}", exception=traceback_str)


if __name__ == "__main__":
    # === PHASE 1: Core System Setup ===
    # Initialize logging and error handling before any other operations
    # This ensures all subsequent operations can be properly logged and errors handled
    setup_logging()
    setup_global_exception_handlers()

    try:
        # === PHASE 2: Pre-Application Integrity Checks ===
        # Run comprehensive system validation before initializing the GUI
        # This includes database schema checks, file system validation, and configuration verification
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            # Execute all startup checks with critical failure handling
            # If any critical check fails, the application will not start
            results = run_all_checks(raise_on_critical=True)
            summary = get_check_summary(results)
            logger.info(summary)

            # Handle non-critical warnings by showing user notification
            # Application can continue with warnings but user should be informed
            warnings = [r for r in results if r.status == CheckStatus.WARNING]
            if warnings:
                # Create temporary Tkinter root for warning dialog (no main window yet)
                temp_root = tk.Tk()
                temp_root.withdraw()
                warning_msg = "\n".join([f"• {r.name}: {r.message}" for r in warnings])
                messagebox.showwarning(
                    "Startup Warnings",
                    f"The application started with the following warnings:\n\n{warning_msg}\n\nThe application will continue with default settings."
                )
                temp_root.destroy()

        except IntegrityError as e:
            # Critical startup failure - cannot proceed with application launch
            # Show error dialog and exit cleanly
            temp_root = tk.Tk()
            temp_root.withdraw()
            messagebox.showerror(
                "Startup Failed",
                f"Critical integrity check failed:\n\n{str(e)}\n\nThe application cannot start."
            )
            temp_root.destroy()
            raise SystemExit(1)

        # === PHASE 3: Data Preloading ===
        # Preload question data into memory cache before GUI initialization
        # This improves application responsiveness by avoiding lazy-loading delays
        logger.info("Preloading questions into memory...")
        if not initialize_questions():
            logger.warning("Initial question preload failed. Application will attempt lazy-loading.")

        # === PHASE 4: GUI Framework Initialization ===
        # Create the main Tkinter root window - foundation for all UI components
        root = tk.Tk()

        # === PHASE 5: Exception Handling Setup ===
        # Register Tkinter-specific exception handler for GUI callback errors
        # This catches exceptions that occur during event processing
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
            user_msg = handler.get_user_message(exc_value)
            show_error("Interface Error", user_msg, exc_value)

        root.report_callback_exception = tk_report_callback_exception

        # === PHASE 6: Application Core Initialization ===
        # Create the main SoulSenseApp instance with all modules and managers
        # This is the central application object that coordinates all functionality
        app = SoulSenseApp(root)

        # === PHASE 7: Shutdown Handling Setup ===
        # Register multiple shutdown mechanisms for graceful application termination

        # Handle window close button (X) clicks
        root.protocol("WM_DELETE_WINDOW", app.graceful_shutdown)

        # Handle system signals (Ctrl+C, termination signals)
        def signal_handler(signum, frame):
            app.logger.info(f"Received signal {signum}, initiating shutdown")
            app.graceful_shutdown()

        import signal
        signal.signal(signal.SIGINT, signal_handler)

        # Try to register SIGTERM handler (may not be available on all platforms)
        try:
            signal.signal(signal.SIGTERM, signal_handler)
        except (AttributeError, ValueError, OSError):
            # SIGTERM may not be available on some platforms (e.g., older Windows)
            app.logger.debug("SIGTERM not available on this platform, skipping registration")

        # Register atexit handler as final safety net for unexpected termination
        import atexit
        atexit.register(app.graceful_shutdown)

        # === PHASE 8: Main Event Loop ===
        # Start the Tkinter event loop - this is where the application runs
        # The loop processes user interactions, updates UI, and handles events
        root.mainloop()

    except SystemExit:
        pass  # Clean exit from integrity failure
    except Exception as e:
        # Handle any unexpected startup errors with comprehensive logging
        import traceback
        from app.error_handler import get_error_handler, ErrorSeverity
        handler = get_error_handler()
        handler.log_error(e, module="main", operation="startup", severity=ErrorSeverity.CRITICAL)
        traceback.print_exc()
