# app/ui/journal.py
import tkinter as tk
from typing import Optional, Any
from tkinter import ttk, messagebox, scrolledtext
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta
import logging

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from sqlalchemy import desc, text

from app.i18n_manager import get_i18n
from app.models import JournalEntry, User, UserEmotionalPatterns
from app.db import safe_db_context
from app.validation import validate_required, validate_length, validate_range, sanitize_text, RANGES
from app.validation import MAX_TEXT_LENGTH

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
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon', quiet=True)
            
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

        tk.Button(btn_frame, text=self.i18n.get("journal.dashboard"), command=self.open_dashboard,
                 font=("Segoe UI", 11), bg=colors["surface"], fg=colors["text_primary"],
                 relief="flat", padx=15).pack(side="left")
        
        tk.Button(btn_frame, text="Save Entry", command=self.save_and_analyze,
                 font=("Segoe UI", 11, "bold"), bg=colors["primary"], fg=colors.get("text_inverse", "white"),
                 padx=20, pady=8, relief="flat").pack(side="right")
                 
        if hasattr(self.app, 'switch_view'):
             tk.Button(btn_frame, text="Cancel", command=lambda: self.app.switch_view('home'),
                     font=("Segoe UI", 11), bg=colors["bg"], fg=colors["text_secondary"],
                     relief="flat").pack(side="right", padx=10)

    def open_journal_window(self, username):
        """Standalone Window Mode (Deprecated but kept for compat)"""
        self.username = username
        self.journal_window = tk.Toplevel(self.parent_root)
        self.journal_window.title(self.i18n.get("journal.title"))
        self.journal_window.geometry("800x600")
        self.journal_window.configure(bg=self.colors.get("bg"))
        self.render_journal_view(self.journal_window, username)
    
    def analyze_sentiment(self, text):
        """Analyze sentiment using NLTK VADER"""
        if not text.strip():
            return 0.0
            
        if self.sia:
            try:
                scores = self.sia.polarity_scores(text)
                # Convert compound (-1 to 1) to -100 to 100
                return scores['compound'] * 100
            except Exception as e:
                logging.error(f"Sentiment analysis error: {e}")
                return 0.0
        else:
            # Fallback to simple keyword matching if VADER fails
            positive_words = ['happy', 'joy', 'excited', 'grateful', 'peaceful', 'confident']
            negative_words = ['sad', 'angry', 'frustrated', 'anxious', 'worried', 'stressed']
            
            text_lower = text.lower()
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            total_words = len(text.split())
            if total_words == 0: 
                return 0.0
            
            score = (positive_count - negative_count) / max(total_words, 1) * 100
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
    
    def save_and_analyze(self):
        """Save journal entry and perform AI analysis"""
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
        
        # Perform analysis
        sentiment_score = self.analyze_sentiment(content)
        emotional_patterns = self.extract_emotional_patterns(content)
        
        # Save to database
        try:
            with safe_db_context() as session:
                entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = JournalEntry(
                    username=self.username,
                    entry_date=entry_date,
                    content=content,
                    sentiment_score=sentiment_score,
                    emotional_patterns=emotional_patterns,
                    # Metrics
                    sleep_hours=self.sleep_hours_var.get(),
                    sleep_quality=self.sleep_quality_var.get(),
                    energy_level=self.energy_level_var.get(),
                    work_hours=self.work_hours_var.get(),
                    # PR #6 Expansion
                    screen_time_mins=self.screen_time_var.get(),
                    stress_level=self.stress_level_var.get(),
                    daily_schedule=sanitize_text(self.schedule_text.get("1.0", tk.END)),
                    stress_triggers=sanitize_text(self.triggers_text.get("1.0", tk.END))
                )
                session.add(entry)
                # safe_db_context Auto-commits on exit
            
            # Check for expanded health insights
            health_insights = self.generate_health_insights()
            
            # Show analysis results with insights
            self.show_analysis_results(sentiment_score, emotional_patterns, health_insights)
            
            # Clear text area
            # Clear inputs
            self.text_area.delete("1.0", tk.END)
            self.schedule_text.delete("1.0", tk.END)
            self.triggers_text.delete("1.0", tk.END)
            
        except Exception as e:
            logging.error("Failed to save journal entry", exc_info=True)
            messagebox.showerror("Error", f"Failed to save entry: {e}")
    
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


        # --- Modern Filter Bar (No search, Month + Type filters) ---
        filter_frame = tk.Frame(entries_window, bg=self.colors.get("surface", "#fff"), pady=12)
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Month filter
        month_container = tk.Frame(filter_frame, bg=self.colors.get("surface", "#fff"))
        month_container.pack(side="left", padx=(10, 15))
        
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
        filter_container = tk.Frame(filter_frame, bg=self.colors.get("surface", "#fff"))
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
            month_var.set("All Months")
            type_var.set("All Entries")
            render_entries()
        
        tk.Button(filter_frame, text="Reset", command=clear_filters,
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
                
            selected_month = month_var.get()
            filter_type = type_var.get()
            
            # Using safe_db_context for read operations too
            with safe_db_context() as session:
                entries = session.query(JournalEntry)\
                    .filter_by(username=self.username)\
                    .order_by(desc(JournalEntry.entry_date))\
                    .all()
                print(f"DEBUG: View Past Entries found {len(entries)} records for {self.username}")
                
                filtered_count = 0
                for entry in entries:
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

        # Update on filter change
        month_combo.bind("<<ComboboxSelected>>", lambda e: render_entries())
        type_combo.bind("<<ComboboxSelected>>", lambda e: render_entries())
        
        # Initial Render
        render_entries()

        # Configure canvas width
        def _configure_canvas(event):
            canvas.itemconfig(canvas.create_window((0,0), window=scrollable_frame, anchor="nw"), width=event.width)
        canvas.bind("<Configure>", _configure_canvas)

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
        """Check for recent trends and return comprehensive health insights"""
        try:
            with safe_db_context() as session:
                # Query last 3 days
                three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
                
                # Use SQLAlchemy query instead of raw SQL for better compatibility
                entries = session.query(JournalEntry)\
                    .filter(JournalEntry.username == self.username)\
                    .filter(JournalEntry.entry_date >= three_days_ago)\
                    .order_by(JournalEntry.entry_date.desc())\
                    .all()
                
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
                
                # Calculate Averages
                avg_sleep = sum(sleeps) / len(sleeps) if sleeps else 0
                avg_quality = sum(qualities) / len(qualities) if qualities else 0
                avg_energy = sum(energies) / len(energies) if energies else 0
                avg_work = sum(works) / len(works) if works else 0
                
                insights = []
                
                # --- Logic Rule Engine ---
                
                # 1. Sleep Logic (Duration & Quality)
                if avg_sleep < 6.0:
                    insights.append("🌙 You've been averaging less than 6 hours of sleep.")
                elif avg_sleep >= 7.5 and avg_quality >= 7:
                    insights.append("🛌 You're getting great sleep quantity and quality!")
                
                # Quality specific
                if qualities and avg_quality < 5:
                    insights.append("📉 Your sleep quality is reported low. Ensure your room is cool and dark.")
                elif sleeps and qualities and avg_sleep > 8 and avg_quality < 5:
                    insights.append("🤔 You're sleeping long hours but quality is low. This might indicate restless sleep.")
    
                # 2. Energy Logic
                if len(energies) >= 2 and all(e <= 4 for e in energies[:3]):
                    insights.append("🔋 Warning: Consistent low energy detected. Prevent burnout by taking a break.")
                elif avg_energy >= 8.0:
                    insights.append("⚡ You're continuously reporting high energy!")
                elif len(energies) >= 2 and energies[0] > energies[-1] + 2:
                     insights.append("🚀 Energy trend: Improving compared to recent days.")
    
                # 3. Work Logic
                if avg_work > 10:
                     insights.append("💼 Heavy Workload Alert: Averaging >10h/day. Don't forget to disconnect.")
                elif avg_work > 8:
                     insights.append("👔 You're having a standard productive work week.")
                elif avg_work < 2 and avg_energy > 5:
                     insights.append("🧘 Low work hours + High energy = Great recovery period!")
    
                # Construct final message
                if insights:
                    insight_text = " ".join(insights)
                else:
                    insight_text = "Your health metrics are stable. Consistent tracking discovers hidden patterns!"
                    
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