# app/ui/dashboard.py - FIXED VERSION
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from collections import Counter
import matplotlib
matplotlib.use("Agg") # Prevent GUI mainloop conflicts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import json
import os
import sqlite3
import numpy as np
from typing import Optional, Dict, List, Any, Tuple

from app.i18n_manager import get_i18n
from app.models import Score, JournalEntry, SatisfactionRecord
from app.db import get_connection, safe_db_context
from app.analysis.time_based_analysis import time_analyzer

# Import emotional profile clustering
try:
    from app.ml.clustering import (
        EmotionalProfileClusterer,
        ClusteringVisualizer,
        EMOTIONAL_PROFILES,
        create_profile_clusterer,
        get_user_emotional_profile
    )
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False


class AnalyticsDashboard:
    def __init__(self, parent_root: tk.Widget, username: str, colors: Optional[Dict[str, str]] = None, theme: str = "light") -> None:
        self.parent_root = parent_root
        self.username = username
        self.benchmarks = self.load_benchmarks()
        self.i18n = get_i18n()
        self.theme = theme
        # Default colors for dark/light theme
        if colors:
            self.colors = colors
        else:
            self.colors = {
                "bg": "#0F172A" if theme == "dark" else "#F8FAFC",
                "surface": "#1E293B" if theme == "dark" else "#FFFFFF",
                "text_primary": "#F8FAFC" if theme == "dark" else "#0F172A",
                "text_secondary": "#94A3B8" if theme == "dark" else "#64748B",
                "primary": "#3B82F6",
                "border": "#334155" if theme == "dark" else "#E2E8F0"
            }

    def load_benchmarks(self) -> Optional[Dict[str, Any]]:
        """Load population benchmarks from JSON"""
        try:
            with open("app/benchmarks.json", "r") as f:
                return json.load(f)
        except Exception:
            return None
        
    def _create_scrollable_frame(self, parent: tk.Widget) -> tk.Frame:
        """Create a consistent scrollable frame for tabs (Hidden Scrollbar)"""
        container = tk.Frame(parent, bg=self.colors.get("bg", "#FFFFFF"))
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, bg=self.colors.get("bg", "#FFFFFF"), highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=self.colors.get("bg", "#FFFFFF"))
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Ensure inner frame fills width
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def _on_frame_configure(event):
            # Ensure canvas items exist before config
            if canvas.find_all():
                canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind("<Configure>", _on_frame_configure)
        
        # NO SCROLLBAR VISIBLE (User Request)
        canvas.pack(side="left", fill="both", expand=True)
        
        # Mousewheel binding - Conditional Scrolling
        def _on_mousewheel(event):
            try:
                # Only scroll if content exceeds view
                if scrollable_frame.winfo_reqheight() > canvas.winfo_height():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except: pass

        def _bind(e): 
            try: canvas.bind_all("<MouseWheel>", _on_mousewheel)
            except: pass
        def _unbind(e): 
            try: canvas.unbind_all("<MouseWheel>")
            except: pass
        
        # Bind only when hovering
        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)
        
        return scrollable_frame

    def render_dashboard(self) -> None:
        """Render dashboard embedded in parent_root"""
        colors = self.colors
        
        # Use parent_root directly as the container (Embedded Mode)
        dashboard = self.parent_root
        
        # Header (Hero Style for Web feel)
        header_frame = tk.Frame(dashboard, bg=colors["bg"], pady=20)
        header_frame.pack(fill="x", padx=20)
        
        tk.Label(header_frame, text=f"📊 {self.i18n.get('dashboard.analytics')}", 
                font=("Segoe UI", 24, "bold"), bg=colors["bg"], 
                fg=colors["text_primary"]).pack(side="left")

        # Configure ttk style for dark/light theme
        style = ttk.Style()
        if self.theme == "dark":
            style.configure("TNotebook", background=colors.get("bg", "#0F172A"))
            style.configure("TFrame", background=colors.get("bg", "#0F172A"))
            style.map("TNotebook.Tab", background=[("selected", colors.get("surface", "#1E293B"))], 
                      foreground=[("selected", colors.get("text_primary", "#fff"))])
        
        notebook = ttk.Notebook(dashboard)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))
        
        # Correlation Analysis Tab
        correlation_frame = ttk.Frame(notebook)
        notebook.add(correlation_frame, text="🔗 Correlation")
        self.show_correlation_analysis(correlation_frame)
            
        # EQ Trends
        eq_frame = ttk.Frame(notebook)
        notebook.add(eq_frame, text=self.i18n.get("dashboard.eq_trends_tab"))
        self.show_eq_trends(eq_frame)
        
        # Time-Based Analysis
        time_frame = ttk.Frame(notebook)
        notebook.add(time_frame, text=self.i18n.get("dashboard.time_based_tab"))
        self.show_time_based_analysis(time_frame)
        
        # Journal Analytics
        journal_frame = ttk.Frame(notebook)
        notebook.add(journal_frame, text=self.i18n.get("dashboard.journal_tab"))
        self.show_journal_analytics(journal_frame)
        
        # Insights
        insights_frame = ttk.Frame(notebook)
        notebook.add(insights_frame, text=self.i18n.get("dashboard.insights_tab"))
        self.show_insights(insights_frame)

        # Wellbeing Analytics (New Feature)
        wellbeing_frame = ttk.Frame(notebook)
        notebook.add(wellbeing_frame, text="🧘 Wellbeing")
        self.show_wellbeing_analytics(wellbeing_frame)
        
        # Emotional Profile Clustering Tab
        if CLUSTERING_AVAILABLE:
            clustering_frame = ttk.Frame(notebook)
            notebook.add(clustering_frame, text="🧬 Emotional Profile")
            self.show_emotional_profile(clustering_frame)
        
        # Add Satisfaction Analytics Tab
        satisfaction_frame = ttk.Frame(notebook)
        notebook.add(satisfaction_frame, text="💼 Satisfaction")
        self.show_satisfaction_analytics(satisfaction_frame)

        # Progress Dashboard Tab
        progress_frame = ttk.Frame(notebook)
        notebook.add(progress_frame, text="📈 Progress")
        self.show_progress_dashboard(progress_frame)

    def show_wellbeing_analytics(self, parent: tk.Widget) -> None:
        """Show comprehensive health and wellbeing analytics (PR #7)"""
        parent = self._create_scrollable_frame(parent)
        
        # Get data including new PR #6 fields
        conn = get_connection()
        try:
            # Check if columns exist first to avoid errors during dev
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(journal_entries)")
            columns = [c[1] for c in cursor.fetchall()]
            
            if 'screen_time_mins' not in columns:
                tk.Label(parent, text="Database schema update required (Missing v2 columns)", fg="red").pack()
                return

            query = """
                SELECT entry_date, sleep_hours, energy_level, stress_level, screen_time_mins 
                FROM journal_entries 
                WHERE username = ? 
                ORDER BY entry_date
            """
            cursor.execute(query, (self.username,))
            data = cursor.fetchall()
        finally:
            conn.close()

        if not data:
            tk.Label(parent, text=self.i18n.get("journal.no_entries"), font=("Segoe UI", 12)).pack(pady=50)
            return

        # Parse data
        dates = [datetime.strptime(row[0].split(' ')[0], "%Y-%m-%d") for row in data]
        sleep = [row[1] if row[1] is not None else 0 for row in data]
        energy = [row[2] if row[2] is not None else 0 for row in data]
        stress = [row[3] if row[3] is not None else 0 for row in data]
        screen = [row[4] if row[4] is not None else 0 for row in data]
        
        # --- 1. Weekly Averages Cards ---
        cards_frame = tk.Frame(parent, bg=self.colors["bg"])
        cards_frame.pack(fill="x", padx=10, pady=10)
        
        def create_card(title, value, unit, color):
            f = tk.Frame(cards_frame, bg=self.colors["surface"], bd=1, relief="ridge")
            f.pack(side="left", expand=True, fill="both", padx=5)
            tk.Label(f, text=title, font=("Segoe UI", 10), bg=self.colors["surface"], fg=self.colors["text_secondary"]).pack(pady=(10,0))
            tk.Label(f, text=f"{value:.1f}", font=("Segoe UI", 20, "bold"), bg=self.colors["surface"], fg=color).pack()
            tk.Label(f, text=unit, font=("Segoe UI", 8), bg=self.colors["surface"], fg=self.colors["text_secondary"]).pack(pady=(0,10))

        avg_stress = sum(stress)/len(stress) if stress else 0
        avg_screen = sum(screen)/len(screen) if screen else 0
        avg_sleep = sum(sleep)/len(sleep) if sleep else 0
        
        create_card("Avg Stress", avg_stress, "/ 10", "#EF4444" if avg_stress > 7 else "#22C55E")
        create_card("Screen Time", avg_screen/60, "hours/day", "#F59E0B" if avg_screen > 240 else "#3B82F6")
        create_card("Avg Sleep", avg_sleep, "hours", "#8B5CF6")

        # --- 2. Matplotlib Visualization (Modern Style) ---
        viz_frame = tk.Frame(parent, bg=self.colors["bg"])
        viz_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        fig = Figure(figsize=(10, 8), dpi=100, facecolor=self.colors["bg"])
        
        # Plot 1: Wellbeing Trends (Multi-line with modern styling)
        ax1 = fig.add_subplot(211)
        ax1.set_facecolor(self.colors.get("surface", "#fff"))
        
        x_vals = range(len(dates))
        ax1.plot(x_vals, stress, 'o-', color='#EF4444', label='🔴 Stress', linewidth=2.5, markersize=8)
        ax1.plot(x_vals, energy, 's-', color='#22C55E', label='⚡ Energy', linewidth=2.5, markersize=8)
        ax1.plot(x_vals, sleep, '^-', color='#8B5CF6', label='💤 Sleep (hrs)', linewidth=2.5, markersize=8)
        
        ax1.set_title('📊 Wellbeing Trends Over Time', fontsize=14, fontweight='bold', color=self.colors.get("text_primary", "#000"), pad=10)
        ax1.legend(loc='upper right', framealpha=0.9, fontsize=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_ylabel('Value', fontsize=10, color=self.colors.get("text_secondary", "#666"))
        ax1.tick_params(colors=self.colors.get("text_secondary", "#666"))
        for spine in ax1.spines.values(): 
            spine.set_visible(False)

        # Plot 2: Stress vs Screen Time (Scatter with enhanced colors)
        ax2 = fig.add_subplot(212)
        ax2.set_facecolor(self.colors.get("surface", "#fff"))
        
        # Color points by Energy level with a vibrant colormap
        sc = ax2.scatter(screen, stress, c=energy, cmap='RdYlGn', s=150, alpha=0.85, edgecolors='white', linewidths=1.5)
        ax2.set_xlabel('📱 Screen Time (mins)', fontsize=11, color=self.colors.get("text_secondary", "#666"))
        ax2.set_ylabel('😰 Stress Level', fontsize=11, color=self.colors.get("text_secondary", "#666"))
        ax2.set_title('📈 Stress vs. Screen Time Correlation', fontsize=14, fontweight='bold', color=self.colors.get("text_primary", "#000"), pad=10)
        
        cbar = fig.colorbar(sc, ax=ax2, shrink=0.8)
        cbar.set_label('⚡ Energy', fontsize=10)
        
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.tick_params(colors=self.colors.get("text_secondary", "#666"))
        for spine in ax2.spines.values(): 
            spine.set_visible(False)
        
        fig.tight_layout(pad=2.0)
        
        canvas = FigureCanvasTkAgg(fig, viz_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
    def show_satisfaction_analytics(self, parent):
        """Show satisfaction analytics"""
        parent = self._create_scrollable_frame(parent)
        # Fetch satisfaction data
        try:
            with safe_db_context() as session:
                records = session.query(SatisfactionRecord).filter(
                    SatisfactionRecord.username == self.username
                ).order_by(SatisfactionRecord.timestamp.desc()).all()
                
                if not records:
                    tk.Label(parent, 
                            text="No satisfaction data available.\n\n"
                                 "Complete a satisfaction survey to see your trends!",
                            font=("Arial", 14)).pack(pady=50)
                    return
                
                # Title
                tk.Label(parent, 
                        text="📊 Work/Study Satisfaction Trends",
                        font=("Arial", 16, "bold")).pack(pady=10)
                
                # Overall stats
                stats_frame = tk.Frame(parent, bg="#f0f9ff", relief=tk.RIDGE, bd=2)
                stats_frame.pack(fill="x", padx=20, pady=10)
                
                avg_score = sum(r.satisfaction_score for r in records) / len(records)
                latest = records[0].satisfaction_score
                
                tk.Label(stats_frame, 
                        text=f"Latest Score: {latest}/10 | Average: {avg_score:.1f}/10 | Total Surveys: {len(records)}",
                        font=("Arial", 12, "bold"),
                        bg="#f0f9ff").pack(pady=10)
                
                # Create matplotlib chart
                fig = Figure(figsize=(8, 4), dpi=100)
                ax = fig.add_subplot(111)
                
                # Plot satisfaction scores over time
                dates = [datetime.fromisoformat(r.timestamp) for r in records]
                scores = [r.satisfaction_score for r in records]
                
                ax.plot(dates, scores, 'o-', color='#8B5CF6', linewidth=2, markersize=8)
                ax.fill_between(dates, scores, alpha=0.2, color='#8B5CF6')
                ax.set_xlabel('Date')
                ax.set_ylabel('Satisfaction Score (1-10)')
                ax.set_title('Satisfaction Trend Over Time')
                ax.grid(True, alpha=0.3)
                
                # Format x-axis dates
                fig.autofmt_xdate()
                
                # Embed in tkinter
                canvas = FigureCanvasTkAgg(fig, parent)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
                
                # Factors analysis
                factors_frame = tk.Frame(parent)
                factors_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
                
                tk.Label(factors_frame,
                        text="📈 Top Factors Affecting Your Satisfaction",
                        font=("Arial", 14, "bold")).pack(anchor="w", pady=10)
                
                # Analyze common factors
                positive_counts = {}
                negative_counts = {}
                
                for record in records:
                    if record.positive_factors:
                        factors = json.loads(record.positive_factors)
                        for factor in factors:
                            positive_counts[factor] = positive_counts.get(factor, 0) + 1
                    
                    if record.negative_factors:
                        factors = json.loads(record.negative_factors)
                        for factor in factors:
                            negative_counts[factor] = negative_counts.get(factor, 0) + 1
                
                # Display top factors
                cols_frame = tk.Frame(factors_frame)
                cols_frame.pack(fill=tk.BOTH, expand=True)
                
                # Positive factors column
                pos_frame = tk.Frame(cols_frame, relief=tk.GROOVE, bd=1)
                pos_frame.pack(side="left", fill=tk.BOTH, expand=True, padx=(0, 5))
                
                tk.Label(pos_frame, text="✅ Strengths", 
                        font=("Arial", 12, "bold")).pack(pady=10)
                
                for factor, count in sorted(positive_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                    percentage = (count / len(records)) * 100
                    tk.Label(pos_frame, 
                            text=f"• {factor} ({percentage:.0f}% of surveys)",
                            font=("Arial", 10)).pack(anchor="w", padx=10, pady=2)
                
                # Negative factors column
                neg_frame = tk.Frame(cols_frame, relief=tk.GROOVE, bd=1)
                neg_frame.pack(side="right", fill=tk.BOTH, expand=True, padx=(5, 0))
                
                tk.Label(neg_frame, text="⚠️ Challenges", 
                        font=("Arial", 12, "bold")).pack(pady=10)
                
                for factor, count in sorted(negative_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                    percentage = (count / len(records)) * 100
                    tk.Label(neg_frame, 
                            text=f"• {factor} ({percentage:.0f}% of surveys)",
                            font=("Arial", 10)).pack(anchor="w", padx=10, pady=2)
            
        except Exception as e:
            tk.Label(parent, 
                    text=f"Error loading satisfaction data: {str(e)}",
                    font=("Arial", 12), fg="red").pack(pady=50)
    
    # ========== NEW CORRELATION ANALYSIS METHOD ==========
    def show_correlation_analysis(self, parent):
        """Show correlation analysis between EQ scores"""
        parent = self._create_scrollable_frame(parent)
        # Title
        tk.Label(parent, text=self.i18n.get("dashboard.correlation_title"), 
                font=("Arial", 16, "bold")).pack(pady=10)
        
        # Description
        tk.Label(parent, 
                text=self.i18n.get("dashboard.correlation_desc"),
                font=("Arial", 11), wraplength=550).pack(pady=5)
        
        # Button to run analysis
        button_frame = tk.Frame(parent)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text=self.i18n.get("dashboard.run_analysis"), 
                 command=lambda: self.run_correlation(parent),
                 bg="#4CAF50", fg="white",
                 font=("Arial", 11, "bold")).pack()
        
        # Text area for results
        self.correlation_text = tk.Text(parent, wrap=tk.WORD, height=15, 
                                       font=("Arial", 11), state='disabled')
        self.correlation_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Visualization frame
        self.correlation_viz_frame = tk.Frame(parent)
        self.correlation_viz_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def run_correlation(self, parent):
        """Run correlation analysis"""
        try:
            # Clear previous content
            if self.correlation_text:
                self.correlation_text.configure(state='normal') # Enable for updates
                self.correlation_text.delete(1.0, tk.END)
            else:
                return
            
            # Clear previous visualization
            for widget in self.correlation_viz_frame.winfo_children():
                widget.destroy()
            
            # Get EQ scores
            conn = get_connection()
            cursor = conn.cursor()
            
            # First, check what columns exist in the scores table
            cursor.execute("PRAGMA table_info(scores)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Build query based on available columns
            if 'timestamp' in columns:
                cursor.execute("""
                    SELECT total_score, timestamp 
                    FROM scores 
                    WHERE username = ? 
                    ORDER BY timestamp
                """, (self.username,))
            else:
                cursor.execute("""
                    SELECT total_score, id 
                    FROM scores 
                    WHERE username = ? 
                    ORDER BY id
                """, (self.username,))
            
            data = cursor.fetchall()
            conn.close()
            
            if len(data) < 2:
                self.correlation_text.insert(tk.END, 
                    "⚠️ Need at least 2 EQ tests for correlation analysis.\n\n"
                    "Complete more tests and try again!")
                if self.correlation_text:
                     self.correlation_text.configure(state='disabled')
                return
            
            scores = [row[0] for row in data]
            
            # Start analysis
            self.correlation_text.insert(tk.END, "📊 **CORRELATION ANALYSIS RESULTS**\n")
            self.correlation_text.insert(tk.END, "="*60 + "\n\n")
            
            # Import numpy for calculations
            try:
                import numpy as np
                
                # Basic statistics
                self.correlation_text.insert(tk.END, "📈 **Basic Statistics:**\n")
                self.correlation_text.insert(tk.END, f"• Number of tests: {len(scores)}\n")
                self.correlation_text.insert(tk.END, f"• Average score: {np.mean(scores):.2f}/25\n")
                self.correlation_text.insert(tk.END, f"• Best score: {max(scores)}\n")
                self.correlation_text.insert(tk.END, f"• Worst score: {min(scores)}\n")
                self.correlation_text.insert(tk.END, f"• Score range: {max(scores) - min(scores)} points\n\n")
                
                # Trend analysis
                if len(scores) >= 3:
                    x = np.arange(len(scores))
                    z = np.polyfit(x, scores, 1)
                    trend = z[0]
                    
                    self.correlation_text.insert(tk.END, "📈 **Trend Analysis:**\n")
                    self.correlation_text.insert(tk.END, f"• Trend slope: {trend:.3f} points per test\n")
                    
                    if trend > 0.5:
                        self.correlation_text.insert(tk.END, "✅ **Strong positive trend!** Consistent improvement!\n")
                    elif trend > 0.1:
                        self.correlation_text.insert(tk.END, "↗️ **Positive trend** - Gradual improvement\n")
                    elif trend < -0.5:
                        self.correlation_text.insert(tk.END, "📉 **Strong negative trend** - Review strategies\n")
                    elif trend < -0.1:
                        self.correlation_text.insert(tk.END, "↘️ **Negative trend** - Needs attention\n")
                    else:
                        self.correlation_text.insert(tk.END, "⚖️ **Stable performance**\n")
                    self.correlation_text.insert(tk.END, "\n")
                
                # Consistency analysis
                std_dev = np.std(scores)
                cv = (std_dev / np.mean(scores) * 100) if np.mean(scores) > 0 else 0
                
                self.correlation_text.insert(tk.END, "🎯 **Consistency Analysis:**\n")
                self.correlation_text.insert(tk.END, f"• Standard deviation: {std_dev:.2f}\n")
                self.correlation_text.insert(tk.END, f"• Coefficient of variation: {cv:.1f}%\n")
                
                if cv < 15:
                    self.correlation_text.insert(tk.END, "✅ **Excellent consistency** - Very stable scores\n")
                elif cv < 25:
                    self.correlation_text.insert(tk.END, "👍 **Good consistency** - Reliable performance\n")
                elif cv < 35:
                    self.correlation_text.insert(tk.END, "⚠️ **Moderate variation** - Some fluctuations\n")
                else:
                    self.correlation_text.insert(tk.END, "🔀 **High variation** - Inconsistent performance\n")
                self.correlation_text.insert(tk.END, "\n")
                
                # Create visualizations
                self.create_correlation_visualizations(scores)
                
            except ImportError:
                self.correlation_text.insert(tk.END, 
                    "⚠️ NumPy not installed. Install with: pip install numpy\n")
            
            self.correlation_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.correlation_text.insert(tk.END, "✅ **Analysis complete!**\n")
            
        except Exception as e:
            self.correlation_text.insert(tk.END, f"❌ **Error:** {str(e)}\n")
    
    def create_correlation_visualizations(self, scores):
        """Create visualizations for correlation analysis"""
        try:
            import numpy as np
            
            # Create figure
            fig = Figure(figsize=(10, 8))
            
            # Plot 1: Score trend
            ax1 = fig.add_subplot(221)
            x_values = range(1, len(scores) + 1)
            ax1.plot(x_values, scores, 'o-', color='#4CAF50', linewidth=2)
            ax1.set_title(self.i18n.get("dashboard.trend_title"), fontweight='bold')
            ax1.set_xlabel(self.i18n.get("dashboard.trend_xlabel"))
            ax1.set_ylabel(self.i18n.get("dashboard.trend_ylabel"))
            ax1.grid(True, alpha=0.3)
            
            # Add trend line if enough points
            if len(scores) >= 3:
                z = np.polyfit(x_values, scores, 1)
                p = np.poly1d(z)
                ax1.plot(x_values, p(x_values), "r--", alpha=0.5)
                ax1.text(0.05, 0.95, f'Trend: {z[0]:.2f}/test', 
                        transform=ax1.transAxes, fontsize=10,
                        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
            
            # Plot 2: Score distribution
            ax2 = fig.add_subplot(222)
            ax2.hist(scores, bins=5, color='#2196F3', edgecolor='black', alpha=0.7)
            ax2.set_title(self.i18n.get("dashboard.distribution_title"), fontweight='bold')
            ax2.set_xlabel(self.i18n.get("dashboard.distribution_xlabel"))
            ax2.set_ylabel(self.i18n.get("dashboard.distribution_ylabel"))
            ax2.grid(True, alpha=0.3)
            
            # Plot 3: Moving average
            ax3 = fig.add_subplot(223)
            if len(scores) >= 3:
                window = min(3, len(scores))
                moving_avg = [np.mean(scores[max(0, i-window+1):i+1]) 
                             for i in range(len(scores))]
                ax3.plot(x_values, moving_avg, 's-', color='#9C27B0', linewidth=2)
                ax3.set_title(self.i18n.get("dashboard.moving_avg_title", window=window), fontweight='bold')
                ax3.set_xlabel(self.i18n.get("dashboard.trend_xlabel"))
                ax3.set_ylabel(self.i18n.get("dashboard.moving_avg_ylabel"))
                ax3.grid(True, alpha=0.3)
            
            # Plot 4: Performance comparison
            ax4 = fig.add_subplot(224)
            if len(scores) >= 4:
                half = len(scores) // 2
                positions = [self.i18n.get("dashboard.first_half"), self.i18n.get("dashboard.second_half")]
                averages = [np.mean(scores[:half]), np.mean(scores[half:])]
                colors = ['#FF9800', '#4CAF50']
                bars = ax4.bar(positions, averages, color=colors)
                ax4.set_title(self.i18n.get("dashboard.performance_title"), fontweight='bold')
                ax4.set_ylabel(self.i18n.get("dashboard.performance_ylabel"))
                
                # Add value labels
                for bar, avg in zip(bars, averages):
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height,
                            f'{avg:.1f}', ha='center', va='bottom')
            
            fig.tight_layout()
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.correlation_viz_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Make read-only
            if self.correlation_text:
                 self.correlation_text.configure(state='disabled')
            
        except Exception as e:
            self.correlation_text.insert(tk.END, f"⚠️ Could not create visualizations: {str(e)}\n")
            if self.correlation_text:
                 self.correlation_text.configure(state='disabled')
    
    # ========== EXISTING METHODS (UPDATED) ==========
    def show_eq_trends(self, parent):
        """Show EQ score trends with matplotlib graph"""
        parent = self._create_scrollable_frame(parent)
        # Set colors
        colors = self.colors
        bg_color = colors.get("bg", "#F8FAFC")
        surface_color = colors.get("surface", "#FFFFFF")
        text_primary = colors.get("text_primary", "#0F172A")
        text_secondary = colors.get("text_secondary", "#64748B")
        
        # Configure parent
        # parent.configure(style="TFrame")
        
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT total_score, timestamp, id, sentiment_score 
            FROM scores 
            WHERE username = ? 
            ORDER BY id
            """, (self.username,))
            data = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching EQ trends: {e}")
            data = []
        finally:
            conn.close()
        
        if not data:
            tk.Label(parent, text="No EQ data available", font=("Arial", 14), bg=bg_color, fg=text_primary).pack(pady=50)
            return
        
        scores = [row[0] for row in data]
        sentiment_scores = [row[3] if len(row) > 3 else None for row in data]
        
        tk.Label(parent, text="📈 EQ Score Progress Over Time", 
                font=("Segoe UI", 16, "bold"), bg=bg_color, fg=text_primary).pack(pady=(15, 10))
        
        # Stats frame
        stats_frame = tk.Frame(parent, bg=surface_color, relief=tk.RIDGE, bd=1,
                              highlightbackground=colors.get("border", "#E2E8F0"), highlightthickness=1)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Create two columns for stats
        left_col = tk.Frame(stats_frame, bg=surface_color)
        left_col.pack(side=tk.LEFT, padx=30, pady=15, expand=True)
        
        right_col = tk.Frame(stats_frame, bg=surface_color)
        right_col.pack(side=tk.LEFT, padx=30, pady=15, expand=True)
        
        tk.Label(left_col, text=f"Total Attempts: {len(scores)}", 
                font=("Segoe UI", 11, "bold"), bg=surface_color, fg=text_primary).pack(anchor="w", pady=2)
        tk.Label(left_col, text=f"Latest Score: {scores[-1]}", 
                font=("Segoe UI", 11), bg=surface_color, fg=text_primary).pack(anchor="w", pady=2)
        tk.Label(left_col, text=f"Best Score: {max(scores)}", 
                font=("Segoe UI", 11), bg=surface_color, fg="#22C55E").pack(anchor="w", pady=2)
        
        tk.Label(right_col, text=f"First Score: {scores[0]}", 
                font=("Segoe UI", 11), bg=surface_color, fg=text_primary).pack(anchor="w", pady=2)
        tk.Label(right_col, text=f"Average Score: {sum(scores)/len(scores):.1f}", 
                font=("Segoe UI", 11), bg=surface_color, fg=text_primary).pack(anchor="w", pady=2)
        
        if len(scores) > 1:
            improvement = scores[-1] - scores[0]
            improvement_pct = (improvement / scores[0]) * 100 if scores[0] != 0 else 0
            color = "#22C55E" if improvement > 0 else "#EF4444" if improvement < 0 else "#3B82F6"
            symbol = "↑" if improvement > 0 else "↓" if improvement < 0 else "→"
            tk.Label(right_col, text=f"Progress: {symbol} {improvement:+d} ({improvement_pct:+.1f}%)", 
                    font=("Segoe UI", 11, "bold"), bg=surface_color, fg=color).pack(anchor="w", pady=2)
        
        # Create matplotlib figure
        plt.style.use('dark_background' if self.theme == 'dark' else 'default')
        if self.theme == 'dark':
            fig_bg = '#1E293B' # Surface color for dark mode chart
            plot_bg = '#1E293B'
            text_color = '#F8FAFC'
            grid_color = '#334155'
        else:
            fig_bg = '#F8FAFC'
            plot_bg = '#F8FAFC'
            text_color = '#0F172A'
            grid_color = '#E2E8F0'

        fig = Figure(figsize=(6, 4), dpi=80, facecolor=fig_bg)
        ax1 = fig.add_subplot(111)
        ax1.set_facecolor(plot_bg)
        
        # Plot EQ Score
        l1, = ax1.plot(range(1, len(scores) + 1), scores, 
               marker='o', linestyle='-', linewidth=2, markersize=8,
               color='#22C55E', markerfacecolor='#22C55E', 
               markeredgewidth=2, markeredgecolor='white', label="EQ Score")
        
        ax1.set_xlabel('Attempt Number', fontsize=11, fontweight='bold', color=text_color)
        ax1.set_ylabel('EQ Score', fontsize=11, fontweight='bold', color='#22C55E')
        ax1.tick_params(axis='y', labelcolor='#22C55E', colors=text_color)
        ax1.tick_params(axis='x', colors=text_color)
        ax1.set_title('EQ Score & Emotional Sentiment Trends', fontsize=12, fontweight='bold', pad=15, color=text_color)
        ax1.grid(True, alpha=0.3, linestyle='--', color=grid_color)
        ax1.set_xticks(range(1, len(scores) + 1))
        
        for spine in ax1.spines.values():
            spine.set_color(grid_color)
        
        # Plot Sentiment Score (Secondary Axis)
        if sentiment_scores and any(s is not None and s != 0 for s in sentiment_scores):
            ax2 = ax1.twinx()
            # Filter out Nones for plotting
            valid_indices = [i for i, s in enumerate(sentiment_scores) if s is not None]
            valid_x = [i + 1 for i in valid_indices]
            valid_y = [sentiment_scores[i] for i in valid_indices]
            
            l2, = ax2.plot(valid_x, valid_y, 
                     marker='s', linestyle='--', linewidth=2, markersize=6,
                     color='#F59E0B', markerfacecolor='#F59E0B',
                     markeredgewidth=2, markeredgecolor='white', label="Sentiment")
                     
            ax2.set_ylabel('Sentiment Score (-100 to +100)', fontsize=11, fontweight='bold', color='#F59E0B')
            ax2.tick_params(axis='y', labelcolor='#F59E0B', colors=text_color)
            ax2.set_ylim(-110, 110)
            
            for spine in ax2.spines.values():
                spine.set_color(grid_color)
            
            # Combined Legend
            lines = [l1, l2]
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='upper left')
        else:
            ax1.legend(loc='upper left')
        
        fig.tight_layout()
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Add trend analysis
        if len(scores) >= 3:
            trend_frame = tk.Frame(parent, bg="#e3f2fd", relief=tk.RIDGE, bd=2)
            trend_frame.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Label(trend_frame, text="📊 Trend Analysis", 
                    font=("Arial", 11, "bold"), bg="#e3f2fd").pack(pady=5)
            
            recent_trend = sum(scores[-3:]) / 3 - sum(scores[:3]) / 3
            if recent_trend > 5:
                trend_msg = "🎉 Strong upward trend! You're making excellent progress!"
            elif recent_trend > 0:
                trend_msg = "📈 Positive trend! Keep up the good work!"
            elif recent_trend < -5:
                trend_msg = "💪 Scores declining. Focus on emotional awareness practices."
            elif recent_trend < 0:
                trend_msg = "📉 Slight decline. Consider reviewing past strategies."
            else:
                trend_msg = "⚖️ Stable scores. Ready for the next breakthrough!"
            
            tk.Label(trend_frame, text=trend_msg, 
                    font=("Arial", 10), bg="#e3f2fd", wraplength=500).pack(pady=5)

    def show_time_based_analysis(self, parent):
        """Show time-based analysis of responses for returning users"""
        tk.Label(parent, text="⏰ Time-Based Response Analysis", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        # Get score trends
        trend_data = time_analyzer.analyze_score_trends(self.username)
        
        if "error" in trend_data:
            tk.Label(parent, text="No data available for time-based analysis", 
                    font=("Arial", 12)).pack(pady=50)
            return
        
        # Create scrollable frame for stats
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Helper to create styled section
        def create_styled_text(parent_frame, bg_color):
            t = tk.Text(parent_frame, height=7, width=50, font=("Arial", 10), 
                       bg=bg_color, fg="black", relief=tk.FLAT)
            t.tag_config("label", foreground="#555555", font=("Arial", 10, "bold"))
            t.tag_config("value", foreground="#000000", font=("Arial", 10))
            t.tag_config("highlight", foreground="#2E7D32", font=("Arial", 10, "bold")) # Green
            t.tag_config("alert", foreground="#C62828", font=("Arial", 10, "bold")) # Red
            t.tag_config("info", foreground="#1565C0", font=("Arial", 10, "bold")) # Blue
            return t

        def insert_pair(text_widget, label, value, value_tag="value"):
            text_widget.insert(tk.END, f"{label}: ", "label")
            text_widget.insert(tk.END, f"{value}\n", value_tag)
        
        # Stats Frame 1 - Basic Statistics
        stats1_frame = tk.Frame(scrollable_frame, bg="#f0f0f0", relief=tk.RIDGE, bd=2)
        stats1_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(stats1_frame, text="📊 Score Statistics", 
                font=("Arial", 11, "bold"), bg="#f0f0f0", fg="black").pack(anchor="w", padx=10, pady=5)
        
        stats_text1 = create_styled_text(stats1_frame, "#f0f0f0")
        stats_text1.pack(padx=10, pady=5)
        
        insert_pair(stats_text1, "Total Attempts", trend_data.get('total_attempts', 0))
        insert_pair(stats_text1, "First Score", trend_data.get('first_score', 'N/A'))
        insert_pair(stats_text1, "Latest Score", trend_data.get('last_score', 'N/A'), "highlight")
        insert_pair(stats_text1, "Average Score", f"{trend_data.get('average_score', 0):.1f}")
        insert_pair(stats_text1, "Highest Score", trend_data.get('max_score', 'N/A'))
        insert_pair(stats_text1, "Lowest Score", trend_data.get('min_score', 'N/A'))
        insert_pair(stats_text1, "Score Std Dev", f"{trend_data.get('score_std_dev', 0):.2f}")
        stats_text1.config(state=tk.DISABLED)
        
        # Stats Frame 2 - Trend Information
        stats2_frame = tk.Frame(scrollable_frame, bg="#e3f2fd", relief=tk.RIDGE, bd=2)
        stats2_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(stats2_frame, text="📈 Trend Analysis", 
                font=("Arial", 11, "bold"), bg="#e3f2fd", fg="black").pack(anchor="w", padx=10, pady=5)
        
        stats_text2 = create_styled_text(stats2_frame, "#e3f2fd")
        stats_text2.config(height=5)
        stats_text2.pack(padx=10, pady=5)
        
        imp = trend_data.get('total_improvement', 0)
        imp_tag = "highlight" if imp > 0 else "alert" if imp < 0 else "value"
        
        insert_pair(stats_text2, "Total Improvement", f"{imp:+d} points", imp_tag)
        insert_pair(stats_text2, "Improvement %", f"{trend_data.get('improvement_percentage', 0):+.1f}%", imp_tag)
        insert_pair(stats_text2, "Trend Direction", trend_data.get('trend_direction', 'Unknown'), "info")
        insert_pair(stats_text2, "First Attempt", trend_data.get('first_attempt_date', 'N/A'))
        insert_pair(stats_text2, "Latest Attempt", trend_data.get('last_attempt_date', 'N/A'))
        stats_text2.config(state=tk.DISABLED)
        
        # Response Pattern Analysis
        response_patterns = time_analyzer.analyze_response_patterns_over_time(self.username)
        
        if "error" not in response_patterns:
            stats3_frame = tk.Frame(scrollable_frame, bg="#f5f5f5", relief=tk.RIDGE, bd=2)
            stats3_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(stats3_frame, text="🔄 Response Pattern Changes", 
                    font=("Arial", 11, "bold"), bg="#f5f5f5", fg="black").pack(anchor="w", padx=10, pady=5)
            
            stats_text3 = create_styled_text(stats3_frame, "#f5f5f5")
            stats_text3.config(height=4)
            stats_text3.pack(padx=10, pady=5)
            
            insert_pair(stats_text3, "Total Responses", response_patterns.get('total_responses', 0))
            insert_pair(stats_text3, "Unique Questions", response_patterns.get('unique_questions_answered', 0))
            insert_pair(stats_text3, "Overall Avg Response", f"{response_patterns.get('overall_average_response', 0):.2f}")
            insert_pair(stats_text3, "Consistency (Std Dev)", f"{response_patterns.get('overall_response_std_dev', 0):.2f}")
            stats_text3.config(state=tk.DISABLED)
        
        # Comparative Analysis (Last 30 days vs historical)
        comparative = time_analyzer.get_comparative_analysis(self.username, lookback_days=30)
        
        if "error" not in comparative:
            stats4_frame = tk.Frame(scrollable_frame, bg="#fff3e0", relief=tk.RIDGE, bd=2)
            stats4_frame.pack(fill=tk.X, padx=10, pady=5)
            
            tk.Label(stats4_frame, text="📅 Recent vs Historical (Last 30 Days)", 
                    font=("Arial", 11, "bold"), bg="#fff3e0", fg="black").pack(anchor="w", padx=10, pady=5)
            
            comp_text = create_styled_text(stats4_frame, "#fff3e0")
            comp_text.config(height=6)
            comp_text.pack(padx=10, pady=5)
            
            if "historical" in comparative:
                hist = comparative["historical"]
                insert_pair(comp_text, "Historical Avg", f"{hist.get('average_score', 0):.1f}")
                insert_pair(comp_text, "Historical Attempts", hist.get('attempts', 0))
                comp_text.insert(tk.END, "\n")
            
            if "recent" in comparative:
                recent = comparative["recent"]
                insert_pair(comp_text, "Recent Avg (30d)", f"{recent.get('average_score', 0):.1f}")
                insert_pair(comp_text, "Recent Attempts", recent.get('attempts', 0))
            
            if "performance_change" in comparative:
                change = comparative["performance_change"]
                change_pct = comparative.get("performance_change_percentage", 0)
                change_tag = "highlight" if change > 0 else "alert" if change < 0 else "value"
                symbol = "📈" if change > 0 else "📉" if change < 0 else "⚖️"
                
                comp_text.insert(tk.END, f"\n{symbol} Change: ", "label")
                comp_text.insert(tk.END, f"{change:+.1f} ({change_pct:+.1f}%)", change_tag)
            
            comp_text.config(state=tk.DISABLED)

    def show_journal_analytics(self, parent):
        """Show journal analytics"""
        parent = self._create_scrollable_frame(parent)
        conn = get_connection() # Use centralized connection logic
        cursor = conn.cursor()
        
        # Check if journal_entries table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='journal_entries'")
        if not cursor.fetchone():
            conn.close()
            tk.Label(parent, text="Journal feature not yet used", font=("Arial", 14)).pack(pady=50)
            return
        
        # Get journal data
        cursor.execute("""
            SELECT sentiment_score, emotional_patterns 
            FROM journal_entries 
            WHERE username = ? 
            ORDER BY id
        """, (self.username,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            tk.Label(parent, text="No journal entries found", font=("Arial", 14)).pack(pady=50)
            return
            
        tk.Label(parent, text="📝 Journal Analytics", font=("Arial", 14, "bold")).pack(pady=10)
        
        sentiments = [r[0] for r in rows if r[0] is not None]
        
        # Stats
        stats_frame = tk.Frame(parent)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(stats_frame, text=f"Total Entries: {len(rows)}", font=("Arial", 12)).pack(anchor="w")
        
        if sentiments:
            tk.Label(stats_frame, text=f"Avg Sentiment: {sum(sentiments)/len(sentiments):.1f}", 
                    font=("Arial", 12)).pack(anchor="w")
            tk.Label(stats_frame, text=f"Most Positive: {max(sentiments):.1f}", 
                    font=("Arial", 12)).pack(anchor="w")
        
        # Patterns
        patterns_frame = tk.Frame(parent)
        patterns_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(patterns_frame, text="Top Emotional Patterns:", 
                font=("Arial", 12, "bold")).pack(anchor="w")
        
        all_patterns = []
        for r in rows:
            if r[1]: # emotional_patterns
                all_patterns.extend(r[1].split('; '))
        
        pattern_counts = Counter(all_patterns)
        
        patterns_text = tk.Text(patterns_frame, height=6, font=("Arial", 11))
        patterns_text.pack(fill=tk.BOTH, expand=True)
        
        for pattern, count in pattern_counts.most_common(3):
            percentage = (count / len(rows)) * 100 if len(rows) > 0 else 0
            patterns_text.insert(tk.END, f"{pattern}: {count} times ({percentage:.1f}%)\n")
        
        patterns_text.config(state=tk.DISABLED)
        
    def show_insights(self, parent):
        """Show personalized insights"""
        parent = self._create_scrollable_frame(parent)
        tk.Label(parent, text="🔍 Your Insights", font=("Arial", 14, "bold")).pack(pady=10)
        
        insights_text = tk.Text(parent, wrap=tk.WORD, font=("Arial", 11), bg="#f8f9fa")
        insights_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        insights = self.generate_insights()
        
        for insight in insights:
            insights_text.insert(tk.END, f"• {insight}\n\n")
            
        insights_text.config(state=tk.DISABLED)
    
    # ========== EMOTIONAL PROFILE CLUSTERING TAB ==========
    def show_emotional_profile(self, parent):
        """Show emotional profile clustering analysis."""
        parent = self._create_scrollable_frame(parent)
        if not CLUSTERING_AVAILABLE:
            tk.Label(parent, text="❌ Clustering module not available", 
                    font=("Arial", 14)).pack(pady=50)
            return
        
        # Title
        tk.Label(parent, text="🧬 Your Emotional Profile", 
                font=("Arial", 16, "bold")).pack(pady=10)
        
        # Description
        tk.Label(parent, 
                text="Discover your emotional profile based on unsupervised learning analysis of your assessment patterns.",
                font=("Arial", 11), wraplength=600).pack(pady=5)
        
        # Results frame
        results_frame = tk.Frame(parent, bg="#f8f9fa", relief=tk.RIDGE, bd=2)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Load or compute profile
        try:
            profile = get_user_emotional_profile(self.username)
            
            if profile is None:
                tk.Label(results_frame, 
                        text="⚠️ Not enough data to determine your emotional profile yet.\n\n"
                             "Complete more assessments to unlock this feature!",
                        font=("Arial", 12), bg="#f8f9fa", fg="#666").pack(pady=50)
                return
            
            profile_info = profile.get('profile', {})
            
            # --- Sentiment-style summary card (compact) ---
            # Use avg_sentiment from features if available (scale -1..1 -> -100..100)
            avg_sent = 0
            try:
                avg_sent = float(profile.get('features', {}).get('avg_sentiment', 0))
            except Exception:
                avg_sent = 0

            sentiment_score = avg_sent * 100.0
            if sentiment_score > 20:
                sentiment_label = "Positive"
                sentiment_color = "#4CAF50"
            elif sentiment_score < -20:
                sentiment_label = "Negative"
                sentiment_color = "#E53935"
            else:
                sentiment_label = "Neutral/Balanced"
                sentiment_color = "#FFC107"

            card_bg = "#111111"
            card_fg = sentiment_color

            card_frame = tk.Frame(results_frame, bg=card_bg, relief=tk.RIDGE, bd=0)
            card_frame.pack(fill=tk.X, padx=20, pady=(10, 8))

            tk.Label(card_frame, text="Emotional Sentiment:",
                    font=("Arial", 12, "bold"), bg=card_bg, fg="#FFFFFF").pack(anchor="w", padx=12, pady=(10, 0))

            # Large score line
            score_text = f"{sentiment_score:+.1f} ({sentiment_label})"
            tk.Label(card_frame, text=score_text,
                    font=("Arial", 20, "bold"), bg=card_bg, fg=card_fg).pack(anchor="w", padx=12, pady=(4, 2))

            # Subtext
            subtext = "Your reflection shows balanced emotions."
            if sentiment_label == "Positive":
                subtext = "Your reflection shows positive emotional tone."
            elif sentiment_label == "Negative":
                subtext = "Your reflection indicates negative emotional tone; consider support."

            tk.Label(card_frame, text=subtext,
                    font=("Arial", 10, "italic"), bg=card_bg, fg="#DDDDDD").pack(anchor="w", padx=12, pady=(0, 10))

            # Quick actions
            action_frame = tk.Frame(card_frame, bg=card_bg)
            action_frame.pack(anchor="e", padx=12, pady=(0, 10))

            def _open_full_report():
                try:
                    clusterer = create_profile_clusterer()
                    visualizer = ClusteringVisualizer(clusterer)
                    report_text = visualizer.generate_profile_report(self.username)

                    rpt = tk.Toplevel(self.parent_root)
                    rpt.title("Emotional Profile Report")
                    txt = tk.Text(rpt, wrap=tk.WORD, font=("Courier", 10))
                    txt.insert(tk.END, report_text)
                    txt.config(state=tk.DISABLED)
                    txt.pack(fill=tk.BOTH, expand=True)
                except Exception as e:
                    tk.messagebox.showerror("Error", f"Could not open report: {e}")

            tk.Button(action_frame, text="See full profile report",
                      command=_open_full_report, bg="#333333", fg="#FFFFFF", padx=8, pady=4).pack()

            # Profile Header
            header_frame = tk.Frame(results_frame, bg="#f8f9fa")
            header_frame.pack(fill=tk.X, padx=20, pady=15)
            
            profile_emoji = profile_info.get('emoji', '🔍')
            profile_name = profile_info.get('name', 'Unknown')
            profile_color = profile_info.get('color', '#333333')
            
            tk.Label(header_frame, 
                    text=f"{profile_emoji} {profile_name}",
                    font=("Arial", 20, "bold"), bg="#f8f9fa", fg=profile_color).pack()
            
            # Confidence
            confidence = profile.get('confidence', 0) * 100
            tk.Label(header_frame, 
                    text=f"Confidence: {confidence:.1f}%",
                    font=("Arial", 11), bg="#f8f9fa", fg="#666").pack(pady=5)
            
            # Description
            desc_frame = tk.Frame(results_frame, bg="#ffffff", relief=tk.GROOVE, bd=1)
            desc_frame.pack(fill=tk.X, padx=20, pady=10)
            
            tk.Label(desc_frame, 
                    text=profile_info.get('description', ''),
                    font=("Arial", 11), bg="#ffffff", wraplength=550).pack(pady=15, padx=15)
            
            # Two-column layout for characteristics and recommendations
            content_frame = tk.Frame(results_frame, bg="#f8f9fa")
            content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # Characteristics column
            char_frame = tk.Frame(content_frame, bg="#e3f2fd", relief=tk.GROOVE, bd=1)
            char_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            tk.Label(char_frame, text="✨ Key Characteristics",
                    font=("Arial", 12, "bold"), bg="#e3f2fd").pack(pady=10)
            
            for char in profile_info.get('characteristics', []):
                tk.Label(char_frame, text=f"• {char}",
                        font=("Arial", 10), bg="#e3f2fd", 
                        wraplength=250, justify=tk.LEFT).pack(anchor="w", padx=15, pady=3)
            
            # Recommendations column
            rec_frame = tk.Frame(content_frame, bg="#e8f5e9", relief=tk.GROOVE, bd=1)
            rec_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
            tk.Label(rec_frame, text="💡 Recommendations",
                    font=("Arial", 12, "bold"), bg="#e8f5e9").pack(pady=10)
            
            for rec in profile_info.get('recommendations', []):
                tk.Label(rec_frame, text=f"→ {rec}",
                        font=("Arial", 10), bg="#e8f5e9",
                        wraplength=250, justify=tk.LEFT).pack(anchor="w", padx=15, pady=3)
            
            # Profile Distribution (All Profiles Overview)
            dist_frame = tk.Frame(results_frame, bg="#f8f9fa")
            dist_frame.pack(fill=tk.X, padx=20, pady=15)
            
            tk.Label(dist_frame, text="📊 All Emotional Profiles",
                    font=("Arial", 12, "bold"), bg="#f8f9fa").pack(pady=5)
            
            # Show all profiles as a legend
            profiles_row = tk.Frame(dist_frame, bg="#f8f9fa")
            profiles_row.pack()
            
            for pid, pinfo in EMOTIONAL_PROFILES.items():
                is_current = pid == profile.get('cluster_id')
                badge_bg = pinfo['color'] if is_current else "#cccccc"
                badge_fg = "white" if is_current else "#666666"
                
                badge = tk.Label(profiles_row, 
                               text=f"{pinfo['emoji']} {pinfo['name'][:15]}",
                               font=("Arial", 9, "bold" if is_current else "normal"),
                               bg=badge_bg, fg=badge_fg,
                               padx=8, pady=4, relief=tk.RAISED if is_current else tk.FLAT)
                badge.pack(side=tk.LEFT, padx=3)
            
        except Exception as e:
            tk.Label(results_frame, 
                    text=f"⚠️ Error loading profile: {str(e)}",
                    font=("Arial", 11), bg="#f8f9fa", fg="red").pack(pady=50)
        
    def generate_insights(self):
        """Generate insights"""
        insights = []
        
        scores = []
        test_sentiments = []
        journal_sentiments = []

        try:
            with safe_db_context() as session:
                # EQ and Sentiment insights from SCORES table
                eq_rows = session.query(Score.total_score, Score.sentiment_score)\
                    .filter_by(username=self.username)\
                    .order_by(Score.id)\
                    .all()
                scores = [r[0] for r in eq_rows]
                test_sentiments = [r[1] for r in eq_rows if r[1] is not None]
                
                # Journal insights purely from Journal entries
                j_rows = session.query(JournalEntry.sentiment_score)\
                    .filter_by(username=self.username)\
                    .all()
                journal_sentiments = [r[0] for r in j_rows]
        except Exception as e:
            # Log error but continue with empty data to avoid crashing UI
            print(f"Error generating insights: {e}")
        
        if len(scores) > 1:
            improvement = ((scores[-1] - scores[0]) / scores[0]) * 100 if scores[0] != 0 else 0
            if improvement > 10:
                insights.append(f"📈 Great progress! Your EQ improved by {improvement:.1f}%")
            elif improvement > 0:
                insights.append(f"📊 Steady progress with {improvement:.1f}% EQ improvement")
            else:
                insights.append("💪 Focus on emotional awareness to boost EQ scores")
        
        if journal_sentiments:
            avg_sentiment = sum(journal_sentiments) / len(journal_sentiments)
            if avg_sentiment > 20:
                insights.append("😊 Your journal shows positive emotional tone - keep it up!")
            elif avg_sentiment < -20:
                insights.append("🤗 Consider stress management techniques for better emotional balance")
            else:
                insights.append("⚖️ You maintain balanced emotional tone in your reflections")
                
        # Correlation Insight
        if scores and test_sentiments:
            latest_score = scores[-1]
            latest_sentiment = test_sentiments[-1]
            
            if latest_score > 35 and latest_sentiment < -20:
                insights.append("🎭 You have high EQ skills but are feeling down. Use your skills to navigate this emotions.")
            elif latest_score < 25 and latest_sentiment > 20:
                insights.append("🌱 Your spirit is high despite lower EQ scores! Use this optimism to learn emotional skills.")
        
        if not insights:
            insights.append("📝 Complete more assessments and journal entries for insights!")
        
        # Add Benchmark Insights
        if self.benchmarks and self.benchmarks.get("global_avg"):
            avg = self.benchmarks["global_avg"]
            if scores and scores[-1] > avg:
                insights.append(f"🌟 You are above the Global Average ({avg:.1f})!")
            elif scores:
                insights.append(f"📊 Global Average is {avg:.1f}. Keep practicing!")


        return insights

    # ========== WELLBEING ANALYTICS (PR 1.5) ==========
    def show_wellbeing_analytics(self, parent):
        """Show wellbeing analytics (Sleep vs Mood, Work vs Mood)"""
        parent = self._create_scrollable_frame(parent)
        # Fetch Data
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT sentiment_score, sleep_hours, energy_level, work_hours 
                FROM journal_entries 
                WHERE username = ? AND sleep_hours IS NOT NULL
                ORDER BY entry_date ASC
            """, (self.username,))
            rows = cursor.fetchall()
        finally:
            conn.close()

        # Handle Empty State
        if len(rows) < 3:
            tk.Label(parent, text="🧘 Wellbeing Analytics", font=("Arial", 16, "bold")).pack(pady=20)
            tk.Label(parent, 
                text="Not enough data yet!\n\n"
                     "Track your Sleep, Energy, and Work for at least 3 days\n"
                     "to unlock personalized health correlations.",
                font=("Arial", 12), fg="#666").pack(pady=20)
            return

        # Prepare Data
        sentiments = [r[0] for r in rows]
        sleeps = [r[1] for r in rows]
        energies = [r[2] for r in rows]
        works = [r[3] for r in rows]

        # --- UI Layout ---
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=0) # Title
        parent.rowconfigure(1, weight=1) # Charts
        parent.rowconfigure(2, weight=0) # Insights

        # Title & Controls
        header_frame = tk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        tk.Label(header_frame, text="🧘 Daily Wellbeing Correlations", font=("Arial", 16, "bold")).pack(side="left")
        
        def open_history():
            from app.ui.daily_view import DailyHistoryView
            top = tk.Toplevel(self.parent_root)
            DailyHistoryView(top, self, self.username)
            
        tk.Button(header_frame, text="📅 Explore History", command=open_history,
                 bg=self.colors["primary"], fg="white", relief="flat", padx=15, pady=5).pack(side="right")
        
        # --- Visualizations ---
        viz_frame = tk.Frame(parent)
        viz_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Matplotlib Setup - Modern Style
        plt.style.use('seaborn-v0_8-whitegrid' if plt.style.available else 'fast')
        fig = Figure(figsize=(10, 5), dpi=100)
        
        # Theme Colors
        is_dark = self.theme == "dark"
        bg_color = "#0F172A" if is_dark else "#FFFFFF"
        text_color = "white" if is_dark else "#333333"
        grid_color = "#334155" if is_dark else "#E5E7EB"
        
        fig.patch.set_facecolor(bg_color)

        # Plot 1: Sleep vs Sentiment (Smooth Line + Gradient Fill)
        ax1 = fig.add_subplot(121)
        ax1.set_facecolor(bg_color)
        
        # Sort for line plotting
        if len(sleeps) > 0:
            sorted_indices = sorted(range(len(sleeps)), key=lambda k: sleeps[k])
            s_sleep = np.array([sleeps[i] for i in sorted_indices])
            s_mood = np.array([sentiments[i] for i in sorted_indices])
            
            # Smooth Line Interpolation
            try:
                from scipy.interpolate import make_interp_spline
                if len(s_sleep) > 3:
                    # Handle duplicate X values by grouping and averaging
                    unique_sleep_dict = {}
                    for s, m in zip(s_sleep, s_mood):
                        if s not in unique_sleep_dict:
                            unique_sleep_dict[s] = []
                        unique_sleep_dict[s].append(m)
                    
                    sorted_unique_sleep = sorted(unique_sleep_dict.keys())
                    avg_mood_unique = [np.mean(unique_sleep_dict[k]) for k in sorted_unique_sleep]
                    
                    X_unique = np.array(sorted_unique_sleep)
                    Y_unique = np.array(avg_mood_unique)

                    if len(X_unique) > 3: # Check again after deduplication
                        X_line = np.linspace(X_unique.min(), X_unique.max(), 300)
                        spl = make_interp_spline(X_unique, Y_unique, k=3)
                        Y_line = spl(X_line)
                        # Vibrant Purple Line
                        ax1.plot(X_line, Y_line, color='#8B5CF6', linewidth=3, alpha=1.0)
                        # Gradient Fill
                        ax1.fill_between(X_line, Y_line, alpha=0.15, color='#8B5CF6')
                    else:
                        # Fallback if deduplication reduces points too much
                         ax1.plot(s_sleep, s_mood, color='#8B5CF6', linewidth=2, alpha=0.8)
                else:
                    ax1.plot(s_sleep, s_mood, color='#8B5CF6', linewidth=3, alpha=1.0)
            except Exception as e:
                # Fallback for any spline error (duplicates, singular matrix, etc)
                print(f"Spline error: {e}")
                ax1.plot(s_sleep, s_mood, color='#8B5CF6', linewidth=3, alpha=1.0)

            # Scatter Accents (Pink)
            ax1.scatter(sleeps, sentiments, c='#EC4899', s=80, edgecolors='white', linewidth=2, zorder=5)

        ax1.set_title("Sleep Quality & Mood", color=text_color, fontweight="bold", fontsize=11, pad=15)
        ax1.set_xlabel("Sleep Hours", color="#94A3B8", fontsize=9)
        ax1.set_ylabel("Sentiment Score", color="#94A3B8", fontsize=9)
        
        # Minimalist Grid
        ax1.grid(True, linestyle= '--', alpha=0.2, color=grid_color)
        ax1.tick_params(colors="#94A3B8")
        # Despine
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color(grid_color)
        ax1.spines['bottom'].set_color(grid_color)

        # Plot 2: Productivity Sweet Spot (Vibrant Pillars)
        ax2 = fig.add_subplot(122)
        ax2.set_facecolor(bg_color)
        
        # Binning Logic
        buckets = {"0-4h": [], "4-8h": [], "8h+": []}
        for w, s in zip(works, sentiments):
            if w < 4: buckets["0-4h"].append(s)
            elif w < 8: buckets["4-8h"].append(s)
            else: buckets["8h+"].append(s)
            
        bucket_avgs = [
            np.mean(buckets["0-4h"]) if buckets["0-4h"] else 0,
            np.mean(buckets["4-8h"]) if buckets["4-8h"] else 0,
            np.mean(buckets["8h+"]) if buckets["8h+"] else 0
        ]
        
        # Vibrant Colors: Amber -> Emerald -> Blue
        bar_colors = ["#F59E0B", "#10B981", "#3B82F6"]
        bars = ax2.bar(buckets.keys(), bucket_avgs, color=bar_colors, width=0.5, edgecolor=None)
        
        ax2.set_title("Productivity Sweet Spot", color=text_color, fontweight="bold", fontsize=11, pad=15)
        ax2.set_xlabel("Work Duration", color="#94A3B8", fontsize=9)
        ax2.set_ylabel("Avg Happiness", color="#94A3B8", fontsize=9)
        
        ax2.grid(axis='y', linestyle= '--', alpha=0.2, color=grid_color)
        ax2.tick_params(colors="#94A3B8", bottom=False) # Hide x ticks
        
        # Despine completely for cleaner look
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['bottom'].set_color(grid_color)
        
        # Annotate Bars
        for bar in bars:
            height = bar.get_height()
            if height != 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                         f'{height:.1f}',
                         ha='center', va='bottom',
                         color=text_color, fontweight="bold", fontsize=9)

        fig.tight_layout()
        
        # Render
        canvas = FigureCanvasTkAgg(fig, viz_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Text Insights ---
        insights_panel = tk.Frame(parent, bg="#F0F9FF" if not is_dark else "#1E293B", relief=tk.RIDGE, bd=1)
        insights_panel.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        
        # Generate Text Insight
        best_bucket = max(zip(buckets.keys(), bucket_avgs), key=lambda x: x[1])[0]
        max_val = max(bucket_avgs)
        
        insight_msg = f"💡 **Insight**: "
        if max_val > 10:
            insight_msg += f"You feel happiest when you work **{best_bucket}**. "
        else:
            insight_msg += "Your mood is relatively stable across work hours. "
            
        # Sleep Insight
        avg_sleep = np.mean(sleeps)
        if avg_sleep < 6:
            insight_msg += "⚠️ Your average sleep is low (< 6h). Try to rest more!"
        elif avg_sleep > 9:
            insight_msg += "😴 You're getting plenty of rest!"
        else:
            insight_msg += "✨ Your sleep schedule (avg {:.1f}h) seems balanced.".format(avg_sleep)

        tk.Label(insights_panel, text=insight_msg,
             font=("Arial", 11), bg=insights_panel["bg"], fg=text_color,
             wraplength=800, justify="left", padx=15, pady=15).pack(anchor="w")

    def show_progress_dashboard(self, parent):
        """Show comprehensive EQ growth progress dashboard"""
        parent = self._create_scrollable_frame(parent)

        # Title
        tk.Label(parent, text="📈 EQ Growth Progress Dashboard",
                font=("Arial", 18, "bold")).pack(pady=(20, 10))

        tk.Label(parent,
                text="Track your emotional intelligence development journey with interactive charts and personalized milestones.",
                font=("Arial", 11), wraplength=600).pack(pady=(0, 20))

        # Fetch data
        eq_scores = []
        eq_dates = []
        journal_entries = []
        journal_dates = []
        sentiment_scores = []

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Get EQ scores
            cursor.execute("""
                SELECT total_score, timestamp, sentiment_score
                FROM scores
                WHERE username = ?
                ORDER BY timestamp
            """, (self.username,))
            eq_data = cursor.fetchall()

            for row in eq_data:
                eq_scores.append(row[0])
                eq_dates.append(datetime.fromisoformat(row[1]))
                if row[2] is not None:
                    sentiment_scores.append(row[2])

            # Get journal entries
            cursor.execute("""
                SELECT entry_date, sentiment_score
                FROM journal_entries
                WHERE username = ?
                ORDER BY entry_date
            """, (self.username,))
            journal_data = cursor.fetchall()

            for row in journal_data:
                journal_entries.append(row[1] if row[1] is not None else 0)
                journal_dates.append(datetime.strptime(row[0].split(' ')[0], "%Y-%m-%d"))

            conn.close()
        except Exception as e:
            tk.Label(parent, text=f"Error loading progress data: {str(e)}",
                    font=("Arial", 12), fg="red").pack(pady=50)
            return

        if not eq_scores and not journal_entries:
            tk.Label(parent, text="No progress data available yet.\n\nComplete assessments and journal entries to see your growth!",
                    font=("Arial", 14)).pack(pady=50)
            return

        # --- 1. Progress Overview Cards ---
        cards_frame = tk.Frame(parent, bg=self.colors["bg"])
        cards_frame.pack(fill="x", padx=20, pady=10)

        def create_progress_card(title, value, subtitle, color, icon):
            card = tk.Frame(cards_frame, bg=self.colors["surface"], relief="ridge", bd=2)
            card.pack(side="left", expand=True, fill="both", padx=5)

            tk.Label(card, text=icon, font=("Arial", 24), bg=self.colors["surface"]).pack(pady=(15, 5))
            tk.Label(card, text=title, font=("Arial", 10, "bold"), bg=self.colors["surface"],
                    fg=self.colors["text_secondary"]).pack()
            tk.Label(card, text=str(value), font=("Arial", 20, "bold"), bg=self.colors["surface"],
                    fg=color).pack(pady=(5, 0))
            tk.Label(card, text=subtitle, font=("Arial", 8), bg=self.colors["surface"],
                    fg=self.colors["text_secondary"]).pack(pady=(0, 15))

        # Calculate metrics
        total_assessments = len(eq_scores)
        total_journal_entries = len(journal_entries)
        avg_score = sum(eq_scores)/len(eq_scores) if eq_scores else 0
        avg_sentiment = sum(sentiment_scores)/len(sentiment_scores) if sentiment_scores else 0

        create_progress_card("Assessments", total_assessments, "Completed", "#3B82F6", "🧠")
        create_progress_card("Journal Entries", total_journal_entries, "Written", "#8B5CF6", "📝")
        create_progress_card("Avg EQ Score", f"{avg_score:.1f}", "/25", "#22C55E", "📊")
        create_progress_card("Emotional Tone", f"{avg_sentiment:+.1f}", "sentiment", "#F59E0B", "😊" if avg_sentiment > 0 else "😐")

        # --- 2. EQ Score Progress Chart ---
        if eq_scores:
            progress_frame = tk.Frame(parent, bg=self.colors["surface"], relief="ridge", bd=2)
            progress_frame.pack(fill="both", expand=True, padx=20, pady=10)

            tk.Label(progress_frame, text="🎯 EQ Score Progress Over Time",
                    font=("Arial", 14, "bold"), bg=self.colors["surface"]).pack(pady=10)

            fig = Figure(figsize=(8, 4), dpi=100, facecolor=self.colors["surface"])
            ax = fig.add_subplot(111)
            ax.set_facecolor(self.colors["surface"])

            # Plot EQ scores with milestone markers
            x_vals = range(1, len(eq_scores) + 1)
            ax.plot(x_vals, eq_scores, 'o-', color='#22C55E', linewidth=3, markersize=8,
                   markerfacecolor='#22C55E', markeredgewidth=2, markeredgecolor='white')

            # Add milestone markers for significant improvements
            milestones = []
            for i in range(1, len(eq_scores)):
                if eq_scores[i] >= 20 and eq_scores[i-1] < 20:  # First score >= 20
                    milestones.append((i+1, eq_scores[i], "🎯 EQ Milestone: 20+"))
                elif eq_scores[i] >= 15 and eq_scores[i-1] < 15:  # First score >= 15
                    milestones.append((i+1, eq_scores[i], "⭐ EQ Milestone: 15+"))

            for x, y, label in milestones:
                ax.scatter(x, y, s=200, c='#FFD700', marker='*', edgecolors='black', linewidths=2, zorder=5)
                ax.annotate(label, (x, y), xytext=(10, 10), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8),
                           fontsize=9, fontweight='bold')

            ax.set_xlabel('Assessment Number', fontsize=11, color=self.colors["text_secondary"])
            ax.set_ylabel('EQ Score', fontsize=11, color='#22C55E')
            ax.set_title('Your EQ Growth Journey', fontsize=12, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_xticks(x_vals)

            # Add trend line if enough data
            if len(eq_scores) >= 3:
                try:
                    import numpy as np
                    z = np.polyfit(x_vals, eq_scores, 1)
                    p = np.poly1d(z)
                    trend_line = p(x_vals)
                    ax.plot(x_vals, trend_line, '--', color='#EF4444', alpha=0.7, linewidth=2,
                           label=f'Trend: {z[0]:+.2f}/assessment')
                    ax.legend(loc='upper left')
                except:
                    pass

            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, progress_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

        # --- 3. Journaling Frequency & Emotional Trends ---
        if journal_entries:
            trends_frame = tk.Frame(parent, bg=self.colors["surface"], relief="ridge", bd=2)
            trends_frame.pack(fill="both", expand=True, padx=20, pady=10)

            tk.Label(trends_frame, text="📝 Journaling Activity & Emotional Trends",
                    font=("Arial", 14, "bold"), bg=self.colors["surface"]).pack(pady=10)

            fig = Figure(figsize=(10, 6), dpi=100, facecolor=self.colors["surface"])

            # Journaling frequency (bar chart)
            ax1 = fig.add_subplot(211)
            ax1.set_facecolor(self.colors["surface"])

            # Group by week for frequency
            weekly_counts = {}
            for date in journal_dates:
                week_start = date - timedelta(days=date.weekday())
                week_key = week_start.strftime("%Y-%m-%d")
                weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1

            weeks = sorted(weekly_counts.keys())
            counts = [weekly_counts[w] for w in weeks]

            bars = ax1.bar(range(len(weeks)), counts, color='#8B5CF6', alpha=0.7, width=0.6)
            ax1.set_xlabel('Week', fontsize=11, color=self.colors["text_secondary"])
            ax1.set_ylabel('Journal Entries', fontsize=11, color='#8B5CF6')
            ax1.set_title('Weekly Journaling Frequency', fontsize=12, fontweight='bold', pad=10)
            ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
            ax1.set_xticks(range(len(weeks)))
            ax1.set_xticklabels([w[-5:] for w in weeks], rotation=45, ha='right')  # Show MM-DD

            # Add value labels on bars
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1, str(count),
                        ha='center', va='bottom', fontsize=9, fontweight='bold')

            # Emotional trends (line chart)
            ax2 = fig.add_subplot(212)
            ax2.set_facecolor(self.colors["surface"])

            ax2.plot(range(len(journal_entries)), journal_entries, 'o-', color='#F59E0B',
                    linewidth=2, markersize=6, markerfacecolor='#F59E0B',
                    markeredgewidth=2, markeredgecolor='white')

            ax2.set_xlabel('Journal Entry Number', fontsize=11, color=self.colors["text_secondary"])
            ax2.set_ylabel('Sentiment Score', fontsize=11, color='#F59E0B')
            ax2.set_title('Emotional Sentiment Trends', fontsize=12, fontweight='bold', pad=10)
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)  # Neutral line

            fig.tight_layout(pad=2.0)
            canvas = FigureCanvasTkAgg(fig, trends_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=10)

        # --- 4. Personalized Milestones ---
        milestones_frame = tk.Frame(parent, bg=self.colors["surface"], relief="ridge", bd=2)
        milestones_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(milestones_frame, text="🏆 Your EQ Growth Milestones",
                font=("Arial", 14, "bold"), bg=self.colors["surface"]).pack(pady=10)

        # Define milestones
        milestones_data = [
            {"name": "First Assessment", "description": "Completed your first EQ assessment",
             "threshold": 1, "current": total_assessments, "icon": "🎯", "color": "#3B82F6"},
            {"name": "EQ Explorer", "description": "Completed 5 assessments",
             "threshold": 5, "current": total_assessments, "icon": "🧭", "color": "#8B5CF6"},
            {"name": "EQ Achiever", "description": "Scored 20+ on an assessment",
             "threshold": 20, "current": max(eq_scores) if eq_scores else 0, "icon": "⭐", "color": "#F59E0B"},
            {"name": "EQ Master", "description": "Scored 22+ on an assessment",
             "threshold": 22, "current": max(eq_scores) if eq_scores else 0, "icon": "👑", "color": "#EF4444"},
            {"name": "Reflective Mind", "description": "Written 10 journal entries",
             "threshold": 10, "current": total_journal_entries, "icon": "📝", "color": "#22C55E"},
            {"name": "Emotional Chronicler", "description": "Written 25 journal entries",
             "threshold": 25, "current": total_journal_entries, "icon": "📚", "color": "#06B6D4"},
        ]

        # Display milestones in a grid
        milestones_container = tk.Frame(milestones_frame, bg=self.colors["surface"])
        milestones_container.pack(fill="both", expand=True, padx=20, pady=10)

        for i, milestone in enumerate(milestones_data):
            row = i // 2
            col = i % 2

            # Create milestone card
            card = tk.Frame(milestones_container, bg="#f8f9fa", relief="groove", bd=1)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            # Configure grid weights
            milestones_container.grid_rowconfigure(row, weight=1)
            milestones_container.grid_columnconfigure(col, weight=1)

            # Header with icon and progress
            header_frame = tk.Frame(card, bg="#f8f9fa")
            header_frame.pack(fill="x", padx=10, pady=10)

            achieved = milestone["current"] >= milestone["threshold"]
            icon_color = milestone["color"] if achieved else "#94A3B8"

            tk.Label(header_frame, text=milestone["icon"], font=("Arial", 20),
                    bg="#f8f9fa", fg=icon_color).pack(side="left")

            progress_frame = tk.Frame(header_frame, bg="#f8f9fa")
            progress_frame.pack(side="right")

            tk.Label(progress_frame, text=f"{milestone['current']}/{milestone['threshold']}",
                    font=("Arial", 10, "bold"), bg="#f8f9fa",
                    fg=milestone["color"] if achieved else "#666").pack()

            # Title and description
            tk.Label(card, text=milestone["name"], font=("Arial", 12, "bold"),
                    bg="#f8f9fa", fg=milestone["color"] if achieved else "#666").pack(anchor="w", padx=10)

            tk.Label(card, text=milestone["description"], font=("Arial", 9),
                    bg="#f8f9fa", fg="#666", wraplength=200, justify="left").pack(anchor="w", padx=10, pady=(0, 10))

            # Progress bar
            progress_value = min(100, (milestone["current"] / milestone["threshold"]) * 100)
            progress_bar = tk.Canvas(card, width=200, height=8, bg="#E5E7EB", highlightthickness=0)
            progress_bar.pack(pady=(0, 10))

            # Draw progress bar
            progress_bar.create_rectangle(0, 0, 200, 8, fill="#E5E7EB", outline="")
            if progress_value > 0:
                progress_bar.create_rectangle(0, 0, progress_value * 2, 8,
                                            fill=milestone["color"] if achieved else "#CBD5E1", outline="")

            # Achievement indicator
            if achieved:
                tk.Label(card, text="✅ ACHIEVED!", font=("Arial", 8, "bold"),
                        bg="#f8f9fa", fg=milestone["color"]).pack(pady=(0, 10))
            else:
                remaining = milestone["threshold"] - milestone["current"]
                tk.Label(card, text=f"{remaining} more to go!", font=("Arial", 8),
                        bg="#f8f9fa", fg="#666").pack(pady=(0, 10))

        # --- 5. Next Steps & Recommendations ---
        if eq_scores or journal_entries:
            recommendations_frame = tk.Frame(parent, bg="#E0F2FE", relief="ridge", bd=2)
            recommendations_frame.pack(fill="x", padx=20, pady=20)

            tk.Label(recommendations_frame, text="💡 Growth Recommendations",
                    font=("Arial", 14, "bold"), bg="#E0F2FE").pack(pady=10)

            recommendations = []

            # EQ Score recommendations
            if eq_scores:
                latest_score = eq_scores[-1]
                if latest_score < 15:
                    recommendations.append("📈 Focus on building foundational EQ skills through regular assessments")
                elif latest_score < 20:
                    recommendations.append("🎯 You're progressing well! Continue practicing emotional awareness")
                else:
                    recommendations.append("⭐ Excellent EQ skills! Maintain consistency and help others learn")

            # Journaling recommendations
            if total_journal_entries < 5:
                recommendations.append("📝 Start journaling regularly to track your emotional patterns")
            elif total_journal_entries < 15:
                recommendations.append("🔄 Great journaling habit! Try exploring different emotional triggers")
            else:
                recommendations.append("📚 You're building a rich emotional history - keep reflecting!")

            # Overall progress
            if total_assessments >= 3 and total_journal_entries >= 5:
                recommendations.append("🚀 You're on a great growth journey! Consider sharing insights with others")
            elif total_assessments < 3:
                recommendations.append("🧠 Take more assessments to track your EQ development over time")

            for rec in recommendations:
                tk.Label(recommendations_frame, text=f"• {rec}", font=("Arial", 10),
                        bg="#E0F2FE", wraplength=700, justify="left").pack(anchor="w", padx=20, pady=2)

            tk.Label(recommendations_frame, text="", bg="#E0F2FE").pack(pady=10)  # Spacer
