# app/ui/emotion_timeline.py
"""
Emotion History Timeline View - Issue #1324

Interactive timeline that visually represents emotion entries over time.
Features:
- Daily/Weekly/Monthly grouping
- Emotion cards with intensity visualization
- Pagination for large datasets
- No data state handling
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, List, Any

from app.i18n_manager import get_i18n
from app.db import safe_db_context
from app.models import JournalEntry
from app.services.journal_service import JournalService
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Emotion emoji mapping based on mood score
EMOTION_MAP = {
    "1": "😢", "2": "😢",      # Very sad
    "3": "😕", "4": "😕",      # Worried/Sad
    "5": "😐", "6": "😐",      # Neutral
    "7": "🙂", "8": "🙂",      # Happy
    "9": "😄", "10": "😄"      # Very happy
}


class EmotionTimelineView:
    """
    Interactive timeline view for emotion entries with daily/weekly/monthly grouping.
    """

    def __init__(self, parent: tk.Widget, app_root: tk.Widget, username: str) -> None:
        """
        Initialize Emotion Timeline View.
        
        Args:
            parent: Parent tkinter frame
            app_root: Root application window (for styling)
            username: Username for fetching entries
        """
        self.parent = parent
        self.root = app_root
        self.username = username
        self.i18n = get_i18n()
        self.logger = logger

        # Color scheme
        self.colors = self._get_colors()

        # State
        self.current_period = "daily"  # daily, weekly, monthly
        self.current_page = 1
        self.entries_per_page = 20
        self.total_pages = 1
        self.filtered_entries = []
        self.start_date = None
        self.end_date = None

        self._setup_ui()
        self._load_timeline_data()

    def _get_colors(self) -> Dict[str, str]:
        """Get color scheme from app or use defaults."""
        default_colors = {
            "bg": "#0F172A",
            "surface": "#1E293B",
            "text_primary": "#F8FAFC",
            "text_secondary": "#94A3B8",
            "primary": "#3B82F6",
            "secondary": "#8B5CF6",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "border": "#334155"
        }

        # Merge with app colors if available
        if hasattr(self.root, 'colors'):
            default_colors.update(self.root.colors)

        return default_colors

    def _setup_ui(self) -> None:
        """Setup the timeline UI components."""
        self.parent.configure(bg=self.colors["bg"])

        # === HEADER ===
        header_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        header_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            header_frame,
            text="📋 Emotion Timeline",
            font=("Segoe UI", 20, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"]
        ).pack(side=tk.LEFT)

        # === CONTROLS FRAME ===
        controls_frame = tk.Frame(self.parent, bg=self.colors["surface"], padx=15, pady=10)
        controls_frame.pack(fill=tk.X, padx=15, pady=10)

        # Period selector
        period_label = tk.Label(
            controls_frame,
            text="View by:",
            bg=self.colors["surface"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10)
        )
        period_label.pack(side=tk.LEFT, padx=(0, 10))

        button_frame = tk.Frame(controls_frame, bg=self.colors["surface"])
        button_frame.pack(side=tk.LEFT, padx=5)

        for period in ["Daily", "Weekly", "Monthly"]:
            btn = tk.Button(
                button_frame,
                text=period,
                width=8,
                bg=self.colors["primary"],
                fg="white",
                relief=tk.FLAT,
                font=("Segoe UI", 9, "bold"),
                command=lambda p=period.lower(): self._change_period(p)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Date range selector
        date_label = tk.Label(
            controls_frame,
            text="Date range:",
            bg=self.colors["surface"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10)
        )
        date_label.pack(side=tk.LEFT, padx=(20, 10))

        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()

        # Set default date range (last 90 days)
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=90)
        self.start_date_var.set(start_dt.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_dt.strftime("%Y-%m-%d"))

        self.start_date_entry = DateEntry(
            controls_frame,
            textvariable=self.start_date_var,
            width=12,
            background=self.colors["primary"],
            foreground="white",
            borderwidth=0,
            date_pattern="y-mm-dd",
            font=("Segoe UI", 9)
        )
        self.start_date_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(
            controls_frame,
            text="to",
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5)

        self.end_date_entry = DateEntry(
            controls_frame,
            textvariable=self.end_date_var,
            width=12,
            background=self.colors["primary"],
            foreground="white",
            borderwidth=0,
            date_pattern="y-mm-dd",
            font=("Segoe UI", 9)
        )
        self.end_date_entry.pack(side=tk.LEFT, padx=2)

        # Filter button
        tk.Button(
            controls_frame,
            text="🔍 Filter",
            bg=self.colors["success"],
            fg="white",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            command=self._apply_filters
        ).pack(side=tk.LEFT, padx=10)

        # === MAIN CONTENT (SCROLLABLE) ===
        self.canvas = tk.Canvas(
            self.parent,
            bg=self.colors["bg"],
            highlightthickness=0
        )
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Mousewheel scrolling
        def _on_mousewheel(event):
            try:
                if self.scrollable_frame.winfo_reqheight() > self.canvas.winfo_height():
                    self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except:
                pass

        def _bind(e):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind(e):
            self.canvas.unbind_all("<MouseWheel>")

        self.canvas.bind("<Enter>", _bind)
        self.canvas.bind("<Leave>", _unbind)

        # === TIMELINE ENTRIES CONTAINER ===
        self.timeline_container = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        self.timeline_container.pack(fill=tk.BOTH, expand=True)

        # === NO DATA STATE PLACEHOLDER ===
        self.no_data_frame = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        self._show_no_data_state()

    def _change_period(self, period: str) -> None:
        """Change timeline period (daily/weekly/monthly)."""
        self.current_period = period
        self.current_page = 1
        self._load_timeline_data()

    def _apply_filters(self) -> None:
        """Apply date range filters."""
        try:
            self.start_date = self.start_date_var.get()
            self.end_date = self.end_date_var.get()
            self.current_page = 1
            self._load_timeline_data()
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            messagebox.showerror("Filter Error", "Failed to apply filters")

    def _load_timeline_data(self) -> None:
        """Fetch and display timeline data."""
        try:
            # Clear existing widgets
            for widget in self.timeline_container.winfo_children():
                widget.destroy()
            for widget in self.no_data_frame.winfo_children():
                widget.destroy()

            # Fetch data based on current filters
            if self.current_period == "daily":
                grouped = JournalService.get_timeline_grouped_by_period(
                    self.username,
                    period="daily",
                    start_date=self.start_date,
                    end_date=self.end_date
                )
            elif self.current_period == "weekly":
                grouped = JournalService.get_timeline_grouped_by_period(
                    self.username,
                    period="weekly",
                    start_date=self.start_date,
                    end_date=self.end_date
                )
            else:  # monthly
                grouped = JournalService.get_timeline_grouped_by_period(
                    self.username,
                    period="monthly",
                    start_date=self.start_date,
                    end_date=self.end_date
                )

            if not grouped:
                self._show_no_data_state()
                return

            # Sort periods in descending order (newest first)
            sorted_periods = sorted(grouped.keys(), reverse=True)

            # Pagination
            total_periods = len(sorted_periods)
            self.total_pages = (total_periods + self.entries_per_page - 1) // self.entries_per_page
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages

            start_idx = (self.current_page - 1) * self.entries_per_page
            end_idx = start_idx + self.entries_per_page
            paginated_periods = sorted_periods[start_idx:end_idx]

            # Render timeline entries
            for period_key in paginated_periods:
                entries = grouped[period_key]
                self._render_period_group(period_key, entries)

            # Render pagination controls
            self._render_pagination_controls()

        except DatabaseError as e:
            logger.error(f"Database error loading timeline: {e}")
            messagebox.showerror("Data Error", "Failed to load timeline data")
        except Exception as e:
            logger.error(f"Unexpected error loading timeline: {e}")
            messagebox.showerror("Error", "An unexpected error occurred")

    def _render_period_group(self, period_key: str, entries: List[JournalEntry]) -> None:
        """Render a group of entries for a specific period."""
        # Period header
        header_frame = tk.Frame(self.timeline_container, bg=self.colors["surface"], padx=15, pady=10)
        header_frame.pack(fill=tk.X, padx=10, pady=(15, 5))

        # Format period label
        period_label = self._format_period_label(period_key)

        # Calculate stats for period
        avg_mood = sum(e.mood_score for e in entries if e.mood_score) / len([e for e in entries if e.mood_score]) if any(e.mood_score for e in entries) else 0

        tk.Label(
            header_frame,
            text=f"{period_label} ({len(entries)} entries)",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["surface"],
            fg=self.colors["text_primary"]
        ).pack(anchor="w")

        # Emotion cards for this period
        for entry in sorted(entries, key=lambda e: e.entry_date, reverse=True):
            self._render_emotion_card(entry)

    def _render_emotion_card(self, entry: JournalEntry) -> None:
        """Render a single emotion entry card."""
        card_frame = tk.Frame(self.timeline_container, bg=self.colors["surface"], padx=15, pady=12)
        card_frame.pack(fill=tk.X, padx=10, pady=5)

        # Left: Emotion icon and basic info
        left_frame = tk.Frame(card_frame, bg=self.colors["surface"])
        left_frame.pack(side=tk.LEFT, padx=(0, 15))

        # Emotion emoji based on mood score
        mood = entry.mood_score if entry.mood_score else 5
        emotion_emoji = EMOTION_MAP.get(str(int(mood)), "😐")

        tk.Label(
            left_frame,
            text=emotion_emoji,
            font=("Segoe UI", 28),
            bg=self.colors["surface"]
        ).pack(anchor="center", pady=(0, 5))

        # Mood score visualization (bar)
        mood_label = tk.Label(
            left_frame,
            text=f"Mood: {mood:.1f}/10",
            font=("Segoe UI", 9),
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"]
        )
        mood_label.pack(anchor="center")

        # Mood progress bar
        mood_percent = (mood / 10) * 100
        mood_bar = tk.Canvas(left_frame, width=80, height=8, bg=self.colors["bg"], highlightthickness=0)
        mood_bar.pack(pady=3)
        mood_bar.create_rectangle(0, 0, mood_percent * 0.8, 8, fill=self._get_mood_color(mood), outline="")

        # Center: Entry content
        content_frame = tk.Frame(card_frame, bg=self.colors["surface"])
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        # Timestamp
        entry_dt = datetime.strptime(entry.entry_date, "%Y-%m-%d %H:%M:%S")
        timestamp_text = entry_dt.strftime("%I:%M %p")

        tk.Label(
            content_frame,
            text=timestamp_text,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["surface"],
            fg=self.colors["text_primary"]
        ).pack(anchor="w", pady=(0, 5))

        # Preview text (first 150 chars)
        preview = entry.content[:150] + "..." if len(entry.content) > 150 else entry.content
        preview_text = tk.Label(
            content_frame,
            text=preview,
            font=("Segoe UI", 9),
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"],
            wraplength=400,
            justify=tk.LEFT
        )
        preview_text.pack(anchor="w", fill=tk.X)

        # Additional metadata
        meta_frame = tk.Frame(content_frame, bg=self.colors["surface"])
        meta_frame.pack(fill=tk.X, pady=(5, 0), anchor="w")

        if entry.sentiment_score is not None:
            sentiment_color = "#10B981" if entry.sentiment_score > 0 else "#EF4444" if entry.sentiment_score < 0 else "#F59E0B"
            tk.Label(
                meta_frame,
                text=f"Sentiment: {entry.sentiment_score:.2f}",
                font=("Segoe UI", 8),
                bg=self.colors["surface"],
                fg=sentiment_color
            ).pack(side=tk.LEFT, padx=(0, 15))

        if entry.category:
            tk.Label(
                meta_frame,
                text=f"Category: {entry.category}",
                font=("Segoe UI", 8),
                bg=self.colors["surface"],
                fg=self.colors["text_secondary"]
            ).pack(side=tk.LEFT, padx=(0, 15))

        if entry.stress_level is not None:
            tk.Label(
                meta_frame,
                text=f"Stress: {entry.stress_level}/10",
                font=("Segoe UI", 8),
                bg=self.colors["surface"],
                fg=self.colors["text_secondary"]
            ).pack(side=tk.LEFT)

    def _render_pagination_controls(self) -> None:
        """Render pagination buttons."""
        if self.total_pages <= 1:
            return

        pagination_frame = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        pagination_frame.pack(fill=tk.X, pady=20)

        center_frame = tk.Frame(pagination_frame, bg=self.colors["bg"])
        center_frame.pack(anchor="center")

        # Previous button
        tk.Button(
            center_frame,
            text="◀ Previous",
            bg=self.colors["primary"],
            fg="white",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            command=self._previous_page,
            state=tk.NORMAL if self.current_page > 1 else tk.DISABLED
        ).pack(side=tk.LEFT, padx=5)

        # Page info
        tk.Label(
            center_frame,
            text=f"Page {self.current_page} of {self.total_pages}",
            bg=self.colors["bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=15)

        # Next button
        tk.Button(
            center_frame,
            text="Next ▶",
            bg=self.colors["primary"],
            fg="white",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            command=self._next_page,
            state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED
        ).pack(side=tk.LEFT, padx=5)

    def _next_page(self) -> None:
        """Load next page of timeline."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_timeline_data()

    def _previous_page(self) -> None:
        """Load previous page of timeline."""
        if self.current_page > 1:
            self.current_page -= 1
            self._load_timeline_data()

    def _show_no_data_state(self) -> None:
        """Display no data state message."""
        no_data_container = tk.Frame(self.no_data_frame, bg=self.colors["bg"])
        no_data_container.pack(expand=True, fill=tk.BOTH, padx=20, pady=40)

        tk.Label(
            no_data_container,
            text="📭 No Entries Found",
            font=("Segoe UI", 18, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"]
        ).pack(pady=(0, 10))

        tk.Label(
            no_data_container,
            text="Start journaling to build your emotion timeline!",
            font=("Segoe UI", 11),
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"]
        ).pack(pady=10)

        self.no_data_frame.pack(expand=True, fill=tk.BOTH)

    @staticmethod
    def _format_period_label(period_key: str) -> str:
        """Format period key to readable label."""
        if "-W" in period_key:  # Weekly: 2025-W03
            year, week = period_key.split("-W")
            return f"Week {week}, {year}"
        elif "-" in period_key.split("-")[1]:  # Daily: 2025-01-15
            try:
                dt = datetime.strptime(period_key, "%Y-%m-%d")
                return dt.strftime("%A, %B %d, %Y")
            except:
                return period_key
        else:  # Monthly: 2025-01
            try:
                dt = datetime.strptime(period_key, "%Y-%m")
                return dt.strftime("%B %Y")
            except:
                return period_key

    @staticmethod
    def _get_mood_color(mood: float) -> str:
        """Return color based on mood score."""
        if mood <= 2:
            return "#EF4444"  # Red - very sad
        elif mood <= 4:
            return "#F97316"  # Orange - sad
        elif mood <= 6:
            return "#F59E0B"  # Amber - neutral
        elif mood <= 8:
            return "#FBBF24"  # Yellow - happy
        else:
            return "#10B981"  # Green - very happy
