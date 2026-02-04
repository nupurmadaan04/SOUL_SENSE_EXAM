import tkinter as tk
from app.ui.dashboard import AnalyticsDashboard
from app.ui.journal import JournalFeature
from app.ui.assessments import AssessmentHub
from app.ui.results import ResultsManager
from app.ui.profile import UserProfileView
from app.ui.exam import ExamManager
from app.logger import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.main import SoulSenseApp

class ViewManager:
    def __init__(self, app: 'SoulSenseApp'):
        self.app = app
        self.logger = get_logger(__name__)

    def switch_view(self, view_id):
        self.app.current_view = view_id
        self.clear_screen()

        # Manage Main Sidebar Visibility
        if view_id == "profile":
            if hasattr(self.app, 'sidebar'):
                self.app.sidebar.pack_forget()
        else:
            # Restore sidebar for main views
            if hasattr(self.app, 'sidebar'):
                if not self.app.sidebar.winfo_ismapped():
                    self.app.sidebar.pack(side="left", fill="y")

                # Sync visual selection if it's a valid sidebar item
                if view_id in ["home", "exam", "dashboard", "journal", "history"]:
                    self.app.sidebar.select_item(view_id, trigger_callback=False)

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

    def clear_screen(self):
        for widget in self.app.content_area.winfo_children():
            widget.destroy()

    def show_home(self):
        # --- WEB-STYLE HERO DASHBOARD ---

        # Clear previous
        for widget in self.app.content_area.winfo_children():
            widget.destroy()

        # 1. Hero Section (Greeting)
        hero_frame = tk.Frame(self.app.content_area, bg=self.app.colors["primary"], height=200)
        hero_frame.pack(fill="x", padx=30, pady=(30, 20))
        hero_frame.pack_propagate(False)  # Force height

        # Hero Text
        tk.Label(hero_frame, text=f"Welcome back, {self.app.username or 'Guest'}!",
                 font=("Segoe UI", 28, "bold"),
                 bg=self.app.colors["primary"], fg=self.app.colors["text_inverse"]).pack(anchor="w", padx=30, pady=(40, 5))

        tk.Label(hero_frame, text="Ready to continue your journey to better wellbeing?",
                 font=("Segoe UI", 14),
                 bg=self.app.colors["primary"], fg=self.app.colors.get("primary_light", "#E0E7FF")).pack(anchor="w", padx=30)

        # Journal Summary Section (Enhanced Journal Feature)
        if self.app.username:
            try:
                from app.db import safe_db_context
                from app.models import JournalEntry
                with safe_db_context() as session:
                    recent_entries = session.query(JournalEntry)\
                        .filter_by(username=self.app.username)\
                        .order_by(JournalEntry.entry_date.desc())\
                        .limit(3)\
                        .all()

                    # Calculate average mood
                    if recent_entries:
                        avg_mood = sum(getattr(e, 'sentiment_score', 0) or 0 for e in recent_entries) / len(recent_entries)
                        mood_text = "Positive" if avg_mood > 20 else "Neutral" if avg_mood > -20 else "Negative"
                        mood_color = "#4CAF50" if avg_mood > 20 else "#FF9800" if avg_mood > -20 else "#F44336"
                    else:
                        avg_mood = 0
                        mood_text = "None"
                        mood_color = "gray"

                if recent_entries:
                    summary_frame = tk.Frame(self.app.content_area, bg=self.app.colors["bg"], pady=10)
                    summary_frame.pack(fill="x", padx=30, pady=(10, 0))

                    tk.Label(summary_frame, text="📝 Recent Journal Insights",
                             font=("Segoe UI", 14, "bold"), bg=self.app.colors["bg"],
                             fg=self.app.colors["text_primary"]).pack(anchor="w")

                    tk.Label(summary_frame, text=f"Average mood over last {len(recent_entries)} entries: {mood_text}",
                             font=("Segoe UI", 11), bg=self.app.colors["bg"], fg=mood_color).pack(anchor="w", pady=(5, 0))
            except Exception as e:
                self.logger.error(f"Failed to load journal summary: {e}")

        # 2. Quick Actions Grid
        grid_frame = tk.Frame(self.app.content_area, bg=self.app.colors["bg"])
        grid_frame.pack(fill="both", expand=True, padx=30)

        # Card Helper
        def create_web_card(parent, title, desc, icon, color, cmd):
            card = tk.Frame(parent, bg=self.app.colors["surface"], padx=25, pady=25,
                           highlightbackground=self.app.colors.get("border", "#E2E8F0"), highlightthickness=1)

            # Icon Circle
            icon_canvas = tk.Canvas(card, width=50, height=50, bg=self.app.colors["surface"], highlightthickness=0)
            icon_canvas.pack(anchor="w", pady=(0, 15))
            icon_canvas.create_oval(2, 2, 48, 48, fill=color, outline=color)
            icon_canvas.create_text(25, 25, text=icon, font=("Segoe UI", 20), fill="white")

            # Text
            tk.Label(card, text=title, font=("Segoe UI", 16, "bold"),
                     bg=self.app.colors["surface"], fg=self.app.colors["text_primary"]).pack(anchor="w")

            tk.Label(card, text=desc, font=("Segoe UI", 11), wraplength=200, justify="left",
                     bg=self.app.colors["surface"], fg=self.app.colors["text_secondary"]).pack(anchor="w", pady=(5, 20))

            # Pseudo-Button
            btn_lbl = tk.Label(card, text="Open →", font=("Segoe UI", 11, "bold"),
                              bg=self.app.colors["surface"], fg=self.app.colors["primary"], cursor="hand2")
            btn_lbl.pack(anchor="w")

            # Bind Events
            card.bind("<Enter>", lambda e: card.configure(bg=self.app.colors.get("sidebar_hover", "#F1F5F9")))
            card.bind("<Leave>", lambda e: card.configure(bg=self.app.colors["surface"]))
            card.bind("<Button-1>", lambda e: cmd())
            btn_lbl.bind("<Button-1>", lambda e: cmd())

            return card

        # Layout Cards
        # Grid: 3 columns
        card1 = create_web_card(grid_frame, "Assessment", "Track your mental growth with detailed quizzes.", "🧠", self.app.colors["primary"], lambda: self.app.sidebar.select_item("exam"))
        card1.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        card2 = create_web_card(grid_frame, "Daily Journal", "Record your thoughts and analyze patterns.", "📝", self.app.colors["success"], lambda: self.app.sidebar.select_item("journal"))
        card2.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")

        card3 = create_web_card(grid_frame, "Analytics", "Visualize your wellbeing trends over time.", "📊", self.app.colors["accent"], lambda: self.app.sidebar.select_item("dashboard"))
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

        self.app.exam_manager = ExamManager(AppProxy(self.app))
        self.app.exam_manager.start_test()

    def show_dashboard(self):
        # Open Dashboard (Embedded)
        try:
            self.clear_screen()
            dashboard = AnalyticsDashboard(self.app.content_area, self.app.username, theme="dark", colors=self.app.colors)
            dashboard.render_dashboard()
        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")
            tk.messagebox.showerror("Error", f"Failed to open dashboard: {e}")

    def show_journal(self):
        # Open Journal Application
        # New embedded mode:
        self.clear_screen()
        try:
            journal_feature = JournalFeature(self.app.root, app=self.app)
            journal_feature.render_journal_view(self.app.content_area, self.app.username or "Guest")
        except Exception as e:
            self.logger.error(f"Journal error: {e}")
            tk.messagebox.showerror("Error", f"Failed to open journal: {e}")

    def show_profile(self):
        from app.ui.profile import UserProfileView
        # Render Profile into content_area
        UserProfileView(self.app.content_area, self.app)

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
                self.root = container  # Trick ResultsManager to use this as root
                self.colors = real_app.colors
                self.username = real_app.username
                self.i18n = real_app.i18n
                # Pass-through methods
                self.clear_screen = lambda: [w.destroy() for w in container.winfo_children()]
                self.create_welcome_screen = real_app.show_home  # For "Back" buttons

                # Forward attribute access to real_app for others
                self.__dict__.update({k: v for k, v in real_app.__dict__.items() if k not in self.__dict__})

            def __getattr__(self, name):
                return getattr(self.real_app, name)

        self.clear_screen()
        proxy = ContentProxy(self.app, self.app.content_area)
        rm = ResultsManager(proxy)
        rm.display_user_history(self.app.username)

    def show_assessments(self):
        """Show Assessment Selection Hub"""
        self.clear_screen()
        hub = AssessmentHub(self.app.content_area, self.app)
        hub.render()

    def _do_logout(self):
        """Clear user session and show login screen."""
        self.app.logout()
