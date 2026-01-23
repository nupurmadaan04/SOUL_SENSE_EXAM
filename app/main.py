
import tkinter as tk
from tkinter import messagebox, ttk
import logging
import signal
import atexit
from app.ui.sidebar import SidebarNav
from app.ui.styles import UIStyles
from app.ui.dashboard import AnalyticsDashboard
from app.ui.journal import JournalFeature
from app.ui.profile import UserProfileView
from app.ui.exam import ExamManager
from app.auth import AuthManager
from app.i18n_manager import get_i18n
from app.questions import load_questions
from app.ui.assessments import AssessmentHub
from app.startup_checks import run_all_checks, get_check_summary, CheckStatus
from app.exceptions import IntegrityError
from app.logger import get_logger, setup_logging
from app.error_handler import (
    get_error_handler,
    setup_global_exception_handlers,
    ErrorSeverity,
)
from typing import Optional, Dict, Any, List
from app.db import get_session

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
        login_win = self._create_login_window()
        self._setup_login_form(login_win)
    
    def _create_login_window(self) -> tk.Toplevel:
        """Create and configure login window"""
        login_win = tk.Toplevel(self.root)
        login_win.title("SoulSense Login")
        login_win.geometry("400x500")
        login_win.configure(bg=self.colors["bg"])
        login_win.transient(self.root)
        login_win.grab_set()
        login_win.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())
        
        # Center window
        self._center_window(login_win, 400, 500)
        return login_win
    
    def _center_window(self, window: tk.Toplevel, width: int, height: int) -> None:
        """Center window on parent"""
        window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        window.geometry(f"+{x}+{y}")
    
    def _setup_login_form(self, login_win: tk.Toplevel) -> None:
        """Setup login form elements"""
        # Header
        tk.Label(
            login_win, text="SoulSense AI", 
            font=("Segoe UI", 24, "bold"), bg=self.colors["bg"], fg=self.colors["primary"]
        ).pack(pady=(40, 10))
        
        tk.Label(
            login_win, text="Login to continue",
            font=("Segoe UI", 12), bg=self.colors["bg"], fg=self.colors["text_secondary"]
        ).pack(pady=(0, 30))
        
        # Form
        entry_frame = tk.Frame(login_win, bg=self.colors["bg"])
        entry_frame.pack(fill="x", padx=40)
        
        username_entry = tk.Entry(entry_frame, font=("Segoe UI", 12))
        username_entry.pack(fill="x", pady=(5, 15))
        
        password_entry = tk.Entry(entry_frame, font=("Segoe UI", 12), show="*")
        password_entry.pack(fill="x", pady=(5, 20))
        
        # Buttons
        def do_login():
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()
            
            if not user or not pwd:
                messagebox.showerror("Error", "Please enter username and password")
                return
                
            success, msg = self.auth.login_user(user, pwd)
            if success:
                self.username = user
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

        tk.Button(
            login_win, text="Login", command=do_login,
            font=("Segoe UI", 12, "bold"), bg=self.colors["primary"], fg="white", width=20
        ).pack(pady=10)
                 
        tk.Button(
            login_win, text="Create Account", command=do_register,
            font=("Segoe UI", 10), bg=self.colors["bg"], fg=self.colors["primary"], bd=0
        ).pack()

    def _load_user_settings(self, username: str) -> None:
        """Load settings from DB for user with optimization"""
        from app.utils.error_handler import handle_db_error
        from app.query_optimizer import get_query_optimizer
        
        @handle_db_error
        def load_settings():
            optimizer = get_query_optimizer()
            user_obj = optimizer.get_user_with_profiles(username)
            
            if user_obj:
                self.current_user_id = int(user_obj.id)
                if user_obj.settings:
                    self.settings = {
                        "theme": user_obj.settings.theme,
                        "question_count": user_obj.settings.question_count,
                        "sound_enabled": user_obj.settings.sound_enabled
                    }
                    if self.settings.get("theme"):
                        self.apply_theme(self.settings["theme"])
            return True
        
        load_settings()

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
        """Clear screen with memory cleanup"""
        from app.memory_manager import cleanup_ui_memory
        
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Force memory cleanup
        cleanup_ui_memory()

    def show_assessments(self):
        """Show Assessment Selection Hub"""
        self.clear_screen()
        hub = AssessmentHub(self.content_area, self)
        hub.render()

    def show_home(self):
        """Show home dashboard"""
        self.clear_screen()
        self._create_hero_section()
        self._create_journal_summary()
        self._create_action_cards()
    
    def _create_hero_section(self) -> None:
        """Create hero section with greeting"""
        from app.ui.components import UIComponents
        
        hero_frame = tk.Frame(self.content_area, bg=self.colors["primary"], height=200)
        hero_frame.pack(fill="x", padx=30, pady=(30, 20))
        hero_frame.pack_propagate(False)
        
        UIComponents.create_label(
            hero_frame, f"Welcome back, {self.username or 'Guest'}!",
            {"font": ("Segoe UI", 28, "bold"), "bg": self.colors["primary"], "fg": self.colors["text_inverse"]}
        ).pack(anchor="w", padx=30, pady=(40, 5))
                 
        UIComponents.create_label(
            hero_frame, "Ready to continue your journey to better wellbeing?",
            {"font": ("Segoe UI", 14), "bg": self.colors["primary"], "fg": self.colors.get("primary_light", "#E0E7FF")}
        ).pack(anchor="w", padx=30)
    
    def _create_journal_summary(self) -> None:
        """Create journal insights summary"""
        from app.utils.error_handler import safe_execute
        
        @safe_execute("journal_summary_load")
        def load_journal_data():
            if not self.username:
                return None
                
            from app.db import get_session
            from app.models import JournalEntry
            session = get_session()
            recent_entries = session.query(JournalEntry)\
                .filter_by(username=self.username)\
                .order_by(JournalEntry.entry_date.desc())\
                .limit(3)\
                .all()
            session.close()
            return recent_entries
        
        recent_entries = load_journal_data()
        if recent_entries:
            self._render_journal_insights(recent_entries)
    
    def _render_journal_insights(self, entries) -> None:
        """Render journal insights section"""
        from app.ui.components import UIComponents
        
        summary_frame = tk.Frame(self.content_area, bg=self.colors["bg"], pady=10)
        summary_frame.pack(fill="x", padx=30, pady=(10, 0))

        UIComponents.create_label(
            summary_frame, "📝 Recent Journal Insights",
            {"font": ("Segoe UI", 14, "bold"), "bg": self.colors["bg"], "fg": self.colors["text_primary"]}
        ).pack(anchor="w")

        # Calculate average mood
        avg_mood = sum(getattr(e, 'sentiment_score', 0) or 0 for e in entries) / len(entries)
        mood_text = "Positive" if avg_mood > 20 else "Neutral" if avg_mood > -20 else "Negative"
        mood_color = "#4CAF50" if avg_mood > 20 else "#FF9800" if avg_mood > -20 else "#F44336"

        UIComponents.create_label(
            summary_frame, f"Average mood over last {len(entries)} entries: {mood_text}",
            {"font": ("Segoe UI", 11), "bg": self.colors["bg"], "fg": mood_color}
        ).pack(anchor="w", pady=(5, 0))
    
    def _create_action_cards(self) -> None:
        """Create quick action cards grid"""
        from app.ui.components import UIComponents
        
        grid_frame = tk.Frame(self.content_area, bg=self.colors["bg"])
        grid_frame.pack(fill="both", expand=True, padx=30)
        
        cards_data = [
            ("Assessment", "Track your mental growth with detailed quizzes.", "🧠", self.colors["primary"], lambda: self.sidebar.select_item("exam")),
            ("Daily Journal", "Record your thoughts and analyze patterns.", "📝", self.colors["success"], lambda: self.sidebar.select_item("journal")),
            ("Analytics", "Visualize your wellbeing trends over time.", "📊", self.colors["accent"], lambda: self.sidebar.select_item("dashboard"))
        ]
        
        for i, (title, desc, icon, color, cmd) in enumerate(cards_data):
            card = self._create_web_card(grid_frame, title, desc, icon, color, cmd)
            card.grid(row=0, column=i, padx=15, pady=15, sticky="nsew")
            grid_frame.grid_columnconfigure(i, weight=1)

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
        """Open Dashboard (Embedded)"""
        from app.utils.error_handler import safe_execute
        
        @safe_execute("dashboard_render")
        def render_dashboard():
            self.clear_screen()
            dashboard = AnalyticsDashboard(self.content_area, self.username, theme="dark", colors=self.colors)
            dashboard.render_dashboard()
            return True
        
        render_dashboard()

    def show_journal(self):
        """Open Journal Application"""
        from app.utils.error_handler import safe_execute
        
        @safe_execute("journal_render")
        def render_journal():
            self.clear_screen()
            journal_feature = JournalFeature(self.root, app=self)
            journal_feature.render_journal_view(self.content_area, self.username or "Guest")
            return True
        
        render_journal()

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
        """Perform graceful shutdown operations with cleanup"""
        self.logger.info("Initiating graceful application shutdown...")

        try:
            # Cleanup memory
            from app.memory_manager import memory_manager
            from app.file_manager import file_manager
            
            memory_manager.force_gc()
            file_manager.shutdown()
            
            # Commit any pending database operations
            from app.db import SessionLocal
            session = SessionLocal()
            if session:
                session.commit()
                SessionLocal.remove()
                self.logger.info("Database session committed and removed successfully")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

        self.logger.info("Application shutdown complete")

        if hasattr(self, 'root') and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass

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

    def _setup_login_buttons(self, login_win: tk.Toplevel, username_entry: tk.Entry, password_entry: tk.Entry) -> None:
        """Setup login and register buttons"""
        from app.ui.components import UIComponents
        from app.utils.error_handler import safe_execute
        
        @safe_execute("login_attempt")
        def do_login():
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()
            
            if not user or not pwd:
                messagebox.showerror("Error", "Please enter username and password")
                return
                
            success, msg = self.auth.login_user(user, pwd)
            if success:
                self.username = user
                self._load_user_settings(user)
                login_win.destroy()
                self._post_login_init()
            else:
                messagebox.showerror("Login Failed", msg)
        
        @safe_execute("register_attempt")
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

        # Create buttons
        UIComponents.create_button(
            login_win, "Login", do_login,
            {"font": ("Segoe UI", 12, "bold"), "bg": self.colors["primary"], "fg": "white", "width": 20}
        ).pack(pady=10)
                 
        UIComponents.create_button(
            login_win, "Create Account", do_register,
            {"font": ("Segoe UI", 10), "bg": self.colors["bg"], "fg": self.colors["primary"], "bd": 0}
        ).pack()
    def _create_web_card(self, parent, title: str, desc: str, icon: str, color: str, cmd: Callable) -> tk.Frame:
        """Create interactive web-style card"""
        from app.ui.components import UIComponents
        
        card = UIComponents.create_card(parent, self.colors)
        
        # Icon Circle
        icon_canvas = tk.Canvas(card, width=50, height=50, bg=self.colors["surface"], highlightthickness=0)
        icon_canvas.pack(anchor="w", pady=(0, 15))
        icon_canvas.create_oval(2, 2, 48, 48, fill=color, outline=color)
        icon_canvas.create_text(25, 25, text=icon, font=("Segoe UI", 20), fill="white")

        # Text
        UIComponents.create_label(
            card, title,
            {"font": ("Segoe UI", 16, "bold"), "bg": self.colors["surface"], "fg": self.colors["text_primary"]}
        ).pack(anchor="w")

        UIComponents.create_label(
            card, desc,
            {"font": ("Segoe UI", 11), "wraplength": 200, "justify": "left", "bg": self.colors["surface"], "fg": self.colors["text_secondary"]}
        ).pack(anchor="w", pady=(5, 20))

        # Action button
        btn_lbl = UIComponents.create_label(
            card, "Open →",
            {"font": ("Segoe UI", 11, "bold"), "bg": self.colors["surface"], "fg": self.colors["primary"], "cursor": "hand2"}
        )
        btn_lbl.pack(anchor="w")

        # Bind Events
        card.bind("<Enter>", lambda e: card.configure(bg=self.colors.get("sidebar_hover", "#F1F5F9")))
        card.bind("<Leave>", lambda e: card.configure(bg=self.colors["surface"]))
        card.bind("<Button-1>", lambda e: cmd())
        btn_lbl.bind("<Button-1>", lambda e: cmd())

        return card