# app/ui/timeline_graph.py
"""
Timeline Graph Visualization - Issue #1324

Displays mood and sentiment trends with line graphs for
pattern analysis and long-term emotional journey tracking.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

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

from app.services.journal_service import JournalService
from app.exceptions import DatabaseError
from app.i18n_manager import get_i18n

logger = logging.getLogger(__name__)


class TimelineGraphView:
    """
    Display emotion trends and patterns through line graphs.
    """

    def __init__(self, parent: tk.Widget, app_root: tk.Widget, username: str) -> None:
        """
        Initialize Timeline Graph View.
        
        Args:
            parent: Parent tkinter frame
            app_root: Root application window (for styling)
            username: Username for fetching data
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not installed - graph features unavailable")

        self.parent = parent
        self.root = app_root
        self.username = username
        self.i18n = get_i18n()

        # Color scheme
        self.colors = self._get_colors()

        # State
        self.current_metric = "mood"  # mood, sentiment, energy, stress
        self.current_period = "daily"
        self.start_date = None
        self.end_date = None

        # Set default date range (last 30 days)
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=30)
        self.start_date = start_dt.strftime("%Y-%m-%d")
        self.end_date = end_dt.strftime("%Y-%m-%d")

        self._setup_ui()

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

        if hasattr(self.root, 'colors'):
            default_colors.update(self.root.colors)

        return default_colors

    def _setup_ui(self) -> None:
        """Setup the graph UI."""
        self.parent.configure(bg=self.colors["bg"])

        # === HEADER ===
        header_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        header_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            header_frame,
            text="📈 Emotion Trends",
            font=("Segoe UI", 20, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"]
        ).pack(anchor="w")

        # === CONTROLS ===
        controls_frame = tk.Frame(self.parent, bg=self.colors["surface"], padx=15, pady=10)
        controls_frame.pack(fill=tk.X, padx=15, pady=10)

        # Metric selector
        metric_label = tk.Label(
            controls_frame,
            text="Metric:",
            bg=self.colors["surface"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10)
        )
        metric_label.pack(side=tk.LEFT, padx=(0, 10))

        metrics_frame = tk.Frame(controls_frame, bg=self.colors["surface"])
        metrics_frame.pack(side=tk.LEFT, padx=5)

        self.metric_buttons = {}
        for metric, label in [("mood", "💭 Mood"), ("sentiment", "💬 Sentiment"),
                             ("energy", "⚡ Energy"), ("stress", "😰 Stress")]:
            btn = tk.Button(
                metrics_frame,
                text=label,
                width=10,
                bg=self.colors["primary"] if metric == self.current_metric else self.colors["bg"],
                fg="white" if metric == self.current_metric else self.colors["text_secondary"],
                relief=tk.FLAT,
                font=("Segoe UI", 9, "bold"),
                command=lambda m=metric: self._change_metric(m)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.metric_buttons[metric] = btn

        # Period selector
        period_label = tk.Label(
            controls_frame,
            text="Period:",
            bg=self.colors["surface"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10)
        )
        period_label.pack(side=tk.LEFT, padx=(20, 10))

        periods_frame = tk.Frame(controls_frame, bg=self.colors["surface"])
        periods_frame.pack(side=tk.LEFT, padx=5)

        for period in ["Daily", "Weekly", "Monthly"]:
            btn = tk.Button(
                periods_frame,
                text=period,
                width=8,
                bg=self.colors["primary"] if period.lower() == self.current_period else self.colors["bg"],
                fg="white" if period.lower() == self.current_period else self.colors["text_secondary"],
                relief=tk.FLAT,
                font=("Segoe UI", 9, "bold"),
                command=lambda p=period.lower(): self._change_period(p)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # === GRAPH CONTAINER ===
        self.graph_container = tk.Frame(self.parent, bg=self.colors["surface"], padx=15, pady=15)
        self.graph_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # === STATISTICS PANEL ===
        stats_frame = tk.Frame(self.parent, bg=self.colors["surface"], padx=15, pady=10)
        stats_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        self.stats_label = tk.Label(
            stats_frame,
            text="",
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9),
            justify=tk.LEFT
        )
        self.stats_label.pack(anchor="w")

        # === LOAD INITIAL GRAPH ===
        self._load_graph()

    def _change_metric(self, metric: str) -> None:
        """Change the displayed metric."""
        self.current_metric = metric
        
        # Update button states
        for m, btn in self.metric_buttons.items():
            if m == metric:
                btn.configure(bg=self.colors["primary"], fg="white")
            else:
                btn.configure(bg=self.colors["bg"], fg=self.colors["text_secondary"])
        
        self._load_graph()

    def _change_period(self, period: str) -> None:
        """Change the time period."""
        self.current_period = period
        
        # Adjust date range based on period
        end_dt = datetime.now()
        if period == "daily":
            start_dt = end_dt - timedelta(days=30)
        elif period == "weekly":
            start_dt = end_dt - timedelta(days=90)
        else:  # monthly
            start_dt = end_dt - timedelta(days=180)
        
        self.start_date = start_dt.strftime("%Y-%m-%d")
        self.end_date = end_dt.strftime("%Y-%m-%d")
        
        self._load_graph()

    def _load_graph(self) -> None:
        """Load and display the trend graph."""
        try:
            if not MATPLOTLIB_AVAILABLE:
                self._show_matplotlib_unavailable()
                return

            # Clear previous graph
            for widget in self.graph_container.winfo_children():
                widget.destroy()

            # Fetch trend data
            trends = JournalService.get_emotion_trends(
                self.username,
                start_date=self.start_date,
                end_date=self.end_date,
                period=self.current_period
            )

            if not trends:
                self._show_no_data_message()
                return

            # Parse data
            dates = []
            values = []
            metric_key = f"avg_{self.current_metric}"

            for period_key in sorted(trends.keys()):
                dates.append(period_key)
                values.append(trends[period_key].get(metric_key, 0))

            # Create graph
            self._create_matplotlib_graph(dates, values)

            # Update statistics
            self._update_statistics(values)

        except DatabaseError as e:
            logger.error(f"Database error loading graph: {e}")
            self._show_error_message("Failed to load graph data")
        except Exception as e:
            logger.error(f"Error loading graph: {e}")
            self._show_error_message("An error occurred loading the graph")

    def _create_matplotlib_graph(self, dates: List[str], values: List[float]) -> None:
        """Create matplotlib line graph."""
        try:
            fig = Figure(figsize=(10, 5), dpi=100)
            fig.patch.set_facecolor(self.colors["surface"])

            ax = fig.add_subplot(111)
            ax.set_facecolor(self.colors["bg"])

            # Determine color based on metric
            colors_map = {
                "mood": "#3B82F6",
                "sentiment": "#8B5CF6",
                "energy": "#F59E0B",
                "stress": "#EF4444"
            }
            line_color = colors_map.get(self.current_metric, "#3B82F6")

            # Plot data
            ax.plot(range(len(dates)), values, marker="o", color=line_color, linewidth=2.5,
                   markersize=8, markerfacecolor=line_color, markeredgecolor="white", markeredgewidth=1.5)

            # Add grid
            ax.grid(True, alpha=0.2, linestyle="--", color="#94A3B8")

            # Axis labels
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=9, color=self.colors["text_secondary"])

            # Y-axis
            ax.set_ylabel(self._get_metric_label(), fontsize=10, color=self.colors["text_primary"])
            ax.set_ylim(bottom=0)
            ax.tick_params(axis="y", labelcolor=self.colors["text_secondary"])

            # Styling
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(self.colors["border"])
            ax.spines["bottom"].set_color(self.colors["border"])

            # Title
            fig.suptitle(f"{self._get_metric_label()} Over Time", 
                        fontsize=12, fontweight="bold", color=self.colors["text_primary"])

            fig.tight_layout()

            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, self.graph_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        except Exception as e:
            logger.error(f"Error creating matplotlib graph: {e}")
            self._show_error_message("Failed to render graph")

    def _update_statistics(self, values: List[float]) -> None:
        """Update statistics display."""
        if not values:
            return

        avg = sum(values) / len(values)
        max_val = max(values)
        min_val = min(values)
        trend = "↑" if values[-1] > values[0] else "↓" if values[-1] < values[0] else "→"

        metric_name = self._get_metric_label()
        stats_text = f"{metric_name} | Avg: {avg:.1f} | Max: {max_val:.1f} | Min: {min_val:.1f} | Trend: {trend}"

        self.stats_label.configure(text=stats_text)

    def _get_metric_label(self) -> str:
        """Get human-readable metric label."""
        labels = {
            "mood": "Mood Score",
            "sentiment": "Sentiment",
            "energy": "Energy Level",
            "stress": "Stress Level"
        }
        return labels.get(self.current_metric, "Metric")

    def _show_matplotlib_unavailable(self) -> None:
        """Show message when matplotlib is not available."""
        msg_frame = tk.Frame(self.graph_container, bg=self.colors["surface"])
        msg_frame.pack(expand=True, fill=tk.BOTH)

        tk.Label(
            msg_frame,
            text="📊 Graph Features Unavailable",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["surface"],
            fg=self.colors["text_primary"]
        ).pack(pady=(20, 10))

        tk.Label(
            msg_frame,
            text="Matplotlib is required to display graphs.\nPlease install it to use trend visualization.",
            font=("Segoe UI", 10),
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"]
        ).pack(pady=10)

    def _show_no_data_message(self) -> None:
        """Show message when no data is available."""
        msg_frame = tk.Frame(self.graph_container, bg=self.colors["surface"])
        msg_frame.pack(expand=True, fill=tk.BOTH)

        tk.Label(
            msg_frame,
            text="📭 No Data Available",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["surface"],
            fg=self.colors["text_primary"]
        ).pack(pady=(20, 10))

        tk.Label(
            msg_frame,
            text="No emotion entries found for the selected period.",
            font=("Segoe UI", 10),
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"]
        ).pack(pady=10)

    def _show_error_message(self, message: str) -> None:
        """Show error message."""
        msg_frame = tk.Frame(self.graph_container, bg=self.colors["surface"])
        msg_frame.pack(expand=True, fill=tk.BOTH)

        tk.Label(
            msg_frame,
            text="⚠️ Error",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["surface"],
            fg=self.colors["danger"]
        ).pack(pady=(20, 10))

        tk.Label(
            msg_frame,
            text=message,
            font=("Segoe UI", 10),
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"]
        ).pack(pady=10)
