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
import random
import sqlite3  # Added for satisfaction database
from app.ui.styles import UIStyles, ColorSchemes
from app.ui.auth import AuthManager
from app.ui.exam import ExamManager
from app.ui.results import ResultsManager
from app.ui.settings import SettingsManager

# Import satisfaction modules
from app.models import WorkStudySatisfaction  # Added
from app.ml.score_analyzer import SatisfactionAnalyzer  # Added

# NLTK (optional) - import defensively so app can run without it
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    SENTIMENT_AVAILABLE = True
except Exception:
    SENTIMENT_AVAILABLE = False
    SentimentIntensityAnalyzer = None
import traceback

from app.db import get_session, get_connection
from app.config import APP_CONFIG
from app.constants import BENCHMARK_DATA
from app.models import User, Score, Response, Question
from app.exceptions import DatabaseError, ValidationError, AuthenticationError, APIConnectionError, SoulSenseError, ResourceError
from app.logger import setup_logging
from app.analysis.data_cleaning import DataCleaner
from app.utils import load_settings, save_settings, compute_age_group
from app.questions import load_questions

# Try importing bias checker (optional)
try:
    from scripts.check_gender_bias import SimpleBiasChecker
except ImportError:
    SimpleBiasChecker = None

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

# Import satisfaction UI components
try:
    from app.ui.satisfaction import SatisfactionAssessment
    SATISFACTION_UI_AVAILABLE = True
except ImportError:
    logging.warning("Could not import SatisfactionAssessment UI")
    SATISFACTION_UI_AVAILABLE = False

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

# Create satisfaction table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS work_study_satisfaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    user_id INTEGER,
    motivation_score INTEGER,
    engagement_score INTEGER,
    progress_score INTEGER,
    environment_score INTEGER,
    balance_score INTEGER,
    overall_score REAL,
    weighted_average REAL,
    context_type TEXT,
    occupation TEXT,
    tenure_months INTEGER,
    interpretation TEXT,
    recommendations TEXT,
    insights TEXT,
    assessment_date TEXT,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES scores(id)
)
""")

conn.commit()

# ---------------- SATISFACTION QUESTIONS ----------------
SATISFACTION_QUESTIONS = [
    {
        "id": 101,
        "text": "How motivated are you to engage in your work/studies?",
        "category": "motivation",
        "description": "Your drive and enthusiasm for daily tasks",
        "scale_labels": {
            1: "Not at all motivated",
            2: "Slightly motivated", 
            3: "Moderately motivated",
            4: "Very motivated",
            5: "Extremely motivated"
        }
    },
    {
        "id": 102, 
        "text": "How engaged do you feel during work/study activities?",
        "category": "engagement",
        "description": "Your focus and immersion in activities",
        "scale_labels": {
            1: "Completely disengaged",
            2: "Often distracted",
            3: "Sometimes engaged",
            4: "Usually engaged",
            5: "Fully immersed"
        }
    },
    {
        "id": 103,
        "text": "How satisfied are you with your progress and achievements?",
        "category": "progress",
        "description": "Feeling of accomplishment and growth",
        "scale_labels": {
            1: "Very dissatisfied",
            2: "Dissatisfied",
            3: "Neutral",
            4: "Satisfied",
            5: "Very satisfied"
        }
    },
    {
        "id": 104,
        "text": "How satisfied are you with your work/study environment?",
        "category": "environment",
        "description": "Physical and social setting",
        "scale_labels": {
            1: "Very poor",
            2: "Poor",
            3: "Acceptable",
            4: "Good",
            5: "Excellent"
        }
    },
    {
        "id": 105,
        "text": "How satisfied are you with your work-study-life balance?",
        "category": "balance",
        "description": "Balance between responsibilities and personal life",
        "scale_labels": {
            1: "Very unbalanced",
            2: "Unbalanced",
            3: "Somewhat balanced",
            4: "Well balanced",
            5: "Perfectly balanced"
        }
    }
]

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
        self.root.geometry("650x550")
        
        # Initialize Styles Manager
        self.styles = UIStyles(self)
        self.auth = AuthManager(self)
        self.exam = ExamManager(self)
        self.results = ResultsManager(self)
        self.settings_manager = SettingsManager(self)
        
        # Initialize ML Predictor
        try:
            from app.ml.risk_predictor import RiskPredictor
            self.ml_predictor = RiskPredictor()
            logging.info("ML Predictor initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize ML Predictor: {e}")
            self.ml_predictor = None

        # Initialize Journal Feature
        if JournalFeature:
            self.journal_feature = JournalFeature(self.root)
        else:
            self.journal_feature = None
            logging.warning("JournalFeature disabled: Module could not be imported")

        # Initialize Satisfaction Assessment if available
        if SATISFACTION_UI_AVAILABLE:
            self.satisfaction_assessment = SatisfactionAssessment(self.root, self)
        else:
            self.satisfaction_assessment = None
            logging.warning("SatisfactionAssessment UI disabled: Module could not be imported")

        # Load settings
        self.settings = load_settings()
        
        # Define color schemes
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
        self.assessment_type = "eq"  # Default to emotional intelligence
        
        # Satisfaction-specific variables
        self.occupation = ""
        self.context_type = "work"  # work, study, or both
        self.tenure_months = None
        
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
        self.colors = self.color_schemes.get(theme_name, self.color_schemes["light"])

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
        """Create initial welcome screen with assessment options"""
        self.auth.create_welcome_screen()
        
        # Title
        title = self.create_widget(
            tk.Label,
            self.root,
            text="Welcome to Soul Sense Assessment Suite",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=20)
        
        # Description
        desc = self.create_widget(
            tk.Label,
            self.root,
            text="Choose an assessment type to begin",
            font=("Arial", 12)
        )
        desc.pack(pady=10)
        
        # Assessment Type Selection
        type_frame = self.create_widget(tk.Frame, self.root)
        type_frame.pack(pady=20)
        
        # Emotional Intelligence Button
        eq_btn = self.create_widget(
            tk.Button,
            type_frame,
            text="≡ƒöÇ Emotional Intelligence Test",
            command=lambda: self.set_assessment_type("eq"),
            font=("Arial", 12),
            width=25,
            bg="#2196F3",  # Blue
            fg="white"
        )
        eq_btn.pack(pady=5)
        
        # Work/Study Satisfaction Button
        sat_btn = self.create_widget(
            tk.Button,
            type_frame,
            text="≡ƒöá Work/Study Satisfaction",
            command=lambda: self.set_assessment_type("satisfaction"),
            font=("Arial", 12),
            width=25,
            bg="#4CAF50",  # Green
            fg="white"
        )
        sat_btn.pack(pady=5)
        
        # Combined Assessment Button
        combined_btn = self.create_widget(
            tk.Button,
            type_frame,
            text="≡ƒöê Combined Assessment",
            command=lambda: self.set_assessment_type("combined"),
            font=("Arial", 12),
            width=25,
            bg="#9C27B0",  # Purple
            fg="white"
        )
        combined_btn.pack(pady=5)
        
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
            text=f"\u2022 Questions: {len(self.questions)}\n" +
                 f"\u2022 Theme: {self.settings.get('theme', 'light').title()}\n" +
                 f"\u2022 Sound: {'On' if self.settings.get('sound_effects', True) else 'Off'}",
            font=("Arial", 10),
            justify="left"
        )
        settings_text.pack(pady=5)
        
        # Navigation Buttons
        button_frame = self.create_widget(tk.Frame, self.root)
        button_frame.pack(pady=20)
        
        # Journal Button
        journal_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="≡ƒôû Daily Journal",
            command=self.open_journal_flow,
            font=("Arial", 12),
            width=15,
            bg="#FFB74D",  # Orange accent
            fg="black"
        )
        journal_btn.pack(side="left", padx=5)
        
        # Dashboard Button
        dashboard_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="≡ƒôè Dashboard",
            command=self.open_dashboard_flow,
            font=("Arial", 12),
            width=15,
            bg="#29B6F6",  # Light Blue accent
            fg="black"
        )
        dashboard_btn.pack(side="left", padx=5)
        
        # History Button
        history_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="View History",
            command=self.show_history_screen,
            font=("Arial", 12),
            width=15
        )
        history_btn.pack(side="left", padx=5)
        
        # Settings Button
        settings_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Settings",
            command=self.show_settings,
            font=("Arial", 12),
            width=15
        )
        settings_btn.pack(side="left", padx=5)
        
        # Exit Button
        exit_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Exit",
            command=self.force_exit,
            font=("Arial", 12),
            width=15
        )
        exit_btn.pack(side="left", padx=5)

    def set_assessment_type(self, assessment_type):
        """Set the type of assessment and proceed to user details"""
        self.assessment_type = assessment_type
        self.create_user_details_screen()

    def create_user_details_screen(self):
        """Create user details screen based on assessment type"""
        self.clear_screen()
        
        title_text = ""
        if self.assessment_type == "eq":
            title_text = "Emotional Intelligence Assessment"
        elif self.assessment_type == "satisfaction":
            title_text = "Work/Study Satisfaction Assessment"
        else:  # combined
            title_text = "Combined Assessment"
        
        title = self.create_widget(
            tk.Label,
            self.root,
            text=title_text,
            font=("Arial", 22, "bold")
        )
        title.pack(pady=20)
        
        # Create form frame
        form_frame = self.create_widget(tk.Frame, self.root)
        form_frame.pack(pady=20)
        
        # Common fields
        tk.Label(form_frame, text="Enter your name:", 
                font=("Arial", 12)).grid(row=0, column=0, sticky="w", pady=5)
        name_var = tk.StringVar()
        name_entry = tk.Entry(form_frame, textvariable=name_var, 
                            font=("Arial", 14), width=25)
        name_entry.grid(row=0, column=1, pady=5, padx=10)
        
        tk.Label(form_frame, text="Enter your age:", 
                font=("Arial", 12)).grid(row=1, column=0, sticky="w", pady=5)
        age_var = tk.StringVar()
        age_entry = tk.Entry(form_frame, textvariable=age_var, 
                           font=("Arial", 14), width=25)
        age_entry.grid(row=1, column=1, pady=5, padx=10)
        
        row_counter = 2
        
        # Additional fields for satisfaction/combined assessments
        if self.assessment_type in ["satisfaction", "combined"]:
            tk.Label(form_frame, text="Current occupation/role:", 
                    font=("Arial", 12)).grid(row=row_counter, column=0, sticky="w", pady=5)
            occ_var = tk.StringVar()
            occ_entry = tk.Entry(form_frame, textvariable=occ_var, 
                               font=("Arial", 14), width=25)
            occ_entry.grid(row=row_counter, column=1, pady=5, padx=10)
            row_counter += 1
            
            tk.Label(form_frame, text="Context:", 
                    font=("Arial", 12)).grid(row=row_counter, column=0, sticky="w", pady=5)
            context_frame = tk.Frame(form_frame)
            context_frame.grid(row=row_counter, column=1, sticky="w", pady=5, padx=10)
            context_var = tk.StringVar(value="work")
            tk.Radiobutton(context_frame, text="Work", variable=context_var, 
                          value="work", font=("Arial", 11)).pack(side="left", padx=5)
            tk.Radiobutton(context_frame, text="Study", variable=context_var, 
                          value="study", font=("Arial", 11)).pack(side="left", padx=5)
            tk.Radiobutton(context_frame, text="Both", variable=context_var, 
                          value="both", font=("Arial", 11)).pack(side="left", padx=5)
            row_counter += 1
            
            tk.Label(form_frame, text="Months in current role (optional):", 
                    font=("Arial", 12)).grid(row=row_counter, column=0, sticky="w", pady=5)
            tenure_var = tk.StringVar()
            tenure_entry = tk.Entry(form_frame, textvariable=tenure_var, 
                                  font=("Arial", 14), width=25)
            tenure_entry.grid(row=row_counter, column=1, pady=5, padx=10)
            row_counter += 1
        
        # Button frame
        button_frame = self.create_widget(tk.Frame, self.root)
        button_frame.pack(pady=20)
        
        def start_assessment():
            # Validate name
            if not name_var.get().strip():
                messagebox.showwarning("Name Required", "Please enter your name.")
                return
            
            # Validate age
            if not age_var.get().isdigit():
                messagebox.showwarning("Invalid Age", "Please enter a valid age.")
                return
            
            # Set user data
            self.username = name_var.get().strip()
            self.age = int(age_var.get())
            
            # Set satisfaction data if applicable
            if self.assessment_type in ["satisfaction", "combined"]:
                self.occupation = occ_var.get().strip()
                self.context_type = context_var.get()
                if tenure_var.get().strip() and tenure_var.get().isdigit():
                    self.tenure_months = int(tenure_var.get())
            
            # Start appropriate assessment
            if self.assessment_type == "eq":
                self.start_eq_assessment()
            elif self.assessment_type == "satisfaction":
                self.start_satisfaction_assessment()
            else:  # combined
                # For combined, start with EQ then satisfaction
                self.start_eq_assessment()
        
        start_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Start Assessment",
            command=start_assessment,
            font=("Arial", 12),
            width=20
        )
        start_btn.pack(side="left", padx=10)
        
        back_btn = self.create_widget(
            tk.Button,
            button_frame,
            text="Back to Menu",
            command=self.create_welcome_screen,
            font=("Arial", 12),
            width=15
        )
        back_btn.pack(side="left", padx=10)

    def start_eq_assessment(self):
        """Start emotional intelligence assessment"""
        self.clear_screen()
        # Use existing ExamManager for EQ assessment
        self.exam.start_test()

    def start_satisfaction_assessment(self):
        """Start work/study satisfaction assessment"""
        if self.satisfaction_assessment:
            # Use the dedicated satisfaction UI if available
            self.satisfaction_assessment.start_assessment(
                self.username,
                self.age,
                self.occupation,
                self.context_type,
                self.tenure_months
            )
        else:
            # Fallback to simple satisfaction assessment
            self.run_simple_satisfaction_assessment()

    def run_simple_satisfaction_assessment(self):
        """Simple satisfaction assessment as fallback"""
        self.clear_screen()
        
        # Title
        title = self.create_widget(
            tk.Label,
            self.root,
            text="Work/Study Satisfaction Assessment",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=20)
        
        # Context info
        context_text = f"Assessing: {self.username} | {self.context_type.title()}"
        if self.occupation:
            context_text += f" | {self.occupation}"
        
        context_label = self.create_widget(
            tk.Label,
            self.root,
            text=context_text,
            font=("Arial", 12),
            bg="#E3F2FD",
            padx=10,
            pady=5
        )
        context_label.pack(pady=10)
        
        # Assessment variables
        self.satisfaction_responses = {}
        self.current_satisfaction_question = 0
        
        # Create question display
        self.question_label = self.create_widget(
            tk.Label,
            self.root,
            text="",
            font=("Arial", 16, "bold"),
            wraplength=600,
            justify="left"
        )
        self.question_label.pack(pady=20, padx=20)
        
        self.description_label = self.create_widget(
            tk.Label,
            self.root,
            text="",
            font=("Arial", 12),
            fg="#666",
            wraplength=600,
            justify="left"
        )
        self.description_label.pack(pady=10)
        
        # Rating scale
        scale_frame = self.create_widget(tk.Frame, self.root)
        scale_frame.pack(pady=20)
        
        self.rating_var = tk.IntVar(value=0)
        
        # Create rating buttons 1-5
        for i in range(1, 6):
            btn = tk.Radiobutton(
                scale_frame,
                text=str(i),
                variable=self.rating_var,
                value=i,
                font=("Arial", 14),
                indicatoron=0,
                width=4,
                height=2,
                bg="#E0E0E0",
                activebackground="#BDBDBD",
                relief="raised"
            )
            btn.pack(side="left", padx=5)
        
        # Scale labels
        labels_frame = self.create_widget(tk.Frame, self.root)
        labels_frame.pack(pady=5)
        
        scale_labels = ["Very Low", "Low", "Moderate", "High", "Very High"]
        for label in scale_labels:
            tk.Label(labels_frame, text=label, font=("Arial", 10)).pack(side="left", padx=15)
        
        # Navigation buttons
        nav_frame = self.create_widget(tk.Frame, self.root)
        nav_frame.pack(pady=30)
        
        tk.Button(
            nav_frame,
            text="Previous",
            command=self.prev_satisfaction_question,
            font=("Arial", 12),
            width=10
        ).pack(side="left", padx=10)
        
        tk.Button(
            nav_frame,
            text="Next",
            command=self.next_satisfaction_question,
            font=("Arial", 12),
            width=10,
            bg="#4CAF50",
            fg="white"
        ).pack(side="left", padx=10)
        
        tk.Button(
            nav_frame,
            text="Finish",
            command=self.finish_satisfaction_assessment,
            font=("Arial", 12),
            width=10,
            bg="#2196F3",
            fg="white"
        ).pack(side="left", padx=10)
        
        # Load first question
        self.load_satisfaction_question()

    def load_satisfaction_question(self):
        """Load current satisfaction question"""
        if self.current_satisfaction_question < len(SATISFACTION_QUESTIONS):
            q = SATISFACTION_QUESTIONS[self.current_satisfaction_question]
            self.question_label.config(text=f"Q{self.current_satisfaction_question + 1}. {q['text']}")
            self.description_label.config(text=q['description'])
            
            # Restore previous response if available
            if q['id'] in self.satisfaction_responses:
                self.rating_var.set(self.satisfaction_responses[q['id']])
            else:
                self.rating_var.set(0)
        else:
            self.finish_satisfaction_assessment()

    def prev_satisfaction_question(self):
        """Go to previous satisfaction question"""
        if self.current_satisfaction_question > 0:
            # Save current response
            current_q = SATISFACTION_QUESTIONS[self.current_satisfaction_question]
            if self.rating_var.get() > 0:
                self.satisfaction_responses[current_q['id']] = self.rating_var.get()
            
            self.current_satisfaction_question -= 1
            self.load_satisfaction_question()

    def next_satisfaction_question(self):
        """Go to next satisfaction question"""
        if self.rating_var.get() == 0:
            messagebox.showwarning("Selection Required", "Please select a rating before continuing.")
            return
        
        # Save current response
        current_q = SATISFACTION_QUESTIONS[self.current_satisfaction_question]
        self.satisfaction_responses[current_q['id']] = self.rating_var.get()
        
        self.current_satisfaction_question += 1
        self.load_satisfaction_question()

    def finish_satisfaction_assessment(self):
        """Finish and score satisfaction assessment"""
        # Save last response
        if self.current_satisfaction_question < len(SATISFACTION_QUESTIONS):
            current_q = SATISFACTION_QUESTIONS[self.current_satisfaction_question]
            if self.rating_var.get() > 0:
                self.satisfaction_responses[current_q['id']] = self.rating_var.get()
        
        # Calculate score
        try:
            score_result = SatisfactionAnalyzer.calculate_satisfaction_score(self.satisfaction_responses)
            
            # Save to database
            session = get_session()
            try:
                satisfaction = WorkStudySatisfaction(
                    username=self.username,
                    motivation_score=self.satisfaction_responses.get(101, 0),
                    engagement_score=self.satisfaction_responses.get(102, 0),
                    progress_score=self.satisfaction_responses.get(103, 0),
                    environment_score=self.satisfaction_responses.get(104, 0),
                    balance_score=self.satisfaction_responses.get(105, 0),
                    overall_score=score_result['overall_score']['score_0_100'],
                    weighted_average=score_result['overall_score']['weighted_average_5'],
                    context_type=self.context_type,
                    occupation=self.occupation,
                    tenure_months=self.tenure_months,
                    interpretation=score_result['interpretation']['level'],
                    recommendations=json.dumps(score_result['recommendations']),
                    assessment_date=datetime.now().isoformat(),
                    created_at=datetime.now().isoformat()
                )
                session.add(satisfaction)
                session.commit()
                
                # Show results
                self.show_satisfaction_results(score_result)
                
            except Exception as e:
                session.rollback()
                logging.error(f"Error saving satisfaction results: {e}")
                messagebox.showerror("Error", f"Could not save results: {str(e)}")
            finally:
                session.close()
                
        except Exception as e:
            logging.error(f"Error calculating satisfaction score: {e}")
            messagebox.showerror("Error", f"Could not calculate score: {str(e)}")
            self.create_welcome_screen()

    def show_satisfaction_results(self, score_result):
        """Show satisfaction assessment results"""
        self.clear_screen()
        
        # Title
        title = self.create_widget(
            tk.Label,
            self.root,
            text="Satisfaction Assessment Results",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=20)
        
        # Overall score
        score_frame = self.create_widget(tk.Frame, self.root, bg="white", relief="raised", borderwidth=2)
        score_frame.pack(pady=10, padx=20, fill="x")
        
        interpretation = score_result['interpretation']
        
        # Create simple score display
        score_label = self.create_widget(
            tk.Label,
            score_frame,
            text=f"Overall Satisfaction Score: {score_result['overall_score']['score_0_100']:.1f}/100",
            font=("Arial", 18, "bold"),
            fg=interpretation.get('color', '#333'),
            bg="white"
        )
        score_label.pack(pady=10)
        
        # Interpretation
        tk.Label(score_frame, text=interpretation['level'], 
                font=("Arial", 16, "bold"), bg="white").pack()
        tk.Label(score_frame, text=interpretation['description'], 
                font=("Arial", 12), bg="white", wraplength=500).pack(pady=5)
        
        # Domain scores
        domains_frame = tk.LabelFrame(self.root, text="Domain Scores", 
                                     font=("Arial", 14, "bold"))
        domains_frame.pack(pady=20, padx=20, fill="x")
        
        for domain, data in score_result['domain_scores'].items():
            domain_frame = tk.Frame(domains_frame)
            domain_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(domain_frame, text=domain.title(), 
                    font=("Arial", 12, "bold"), width=15, anchor="w").pack(side="left")
            
            # Simple bar representation
            bar_width = 200
            filled_width = (data['raw'] / 5) * bar_width
            
            canvas = tk.Canvas(domain_frame, width=bar_width, height=20, bg="#F5F5F5", highlightthickness=0)
            canvas.pack(side="left", padx=10)
            
            # Draw bar
            bar_color = "#4CAF50" if data['raw'] >= 4 else "#FFC107" if data['raw'] >= 3 else "#F44336"
            canvas.create_rectangle(0, 5, filled_width, 15, fill=bar_color, outline="")
            
            tk.Label(domain_frame, text=f"{data['raw']}/5", 
                    font=("Arial", 11)).pack(side="left", padx=10)
        
        # Recommendations
        if score_result.get('recommendations'):
            rec_frame = tk.LabelFrame(self.root, text="Recommendations", 
                                     font=("Arial", 14, "bold"))
            rec_frame.pack(pady=10, padx=20, fill="x")
            
            for rec in score_result['recommendations'][:3]:  # Show top 3
                tk.Label(rec_frame, text=f"• {rec['title']}: {rec['description']}", 
                        font=("Arial", 11), wraplength=550, justify="left").pack(anchor="w", padx=10, pady=2)
        
        # Navigation buttons
        button_frame = self.create_widget(tk.Frame, self.root)
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Back to Menu",
            command=self.create_welcome_screen,
            font=("Arial", 12),
            width=15
        ).pack(side="left", padx=10)
        
        tk.Button(
            button_frame,
            text="Take Another Assessment",
            command=lambda: self.set_assessment_type("satisfaction"),
            font=("Arial", 12),
            width=20,
            bg="#4CAF50",
            fg="white"
        ).pack(side="left", padx=10)

    # ---------- EXISTING METHODS ----------
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
            dashboard = AnalyticsDashboard(self.root, self.username, self.colors, self.settings.get("theme", "light"))
            dashboard.open_dashboard()
        else:
            messagebox.showerror("Error", "Dashboard component could not be loaded")

    def run_bias_check(self):
        """Quick bias check after test completion"""
        if not SimpleBiasChecker:
            return

        try:
            checker = SimpleBiasChecker()
            bias_result = checker.check_age_bias()
            
            if bias_result.get('status') == 'potential_bias':
                logging.warning(f"Potential age bias detected: {bias_result}")
        
        except Exception as e:
            logging.error(f"Bias check failed: {e}")
            
    def show_settings(self):
        """Show settings configuration window"""
        self.settings_manager.show_settings()

    # ---------- ORIGINAL METHODS ----------
    def create_username_screen(self):
        # Redirect to new user details screen
        self.create_user_details_screen()
   
   
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
        tk.Label(self.root, text="Emotional Intelligence & Satisfaction Assessment", font=("Arial", 12), bg="#2C3E50", fg="#BDC3C7").pack(expand=True, pady=(0, 30))
        tk.Label(self.root, text="Now with Work/Study Satisfaction Measurement", font=("Arial", 10, "italic"), bg="#2C3E50", fg="#4CAF50").pack(expand=True, pady=(0, 30))
        
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
