import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any

from app.ui.sidebar import SidebarNav
from app.ui.styles import UIStyles
from app.i18n_manager import get_i18n
from app.questions import load_questions
from app.auth import AuthManager
from app.logger import get_logger


class AppInitializer:
    def __init__(self, app):
        self.app = app
        self.setup_ui()
        self.load_initial_data()


    def setup_ui(self):
        """Set up the main UI components"""
        self.app.root.title("SoulSense AI - Mental Wellbeing")
        self.app.root.geometry("1400x900")

        # Initialize Logger
        self.app.logger = get_logger(__name__)

        # Initialize Styles
        self.app.ui_styles = UIStyles(self.app)
        self.app.colors: Dict[str, str] = {}
        self.app.ui_styles.apply_theme("dark")  # Default theme

        # Fonts
        self.app.fonts = {
            "h1": ("Segoe UI", 24, "bold"),
            "h2": ("Segoe UI", 20, "bold"),
            "h3": ("Segoe UI", 16, "bold"),
            "body": ("Segoe UI", 12),
            "small": ("Segoe UI", 10),
        }

        # State
        self.app.username: Optional[str] = None
        self.app.current_user_id: Optional[int] = None
        self.app.age = 25
        self.app.age_group = "adult"
        self.app.i18n = get_i18n()
        self.app.questions = []
        self.app.auth = AuthManager()
        self.app.settings: Dict[str, Any] = {}

        # UI Layout
        self.app.main_container = tk.Frame(self.app.root, bg=self.app.colors.get("bg", "#111111"))
        self.app.main_container.pack(fill="both", expand=True)

        # Sidebar (Initialized but hidden until login)
        self.app.sidebar = SidebarNav(
            self.app.main_container,
            self.app,
            [
                {"id": "home", "label": "Home", "icon": "🏠"},
                {"id": "exam", "label": "Assessment", "icon": "🧠"},
                {"id": "dashboard", "label": "Dashboard", "icon": "📊"},
                {"id": "journal", "label": "Journal", "icon": "📝"},
                {"id": "assessments", "label": "Deep Dive", "icon": "🔍"},
                {"id": "history", "label": "History", "icon": "📚"},
            ],
            on_change=self.app.switch_view,
        )

        # Content Area
        self.app.content_area = tk.Frame(self.app.main_container, bg=self.app.colors.get("bg", "#111111"))
        self.app.content_area.pack(side="right", fill="both", expand=True)

        # Initialize Features
        self.app.exam_manager = None

        # Sidebar hide until login
        self.app.sidebar.pack_forget()

    def load_initial_data(self):
        """Load initial data like questions"""
        try:
            self.app.questions = load_questions()
        except Exception as e:
            self.app.logger.error(f"Failed to load questions: {e}")
            messagebox.showerror("Error", f"Could not load questions: {e}")


    def _load_user_settings(self, username: str):
        """Load settings from DB for user"""
        try:
            from app.db import safe_db_context
            from app.models import User

            with safe_db_context() as session:
                user_obj = session.query(User).filter_by(username=username).first()

                if user_obj:
                    self.app.current_user_id = int(user_obj.id)

                    if user_obj.settings:
                        self.app.settings = {
                            "theme": user_obj.settings.theme,
                            "question_count": user_obj.settings.question_count,
                            "sound_enabled": user_obj.settings.sound_enabled,
                        }

                        # Apply Theme immediately
                        if self.app.settings.get("theme"):
                            self.app.ui_styles.apply_theme(self.app.settings["theme"])

        except Exception as e:
            self.app.logger.error(f"Error loading settings: {e}")

    def _post_login_init(self):
        """Initialize UI after login"""
        if hasattr(self.app, "sidebar"):
            self.app.sidebar.update_user_info()
            self.app.sidebar.pack(side="left", fill="y")
            self.app.sidebar.select_item("home")
        else:
            self.app.switch_view("home")

    def logout_user(self):
        """Reset application state for logout"""
        # Clear session data
        self.app.username = None
        self.app.current_user_id = None
        self.app.settings = {}

        # Clear DB Session
        try:
            from app.db import SessionLocal
            SessionLocal.remove()
            self.app.logger.info("Database session removed during logout")
        except Exception as e:
            self.app.logger.error(f"Error removing session during logout: {e}")

        # Hide Sidebar
        if hasattr(self.app, "sidebar"):
            self.app.sidebar.pack_forget()

        # Clear Content Area
        if hasattr(self.app, "content_area"):
            for widget in self.app.content_area.winfo_children():
                widget.destroy()

        # Show Login Screen again
        # Show Login Screen again
        if hasattr(self.app, "auth_handler"):
            self.app.auth_handler.start_login_flow()
        else:
            # Fallback if auth_handler is somehow missing (initialization race)
             self.app.logger.error("Auth handler not found during logout")
