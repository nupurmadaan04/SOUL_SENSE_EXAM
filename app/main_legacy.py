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
        self.root.title("SoulSense AI - Mental Wellbeing")
        self.root.geometry("1400x900")
        
        # Initialize Logger (use centralized logger)
        self.logger = get_logger(__name__)
        
        # Initialize Styles
        self.ui_styles = UIStyles(self)
        self.colors: Dict[str, str] = {} # Will be populated by apply_theme
        self.ui_styles.apply_theme("dark") # Default theme
        
        # Fonts
        self.fonts = {
            "h1": ("Segoe UI", 24, "bold"),
            "h2": ("Segoe UI", 20, "bold"),
            "h3": ("Segoe UI", 16, "bold"),
            "body": ("Segoe UI", 12),
            "small": ("Segoe UI", 10)
        }
        
        # State
        self.username: Optional[str] = None # Set after login
        self.current_user_id: Optional[int] = None
        self.age = 25
        self.age_group = "adult"
        self.i18n = get_i18n()
        self.questions = []
        self.auth = AuthManager()
        self.settings: Dict[str, Any] = {} 
        
        # Load Questions
        try:
            self.questions = load_questions()
        except Exception as e:
            self.logger.error(f"Failed to load questions: {e}")
            messagebox.showerror("Error", f"Could not load questions: {e}")
        
        # --- UI Layout ---
        self.main_container = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_container.pack(fill="both", expand=True)
        
        # Sidebar (Initialized but hidden until login)
        # Sidebar (Initialized but hidden until login)
        self.sidebar = SidebarNav(self.main_container, self, [
            {"id": "home", "label": "Home", "icon": "🏠"},
            {"id": "exam", "label": "Assessment", "icon": "🧠"},
            {"id": "dashboard", "label": "Dashboard", "icon": "📊"},
            {"id": "journal", "label": "Journal", "icon": "📝"},
            {"id": "assessments", "label": "Deep Dive", "icon": "🔍"},
            {"id": "history", "label": "History", "icon": "�"}, # Replaces Profile
        ], on_change=self.switch_view)
        # self.sidebar.pack(side="left", fill="y") # Don't pack yet
        
        # Content Area
        self.content_area = tk.Frame(self.main_container, bg=self.colors["bg"])
        self.content_area.pack(side="right", fill="both", expand=True)
        
        # Initialize Features
        self.exam_manager = None 
        
        # Start Login Flow
        self.root.after(100, self.show_login_screen)

    def show_login_screen(self) -> None:
        """Show login popup on startup"""
        login_win = tk.Toplevel(self.root)
        login_win.title("SoulSense Login")
        login_win.geometry("400x500")
        login_win.configure(bg=self.colors["bg"])
        login_win.transient(self.root)
        login_win.grab_set()
        
        # Prevent closing without login
        login_win.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())
        
        # Center
        login_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 500) // 2
        login_win.geometry(f"+{x}+{y}")

        # Logo/Title
        tk.Label(login_win, text="SoulSense AI", font=("Segoe UI", 24, "bold"), 
                 bg=self.colors["bg"], fg=self.colors["primary"]).pack(pady=(40, 10))
        
        tk.Label(login_win, text="Login to continue", font=("Segoe UI", 12), 
                 bg=self.colors["bg"], fg=self.colors["text_secondary"]).pack(pady=(0, 30))
        
        # Form
        entry_frame = tk.Frame(login_win, bg=self.colors["bg"])
        entry_frame.pack(fill="x", padx=40)
        
        tk.Label(entry_frame, text="Username", font=("Segoe UI", 10, "bold"), 
                 bg=self.colors["bg"], fg=self.colors["text_primary"]).pack(anchor="w")
        username_entry = tk.Entry(entry_frame, font=("Segoe UI", 12))
        username_entry.pack(fill="x", pady=(5, 15))
        
        tk.Label(entry_frame, text="Password", font=("Segoe UI", 10, "bold"), 
                 bg=self.colors["bg"], fg=self.colors["text_primary"]).pack(anchor="w")
        password_entry = tk.Entry(entry_frame, font=("Segoe UI", 12), show="*")
        password_entry.pack(fill="x", pady=(5, 20))
        
        def do_login():
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()
            
            if not user or not pwd:
                messagebox.showerror("Error", "Please enter username and password")
                return
                
            success, msg = self.auth.login_user(user, pwd)
            if success:
                self.username = user
                # Load User Settings from DB
                self._load_user_settings(user)
                login_win.destroy()
                self._post_login_init()
            else:
                messagebox.showerror("Login Failed", msg)
        
        def do_register():
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()
             
            if not user or not pwd:
                 messagebox.showerror("Error", "Please enter username and password")
                 return
                 
            success, msg = self.auth.register_user(user, pwd)
            if success:
                messagebox.showinfo("Success", "Account created! You can now login.")
            else:
                messagebox.showerror("Registration Failed", msg)

        # Buttons
        tk.Button(login_win, text="Login", command=do_login,
                 font=("Segoe UI", 12, "bold"), bg=self.colors["primary"], fg="white",
                 width=20).pack(pady=10)
                 
        tk.Button(login_win, text="Create Account", command=do_register,
                 font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["primary"],
                 bd=0, cursor="hand2").pack()

    def _load_user_settings(self, username: str) -> None:
        """Load settings from DB for user"""
        try:
            from app.db import get_session
            from app.models import User
            
            session = get_session()
            user_obj = session.query(User).filter_by(username=username).first()
            if user_obj:
                self.current_user_id = int(user_obj.id)
                if user_obj.settings:
                    self.settings = {
                        "theme": user_obj.settings.theme,
                        "question_count": user_obj.settings.question_count,
                        "sound_enabled": user_obj.settings.sound_enabled
                    }
                    # Apply Theme immediately
                    if self.settings.get("theme"):
                        self.apply_theme(self.settings["theme"])
            session.close()
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")

    def _post_login_init(self) -> None:
        """Initialize UI after login"""
        if hasattr(self, 'sidebar'):
            self.sidebar.update_user_info()
            self.sidebar.pack(side="left", fill="y")
            # Select Home to trigger view and visual update
            self.sidebar.select_item("home") # This triggers on_change -> switch_view, which is fine for init
        else:
            self.switch_view("home")

    def apply_theme(self, theme_name: str) -> None:
        """Update colors based on theme"""
        # Delegate to UIStyles manager
        self.ui_styles.apply_theme(theme_name)
        
        # Refresh current view
        # A full restart might be best, but we'll try to update existing frames
        self.main_container.configure(bg=self.colors["bg"])
        self.content_area.configure(bg=self.colors["bg"])
        
        # Update Sidebar
        if hasattr(self, 'sidebar'):
            self.sidebar.update_theme()
            
        # Refresh current content (re-render)
        # This is strictly necessary to apply new colors to inner widgets
        # We can implement a specific update hook or just switch view (reloads it)
        # Determine current view from sidebar if possible, or track it.
        if hasattr(self, 'current_view') and self.current_view:
             self.switch_view(self.current_view)
        elif hasattr(self, 'sidebar') and self.sidebar.active_id:
             self.switch_view(self.sidebar.active_id)

        


    def switch_view(self, view_id):
        self.current_view = view_id
        self.clear_screen()
        
        # Manage Main Sidebar Visibility
        if view_id == "profile":
            if hasattr(self, 'sidebar'):
                self.sidebar.pack_forget()
        else:
            # Restore sidebar for main views
            if hasattr(self, 'sidebar'):
                if not self.sidebar.winfo_ismapped():
                     self.sidebar.pack(side="left", fill="y")
                
                # Sync visual selection if it's a valid sidebar item
                if view_id in ["home", "exam", "dashboard", "journal", "history"]:
                    self.sidebar.select_item(view_id, trigger_callback=False)

        if view_id == "home":
            self.show_home()
        elif view_id == "exam":
            self.start_exam()
        elif view_id == "dashboard":
            self.show_dashboard()
        elif view_id == "journal":
            self.show_journal()
        elif view_id == "profile":
            self.show_profile()
        elif view_id == "history":
            self.show_history()
        elif view_id == "assessments":
            self.show_assessments()
        elif view_id == "login":
            # Logout and show login screen
            self._do_logout()

    def show_history(self):
        """Show User History (Embedded)"""
        from app.ui.results import ResultsManager
        # We need to make sure ResultsManager renders into content_area
        # Ideally, we pass content_area as root or a parent
        # But ResultsManager expects 'app'
        
        # We will create a proxy app for ResultsManager so it uses content_area as root
        class ContentProxy:
            def __init__(self, real_app, container):
                self.real_app = real_app
                self.root = container # Trick ResultsManager to use this as root
                self.colors = real_app.colors
                self.username = real_app.username
                self.i18n = real_app.i18n
                # Pass-through methods
                self.clear_screen = lambda: [w.destroy() for w in container.winfo_children()]
                self.create_welcome_screen = real_app.show_home # For "Back" buttons
                
                # Forward attribute access to real_app for others
                self.__dict__.update({k: v for k, v in real_app.__dict__.items() if k not in self.__dict__})

            def __getattr__(self, name):
                return getattr(self.real_app, name)

        self.clear_screen()
        proxy = ContentProxy(self, self.content_area)
        rm = ResultsManager(proxy)
        rm.display_user_history(self.username)

    def clear_screen(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def show_assessments(self):
        """Show Assessment Selection Hub"""
        self.clear_screen()
        hub = AssessmentHub(self.content_area, self)
        hub.render()

    def show_home(self):
        # --- WEB-STYLE HERO DASHBOARD ---
        
        # Clear previous
        for widget in self.content_area.winfo_children():
            widget.destroy()
            
        # Main Scrollable Container (Optional, but good for web feel)
        # For now, simple pack is cleaner for fixed size
        
        # 1. Hero Section (Greeting)
        hero_frame = tk.Frame(self.content_area, bg=self.colors["primary"], height=200)
        hero_frame.pack(fill="x", padx=30, pady=(30, 20))
        hero_frame.pack_propagate(False) # Force height
        
        # Hero Text
        tk.Label(hero_frame, text=f"Welcome back, {self.username or 'Guest'}!", 
                 font=("Segoe UI", 28, "bold"), 
                 bg=self.colors["primary"], fg=self.colors["text_inverse"]).pack(anchor="w", padx=30, pady=(40, 5))
                 
        tk.Label(hero_frame, text="Ready to continue your journey to better wellbeing?", 
                 font=("Segoe UI", 14), 
                 bg=self.colors["primary"], fg=self.colors.get("primary_light", "#E0E7FF")).pack(anchor="w", padx=30)

        # Journal Summary Section (Enhanced Journal Feature)
        if self.username:
            try:
                from app.db import get_session
                from app.models import JournalEntry
                session = get_session()
                recent_entries = session.query(JournalEntry)\
                    .filter_by(username=self.username)\
                    .order_by(JournalEntry.entry_date.desc())\
                    .limit(3)\
                    .all()
                session.close()

                if recent_entries:
                    summary_frame = tk.Frame(self.content_area, bg=self.colors["bg"], pady=10)
                    summary_frame.pack(fill="x", padx=30, pady=(10, 0))

                    tk.Label(summary_frame, text="📝 Recent Journal Insights",
                             font=("Segoe UI", 14, "bold"), bg=self.colors["bg"],
                             fg=self.colors["text_primary"]).pack(anchor="w")

                    # Calculate average mood
                    avg_mood = sum(getattr(e, 'sentiment_score', 0) or 0 for e in recent_entries) / len(recent_entries)
                    mood_text = "Positive" if avg_mood > 20 else "Neutral" if avg_mood > -20 else "Negative"
                    mood_color = "#4CAF50" if avg_mood > 20 else "#FF9800" if avg_mood > -20 else "#F44336"

                    tk.Label(summary_frame, text=f"Average mood over last {len(recent_entries)} entries: {mood_text}",
                             font=("Segoe UI", 11), bg=self.colors["bg"], fg=mood_color).pack(anchor="w", pady=(5, 0))
            except Exception as e:
                self.logger.error(f"Failed to load journal summary: {e}")

        # 2. Quick Actions Grid
        grid_frame = tk.Frame(self.content_area, bg=self.colors["bg"])
        grid_frame.pack(fill="both", expand=True, padx=30)

        # Card Helper
        def create_web_card(parent, title, desc, icon, color, cmd):
            card = tk.Frame(parent, bg=self.colors["surface"], padx=25, pady=25,
                           highlightbackground=self.colors.get("border", "#E2E8F0"), highlightthickness=1)

            # Icon Circle
            icon_canvas = tk.Canvas(card, width=50, height=50, bg=self.colors["surface"], highlightthickness=0)
            icon_canvas.pack(anchor="w", pady=(0, 15))
            icon_canvas.create_oval(2, 2, 48, 48, fill=color, outline=color)
            icon_canvas.create_text(25, 25, text=icon, font=("Segoe UI", 20), fill="white")

            # Text
            tk.Label(card, text=title, font=("Segoe UI", 16, "bold"),
                     bg=self.colors["surface"], fg=self.colors["text_primary"]).pack(anchor="w")

            tk.Label(card, text=desc, font=("Segoe UI", 11), wraplength=200, justify="left",
                     bg=self.colors["surface"], fg=self.colors["text_secondary"]).pack(anchor="w", pady=(5, 20))

            # Pseudo-Button
            btn_lbl = tk.Label(card, text="Open →", font=("Segoe UI", 11, "bold"),
                              bg=self.colors["surface"], fg=self.colors["primary"], cursor="hand2")
            btn_lbl.pack(anchor="w")

            # Bind Events
            card.bind("<Enter>", lambda e: card.configure(bg=self.colors.get("sidebar_hover", "#F1F5F9")))
            card.bind("<Leave>", lambda e: card.configure(bg=self.colors["surface"]))
            card.bind("<Button-1>", lambda e: cmd())
            btn_lbl.bind("<Button-1>", lambda e: cmd())

            return card

        # Layout Cards
        # Grid: 3 columns
        card1 = create_web_card(grid_frame, "Assessment", "Track your mental growth with detailed quizzes.", "🧠", self.colors["primary"], lambda: self.sidebar.select_item("exam"))
        card1.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        card2 = create_web_card(grid_frame, "Daily Journal", "Record your thoughts and analyze patterns.", "📝", self.colors["success"], lambda: self.sidebar.select_item("journal"))
        card2.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        card3 = create_web_card(grid_frame, "Analytics", "Visualize your wellbeing trends over time.", "📊", self.colors["accent"], lambda: self.sidebar.select_item("dashboard"))
        card3.grid(row=0, column=2, padx=15, pady=15, sticky="nsew")

        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(2, weight=1)

    def start_exam(self):
        # ExamManager expects 'app' with 'root'. 
        # We need to trick it to render into content_area, OR let it takeover.
        # But ExamManager uses self.root which is mapped to self.root (Window).
        # We can temporarily map self.root to self.content_area for the manager?
        # NO, that's risky.
        # Instead, we pass 'self' as app.
        # And we'll patch 'root' on self to be content_area if ExamManager uses app.root
        
        # Actually ExamManager init: self.root = app.root.
        # So we can define property 'root' on App? No, App.root is the Window.
        
        # Let's instantiate ExamManager but pass a Proxy App object that returns content_area as root?
        class AppProxy:
            def __init__(self, app_instance):
                self.app = app_instance
            def __getattr__(self, name):
                if name == "root": return self.app.content_area
                return getattr(self.app, name)

        self.exam_manager = ExamManager(AppProxy(self))
        self.exam_manager.start_test()

    def show_dashboard(self):
        # Open Dashboard (Embedded)
        try:
            self.clear_screen()
            dashboard = AnalyticsDashboard(self.content_area, self.username, theme="dark", colors=self.colors)
            dashboard.render_dashboard()
        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")
            messagebox.showerror("Error", f"Failed to open dashboard: {e}")

    def show_journal(self):
        # Open Journal Application
        # New embedded mode:
        self.clear_screen()
        try:
            journal_feature = JournalFeature(self.root, app=self)
            journal_feature.render_journal_view(self.content_area, self.username or "Guest")
        except Exception as e:
            self.logger.error(f"Journal error: {e}")
            messagebox.showerror("Error", f"Failed to open journal: {e}")

    def show_profile(self):
        from app.ui.profile import UserProfileView
        # Render Profile into content_area
        UserProfileView(self.content_area, self)

    def _do_logout(self) -> None:
        """Clear user session and show login screen."""
        # Clear user state
        self.username = None
        self.current_user_id = None
        self.settings = {}
        
        # Hide sidebar
        if hasattr(self, 'sidebar'):
            self.sidebar.pack_forget()
        
        # Clear content area
        self.clear_screen()
        
        # Show login screen
        self.show_login_screen()

    def graceful_shutdown(self) -> None:
        """Perform graceful shutdown operations"""
        self.logger.info("Initiating graceful application shutdown...")

        try:
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
        if hasattr(self, 'root') and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass  # Window already destroyed

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

