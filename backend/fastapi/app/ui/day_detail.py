# app/ui/day_detail.py
"""Day Detail Popup - Shows detailed graphical breakdown of a single journal entry"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import logging

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib not available for Day Detail charts")


class DayDetailPopup:
    """Popup window showing detailed graphical breakdown of a single journal entry"""
    
    def __init__(self, parent, entry, colors, i18n=None):
        """
        Initialize Day Detail Popup
        
        Args:
            parent: Parent tkinter widget
            entry: JournalEntry object
            colors: Theme colors dictionary
            i18n: Optional i18n manager
        """
        self.entry = entry
        self.colors = colors
        self.i18n = i18n
        
        # Create popup window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Day Detail - {self._format_date()}")
        self.window.geometry("700x800")
        self.window.configure(bg=colors.get("bg", "#f5f5f5"))
        
        # Make it modal-like
        self.window.transient(parent)
        self.window.grab_set()
        
        self._render()
    
    def _format_date(self):
        """Format entry date for display"""
        try:
            dt = datetime.strptime(str(self.entry.entry_date).split('.')[0], "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%B %d, %Y")
        except:
            return str(self.entry.entry_date)
    
    def _render(self):
        """Render the popup content"""
        colors = self.colors
        
        # --- Scrollable Container (Hidden scrollbar - mousewheel only) ---
        canvas = tk.Canvas(self.window, bg=colors.get("bg", "#f5f5f5"), highlightthickness=0)
        main_frame = tk.Frame(canvas, bg=colors.get("bg", "#f5f5f5"))
        
        main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.pack(fill="both", expand=True)
        
        # Enable mousewheel scrolling (scoped to this canvas only)
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass  # Canvas may be destroyed
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        # --- Header ---
        header = tk.Frame(main_frame, bg=colors.get("surface", "#fff"), pady=15)
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        date_str = self._format_date()
        tk.Label(header, text=f"📅 {date_str}", 
                font=("Segoe UI", 18, "bold"), 
                bg=colors.get("surface", "#fff"), 
                fg=colors.get("text_primary", "#000")).pack(anchor="w", padx=15)
        
        # --- Metric Cards Row ---
        self._render_metric_cards(main_frame)
        
        # --- Gauge Charts ---
        if MATPLOTLIB_AVAILABLE:
            self._render_gauge_charts(main_frame)
        
        # --- Satisfaction Factors Analysis ---
        self._render_satisfaction_factors(main_frame)
        
        # --- Daily Schedule ---
        self._render_section(main_frame, "🗓️ Daily Schedule", 
                            getattr(self.entry, 'daily_schedule', '') or "No schedule recorded")
        
        # --- Stress Triggers ---
        self._render_section(main_frame, "⚠️ Stress Triggers", 
                            getattr(self.entry, 'stress_triggers', '') or "None noted")
        
        # --- Journal Content ---
        self._render_section(main_frame, "💭 Journal Entry", 
                            self.entry.content or "No content")
        
        # --- AI Insight ---
        self._render_ai_insight(main_frame)
        
        # --- Close Button ---
        tk.Button(main_frame, text="Close", command=self.window.destroy,
                 font=("Segoe UI", 11), bg=colors.get("primary", "#8B5CF6"), fg="white",
                 relief="flat", padx=20, pady=8).pack(pady=20)
    
    def _render_metric_cards(self, parent):
        """Render the top metric cards"""
        colors = self.colors
        
        cards_frame = tk.Frame(parent, bg=colors.get("bg", "#f5f5f5"))
        cards_frame.pack(fill="x", padx=15, pady=10)
        
        def create_card(title, value, unit, color):
            card = tk.Frame(cards_frame, bg=colors.get("surface", "#fff"), bd=0)
            card.pack(side="left", expand=True, fill="both", padx=5, pady=5)
            
            # Shadow effect
            shadow = tk.Frame(card, bg="#e0e0e0")
            shadow.pack(fill="both", expand=True, padx=(0,2), pady=(0,2))
            
            inner = tk.Frame(shadow, bg=colors.get("surface", "#fff"))
            inner.pack(fill="both", expand=True)
            
            tk.Label(inner, text=title, font=("Segoe UI", 10), 
                    bg=colors.get("surface", "#fff"), 
                    fg=colors.get("text_secondary", "#666")).pack(pady=(12, 2))
            tk.Label(inner, text=str(value), font=("Segoe UI", 24, "bold"), 
                    bg=colors.get("surface", "#fff"), fg=color).pack()
            tk.Label(inner, text=unit, font=("Segoe UI", 9), 
                    bg=colors.get("surface", "#fff"), 
                    fg=colors.get("text_secondary", "#666")).pack(pady=(0, 12))
        
        # Create cards for each metric
        sleep = self.entry.sleep_hours or 0
        energy = self.entry.energy_level or 0
        stress = self.entry.stress_level or 0
        
        create_card("💤 Sleep", f"{sleep:.1f}", "hours", 
                   "#8B5CF6" if sleep >= 7 else "#EF4444")
        create_card("⚡ Energy", f"{energy}", "/10", 
                   "#22C55E" if energy >= 7 else "#F59E0B")
        create_card("😰 Stress", f"{stress}", "/10", 
                   "#EF4444" if stress >= 7 else "#22C55E")
    
    def _render_gauge_charts(self, parent):
        """Render matplotlib gauge charts"""
        colors = self.colors
        
        chart_frame = tk.Frame(parent, bg=colors.get("surface", "#fff"))
        chart_frame.pack(fill="x", padx=15, pady=10)
        
        fig = Figure(figsize=(9, 3), dpi=100, facecolor=colors.get("surface", "#fff"))
        
        # --- Stress Gauge (Left) ---
        ax1 = fig.add_subplot(131)
        stress = self.entry.stress_level or 0
        self._draw_gauge(ax1, stress, 10, "Stress Level", 
                        cmap_name='RdYlGn_r')
        
        # --- Screen Time Bar (Center) ---
        ax2 = fig.add_subplot(132)
        screen_mins = self.entry.screen_time_mins or 0
        self._draw_screen_bar(ax2, screen_mins)
        
        # --- Sleep Arc (Right) ---
        ax3 = fig.add_subplot(133)
        sleep = self.entry.sleep_hours or 0
        self._draw_gauge(ax3, sleep, 10, "Sleep Hours", 
                        cmap_name='RdYlGn', ideal_zone=(7, 9))
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", pady=10)
    
    def _draw_gauge(self, ax, value, max_val, title, cmap_name='RdYlGn', ideal_zone=None):
        """Draw a semi-circular gauge"""
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Semicircle background
        theta = np.linspace(0, np.pi, 100)
        r = 1
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        
        # Color gradient based on value
        cmap = plt.get_cmap(cmap_name)
        norm_val = value / max_val
        color = cmap(norm_val)
        
        # Draw arc
        ax.fill_between(x, 0, y, alpha=0.3, color='#e0e0e0')
        
        # Draw filled portion
        fill_angle = np.pi * norm_val
        theta_fill = np.linspace(0, fill_angle, 50)
        x_fill = r * np.cos(theta_fill)
        y_fill = r * np.sin(theta_fill)
        ax.fill_between(x_fill, 0, y_fill, alpha=0.8, color=color)
        
        # Value text
        ax.text(0, 0.3, f"{value:.1f}" if isinstance(value, float) else str(value), 
               ha='center', va='center', fontsize=20, fontweight='bold')
        ax.text(0, -0.1, f"/ {max_val}", ha='center', va='center', fontsize=10, color='#666')
        ax.set_title(title, fontsize=11, fontweight='bold', pad=5)
    
    def _draw_screen_bar(self, ax, screen_mins):
        """Draw a horizontal bar for screen time"""
        ax.axis('off')
        
        max_mins = 600  # 10 hours max
        hours = screen_mins / 60
        pct = min(screen_mins / max_mins, 1.0)
        
        # Bar background
        ax.barh(0, 1, height=0.3, color='#e0e0e0', left=0)
        
        # Filled bar (color based on value)
        color = '#22C55E' if hours < 4 else '#F59E0B' if hours < 6 else '#EF4444'
        ax.barh(0, pct, height=0.3, color=color, left=0)
        
        # Recommended marker at 4h
        recommended_pct = 240 / max_mins
        ax.axvline(x=recommended_pct, color='#3B82F6', linestyle='--', linewidth=2)
        ax.text(recommended_pct, 0.25, '4h (rec)', ha='center', va='bottom', fontsize=8, color='#3B82F6')
        
        # Value text
        ax.text(0.5, -0.25, f"{hours:.1f} hours", ha='center', va='top', fontsize=14, fontweight='bold')
        ax.set_title("📱 Screen Time", fontsize=11, fontweight='bold', pad=10)
        ax.set_xlim(0, 1.1)
        ax.set_ylim(-0.5, 0.5)
    
    def _render_section(self, parent, title, content):
        """Render a text section"""
        colors = self.colors
        
        section = tk.Frame(parent, bg=colors.get("surface", "#fff"))
        section.pack(fill="x", padx=15, pady=5)
        
        tk.Label(section, text=title, font=("Segoe UI", 12, "bold"),
                bg=colors.get("surface", "#fff"), 
                fg=colors.get("text_primary", "#000")).pack(anchor="w", padx=15, pady=(10, 5))
        content_lbl = tk.Label(section, text=content, font=("Segoe UI", 10),
                              bg=colors.get("surface", "#fff"), 
                              fg=colors.get("text_secondary", "#555"),
                              wraplength=600, justify="left")
        content_lbl.pack(anchor="w", padx=15, pady=(0, 10))
    
    def _render_satisfaction_factors(self, parent):
        """Render satisfaction factor analysis with visual bars"""
        colors = self.colors
        
        section = tk.Frame(parent, bg=colors.get("surface", "#fff"))
        section.pack(fill="x", padx=15, pady=10)
        
        tk.Label(section, text="📊 Factors Affecting Today's Wellbeing", font=("Segoe UI", 12, "bold"),
                bg=colors.get("surface", "#fff"), 
                fg=colors.get("text_primary", "#000")).pack(anchor="w", padx=15, pady=(10, 10))
        
        # Calculate factor impacts
        factors = []
        stress = self.entry.stress_level or 0
        sleep = self.entry.sleep_hours or 0
        screen = (self.entry.screen_time_mins or 0) / 60
        energy = self.entry.energy_level or 0
        work = getattr(self.entry, 'work_hours', 0) or 0
        
        # Stress impact (inverted: high stress = negative impact)
        stress_impact = (10 - stress) * 10  # 0-100 scale
        factors.append(("Stress Level", stress_impact, "#EF4444" if stress > 6 else "#22C55E", f"{stress}/10"))
        
        # Sleep impact
        sleep_impact = min(sleep / 8 * 100, 100)
        factors.append(("Sleep Quality", sleep_impact, "#8B5CF6" if sleep >= 7 else "#9333EA", f"{sleep:.1f}h"))
        
        # Screen time impact (inverted: high screen = negative)
        screen_impact = max(0, 100 - (screen / 6 * 100))
        factors.append(("Screen Balance", screen_impact, "#3B82F6" if screen < 4 else "#F97316", f"{screen:.1f}h"))
        
        # Energy impact
        energy_impact = energy * 10
        factors.append(("Energy Level", energy_impact, "#22C55E" if energy >= 7 else "#F59E0B", f"{energy}/10"))
        
        # Work-life balance (moderate work is good)
        work_impact = 100 if 6 <= work <= 9 else max(0, 100 - abs(work - 8) * 15)
        factors.append(("Work Balance", work_impact, "#0EA5E9" if 6 <= work <= 9 else "#DC2626", f"{work:.1f}h"))
        
        # Draw factor bars
        for name, impact, color, value in factors:
            row = tk.Frame(section, bg=colors.get("surface", "#fff"))
            row.pack(fill="x", padx=15, pady=3)
            
            # Label
            tk.Label(row, text=name, font=("Segoe UI", 10), width=15, anchor="w",
                    bg=colors.get("surface", "#fff"), 
                    fg=colors.get("text_secondary", "#666")).pack(side="left")
            
            # Progress bar container
            bar_bg = tk.Frame(row, bg="#e0e0e0", height=12, width=200)
            bar_bg.pack(side="left", padx=5)
            bar_bg.pack_propagate(False)
            
            # Filled bar
            bar_fill = tk.Frame(bar_bg, bg=color, height=12, width=int(impact * 2))
            bar_fill.pack(side="left", fill="y")
            
            # Value
            tk.Label(row, text=value, font=("Segoe UI", 9, "bold"),
                    bg=colors.get("surface", "#fff"), fg=color).pack(side="left", padx=5)
    
    def _render_ai_insight(self, parent):
        """Render AI insight for this specific day"""
        colors = self.colors
        
        # Generate insight based on this day's data
        insight = self._generate_day_insight()
        
        section = tk.Frame(parent, bg="#E0F2FE", bd=0)
        section.pack(fill="x", padx=15, pady=10)
        
        tk.Label(section, text="🧠 AI Insight for This Day", font=("Segoe UI", 12, "bold"),
                bg="#E0F2FE", fg="#0369A1").pack(anchor="w", padx=15, pady=(10, 5))
        
        tk.Label(section, text=insight, font=("Segoe UI", 10),
                bg="#E0F2FE", fg="#0369A1", wraplength=600, justify="left").pack(anchor="w", padx=15, pady=(0, 10))
    
    def _generate_day_insight(self):
        """Generate insight specific to this day's metrics"""
        stress = self.entry.stress_level or 0
        screen = self.entry.screen_time_mins or 0
        sleep = self.entry.sleep_hours or 0
        energy = self.entry.energy_level or 0
        triggers = getattr(self.entry, 'stress_triggers', '') or ''
        
        insights = []
        
        # Stress + Screen correlation
        if stress >= 7 and screen > 240:
            insights.append(f"Your stress was high ({stress}/10) with {screen//60}+ hours of screen time. Consider a digital detox on similar days.")
        
        # Sleep deficit
        if sleep < 6:
            insights.append(f"You only got {sleep:.1f}h of sleep. This likely impacted your energy ({energy}/10) and stress ({stress}/10).")
        
        # Good day recognition
        if stress < 5 and energy >= 7:
            insights.append("This was a balanced day! Take note of what you did differently and replicate it.")
        
        # Trigger awareness
        if triggers and stress >= 6:
            insights.append(f"Your noted triggers ('{triggers[:30]}...') correlated with elevated stress. Plan ahead for similar situations.")
        
        if not insights:
            return "This was a relatively balanced day with no major red flags detected."
        
        return " ".join(insights)
