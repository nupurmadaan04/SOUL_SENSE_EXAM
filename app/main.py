import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
import threading
import time
from datetime import datetime
import json
import webbrowser
import os
import sys
import random # For random tips
from app.ui.styles import UIStyles, ColorSchemes
from app.ui.auth import AuthManager
from app.ui.exam import ExamManager
from app.ui.results import ResultsManager
from app.ui.settings import SettingsManager

# NLTK (optional) - import defensively so app can run without it
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    SENTIMENT_AVAILABLE = True
except Exception:
    SENTIMENT_AVAILABLE = False
    SentimentIntensityAnalyzer = None
import traceback # Keep this, it was in the original and not explicitly removed

from app.db import get_session, get_connection
from app.config import APP_CONFIG
from app.constants import BENCHMARK_DATA
from app.models import User, Score, Response, Question
from app.exceptions import DatabaseError, ValidationError, AuthenticationError, APIConnectionError, SoulSenseError
from app.logger import setup_logging
from app.analysis.data_cleaning import DataCleaner
from app.utils import load_settings, save_settings, compute_age_group
from app.questions import load_questions

# Try importing optional features
try:
    from app.ui.journal import JournalFeature
except ImportError:
    logging.warning("Could not import JournalFeature")
    JournalFeature = None

try:
    from app.ml.predictor import SoulSenseMLPredictor
except ImportError:
    logging.warning("Could not import SoulSenseMLPredictor")
    SoulSenseMLPredictor = None

try:
    from app.ui.dashboard import AnalyticsDashboard
except ImportError:
    logging.warning("Could not import AnalyticsDashboard")
    AnalyticsDashboard = None

# Ensure VADER lexicon is downloaded when NLTK is available
if SENTIMENT_AVAILABLE:
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        try:
            nltk.download('vader_lexicon', quiet=True)
        except Exception:
            # If download fails, continue without sentiment functionality
            SENTIMENT_AVAILABLE = False

# ---------------- LOGGING SETUP ----------------
setup_logging()

def show_error(title, message, error_obj=None):
    """
    Display a friendly error message to the user and ensure it's logged.
    """
    if error_obj:
        logging.error(f"{title}: {message} | Error: {error_obj}", exc_info=(type(error_obj), error_obj, error_obj.__traceback__) if hasattr(error_obj, '__traceback__') else True)
    else:
        logging.error(f"{title}: {message}")
    
    # Show UI dialog
    try:
        messagebox.showerror(title, f"{message}\n\nDetails have been logged." if error_obj else message)
    except Exception:
        # Fallback if UI fails
        print(f"CRITICAL UI ERROR: {title} - {message}", file=sys.stderr)

def global_exception_handler(self, exc, val, tb):
    """
    Global exception handler for Tkinter callbacks.
    Catches unhandled errors, logs them, and shows a friendly dialog.
    """
    logging.critical("Unhandled exception in GUI", exc_info=(exc, val, tb))
    
    title = "Unexpected Error"
    message = "An unexpected error occurred."
    
    # Handle custom exceptions nicely
    if isinstance(val, SoulSenseError):
        title = "Application Error"
        message = str(val)
    elif isinstance(val, tk.TclError):
        title = "Interface Error"
        message = "A graphical interface error occurred."
    
    show_error(title, message)

# Hook into Tkinter's exception reporting
tk.Tk.report_callback_exception = global_exception_handler

# ---------------- SETTINGS ----------------
# Imported from app.utils





# ---------------- LOGGING ----------------
logging.basicConfig(
    filename="logs/soulsense.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Application started")

# ---------------- DB INIT ----------------
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    total_score INTEGER,
    age INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# ---------------- LOAD QUESTIONS FROM DB ----------------
try:
    rows = load_questions()  # [(id, text, tooltip, min_age, max_age)]
    # Store (text, tooltip) tuple
    all_questions = [(q[1], q[2]) for q in rows]
    
    if not all_questions:
        raise ResourceError("Question bank empty: No questions found in database.")

    logging.info("Loaded %s total questions from DB", len(all_questions))

except Exception as e:
    show_error("Fatal Error", "Question bank could not be loaded.\nThe application cannot start.", e)
    sys.exit(1)

# ---------------- GUI ----------------
class SoulSenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        self.root.geometry("650x550")  # Increased size for benchmarking
        
        # Initialize Styles Manager
        self.styles = UIStyles(self)
        self.auth = AuthManager(self)
        self.exam = ExamManager(self)
        self.results = ResultsManager(self)
        self.settings_manager = SettingsManager(self)
        
        # Initialize ML Predictor

        try:
            self.ml_predictor = SoulSenseMLPredictor()
            logging.info("ML Predictor initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize ML Predictor: {e}")
            self.ml_predictor = None

        # Initialize Journal Feature
        self.journal_feature = JournalFeature(self.root)



        # Load settings
        self.settings = load_settings()
        
        # Define color schemes using premium design system
        # Start with the base schemes from styles module
        self.color_schemes = {
            "light": {
                **ColorSchemes.LIGHT,
                "chart_bg": "#FFFFFF",
                "chart_fg": "#0F172A",
                "improvement_good": "#10B981",
                "improvement_bad": "#EF4444",
                "improvement_neutral": "#F59E0B",
                "excellent": "#3B82F6",
                "good": "#10B981",
                "average": "#F59E0B",
                "needs_work": "#EF4444",
                "benchmark_better": "#10B981",
                "benchmark_worse": "#EF4444",
                "benchmark_same": "#F59E0B"
            },
            "dark": {
                **ColorSchemes.DARK,
                "chart_bg": "#1E293B",
                "chart_fg": "#F8FAFC",
                "improvement_good": "#34D399",
                "improvement_bad": "#F87171",
                "improvement_neutral": "#FBBF24",
                "excellent": "#60A5FA",
                "good": "#34D399",
                "average": "#FBBF24",
                "needs_work": "#F87171",
                "benchmark_better": "#34D399",
                "benchmark_worse": "#F87171",
                "benchmark_same": "#FBBF24"
            }
        }
        
        # Apply theme
        self.apply_theme(self.settings.get("theme", "light"))
        
        # Test variables
        self.username = ""
        self.age = None
        self.age_group = None
        self.profession = None
        
        # Initialize Sentiment Variables
        self.sentiment_score = 0.0 
        self.reflection_text = ""
        
        # Initialize Sentiment Analyzer
        try:
            self.sia = SentimentIntensityAnalyzer()
            logging.info("SentimentIntensityAnalyzer initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize SentimentIntensityAnalyzer: {e}")
            self.sia = None

        self.current_question = 0
        self.responses = []
        self.current_score = 0
        self.current_max_score = 0
        self.current_percentage = 0
        
        # Load questions based on settings
        question_count = self.settings.get("question_count", 10)
        self.questions = all_questions[:min(question_count, len(all_questions))]
        logging.info("Using %s questions based on settings", len(self.questions))
        
        self.total_questions_count = len(all_questions)
        self.create_welcome_screen()

    def reload_questions(self, count):
        """Reload questions based on new settings count"""
        self.questions = all_questions[:min(count, len(all_questions))]
        logging.info("Reloaded %s questions based on settings", len(self.questions))

    def apply_theme(self, theme_name):
        """Apply the selected theme to the application"""
        self.styles.apply_theme(theme_name)

    def toggle_tooltip(self, event, text):
        """Toggle tooltip visibility on click/enter"""
        self.styles.toggle_tooltip(event, text)

    def create_widget(self, widget_type, *args, **kwargs):
        """Create a widget with current theme colors"""
        return self.styles.create_widget(widget_type, *args, **kwargs)

    def darken_color(self, color):
        """Darken a color for active button state"""
        return self.styles.darken_color(color)



    def create_welcome_screen(self):
        """Create initial welcome screen with settings option"""
        self.auth.create_welcome_screen()
        
        # Title
        title = self.create_widget(
            tk.Label,
            self.root,
            text="Welcome to Soul Sense EQ Test",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=20)
        
        # Description
        desc = self.create_widget(
            tk.Label,
            self.root,
            text="Assess your Emotional Intelligence\nwith our comprehensive questionnaire",
            font=("Arial", 12)
        )
        desc.pack(pady=10)
        
        # Current settings display
        settings_frame = self.create_widget(tk.Frame, self.root)
        settings_frame.pack(pady=20)
        
        settings_label = self.create_widget(
            tk.Label,
            settings_frame,
            text="Current Settings:",
            font=("Arial", 11, "bold")
        )
        settings_label.pack()
        
        settings_text = self.create_widget(
            tk.Label,
            settings_frame,
            text=f"ΓÇó Questions: {len(self.questions)}\n" +
                 f"ΓÇó Theme: {self.settings.get('theme', 'light').title()}\n" +
                 f"ΓÇó Sound: {'On' if self.settings.get('sound_effects', True) else 'Off'}",
            font=("Arial", 10),
            justify="left"
        )
        settings_text.pack(pady=5)
        
        # Buttons
        button_frame = self.create_widget(tk.Frame, self.root)
        button_frame.pack(pady=20)
        
        start_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Start Test",
            command=self.create_username_screen,
            font=("Arial", 12),
            width=15
        )
        start_btn.pack(pady=5)
        
        # Journal Button
        journal_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="≡ƒôû Daily Journal",
            command=self.open_journal_flow,
            font=("Arial", 12),
            width=15,
            bg="#FFB74D", # Orange accent
            fg="black"
        )
        journal_btn.pack(pady=5)

        # Dashboard Button (NEW)
        dashboard_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="≡ƒôè Dashboard",
            command=self.open_dashboard_flow,
            font=("Arial", 12),
            width=15,
            bg="#29B6F6", # Light Blue accent
            fg="black"
        )
        dashboard_btn.pack(pady=5)
        
        # View History button
        history_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="View History",
            command=self.show_history_screen,
            font=("Arial", 12),
            width=15
        )
        history_btn.pack(pady=5)
        
        settings_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Settings",
            command=self.show_settings,
            font=("Arial", 12),
            width=15
        )
        settings_btn.pack(pady=5)
        
        exit_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Exit",
            command=self.force_exit,
            font=("Arial", 12),
            width=15
        )
        exit_btn.pack(pady=5)

    def open_journal_flow(self):
        """Handle journal access, prompting for name if needed"""
        if not self.username:
            name = simpledialog.askstring("Journal Access", "Please enter your name to access your journal:", parent=self.root)
            if name and name.strip():
                self.username = name.strip()
            else:
                return
        
        self.journal_feature.open_journal_window(self.username)

    def open_dashboard_flow(self):
        """Handle dashboard access, prompting for name if needed"""
        if not self.username:
            name = simpledialog.askstring("Dashboard Access", "Please enter your name to view your dashboard:", parent=self.root)
            if name and name.strip():
                self.username = name.strip()
            else:
                return
        
        if AnalyticsDashboard:
            dashboard = AnalyticsDashboard(self.root, self.username)
            dashboard.open_dashboard()
        else:
            messagebox.showerror("Error", "Dashboard component could not be loaded")

    def run_bias_check(self):
        """Quick bias check after test completion"""
        try:
            checker = SimpleBiasChecker()
            bias_result = checker.check_age_bias()
            
            if bias_result.get('status') == 'potential_bias':
                # Log bias warning
                logging.warning(f"Potential age bias detected: {bias_result}")
                
                # Optional: Show warning to user
                # messagebox.showwarning("Bias Alert", 
                #     f"Note: Test scores show differences across age groups.\n"
                #     f"Issues: {', '.join(bias_result.get('issues', []))}")
        
        except Exception as e:
            logging.error(f"Bias check failed: {e}")
            
    def show_settings(self):
        """Show settings configuration window"""
        self.settings_manager.show_settings()

    # ---------- ORIGINAL SCREENS (Modified) ----------
    def create_username_screen(self):
        self.auth.create_username_screen()

    def validate_name_input(self, name):
        return self.auth.validate_name_input(name)

    def validate_age_input(self, age_str):
        return self.auth.validate_age_input(age_str)
    
    def _enter_start(self, event):
        self.start_test()

    def start_test(self):
        self.exam.start_test()

    def show_question(self):
        self.exam.show_question()

    def previous_question(self):
        self.exam.previous_question()

    def save_answer(self):
        self.exam.save_answer()

    def finish_test(self):
        self.exam.finish_test()

    def show_reflection_screen(self):
        self.exam.show_reflection_screen()
        
    def submit_reflection(self):
        self.exam.submit_reflection()







    def show_ml_analysis(self):
        self.results.show_ml_analysis()

    def show_history_screen(self):
        self.results.show_history_screen()

    def view_user_history(self, username):
        self.results.view_user_history(username)

    def display_user_history(self, username):
        self.results.display_user_history(username)

    def show_comparison_screen(self):
        self.results.show_comparison_screen()

    def reset_test(self):
        self.results.reset_test()

    def force_exit(self):
        try:
            conn.close()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def clear_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

# ---------------- MAIN ----------------
class SplashScreen:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.geometry("400x300")
        
        # Center Window
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        self.root.geometry(f"+{x}+{y}")
        
        self.root.configure(bg="#2C3E50")
        
        tk.Label(self.root, text="Soul Sense", font=("Arial", 30, "bold"), bg="#2C3E50", fg="white").pack(expand=True, pady=(50, 10))
        tk.Label(self.root, text="Emotional Intelligence Exam", font=("Arial", 14), bg="#2C3E50", fg="#BDC3C7").pack(expand=True, pady=(0, 50))
        
        self.loading_label = tk.Label(self.root, text="Initializing...", font=("Arial", 10), bg="#2C3E50", fg="#BDC3C7")
        self.loading_label.pack(side="bottom", pady=20)

    def close_after_delay(self, delay, callback):
        self.root.after(delay, callback)

if __name__ == "__main__":
    splash_root = tk.Tk()
    splash = SplashScreen(splash_root)

    def launch_main_app():
        splash_root.destroy()
        root = tk.Tk()
        app = SoulSenseApp(root)
        root.protocol("WM_DELETE_WINDOW", app.force_exit)
        root.mainloop()

    splash.close_after_delay(2000, launch_main_app)
    splash_root.mainloop()
