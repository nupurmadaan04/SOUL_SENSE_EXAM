# app/ui/journal.py
import tkinter as tk
from typing import Optional, Any
from tkinter import ttk, messagebox, scrolledtext
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
import logging

# Conditional import for NLTK - sentiment analysis is optional
try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    logging.warning("NLTK not available - sentiment analysis will be disabled")
    nltk = None
    SentimentIntensityAnalyzer = None
    NLTK_AVAILABLE = False

from sqlalchemy import desc, text

from app.i18n_manager import get_i18n
from app.i18n_manager import get_i18n
from app.models import JournalEntry, User
from app.db import get_session, safe_db_context
from app.services.journal_service import JournalService
from app.validation import validate_required, validate_length, validate_range, sanitize_text, RANGES
from app.validation import MAX_TEXT_LENGTH

# Matplotlib imports for mood trend charts
try:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    Figure = None
    FigureCanvasTkAgg = None
    mdates = None

# Lazy imports to avoid circular dependencies
# These will be imported only when needed
AnalyticsDashboard = None
DailyHistoryView = None


class JournalFeature:
    def __init__(self, parent_root: tk.Widget, app: Optional[Any] = None) -> None:
        """
        Initialize Journal Feature
        
        Args:
            parent_root: The parent tkinter root window
            app: Optional SoulSenseApp instance. If None, feature works in standalone mode
        """
        self.parent_root = parent_root
        self.app = app  # Store app reference for theming (can be None)
        self.i18n = get_i18n()
        
        # Initialize theme colors (with defaults)
        # Initialize theme colors (standardized)
        self.colors = {
            "bg": "#f0f0f0",
            "surface": "white",
            "text_primary": "black",
            "text_secondary": "#666",
            "primary": "#8B5CF6",
            "secondary": "#EC4899"
        }
        
        # Use app colors if available
        if app and hasattr(app, 'colors'):
            self.colors = app.colors
        
        # Initialize VADER sentiment analyzer
        self._initialize_sentiment_analyzer()
        
    def _initialize_sentiment_analyzer(self) -> None:
        """Initialize the VADER sentiment analyzer"""
        if not NLTK_AVAILABLE:
            logging.warning("NLTK not available - sentiment analysis disabled")
            self.sia = None
            return
            
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            try:
                nltk.download('vader_lexicon', quiet=True)
            except Exception as download_error:
                logging.error(f"Failed to download VADER lexicon: {download_error}")
                self.sia = None
                return
            
        try:
            self.sia = SentimentIntensityAnalyzer()
        except Exception as e:
            logging.error(f"Failed to initialize sentiment analyzer: {e}")
            self.sia = None

    def render_journal_view(self, parent_frame: tk.Widget, username: str) -> None:
        """Render journal view inside a parent frame (Embedded Mode)"""
        self.username = username
        self.journal_window = parent_frame # Alias for compatibility
        
        # Determine colors
        colors = self.colors
        
        # Header Section
        header_frame = tk.Frame(parent_frame, bg=colors["bg"], pady=10)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text=self.i18n.get("journal.title"), 
                 font=("Segoe UI", 24, "bold"), bg=colors["bg"], 
                 fg=colors["text_primary"]).pack(anchor="w", padx=20)
                 
        today = datetime.now().strftime("%Y-%m-%d")
        tk.Label(header_frame, text=self.i18n.get("journal.date", date=today), 
                 font=("Segoe UI", 12), bg=colors["bg"], 
                 fg=colors["text_secondary"]).pack(anchor="w", padx=20)

        # Scrollable Content
        container = tk.Frame(parent_frame, bg=colors["bg"])
        container.pack(fill="both", expand=True, padx=20)
        
        # --- Metrics Section ---
        metrics_frame = tk.LabelFrame(container, text="Daily Assessment", 
                                     font=("Segoe UI", 12, "bold"), bg=colors["surface"],
                                     fg=colors["text_primary"], padx=15, pady=15)
        metrics_frame.pack(fill="x", pady=10)
        
        metrics_frame.columnconfigure(1, weight=1)
        metrics_frame.columnconfigure(3, weight=1)
        
        # Configure Theme for Sliders
        style = ttk.Style()
        style.configure("TScale", background=colors["surface"], troughcolor=colors.get("border", "#ccc"),
                        sliderthickness=15)

        def create_slider(parent, label_text, from_, to_, row, col, variable, resolution=1):
            lbl = tk.Label(parent, text=label_text, font=("Segoe UI", 11), 
                    bg=colors["surface"], fg=colors["text_primary"])
            lbl.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            
            val_lbl = tk.Label(parent, text=f"{variable.get():g}", width=4, font=("Segoe UI", 11, "bold"),
                              bg=colors["surface"], fg=colors["primary"])
            val_lbl.grid(row=row, column=col+2, padx=5)
            
            def on_scroll(val):
                v = float(val)
                v = int(v) if resolution==1 else round(v, 1)
                variable.set(v)
                val_lbl.config(text=f"{v:g}")

            # Use "TScale" style implicitly or explicitly if needed, but configure sets global default for TScale
            s = ttk.Scale(parent, from_=from_, to=to_, orient="horizontal", variable=variable, command=on_scroll)
            s.grid(row=row, column=col+1, sticky="ew", padx=5)

        # Row 0
        self.sleep_hours_var = tk.DoubleVar(value=7.0)
        create_slider(metrics_frame, "Sleep (hrs)", 0, 16, 0, 0, self.sleep_hours_var, 0.5)

        self.sleep_quality_var = tk.IntVar(value=7)
        create_slider(metrics_frame, "Sleep Quality (1-10)", 1, 10, 0, 3, self.sleep_quality_var, 1)
        
        # Row 1
        self.energy_level_var = tk.IntVar(value=7)
        create_slider(metrics_frame, "Energy (1-10)", 1, 10, 1, 0, self.energy_level_var, 1)
        
        self.work_hours_var = tk.DoubleVar(value=8.0)
        create_slider(metrics_frame, "Work (hrs)", 0, 16, 1, 3, self.work_hours_var, 0.5)

        # Row 2 (PR #6 Expansion)
        self.stress_level_var = tk.IntVar(value=3)
        create_slider(metrics_frame, "Stress (1-10)", 1, 10, 2, 0, self.stress_level_var, 1)

        # Screen Time (Slider)
        self.screen_time_var = tk.IntVar(value=120)
        create_slider(metrics_frame, "Screen Time (mins)", 0, 720, 2, 3, self.screen_time_var, 15)

        # --- Daily Context Section (PR #6) ---
        context_frame = tk.LabelFrame(container, text="Daily Context", 
                                     font=("Segoe UI", 12, "bold"), bg=colors["surface"],
                                     fg=colors["text_primary"], padx=15, pady=10)
        context_frame.pack(fill="x", pady=5)
        
        def create_compact_text(parent, label, ht=3):
            frame = tk.Frame(parent, bg=colors["surface"])
            frame.pack(fill="x", pady=5)
            tk.Label(frame, text=label, font=("Segoe UI", 10, "bold"), 
                    bg=colors["surface"], fg=colors["text_secondary"]).pack(anchor="w")
            txt = tk.Text(frame, height=ht, font=("Segoe UI", 10),
                         bg=colors.get("input_bg", "#fff"), fg=colors.get("input_fg", "#000"),
                         relief="flat", highlightthickness=1,
                         highlightbackground=colors.get("border", "#ccc"))
            txt.pack(fill="x")
            return txt

        self.schedule_text = create_compact_text(context_frame, "Daily Schedule / Key Events")
        self.triggers_text = create_compact_text(context_frame, "Stress Triggers (if any)")

        # --- Reflection Section ---
        tk.Label(container, text="Your thoughts today...",
                font=("Segoe UI", 12, "bold"), bg=colors["bg"],
                fg=colors["text_primary"]).pack(anchor="w", pady=(15, 5))

        # Tags input field
        tags_frame = tk.Frame(container, bg=colors["bg"])
        tags_frame.pack(fill="x", pady=(0, 10))
        tk.Label(tags_frame, text="Tags (comma-separated, e.g., stress, gratitude, relationships):",
                font=("Segoe UI", 10), bg=colors["bg"],
                fg=colors["text_secondary"]).pack(anchor="w")
        self.tags_entry = tk.Entry(tags_frame, font=("Segoe UI", 10),
                                  bg=colors.get("input_bg", "#fff"), fg=colors.get("input_fg", "#000"),
                                  relief="flat", highlightthickness=1,
                                  highlightbackground=colors.get("border", "#ccc"))
        self.tags_entry.pack(fill="x")

        self.text_area = scrolledtext.ScrolledText(container, width=60, height=8,
                                                  font=("Segoe UI", 11),
                                                  bg=colors["surface"], fg=colors["text_primary"],
                                                  relief="flat", highlightthickness=1,
                                                  highlightbackground=colors.get("border", "#ccc"))
        self.text_area.pack(fill="x", expand=True)
        
        # Buttons
        btn_frame = tk.Frame(container, bg=colors["bg"])
        btn_frame.pack(fill="x", pady=20)

        # Navigation Buttons
        tk.Button(btn_frame, text=self.i18n.get("journal.view_past"), command=self.view_past_entries,
                 font=("Segoe UI", 11), bg=colors["surface"], fg=colors["text_primary"],
                 relief="flat", padx=15).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="📊 Mood Trends", command=self.show_mood_trends,
                 font=("Segoe UI", 11), bg=colors["surface"], fg=colors["text_primary"],
                 relief="flat", padx=15).pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text=self.i18n.get("journal.dashboard"), command=self.open_dashboard,
                 font=("Segoe UI", 11), bg=colors["surface"], fg=colors["text_primary"],
                 relief="flat", padx=15).pack(side="left", padx=(0, 10))

        # Toggle Search Section
        self.search_visible = False
        self.search_toggle_btn = tk.Button(btn_frame, text="🔍 Search Past Entries", command=self.toggle_search_section,
                                          font=("Segoe UI", 11), bg=colors["accent"], fg="white",
                                          relief="flat", padx=15)
        self.search_toggle_btn.pack(side="left", padx=(0, 10))

        tk.Button(btn_frame, text="Save Entry", command=self.save_and_analyze,
                 font=("Segoe UI", 11, "bold"), bg=colors["primary"], fg=colors.get("text_inverse", "white"),
                 padx=20, pady=8, relief="flat").pack(side="right")

        if hasattr(self.app, 'switch_view'):
             tk.Button(btn_frame, text="Cancel", command=lambda: self.app.switch_view('home'),
                     font=("Segoe UI", 11), bg=colors["bg"], fg=colors["text_secondary"],
                     relief="flat").pack(side="right", padx=10)

        # Collapsible Search Section
        self.search_frame = tk.LabelFrame(container, text="Search Past Entries", font=("Segoe UI", 12, "bold"),
                                         bg=colors["surface"], fg=colors["text_primary"], padx=15, pady=15)
        # Initially hidden
        self.search_frame.pack_forget()

        # Search Filters
        search_filters_frame = tk.Frame(self.search_frame, bg=colors["surface"])
        search_filters_frame.pack(fill="x", pady=(0, 10))

        # Tags filter
        tags_container = tk.Frame(search_filters_frame, bg=colors["surface"])
        tags_container.pack(side="left", padx=(0, 15))

        tk.Label(tags_container, text="🏷️ Tags:", font=("Segoe UI", 10, "bold"),
                bg=colors["surface"], fg=colors["text_secondary"]).pack(side="left")

        self.inline_tags_var = tk.StringVar()
        self.inline_tags_entry = tk.Entry(tags_container, textvariable=self.inline_tags_var, font=("Segoe UI", 10),
                                         bg=colors.get("input_bg", "#fff"), fg=colors.get("input_fg", "#000"),
                                         relief="flat", highlightthickness=1,
                                         highlightbackground=colors.get("border", "#ccc"), width=20)
        self.inline_tags_entry.pack(side="left", padx=5)
        self.inline_tags_entry.insert(0, "e.g., stress, gratitude")

        # Date range filter
        date_container = tk.Frame(search_filters_frame, bg=colors["surface"])
        date_container.pack(side="left", padx=10)

        tk.Label(date_container, text="📅 From:", font=("Segoe UI", 10, "bold"),
                bg=colors["surface"], fg=colors.get("text_secondary", "#666")).pack(side="left")

        self.inline_from_date_var = tk.StringVar()
        self.inline_from_date_entry = tk.Entry(date_container, textvariable=self.inline_from_date_var, font=("Segoe UI", 10),
                                              bg=colors.get("input_bg", "#fff"), fg=colors.get("input_fg", "#000"),
                                              relief="flat", highlightthickness=1,
                                              highlightbackground=colors.get("border", "#ccc"), width=12)
        self.inline_from_date_entry.pack(side="left", padx=5)
        self.inline_from_date_entry.insert(0, "YYYY-MM-DD")

        tk.Label(date_container, text="To:", font=("Segoe UI", 10, "bold"),
                bg=colors["surface"], fg=colors.get("text_secondary", "#666")).pack(side="left", padx=(10, 5))

        self.inline_to_date_var = tk.StringVar()
        self.inline_to_date_entry = tk.Entry(date_container, textvariable=self.inline_to_date_var, font=("Segoe UI", 10),
                                            bg=colors.get("input_bg", "#fff"), fg=colors.get("input_fg", "#000"),
                                            relief="flat", highlightthickness=1,
                                            highlightbackground=colors.get("border", "#ccc"), width=12)
        self.inline_to_date_entry.pack(side="left", padx=5)
        self.inline_to_date_entry.insert(0, "YYYY-MM-DD")

        # Mood filter
        mood_container = tk.Frame(search_filters_frame, bg=colors["surface"])
        mood_container.pack(side="left", padx=10)

        tk.Label(mood_container, text="😊 Mood:", font=("Segoe UI", 10, "bold"),
                bg=colors["surface"], fg=colors.get("text_secondary", "#666")).pack(side="left")

        self.inline_mood_var = tk.StringVar(value="All Moods")
        self.inline_mood_combo = ttk.Combobox(mood_container, textvariable=self.inline_mood_var,
                                             values=["All Moods", "Positive", "Neutral", "Negative"],
                                             state="readonly", width=12)
        self.inline_mood_combo.pack(side="left", padx=5)

        # Clear button
        tk.Button(search_filters_frame, text="Reset Filters", command=self.clear_inline_filters,
                 font=("Segoe UI", 9), bg=colors.get("primary", "#8B5CF6"), fg="white",
                 relief="flat", padx=12, pady=4).pack(side="right", padx=10)

        # Scrolled Frame for Results
        self.results_canvas = tk.Canvas(self.search_frame, bg=colors["surface"], highlightthickness=0)
        self.results_scrollable_frame = tk.Frame(self.results_canvas, bg=colors["surface"])

        self.results_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )

        self.results_canvas.create_window((0, 0), window=self.results_scrollable_frame, anchor="nw")
        self.results_canvas.pack(fill="both", expand=True, padx=0, pady=(10, 0))

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            try:
                self.results_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass

        self.results_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.results_canvas.bind("<Enter>", lambda e: self.results_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.results_canvas.bind("<Leave>", lambda e: self.results_canvas.unbind_all("<MouseWheel>"))

        # Bind filter changes to update results
        self.inline_tags_entry.bind("<KeyRelease>", lambda e: self.update_inline_results())
        self.inline_from_date_entry.bind("<KeyRelease>", lambda e: self.update_inline_results())
        self.inline_to_date_entry.bind("<KeyRelease>", lambda e: self.update_inline_results())
        self.inline_mood_combo.bind("<<ComboboxSelected>>", lambda e: self.update_inline_results())

        # Initial render (empty)
        self.update_inline_results()

    def toggle_search_section(self):
        """Toggle the visibility of the search section"""
        if self.search_visible:
            self.search_frame.pack_forget()
            self.search_toggle_btn.config(text="🔍 Search Past Entries")
            self.search_visible = False
        else:
            self.search_frame.pack(fill="x", pady=10)
            self.search_toggle_btn.config(text="🔍 Hide Search")
            self.search_visible = True

    def clear_inline_filters(self):
        """Clear all inline search filters"""
        self.inline_tags_var.set("")
        self.inline_from_date_var.set("")
        self.inline_to_date_var.set("")
        self.inline_mood_var.set("All Moods")
        self.update_inline_results()

    def update_inline_results(self):
        """Update the inline search results based on current filters"""
        # Clear existing results
        for widget in self.results_scrollable_frame.winfo_children():
            widget.destroy()

        # Get filter values
        selected_tags = self.inline_tags_var.get().strip().lower()
        from_date = self.inline_from_date_var.get().strip()
        to_date = self.inline_to_date_var.get().strip()
        selected_mood = self.inline_mood_var.get()

        with safe_db_context() as session:
            entries = session.query(JournalEntry)\
                .filter_by(username=self.username)\
                .order_by(desc(JournalEntry.entry_date))\
                .all()

            filtered_count = 0
            for entry in entries:
                # Apply tags filter
                if selected_tags and selected_tags != "e.g., stress, gratitude":
                    entry_tags = (getattr(entry, 'tags', '') or '').lower()
                    tag_list = [tag.strip() for tag in selected_tags.split(',') if tag.strip()]
                    if not any(tag in entry_tags for tag in tag_list):
                        continue

                # Apply date range filter
                if from_date and from_date != "YYYY-MM-DD":
                    try:
                        entry_date = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S").date()
                        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                        if entry_date < from_date_obj:
                            continue
                    except (ValueError, AttributeError):
                        pass

                if to_date and to_date != "YYYY-MM-DD":
                    try:
                        entry_date = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S").date()
                        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
                        if entry_date > to_date_obj:
                            continue
                    except (ValueError, AttributeError):
                        pass

                # Apply mood filter
                if selected_mood != "All Moods":
                    sentiment_score = getattr(entry, 'sentiment_score', 0) or 0
                    if selected_mood == "Positive" and sentiment_score <= 30:
                        continue
                    elif selected_mood == "Neutral" and (sentiment_score > 30 or sentiment_score < -30):
                        continue
                    elif selected_mood == "Negative" and sentiment_score >= -30:
                        continue

                filtered_count += 1
                self._create_entry_card(self.results_scrollable_frame, entry)

            if filtered_count == 0:
                tk.Label(self.results_scrollable_frame, text="No entries found matching filters.",
                        font=("Segoe UI", 12), bg=self.colors.get("surface", "#fff"),
                        fg=self.colors.get("text_secondary", "#666")).pack(pady=20)

    def open_journal_window(self, username):
        """Standalone Window Mode (Deprecated but kept for compat)"""
        self.username = username
        self.journal_window = tk.Toplevel(self.parent_root)
        self.journal_window.title(self.i18n.get("journal.title"))
        self.journal_window.geometry("800x600")
        self.journal_window.configure(bg=self.colors.get("bg"))
        self.render_journal_view(self.journal_window, username)
    
    def analyze_sentiment(self, text):
        """Analyze sentiment using NLTK VADER or fallback keyword matching"""
        if not text.strip():
            return 0.0
            
        if self.sia and NLTK_AVAILABLE:
            try:
                scores = self.sia.polarity_scores(text)
                # Convert compound (-1 to 1) to -100 to 100
                return scores['compound'] * 100
            except Exception as e:
                logging.error(f"VADER sentiment analysis error: {e}")
                # Fall through to keyword matching
        else:
            logging.debug("Using keyword-based sentiment analysis (NLTK not available)")
        
        # Fallback to simple keyword matching when VADER is unavailable
        positive_words = ['happy', 'joy', 'excited', 'grateful', 'peaceful', 'confident', 'good', 'great', 'excellent']
        negative_words = ['sad', 'angry', 'frustrated', 'anxious', 'worried', 'stressed', 'bad', 'terrible', 'awful']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        if total_words == 0: 
            return 0.0
        
        # Calculate sentiment as percentage of emotional words
        score = (positive_count - negative_count) / max(total_words * 0.1, 1) * 100
        return max(-100, min(100, score))
    
    def extract_emotional_patterns(self, text):
        """Extract emotional patterns from text"""
        patterns = []
        text_lower = text.lower()
        
        # Stress indicators
        stress_words = ['stress', 'pressure', 'overwhelm', 'burden', 'exhausted']
        if any(word in text_lower for word in stress_words):
            patterns.append(self.i18n.get("patterns.stress_indicators"))
        
        # Relationship mentions
        relationship_words = ['friend', 'family', 'colleague', 'partner', 'relationship']
        if any(word in text_lower for word in relationship_words):
            patterns.append(self.i18n.get("patterns.social_focus"))
        
        # Growth mindset
        growth_words = ['learn', 'grow', 'improve', 'better', 'progress', 'develop']
        if any(word in text_lower for word in growth_words):
            patterns.append(self.i18n.get("patterns.growth_oriented"))
        
        # Self-reflection
        reflection_words = ['realize', 'understand', 'reflect', 'think', 'feel', 'notice']
        if any(word in text_lower for word in reflection_words):
            patterns.append(self.i18n.get("patterns.self_reflective"))
        
        return "; ".join(patterns) if patterns else self.i18n.get("patterns.general_expression")

    def _app_mood_from_score(self, score: float) -> str:
        """Convert sentiment score to mood string"""
        if score >= 20:
            return "Positive"
        elif score <= -20:
            return "Negative"
        else:
            return "Neutral"
    
    def save_and_analyze(self):
        """Save journal entry and perform AI analysis"""
        from app.ui.components.loading_overlay import show_loading, hide_loading
        
        content = sanitize_text(self.text_area.get("1.0", tk.END))
        
        # Validation checks
        valid_req, msg_req = validate_required(content, "Journal content")
        if not valid_req:
            messagebox.showwarning(self.i18n.get("journal.empty_entry"), msg_req)
            return
        
        valid_len, msg_len = validate_length(content, MAX_TEXT_LENGTH, "Content", min_len=10)
        if not valid_len:
            messagebox.showwarning("Validation Error", msg_len)
            return

        # Numeric Range Validation (Defensive programming)
        # Even though sliders enforce it, external calls or future UI changes might not
        ranges_check = [
            (self.sleep_hours_var.get(), *RANGES['sleep'], "Sleep Hours"),
            (self.sleep_quality_var.get(), *RANGES['stress'], "Sleep Quality"), # reusing 1-10 range
            (self.energy_level_var.get(), *RANGES['energy'], "Energy Level"),
            # (self.work_hours_var.get(), *RANGES['work'], "Work Hours"), # Use default logic: work range 0-24
            (self.stress_level_var.get(), *RANGES['stress'], "Stress Level"),
        ]
        
        for val, min_v, max_v, lbl in ranges_check:
             if not validate_range(val, min_v, max_v, lbl)[0]:
                 # Log valid ranges error but maybe don't block user if sliders are just buggy? 
                 # Better to block to prevent DB corruption
                 messagebox.showwarning("Validation Error", f"Invalid value for {lbl}")
                 return
        
        # Guard
        if hasattr(self, 'is_processing') and self.is_processing:
            return

        # Start Processing
        self.is_processing = True
        
        if hasattr(self, 'save_btn'):
            self.save_btn.configure(state="disabled")
            
        overlay = None
        try:
            overlay = show_loading(self.parent_root, "Analyzing Emotions...")
        except Exception as e:
            # If creating overlay fails (e.g. parent destroyed), minimal fallback
            logging.error(f"Could not create loading overlay: {e}")
            # continue processing anyway

        try:
            current_time = datetime.now()
            
            # 1. Perform Analysis (Heavy)
            sentiment_score = 0.0
            try:
                sentiment_score = self.analyze_sentiment(content)
                emotional_patterns = self.extract_emotional_patterns(content)
            except Exception as e:
                logging.error(f"Analysis failed: {e}")
                    # Continue saving even if analysis fails slightly
            
            # 2. Database Save
            # 2. Database Save (via Service)
            try:
                # Collect metrics from sliders
                metrics = {
                    "sleep_hours": self.sleep_hours_var.get(),
                    "sleep_quality": self.sleep_quality_var.get(),
                    "energy_level": self.energy_level_var.get(),
                    "stress_level": self.stress_level_var.get(),
                    "work_hours": self.work_hours_var.get(),
                    "screen_time_mins": self.screen_time_var.get()
                }
                
                JournalService.create_entry(
                    username=self.username if hasattr(self, 'username') else (self.app.username if self.app and hasattr(self.app, 'username') else 'guest'),
                    content=content,
                    sentiment_score=sentiment_score,
                    emotional_patterns=emotional_patterns,
                    entry_date=current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    **metrics
                )
            except Exception as e:
                logging.error(f"Service save failed: {e}")
                raise e # Re-raise to trigger outer error handler
            
            # 3. Dynamic Health Insights
            health_insights = self.generate_health_insights()
            
            # 4. Show Result (Popup)
            # Hide overlay BEFORE showing result, otherwise popup might be behind overlay
            hide_loading(overlay)
            overlay = None # invalid ref
            
            self.show_analysis_results(sentiment_score, emotional_patterns, health_insights)
            
            # 5. Clear Input
            self.text_area.delete("1.0", tk.END)
            # Reset word count
            if hasattr(self, 'word_count_label'):
                self.word_count_label.config(text="0 words")
                
                # self.load_entries() # Method does not exist, and view_past_entries is a separate window
            
        except Exception as e:
            logging.error("Failed to save journal entry", exc_info=True)
            messagebox.showerror("Error", f"Failed to save entry: {e}")
            
        finally:
            # Cleanup
            if overlay:
                hide_loading(overlay)
            
            self.is_processing = False
            if hasattr(self, 'save_btn') and self.save_btn.winfo_exists():
                self.save_btn.configure(state="normal")
    
    def show_analysis_results(self, sentiment_score, patterns, nudge_advice=None):
        """Display AI analysis results"""
        # Use stored colors
        bg_color = self.colors.get("bg", "#f5f5f5")
        card_bg = self.colors.get("surface", "white")
        text_color = self.colors.get("text_primary", "black")
        subtext_color = self.colors.get("text_secondary", "#666")
        nudge_bg = "#FFF3E0"
        nudge_text_color = "#333"
        nudge_title_color = "#EF6C00"
        
        # Adjust for dark mode if theme is known
        if self.app and hasattr(self.app, 'current_theme') and self.app.current_theme == 'dark':
            nudge_bg = self.colors.get("bg_tertiary", "#334155")
            nudge_text_color = self.colors.get("text_primary", "#F8FAFC")
            nudge_title_color = "#FFA726"
        
        result_window = tk.Toplevel(self.journal_window)
        result_window.title(self.i18n.get("journal.analysis_title"))
        result_window.geometry("450x450")
        result_window.configure(bg=bg_color)
        
        main_frame = tk.Frame(result_window, bg=bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        tk.Label(main_frame, text=self.i18n.get("journal.emotional_analysis"), 
                font=("Arial", 16, "bold"), bg=bg_color, fg=text_color).pack(pady=(0, 15))
        
        # Sentiment Card
        card_frame = tk.Frame(main_frame, bg=card_bg, relief=tk.RIDGE, bd=1)
        card_frame.pack(fill=tk.X, pady=5)
        
        # Sentiment interpretation
        if sentiment_score > 20:
            sentiment_text = self.i18n.get("journal.positive_tone")
            color = "#4CAF50"
            emoji = "😊"
        elif sentiment_score < -20:
            sentiment_text = self.i18n.get("journal.negative_tone")
            color = "#F44336"
            emoji = "😔"
        else:
            sentiment_text = self.i18n.get("journal.neutral_tone")
            color = "#2196F3"
            emoji = "😐"
        
        tk.Label(card_frame, text=f"{emoji} Sentiment Score: {sentiment_score:.1f}", 
                font=("Arial", 14, "bold"), fg=color, bg=card_bg).pack(pady=(15, 5))
        tk.Label(card_frame, text=sentiment_text, 
                font=("Arial", 11), fg=subtext_color, bg=card_bg).pack(pady=(0, 15))
        
        # Patterns Section
        tk.Label(main_frame, text=self.i18n.get("journal.emotional_patterns"), 
                font=("Arial", 12, "bold"), bg=bg_color, fg=text_color).pack(pady=(15, 5))
        
        lbl_patterns = tk.Label(main_frame, text=patterns, 
                font=("Arial", 11), wraplength=380, bg=bg_color, fg=text_color)
        lbl_patterns.pack(pady=5)
        
        # --- Nudge Section ---
        if nudge_advice:
            nudge_frame = tk.Frame(main_frame, bg=nudge_bg, relief=tk.FLAT, bd=0)
            nudge_frame.pack(fill=tk.X, pady=15, ipadx=10, ipady=10)
            
            tk.Label(nudge_frame, text="💡 AI Health Assistant", 
                    font=("Arial", 11, "bold"), bg=nudge_bg, fg=nudge_title_color).pack(anchor="w")
            
            tk.Label(nudge_frame, text=nudge_advice, 
                    font=("Arial", 10), bg=nudge_bg, fg=nudge_text_color, 
                    justify="left", wraplength=360).pack(anchor="w", pady=(5,0))
        
        tk.Button(main_frame, text=self.i18n.get("journal.close"), 
                 command=result_window.destroy, 
                 font=("Arial", 11), bg="#ddd", relief=tk.FLAT, padx=15).pack(pady=20)
    
    def view_past_entries(self):
        """View past journal entries"""
        entries_window = tk.Toplevel(self.journal_window)
        entries_window.title(self.i18n.get("journal.past_entries_title"))
        entries_window.geometry("700x500")
        entries_window.configure(bg=self.colors.get("bg", "#f0f0f0"))

        tk.Label(entries_window, text=self.i18n.get("journal.emotional_journey"),
                font=("Arial", 16, "bold"), bg=self.colors.get("bg", "#f0f0f0"),
                fg=self.colors.get("text_primary", "#000")).pack(pady=10)

        def open_history_view():
            """Open daily history view with lazy import"""
            try:
                # Lazy import to avoid circular dependency
                from app.ui.daily_view import DailyHistoryView
                top = tk.Toplevel(self.parent_root)
                DailyHistoryView(top, self.app, self.username)
                entries_window.destroy()
            except ImportError as e:
                logging.error(f"Failed to import DailyHistoryView: {e}")
                messagebox.showerror("Error", "Calendar view feature not available")

        tk.Button(entries_window, text="📅 Calendar View", command=open_history_view,
                 bg=self.colors.get("secondary", "#8B5CF6"), fg="white",
                 relief="flat", padx=10).pack(pady=5)

        # --- Enhanced Filter Bar (Tags, Date Range, Mood, Month + Type filters) ---
        filter_frame = tk.Frame(entries_window, bg=self.colors.get("surface", "#fff"), pady=12)
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        # Row 1: Tags and Date Range
        row1_frame = tk.Frame(filter_frame, bg=self.colors.get("surface", "#fff"))
        row1_frame.pack(fill="x", pady=(0, 8))

        # Tags filter
        tags_container = tk.Frame(row1_frame, bg=self.colors.get("surface", "#fff"))
        tags_container.pack(side="left", padx=(10, 15))

        tk.Label(tags_container, text="🏷️ Tags:", font=("Segoe UI", 10, "bold"),
                bg=self.colors.get("surface", "#fff"),
                fg=self.colors.get("text_secondary", "#666")).pack(side="left")

        tags_var = tk.StringVar()
        tags_entry = tk.Entry(tags_container, textvariable=tags_var, font=("Segoe UI", 10),
                             bg=self.colors.get("input_bg", "#fff"), fg=self.colors.get("input_fg", "#000"),
                             relief="flat", highlightthickness=1,
                             highlightbackground=self.colors.get("border", "#ccc"), width=20)
        tags_entry.pack(side="left", padx=5)
        tags_entry.insert(0, "e.g., stress, gratitude")

        # Date range filter
        date_container = tk.Frame(row1_frame, bg=self.colors.get("surface", "#fff"))
        date_container.pack(side="left", padx=10)

        tk.Label(date_container, text="📅 From:", font=("Segoe UI", 10, "bold"),
                bg=self.colors.get("surface", "#fff"),
                fg=self.colors.get("text_secondary", "#666")).pack(side="left")

        from_date_var = tk.StringVar()
        from_date_entry = tk.Entry(date_container, textvariable=from_date_var, font=("Segoe UI", 10),
                                  bg=self.colors.get("input_bg", "#fff"), fg=self.colors.get("input_fg", "#000"),
                                  relief="flat", highlightthickness=1,
                                  highlightbackground=self.colors.get("border", "#ccc"), width=12)
        from_date_entry.pack(side="left", padx=5)
        from_date_entry.insert(0, "YYYY-MM-DD")

        tk.Label(date_container, text="To:", font=("Segoe UI", 10, "bold"),
                bg=self.colors.get("surface", "#fff"),
                fg=self.colors.get("text_secondary", "#666")).pack(side="left", padx=(10, 5))

        to_date_var = tk.StringVar()
        to_date_entry = tk.Entry(date_container, textvariable=to_date_var, font=("Segoe UI", 10),
                                bg=self.colors.get("input_bg", "#fff"), fg=self.colors.get("input_fg", "#000"),
                                relief="flat", highlightthickness=1,
                                highlightbackground=self.colors.get("border", "#ccc"), width=12)
        to_date_entry.pack(side="left", padx=5)
        to_date_entry.insert(0, "YYYY-MM-DD")

        # Row 2: Mood, Month, and Type filters
        row2_frame = tk.Frame(filter_frame, bg=self.colors.get("surface", "#fff"))
        row2_frame.pack(fill="x")

        # Mood filter
        mood_container = tk.Frame(row2_frame, bg=self.colors.get("surface", "#fff"))
        mood_container.pack(side="left", padx=(10, 15))

        tk.Label(mood_container, text="😊 Mood:", font=("Segoe UI", 10, "bold"),
                bg=self.colors.get("surface", "#fff"),
                fg=self.colors.get("text_secondary", "#666")).pack(side="left")

        mood_var = tk.StringVar(value="All Moods")
        mood_combo = ttk.Combobox(mood_container, textvariable=mood_var,
                                 values=["All Moods", "Positive", "Neutral", "Negative"],
                                 state="readonly", width=12)
        mood_combo.pack(side="left", padx=5)

        # Month filter
        month_container = tk.Frame(row2_frame, bg=self.colors.get("surface", "#fff"))
        month_container.pack(side="left", padx=10)

        tk.Label(month_container, text="📅 Month:", font=("Segoe UI", 10, "bold"),
                bg=self.colors.get("surface", "#fff"),
                fg=self.colors.get("text_secondary", "#666")).pack(side="left")

        # Generate month options
        from datetime import datetime
        current_month = datetime.now()
        month_options = ["All Months"]
        for i in range(12):
            month_date = datetime(current_month.year if current_month.month - i > 0 else current_month.year - 1,
                                 ((current_month.month - i - 1) % 12) + 1, 1)
            month_options.append(month_date.strftime("%B %Y"))

        month_var = tk.StringVar(value="All Months")
        month_combo = ttk.Combobox(month_container, textvariable=month_var,
                                  values=month_options, state="readonly", width=15)
        month_combo.pack(side="left", padx=5)

        # Type filter
        filter_container = tk.Frame(row2_frame, bg=self.colors.get("surface", "#fff"))
        filter_container.pack(side="left", padx=10)

        tk.Label(filter_container, text="Type:", font=("Segoe UI", 10, "bold"),
                bg=self.colors.get("surface", "#fff"),
                fg=self.colors.get("text_secondary", "#666")).pack(side="left")

        type_var = tk.StringVar(value="All Entries")
        type_combo = ttk.Combobox(filter_container, textvariable=type_var,
                                 values=["All Entries", "High Stress", "Great Days", "Bad Sleep"],
                                 state="readonly", width=15)
        type_combo.pack(side="left", padx=5)

        # Clear button
        def clear_filters():
            tags_var.set("")
            from_date_var.set("")
            to_date_var.set("")
            mood_var.set("All Moods")
            month_var.set("All Months")
            type_var.set("All Entries")
            render_entries()

        tk.Button(row2_frame, text="Reset", command=clear_filters,
                 font=("Segoe UI", 9), bg=self.colors.get("primary", "#8B5CF6"), fg="white",
                 relief="flat", padx=12, pady=4).pack(side="right", padx=10)

        # Scrollable Area (Hidden scrollbar - mousewheel only)
        canvas = tk.Canvas(entries_window, bg=self.colors.get("bg", "#f0f0f0"), highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=self.colors.get("bg", "#f0f0f0"))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.pack(fill="both", expand=True, padx=20)

        # Enable mousewheel scrolling (scoped to this canvas only)
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass  # Canvas may be destroyed

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        def render_entries():
            # Clear existing
            for widget in scrollable_frame.winfo_children():
                widget.destroy()

            # Get filter values
            selected_tags = tags_var.get().strip().lower()
            from_date = from_date_var.get().strip()
            to_date = to_date_var.get().strip()
            selected_mood = mood_var.get()
            selected_month = month_var.get()
            filter_type = type_var.get()
            
            # Using safe_db_context for read operations too
            # Using JournalService for read operations
            try:
                entries = JournalService.get_entries(self.username)
                print(f"DEBUG: View Past Entries found {len(entries)} records for {self.username}")

                filtered_count = 0
                for entry in entries:
                    # Apply tags filter
                    if selected_tags and selected_tags != "e.g., stress, gratitude":
                        entry_tags = (getattr(entry, 'tags', '') or '').lower()
                        tag_list = [tag.strip() for tag in selected_tags.split(',') if tag.strip()]
                        if not any(tag in entry_tags for tag in tag_list):
                            continue

                    # Apply date range filter
                    if from_date and from_date != "YYYY-MM-DD":
                        try:
                            entry_date = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S").date()
                            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                            if entry_date < from_date_obj:
                                continue
                        except (ValueError, AttributeError):
                            pass

                    if to_date and to_date != "YYYY-MM-DD":
                        try:
                            entry_date = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S").date()
                            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
                            if entry_date > to_date_obj:
                                continue
                        except (ValueError, AttributeError):
                            pass

                    # Apply mood filter
                    if selected_mood != "All Moods":
                        sentiment_score = getattr(entry, 'sentiment_score', 0) or 0
                        if selected_mood == "Positive" and sentiment_score <= 30:
                            continue
                        elif selected_mood == "Neutral" and (sentiment_score > 30 or sentiment_score < -30):
                            continue
                        elif selected_mood == "Negative" and sentiment_score >= -30:
                            continue

                    # Apply month filter
                    if selected_month != "All Months":
                        try:
                            entry_month = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
                            if entry_month != selected_month:
                                continue
                        except:
                            pass

                    # Apply type filter
                    if filter_type == "High Stress" and (entry.stress_level or 0) <= 7:
                        continue
                    if filter_type == "Great Days" and (entry.energy_level or 0) <= 7:
                        continue
                    if filter_type == "Bad Sleep" and (entry.sleep_hours or 7) >= 6:
                        continue

                    filtered_count += 1
                    self._create_entry_card(scrollable_frame, entry)
                    if filtered_count == 0:
                        tk.Label(scrollable_frame, text="No entries found matching filters.", 
                                font=("Segoe UI", 12), bg=self.colors.get("bg", "#f0f0f0"), 
                                fg=self.colors.get("text_secondary", "#666")).pack(pady=20)
            except Exception as e:
                logging.error(f"Failed to render entries: {e}")
                tk.Label(scrollable_frame, text="Could not load entries.", 
                        font=("Segoe UI", 12), bg=self.colors.get("bg", "#f0f0f0"), 
                        fg="red").pack(pady=20)

        # Update on filter change
        month_combo.bind("<<ComboboxSelected>>", lambda e: render_entries())
        type_combo.bind("<<ComboboxSelected>>", lambda e: render_entries())
        mood_combo.bind("<<ComboboxSelected>>", lambda e: render_entries())
        tags_entry.bind("<KeyRelease>", lambda e: render_entries())
        from_date_entry.bind("<KeyRelease>", lambda e: render_entries())
        to_date_entry.bind("<KeyRelease>", lambda e: render_entries())

        # Initial Render
        render_entries()

        # Configure canvas width
        def _configure_canvas(event):
            canvas.itemconfig(canvas.create_window((0,0), window=scrollable_frame, anchor="nw"), width=event.width)
        canvas.bind("<Configure>", _configure_canvas)

    def show_mood_trends(self):
        """Display visual mood trend charts using Matplotlib"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Error", "Matplotlib is not installed. Please install it to view mood trend charts.")
            return

        # Create chart window
        chart_window = tk.Toplevel(self.journal_window)
        chart_window.title("Mood Trends Over Time")
        chart_window.geometry("800x600")
        chart_window.configure(bg=self.colors.get("bg", "#f0f0f0"))

        # Header
        tk.Label(chart_window, text="📊 Your Emotional Journey",
                font=("Segoe UI", 16, "bold"), bg=self.colors.get("bg", "#f0f0f0"),
                fg=self.colors.get("text_primary", "#000")).pack(pady=10)

        # Get data
        with safe_db_context() as session:
            entries = session.query(JournalEntry)\
                .filter_by(username=self.username)\
                .order_by(JournalEntry.entry_date)\
                .all()

            if not entries:
                tk.Label(chart_window, text="No journal entries found to analyze trends.",
                        font=("Segoe UI", 12), bg=self.colors.get("bg", "#f0f0f0"),
                        fg=self.colors.get("text_secondary", "#666")).pack(pady=20)
                return

            # Extract data
            dates = []
            sentiments = []
            stress_levels = []
            energy_levels = []
            sleep_hours = []

            for entry in entries:
                try:
                    date_obj = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S")
                    dates.append(date_obj)
                    sentiments.append(getattr(entry, 'sentiment_score', 0) or 0)
                    stress_levels.append(getattr(entry, 'stress_level', 5) or 5)
                    energy_levels.append(getattr(entry, 'energy_level', 5) or 5)
                    sleep_hours.append(getattr(entry, 'sleep_hours', 7) or 7)
                except:
                    continue

            if not dates:
                tk.Label(chart_window, text="Unable to process entry dates for trend analysis.",
                        font=("Segoe UI", 12), bg=self.colors.get("bg", "#f0f0f0"),
                        fg=self.colors.get("text_secondary", "#666")).pack(pady=20)
                return

            # Create figure with subplots
            fig = Figure(figsize=(10, 8), dpi=100, facecolor=self.colors.get("surface", "#fff"))
            fig.suptitle("Mood & Wellness Trends", fontsize=14, fontweight='bold')

            # Sentiment over time
            ax1 = fig.add_subplot(221)
            ax1.plot(dates, sentiments, 'b-', linewidth=2, marker='o', markersize=4)
            ax1.set_title("Sentiment Score Over Time", fontsize=12)
            ax1.set_ylabel("Sentiment (-100 to +100)")
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

            # Stress levels
            ax2 = fig.add_subplot(222)
            ax2.plot(dates, stress_levels, 'r-', linewidth=2, marker='s', markersize=4)
            ax2.set_title("Stress Levels Over Time", fontsize=12)
            ax2.set_ylabel("Stress Level (1-10)")
            ax2.set_ylim(0, 11)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

            # Energy levels
            ax3 = fig.add_subplot(223)
            ax3.plot(dates, energy_levels, 'g-', linewidth=2, marker='^', markersize=4)
            ax3.set_title("Energy Levels Over Time", fontsize=12)
            ax3.set_ylabel("Energy Level (1-10)")
            ax3.set_ylim(0, 11)
            ax3.grid(True, alpha=0.3)
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

            # Sleep hours
            ax4 = fig.add_subplot(224)
            ax4.plot(dates, sleep_hours, 'purple', linewidth=2, marker='d', markersize=4)
            ax4.set_title("Sleep Hours Over Time", fontsize=12)
            ax4.set_ylabel("Sleep Hours")
            ax4.set_ylim(0, max(sleep_hours) + 2 if sleep_hours else 12)
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

            fig.tight_layout()

            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, master=chart_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

            # Close button
            tk.Button(chart_window, text="Close", command=chart_window.destroy,
                     font=("Segoe UI", 11), bg=self.colors.get("primary", "#8B5CF6"),
                     fg="white", relief="flat", padx=20, pady=8).pack(pady=(0, 20))

    def _create_entry_card(self, parent, entry):
        """Create a modern, aesthetic card for a journal entry with click-to-detail"""
        # --- Card Container (Shadow effect via nested frames) ---
        shadow = tk.Frame(parent, bg="#d0d0d0")
        shadow.pack(fill="x", pady=(8, 0), padx=(12, 8))
        
        card = tk.Frame(shadow, bg=self.colors.get("surface", "#fff"), bd=0, cursor="hand2")
        card.pack(fill="x", padx=(0, 2), pady=(0, 2))
        
        # Click handler to open Day Detail
        def open_day_detail(e=None):
            try:
                from app.ui.day_detail import DayDetailPopup
                DayDetailPopup(card, entry, self.colors, self.i18n)
            except Exception as err:
                logging.error(f"Failed to open Day Detail: {err}")
        
        card.bind("<Button-1>", open_day_detail)
        
        # --- Header: Color Bar + Date + Stress Label ---
        header = tk.Frame(card, bg=self.colors.get("surface", "#fff"))
        header.pack(fill="x", padx=0, pady=0)
        
        # Stress color bar on left edge
        stress_val = entry.stress_level or 0
        if stress_val >= 8:
            stress_color, stress_label = "#EF4444", "High Stress"
        elif stress_val >= 5:
            stress_color, stress_label = "#F59E0B", "Moderate"
        else:
            stress_color, stress_label = "#22C55E", "Low Stress"
        
        color_bar = tk.Frame(header, bg=stress_color, width=6)
        color_bar.pack(side="left", fill="y")
        color_bar.bind("<Button-1>", open_day_detail)
        
        # Date and stress text
        date_container = tk.Frame(header, bg=self.colors.get("surface", "#fff"))
        date_container.pack(side="left", fill="x", expand=True, padx=15, pady=12)
        date_container.bind("<Button-1>", open_day_detail)
        
        try:
            date_str = datetime.strptime(str(entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y • %I:%M %p")
        except:
            date_str = str(entry.entry_date)
        
        date_lbl = tk.Label(date_container, text=date_str, 
                font=("Segoe UI", 11, "bold"), bg=self.colors.get("surface", "#fff"), fg=self.colors.get("text_primary", "#000"))
        date_lbl.pack(side="left")
        date_lbl.bind("<Button-1>", open_day_detail)
        
        # Stress label badge
        stress_badge = tk.Label(date_container, text=stress_label, font=("Segoe UI", 9, "bold"),
                               bg=stress_color, fg="white", padx=8, pady=2)
        stress_badge.pack(side="left", padx=10)
        stress_badge.bind("<Button-1>", open_day_detail)
        
        # Sentiment meter (mini bar from red to green)
        score = getattr(entry, 'sentiment_score', 0) or 0
        sentiment_text = "Positive" if score > 30 else "Neutral" if score > -30 else "Negative"
        sentiment_color = "#22C55E" if score > 30 else "#6B7280" if score > -30 else "#EF4444"
        
        sentiment_lbl = tk.Label(header, text=f"Mood: {sentiment_text}", font=("Segoe UI", 9),
                                bg=self.colors.get("surface", "#fff"), fg=sentiment_color)
        sentiment_lbl.pack(side="right", padx=15)
        sentiment_lbl.bind("<Button-1>", open_day_detail)
        
        # --- Content Preview ---
        preview = entry.content[:180] + "..." if len(entry.content) > 180 else entry.content
        content_lbl = tk.Label(card, text=preview, font=("Segoe UI", 10), 
                bg=self.colors.get("surface", "#fff"), fg=self.colors.get("text_secondary", "#555"), 
                wraplength=550, justify="left", anchor="w")
        content_lbl.pack(fill="x", padx=15, pady=5)
        content_lbl.bind("<Button-1>", open_day_detail)
        
        # --- Metrics Bar (Clear Text Labels) ---
        metrics_bar = tk.Frame(card, bg=self.colors.get("surface", "#fff"))
        metrics_bar.pack(fill="x", padx=15, pady=(5, 12))
        metrics_bar.bind("<Button-1>", open_day_detail)
        
        def add_metric(text, bg_color, fg_color="#fff"):
            m = tk.Label(metrics_bar, text=text, font=("Segoe UI", 9, "bold"), 
                        bg=bg_color, fg=fg_color, padx=10, pady=3)
            m.pack(side="left", padx=(0, 8))
            m.configure(relief="flat", highlightthickness=0)
            m.bind("<Button-1>", open_day_detail)
            
        # Add metrics with clear text labels
        if entry.sleep_hours: 
            sleep_color = "#8B5CF6" if entry.sleep_hours >= 7 else "#9333EA"
            add_metric(f"Sleep: {entry.sleep_hours:.1f}h", sleep_color)
        if entry.screen_time_mins: 
            screen_hrs = entry.screen_time_mins / 60
            screen_color = "#F97316" if screen_hrs > 4 else "#3B82F6"
            add_metric(f"Screen: {screen_hrs:.1f}h", screen_color)
        if entry.energy_level:
            energy_color = "#22C55E" if entry.energy_level >= 7 else "#6B7280"
            add_metric(f"Energy: {entry.energy_level}/10", energy_color)
        if entry.work_hours:
            work_color = "#0EA5E9" if entry.work_hours <= 8 else "#DC2626"
            add_metric(f"Work: {entry.work_hours:.1f}h", work_color)
        
        # Click hint
        hint = tk.Label(card, text="Click to view details →", font=("Segoe UI", 8, "italic"),
                       bg=self.colors.get("surface", "#fff"), fg=self.colors.get("text_secondary", "#999"))
        hint.pack(anchor="e", padx=15, pady=(0, 8))
        hint.bind("<Button-1>", open_day_detail)
    
    def open_dashboard(self):
        """Open analytics dashboard with lazy import"""
        try:
            # Lazy import to avoid circular dependency
            from app.ui.dashboard import AnalyticsDashboard
            colors = getattr(self.app, 'colors', self.colors)
            theme = self.app.settings.get("theme", "light") if self.app else "light"
            dashboard = AnalyticsDashboard(self.journal_window, self.username, colors=colors, theme=theme)
            dashboard.render_dashboard()
        except ImportError as e:
            logging.error(f"Failed to import AnalyticsDashboard: {e}")
            messagebox.showerror("Error", "Dashboard feature not available")

    # ========== HEALTH INSIGHTS & NUDGES ==========
    def generate_health_insights(self):
        """Check for recent trends and return comprehensive health insights"""
        insight_text = "Not enough data for insights yet."
        try:
            # Query last 3 days via Service
            entries = JournalService.get_recent_entries(self.username, days=3)
            
            if not entries:
                return "Start tracking your sleep and energy to get personalized health insights!"
            
            # Data extraction
            sleeps = []
            qualities = []
            energies = []
            works = []
            screens = []
            stresses = []
            
            for entry in entries:
                sleeps.append(entry.sleep_hours)
                qualities.append(entry.sleep_quality)
                energies.append(entry.energy_level)
                works.append(entry.work_hours)
                screens.append(getattr(entry, 'screen_time_mins', None))
                stresses.append(getattr(entry, 'stress_level', None))
            
            # --- DEBUG LOGGING ---
            print(f"DEBUG: Entries found: {len(entries)}")
            print(f"DEBUG: Screens: {screens}")
            print(f"DEBUG: Stresses: {stresses}")
            print(f"DEBUG: Work: {works}")
            print(f"DEBUG: Energy: {energies}")
            print(f"DEBUG: Sleep: {sleeps}")
            # ---------------------

            # --- ADVANCED ANALYSIS ENGINE ---
            
            risk_factors = []
            advice_components = []
            
            # 1. Digital Overload Check
            avg_screen = sum(s for s in screens if s)/len([s for s in screens if s]) if any(screens) else 0
            avg_stress = sum(s for s in stresses if s)/len([s for s in stresses if s]) if any(stresses) else 0
            
            if avg_screen > 240 and avg_stress > 6:
                risk_factors.append("Digital Overload")
                advice_components.append("Reducing screen time by 1 hour could lower your stress levels.")

            # 2. Burnout Check
            avg_work = sum(w for w in works if w)/len([w for w in works if w]) if any(works) else 0
            avg_energy = sum(e for e in energies if e)/len([e for e in energies if e]) if any(energies) else 0
            
            if avg_work > 9 and avg_energy < 5:
                risk_factors.append("Early Burnout")
                advice_components.append("Your energy is low despite high work output. This is sustainable for only short periods.")

            # 3. Sleep Check
            avg_sleep = sum(s for s in sleeps if s)/len([s for s in sleeps if s]) if any(sleeps) else 0
            if avg_sleep < 6:
                risk_factors.append("Sleep Deprivation")
                advice_components.append("Recovery is your #1 priority right now. Aim for 7h tonight.")

            # 4. Contextual Triggers & Schedule
            recent_triggers = [t for t in [getattr(e, 'stress_triggers', '') for e in entries] if t]
            common_trigger = recent_triggers[0][:15] + "..." if recent_triggers else None
            
            schedules = [s for s in [getattr(e, 'daily_schedule', '') for e in entries] if s]
            is_busy = schedules and len(schedules[0]) > 50

            # --- SYNTHESIS ---
            # Load user's emotional patterns (Issue #269)
            user_emotions = []
            preferred_support = None
            try:
                with safe_db_context() as session:
                    user = session.query(User).filter_by(username=self.username).first()
                    if user and user.emotional_patterns:
                        ep = user.emotional_patterns
                        import json
                        try:
                            user_emotions = json.loads(ep.common_emotions) if ep.common_emotions else []
                        except:
                            user_emotions = []
                        preferred_support = ep.preferred_support
            except Exception as e:
                logging.warning(f"Could not load emotional patterns: {e}")
            
            # Check if detected patterns match user-defined emotions
            personalized_note = ""
            for emotion in user_emotions:
                emotion_lower = emotion.lower()
                if emotion_lower in ["anxiety", "stress", "overwhelm"] and avg_stress > 5:
                    personalized_note = f"💭 I notice you've identified **{emotion}** as something you often experience. This pattern seems active right now."
                    break
                elif emotion_lower in ["sadness"] and any(e.sentiment_score and e.sentiment_score < -30 for e in entries):
                    personalized_note = f"💭 Your journals show a low sentiment, and you've mentioned **{emotion}** as a common feeling."
                    break
            
            # Personalize response based on support style
            def style_message(base_msg):
                if not preferred_support:
                    return base_msg
                if "Encouraging" in preferred_support:
                    return f"💪 {base_msg}\n\n**Remember**: You've handled tough days before. You've got this!"
                elif "Problem-Solving" in preferred_support:
                    return f"📋 {base_msg}\n\n**Action Item**: Pick one small thing to improve today."
                elif "Listen" in preferred_support:
                    return f"🤗 {base_msg}\n\n**It's okay to feel this way.** Take your time."
                elif "Distraction" in preferred_support:
                    return f"✨ {base_msg}\n\n**Fun idea**: Take a 5-min break and do something you enjoy!"
                return base_msg
            
            if not risk_factors:
                return style_message("🌟 **Balanced State**: Your metrics look healthy! Keep maintaining this rhythm.")
            
            if len(risk_factors) == 1:
                # Single issue
                msg = f"⚠️ **Attention Needed**: I've detected signs of {risk_factors[0]}.\n"
                msg += advice_components[0]
                if common_trigger: msg += f"\n(Context: You mentioned '{common_trigger}' as a trigger)"
                if personalized_note: msg += f"\n\n{personalized_note}"
                return style_message(msg)
            
            else:
                # Complex/Combined issue (Smart Synthesis)
                combined = " + ".join(risk_factors)
                msg = f"🛑 **Complex Alert**: You are facing a combination of {combined}.\n\n"
                msg += "This compounding effect requires immediate action:\n"
                
                # Prioritize Sleep if present
                if "Sleep Deprivation" in risk_factors:
                    msg += "1. **Fix Sleep First**: Without rest, stress and burnout are 2x harder to manage.\n"
                    msg += "2. **Secondary Step**: " + ("Cut screen time." if "Digital Overload" in risk_factors else "Limit work hours.")
                elif "Digital Overload" in risk_factors and "Early Burnout" in risk_factors:
                    msg += "1. **Disconnect**: Your high screen time is preventing mental recovery from work.\n"
                    msg += "2. **Hard Stop**: Set a strict work cutoff time today."
                
                if is_busy:
                    msg += "\n\n🗓️ **Note**: Your schedule looks packed. Clear 30 mins for 'do nothing' time."
                
                if personalized_note: msg += f"\n\n{personalized_note}"
                return style_message(msg)
            
        except Exception as e:
            logging.error(f"Insight generation failed: {e}")
            insight_text = "Could not generate insights at this moment."
            
        return insight_text


# Standalone test function
if __name__ == "__main__":
    root = tk.Tk()
    journal = JournalFeature(root)
    journal.open_journal_window("test_user")
    root.mainloop()
