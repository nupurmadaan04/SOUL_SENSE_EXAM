import tkinter as tk
from tkinter import ttk, messagebox
# DateEntry removed due to GPL license violation
DateEntry = None
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

from app.db import get_session, safe_db_context
from app.models import JournalEntry
from app.i18n_manager import get_i18n

class DailyHistoryView:
    def __init__(self, parent, app_root, username):
        self.parent = parent
        self.root = app_root
        self.username = username
        self.i18n = get_i18n()
        self.style = getattr(self.root, 'ui_style', None)
        
        # Colors Handling
        default_colors = {
            "bg": "#0F172A", "surface": "#1E293B", 
            "text_primary": "#F8FAFC", "text_secondary": "#94A3B8",
            "primary": "#3B82F6", "secondary": "#8B5CF6",
            "bg_tertiary": "#334155", "border": "#334155",
        }
        
        # Merge defaults with passed app colors to ensure all keys exist
        app_colors = getattr(self.root, 'colors', {})
        self.colors = default_colors.copy()
        if app_colors:
            self.colors.update(app_colors)

        # State for Interactive Graph
        self.history_data = {
            "dates": [], "sleep": [], "quality": [], "energy": [], "work": []
        }
        self.current_metric = "sleep" # Default
        self.selected_date_str = None
        
        self.setup_ui()
        
    def setup_ui(self):
        self.parent.configure(bg=self.colors["bg"])
        self.parent.title("📅 Wellness History")
        self.parent.geometry("1000x750")
        
        # --- Header ---
        header_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        header_frame.pack(fill=tk.X, padx=30, pady=20)
        
        tk.Label(header_frame, text="Daily Insights", 
                font=("Segoe UI", 24, "bold"), bg=self.colors["bg"], fg=self.colors["text_primary"]).pack(side=tk.LEFT)
        
        # Date Picker (Styled)
        # Date Picker replacement (GPL Concern)
        self.date_entry = tk.Entry(header_frame, width=12, font=("Segoe UI", 12))
        self.date_entry.pack(side=tk.RIGHT)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Add a refresh button since we can't easily detect date change in Entry
        tk.Button(header_frame, text="🔍", command=self.load_data, 
                  font=("Segoe UI", 10), bg=self.colors["primary"], fg="white", relief="flat").pack(side=tk.RIGHT, padx=5)
        
        self.date_entry.bind("<Return>", lambda e: self.load_data())

        # --- Main Layout (Scrollable) ---
        self.canvas = tk.Canvas(self.parent, bg=self.colors["bg"], highlightthickness=0)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg"])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create Window
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=980)
        
        # Pack Canvas (Hidden Scrollbar)
        self.canvas.pack(side="left", fill="both", expand=True, padx=10)
        
        # Conditional Mousewheel
        def _on_mousewheel(event):
            try:
                if self.scrollable_frame.winfo_reqheight() > self.canvas.winfo_height():
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except: pass

        def _bind(e): self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind(e): self.canvas.unbind_all("<MouseWheel>")
        
        self.canvas.bind("<Enter>", _bind)
        self.canvas.bind("<Leave>", _unbind)
        
        # Container Frames
        self.cards_container = tk.Frame(self.scrollable_frame, bg=self.colors["bg"])
        self.cards_container.pack(fill=tk.X, padx=20, pady=10)
        
        self.chart_container = tk.Frame(self.scrollable_frame, bg=self.colors["surface"], padx=20, pady=20)
        self.chart_container.pack(fill=tk.X, padx=20, pady=20)
        
        self.entry_container = tk.Frame(self.scrollable_frame, bg=self.colors["surface"], padx=20, pady=20)
        self.entry_container.pack(fill=tk.X, padx=20, pady=20)

        # Initialize Chart UI structure
        self.setup_chart_ui()
        
        # Load Initial Data
        self.load_data()

    def setup_chart_ui(self):
        """Setup the Sidebar + Chart layout"""
        tk.Label(self.chart_container, text="Weekly Trends", font=("Segoe UI", 16, "bold"),
                bg=self.colors["surface"], fg=self.colors["text_primary"]).pack(anchor="w", pady=(0, 15))
        
        content = tk.Frame(self.chart_container, bg=self.colors["surface"])
        content.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar Actions
        sidebar = tk.Frame(content, bg=self.colors["surface"], width=150)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        self.create_metric_btn(sidebar, "🌙 Sleep Hours", "sleep", "#8B5CF6")
        self.create_metric_btn(sidebar, "✨ Sleep Quality", "quality", "#EC4899")
        self.create_metric_btn(sidebar, "⚡ Energy Level", "energy", "#F59E0B")
        self.create_metric_btn(sidebar, "💼 Work Hours", "work", "#10B981")
        
        # Chart Area (Fixed Size)
        self.fig = Figure(figsize=(7, 4), dpi=100) # Slightly taller for clarity
        self.fig.patch.set_facecolor(self.colors["surface"])
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self.colors["surface"])
        
        self.chart_canvas = FigureCanvasTkAgg(self.fig, content)
        # expand=False keeps size consistent as per user request
        self.chart_canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=10)

    def create_metric_btn(self, parent, text, metric_key, color):
        btn = tk.Button(parent, text=text, font=("Segoe UI", 10, "bold"),
                       bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"],
                       activebackground=color, activeforeground="white",
                       relief="flat", pady=8, width=15, anchor="w", padx=10,
                       command=lambda: self.update_chart(metric_key, color))
        btn.pack(pady=5)

    def load_data(self, event=None):
        date_str = self.date_entry.get().strip()
        if not date_str or date_str == "":
            date_str = datetime.now().strftime("%Y-%m-%d")
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, date_str)
            
        self.selected_date_str = date_str
        
        print(f"Loading data for {date_str}...")
        
        # 1. Fetch User Entry for Selected Date
        entry = self.fetch_single_entry(date_str)
        self.render_cards(entry)
        self.render_journal_text(entry)
        
        # 2. Fetch Weekly History for Graph
        self.fetch_weekly_history(date_str)
        self.update_chart("sleep", "#8B5CF6") # Reset to sleep default

    def fetch_single_entry(self, date_str):
        with safe_db_context() as session:
            entry = session.query(JournalEntry).filter(
                JournalEntry.username == self.username,
                JournalEntry.entry_date.like(f"{date_str}%")
            ).first()
            if entry:
                return {
                     "sleep": entry.sleep_hours or 0,
                    "quality": getattr(entry, 'sleep_quality', 0) or 0,
                    "energy": getattr(entry, 'energy_level', 0) or 0,
                    "work": getattr(entry, 'work_hours', 0) or 0,
                    "content": entry.content
                }
            return None

    def fetch_weekly_history(self, end_date_str):
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        start_date = end_date - timedelta(days=6)
        
        self.history_data = {"dates": [], "sleep": [], "quality": [], "energy": [], "work": [], "mood": []}
        
        # Initialize 7 days with 0s to ensure graph structure
        date_map = {}
        for i in range(7):
            d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            date_label = (start_date + timedelta(days=i)).strftime("%a\n%d")
            self.history_data["dates"].append(date_label)
            date_map[d] = i # Index map
            self.history_data["sleep"].append(0)
            self.history_data["quality"].append(0)
            self.history_data["energy"].append(0)
            self.history_data["work"].append(0)
            self.history_data["mood"].append(0)

        with safe_db_context() as session:
            entries = session.query(JournalEntry).filter(
                JournalEntry.username == self.username,
                JournalEntry.entry_date >= start_date.strftime("%Y-%m-%d"),
                JournalEntry.entry_date <= end_date_str + " 23:59:59"
            ).all()
            
            for e in entries:
                d_key = e.entry_date.split()[0]
                if d_key in date_map:
                    idx = date_map[d_key]
                    self.history_data["sleep"][idx] = e.sleep_hours or 0
                    self.history_data["quality"][idx] = getattr(e, 'sleep_quality', 0) or 0
                    self.history_data["energy"][idx] = getattr(e, 'energy_level', 0) or 0
                    self.history_data["work"][idx] = getattr(e, 'work_hours', 0) or 0
                    self.history_data["mood"][idx] = e.sentiment_score or 0 or 0

    def update_chart(self, metric, color):
        self.current_metric = metric
        
        # Remove any existing secondary axes (twins) to prevent stacking
        for ax in self.fig.axes:
            if ax != self.ax:
                self.fig.delaxes(ax)
                
        self.ax.clear()
        
        values = self.history_data[metric]
        dates = self.history_data["dates"]
        
        # Bars
        bars = self.ax.bar(dates, values, color=color, width=0.6, alpha=0.9, zorder=3, label=self.current_metric.title())
        
        # Highlight Selected Day
        bars[-1].set_color("white")
        bars[-1].set_edgecolor(color)
        bars[-1].set_linewidth(2)
        bars[-1].set_alpha(1.0)
        
        from scipy.interpolate import make_interp_spline

        # Secondary Axis for Sentiment (Smooth Curve)
        ax2 = self.ax.twinx()
        mood_values = self.history_data["mood"]
        x_indices = np.arange(len(dates))
        
        # Spline Interpolation
        if len(dates) > 2:
            try:
                x_smooth = np.linspace(x_indices.min(), x_indices.max(), 300)
                spl = make_interp_spline(x_indices, mood_values, k=3)
                y_smooth = spl(x_smooth)
                ax2.plot(x_smooth, y_smooth, color="#F472B6", linewidth=3, linestyle="-", label="Sentiment", zorder=4)
            except Exception:
                # Fallback if spline fails
                ax2.plot(dates, mood_values, color="#F472B6", marker="o", linewidth=3, linestyle="-", label="Sentiment", zorder=4)
        else:
             ax2.plot(dates, mood_values, color="#F472B6", marker="o", linewidth=3, linestyle="-", label="Sentiment", zorder=4)

        ax2.set_ylim(-100, 100)
        ax2.spines['top'].set_visible(False)
        ax2.spines['bottom'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.tick_params(axis='y', colors="#F472B6", labelsize=8)
        ax2.set_axisbelow(True) # Keep behind text

        # Styling (Remove Grid)
        self.ax.grid(False) 
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        
        self.ax.tick_params(axis='x', colors=self.colors["text_secondary"], labelsize=9)
        self.ax.tick_params(axis='y', colors=self.colors["text_secondary"], labelsize=9)
        
        # Add labels on top of bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                self.ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.1f}' if isinstance(height, float) else f'{height}',
                        ha='center', va='bottom', color=self.colors["text_primary"], fontsize=9, fontweight='bold')

        self.chart_canvas.draw()

    def render_cards(self, data):
        for widget in self.cards_container.winfo_children():
            widget.destroy()
            
        if not data:
            data = {"sleep": 0, "energy": 0, "work": 0} # Empty state
            
        self.create_stat_card(self.cards_container, "Sleep Goal", f"{data['sleep']}h", data['sleep']/8, "#8B5CF6")
        self.create_stat_card(self.cards_container, "Energy Level", f"{data['energy']}/10", data['energy']/10, "#F59E0B")
        self.create_stat_card(self.cards_container, "Work Balance", f"{data['work']}h", min(data['work']/10, 1.0), "#10B981")

    def create_stat_card(self, parent, title, value_text, fraction, color):
        """Creates a card with a Circular Progress Ring"""
        card = tk.Frame(parent, bg=self.colors["surface"], width=280, height=200)
        card.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        card.pack_propagate(False)
        
        # Title
        tk.Label(card, text=title, font=("Segoe UI", 11), bg=self.colors["surface"], fg=self.colors["text_secondary"]).pack(pady=(15, 5))
        
        # Canvas for Circle
        canvas_size = 120
        canvas = tk.Canvas(card, width=canvas_size, height=canvas_size, bg=self.colors["surface"], highlightthickness=0)
        canvas.pack(pady=5)
        
        # Draw Circle
        x, y, r = canvas_size/2, canvas_size/2, 45
        width = 10
        
        # Background Ring
        canvas.create_oval(x-r, y-r, x+r, y+r, outline=self.colors["bg_tertiary"], width=width)
        
        # Foreground Ring (Arc)
        # Tkinter arc starts at 3 o'clock (0), goes counter-clockwise.
        # We want start at 12 o'clock (90) and go clockwise (negative extent).
        # Cap at 359.9 to avoid Tkinter treating 360 as 0
        extent = -(min(fraction, 0.9999) * 360) 
        if fraction > 1.0: extent = -359.9
        if fraction > 0:
            canvas.create_arc(x-r, y-r, x+r, y+r, start=90, extent=extent, style=tk.ARC, outline=color, width=width)
            
        # Center Text
        canvas.create_text(x, y, text=value_text, font=("Segoe UI", 16, "bold"), fill=self.colors["text_primary"])
        
        # Label for 'Sentiment' Legend if needed, but not here.


    def render_journal_text(self, data):
        for widget in self.entry_container.winfo_children():
            widget.destroy()
            
        tk.Label(self.entry_container, text="📝 Journal Entry", font=("Segoe UI", 16, "bold"), 
                bg=self.colors["surface"], fg=self.colors["text_primary"]).pack(anchor="w", pady=(0, 10))
        
        text = data['content'] if data else "No entry for this day."
        color = self.colors["text_primary"] if data else self.colors["text_secondary"]
        
        tk.Label(self.entry_container, text=text, font=("Segoe UI", 12), wraplength=850, justify="left",
                bg=self.colors["surface"], fg=color).pack(anchor="w")
