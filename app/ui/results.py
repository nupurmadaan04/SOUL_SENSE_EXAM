import tkinter as tk
from tkinter import messagebox
import logging
from datetime import datetime
import random
from app.db import get_connection, get_session
from app.models import Score
from app.constants import BENCHMARK_DATA
try:
    from app.services.pdf_generator import generate_pdf_report
except ImportError:
    generate_pdf_report = None
import json
from app.models import AssessmentResult
from typing import Any, Dict, List, Optional, Tuple

class ResultsManager:
    def __init__(self, app: Any) -> None:
        self.app = app

    def show_satisfaction_survey(self) -> None:
        """Show satisfaction survey from results page"""
        try:
            from app.ui.satisfaction import SatisfactionSurvey
            
            # Get latest score ID
            session = get_session()
            try:
                latest_score = session.query(Score).filter(
                    Score.username == self.app.username
                ).order_by(Score.id.desc()).first()
                
                eq_score_id = latest_score.id if latest_score else None
                
                survey = SatisfactionSurvey(
                    parent=self.app.root,
                    username=self.app.username,
                    user_id=self.app.current_user_id,
                    eq_score_id=eq_score_id,
                    language=self.app.settings.get("language", "en")
                )
                survey.show()
            finally:
                session.close()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open survey: {str(e)}")
        
    # ---------- BENCHMARKING FUNCTIONS ----------
    def calculate_percentile(self, score: float, avg_score: float, std_dev: float) -> int:
        """Calculate percentile based on normal distribution"""
        if std_dev == 0:
            return 50 if score == avg_score else (100 if score > avg_score else 0)
        
        # Z-score calculation
        z_score = (score - avg_score) / std_dev
        
        # Convert Z-score to percentile (simplified approximation)
        if z_score <= -2.5:
            percentile = 1
        elif z_score <= -2.0:
            percentile = 2
        elif z_score <= -1.5:
            percentile = 7
        elif z_score <= -1.0:
            percentile = 16
        elif z_score <= -0.5:
            percentile = 31
        elif z_score <= 0:
            percentile = 50
        elif z_score <= 0.5:
            percentile = 69
        elif z_score <= 1.0:
            percentile = 84
        elif z_score <= 1.5:
            percentile = 93
        elif z_score <= 2.0:
            percentile = 98
        elif z_score <= 2.5:
            percentile = 99
        else:
            percentile = 99.5
            
        return percentile

    def get_benchmark_comparison(self) -> Dict[str, Any]:
        """Get benchmark comparisons for the current score"""
        comparisons = {}
        
        # Global comparison
        global_bench = BENCHMARK_DATA["global"]
        comparisons["global"] = {
            "your_score": self.app.current_score,
            "avg_score": global_bench["avg_score"],
            "difference": self.app.current_score - global_bench["avg_score"],
            "percentile": self.calculate_percentile(self.app.current_score, global_bench["avg_score"], global_bench["std_dev"]),
            "sample_size": global_bench["sample_size"]
        }
        
        # Age group comparison
        if self.app.age_group and self.app.age_group in BENCHMARK_DATA["age_groups"]:
            age_bench = BENCHMARK_DATA["age_groups"][self.app.age_group]
            comparisons["age_group"] = {
                "group": self.app.age_group,
                "your_score": self.app.current_score,
                "avg_score": age_bench["avg_score"],
                "difference": self.app.current_score - age_bench["avg_score"],
                "percentile": self.calculate_percentile(self.app.current_score, age_bench["avg_score"], age_bench["std_dev"]),
                "sample_size": age_bench["sample_size"]
            }
        
        # Profession comparison
        if self.app.profession and self.app.profession in BENCHMARK_DATA["professions"]:
            prof_bench = BENCHMARK_DATA["professions"][self.app.profession]
            comparisons["profession"] = {
                "profession": self.app.profession,
                "your_score": self.app.current_score,
                "avg_score": prof_bench["avg_score"],
                "difference": self.app.current_score - prof_bench["avg_score"],
                "percentile": self.calculate_percentile(self.app.current_score, prof_bench["avg_score"], prof_bench["std_dev"])
            }
        
        return comparisons

    def get_benchmark_interpretation(self, comparisons: Dict[str, Any]) -> List[str]:
        """Get interpretation text based on benchmark comparisons"""
        interpretations = []
        
        if "global" in comparisons:
            comp = comparisons["global"]
            if comp["difference"] > 5:
                interpretations.append(f"Your score is significantly higher than the global average ({comp['avg_score']}).")
            elif comp["difference"] > 2:
                interpretations.append(f"Your score is above the global average ({comp['avg_score']}).")
            elif comp["difference"] < -5:
                interpretations.append(f"Your score is significantly lower than the global average ({comp['avg_score']}).")
            elif comp["difference"] < -2:
                interpretations.append(f"Your score is below the global average ({comp['avg_score']}).")
            else:
                interpretations.append(f"Your score is close to the global average ({comp['avg_score']}).")
            
            interpretations.append(f"You scored higher than {comp['percentile']:.1f}% of test-takers globally.")
        
        if "age_group" in comparisons:
            comp = comparisons["age_group"]
            if comp["difference"] > 0:
                interpretations.append(f"You scored above average for your age group ({comp['group']}).")
            elif comp["difference"] < 0:
                interpretations.append(f"You scored below average for your age group ({comp['group']}).")
            else:
                interpretations.append(f"You scored average for your age group ({comp['group']}).")
            
            interpretations.append(f"You're in the {comp['percentile']:.0f}th percentile for your age group.")
        
        if "profession" in comparisons:
            comp = comparisons["profession"]
            if comp["difference"] > 0:
                interpretations.append(f"You scored above average for {comp['profession']} professionals.")
            elif comp["difference"] < 0:
                interpretations.append(f"You scored below average for {comp['profession']} professionals.")
            else:
                interpretations.append(f"You scored average for {comp['profession']} professionals.")
        
        return interpretations

    def create_benchmark_chart(self, parent: tk.Widget, comparisons: Dict[str, Any]) -> tk.Frame:
        """Create a visual benchmark comparison chart"""
        chart_frame = tk.Frame(parent)
        chart_frame.pack(fill="x", pady=10)
        
        tk.Label(
            chart_frame,
            text="Benchmark Comparison",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", pady=5)
        
        # Create canvas for benchmark bars
        chart_canvas = tk.Canvas(chart_frame, height=150, bg="#F8FAFC", highlightthickness=0)
        chart_canvas.pack(fill="x", pady=10)
        
        # Prepare data for chart
        chart_data = []
        if "global" in comparisons:
            chart_data.append(("Global", comparisons["global"]))
        if "age_group" in comparisons:
            chart_data.append((comparisons["age_group"]["group"], comparisons["age_group"]))
        if "profession" in comparisons:
            chart_data.append((comparisons["profession"]["profession"], comparisons["profession"]))
        
        if not chart_data:
            return chart_frame
        
        # Calculate chart dimensions
        num_bars = len(chart_data)
        chart_width = 500
        bar_width = 80
        spacing = 30
        start_x = 100
        max_score = max([max(d["your_score"], d["avg_score"]) for _, d in chart_data])
        scale_factor = 100 / max(1, max_score)
        
        # Draw bars for each comparison
        for i, (label, data) in enumerate(chart_data):
            x = start_x + i * (bar_width + spacing)
            
            # Your score bar
            your_height = data["your_score"] * scale_factor
            y_your = 130 - your_height
            your_color = "#22C55E" if data["difference"] > 0 else "#EF4444" if data["difference"] < 0 else "#F59E0B"
            
            chart_canvas.create_rectangle(x, y_your, x + bar_width/2, 130, 
                                         fill=your_color, outline="black")
            chart_canvas.create_text(x + bar_width/4, y_your - 10, 
                                    text=f"You: {data['your_score']}", 
                                    fill="#0F172A", font=("Arial", 8, "bold"))
            
            # Average score bar
            avg_height = data["avg_score"] * scale_factor
            y_avg = 130 - avg_height
            
            chart_canvas.create_rectangle(x + bar_width/2, y_avg, x + bar_width, 130, 
                                         fill="#888888", outline="black")
            chart_canvas.create_text(x + bar_width * 0.75, y_avg - 10, 
                                    text=f"Avg: {data['avg_score']}", 
                                    fill="#0F172A", font=("Arial", 8, "bold"))
            
            # Label
            chart_canvas.create_text(x + bar_width/2, 145, text=label, 
                                    fill="#0F172A", font=("Arial", 9))
            
            # Difference indicator
            diff = data["difference"]
            if diff != 0:
                diff_text = f"{'+' if diff > 0 else ''}{diff:.1f}"
                diff_color = "#22C55E" if diff > 0 else "#EF4444"
                chart_canvas.create_text(x + bar_width/2, y_your - 25, text=diff_text, 
                                        fill=diff_color, font=("Arial", 9, "bold"))
        
        # Y-axis labels
        for score in [0, max_score//2, max_score]:
            y = 130 - (score * scale_factor)
            chart_canvas.create_text(80, y, text=str(score), fill="#0F172A", font=("Arial", 8))
        
        chart_canvas.create_text(50, 65, text="Score", fill="#0F172A", angle=90)
        
        # Legend
        legend_frame = tk.Frame(chart_frame, bg="#F8FAFC")
        legend_frame.pack(pady=5)
        
        # Your score legend
        your_legend = tk.Canvas(legend_frame, width=20, height=20, bg="#F8FAFC", highlightthickness=0)
        your_legend.create_rectangle(0, 0, 20, 20, fill="#22C55E", outline="black")
        your_legend.pack(side="left", padx=5)
        tk.Label(legend_frame, text="Your Score", bg="#F8FAFC", fg="#0F172A").pack(side="left", padx=5)
        
        # Average score legend
        avg_legend = tk.Canvas(legend_frame, width=20, height=20, bg="#F8FAFC", highlightthickness=0)
        avg_legend.create_rectangle(0, 0, 20, 20, fill="#888888", outline="black")
        avg_legend.pack(side="left", padx=20)
        tk.Label(legend_frame, text="Average Score", bg="#F8FAFC", fg="#0F172A").pack(side="left", padx=5)
        
        return chart_frame

    def export_results_pdf(self) -> None:
        """Export current results to PDF"""
        if not generate_pdf_report:
            messagebox.showerror("Error", "PDF Generator module not available.")
            return

        try:
            from app.utils.file_validation import validate_file_path, sanitize_filename, ValidationError
            
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_username = sanitize_filename(self.app.username)
            default_name = f"EQ_Report_{safe_username}_{timestamp}.pdf"
            
            # Ask user for location
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Save PDF Report",
                initialfile=default_name,
                defaultextension=".pdf",
                filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
            )
            
            if not filename:
                return # User cancelled

            # Validate the user-selected path
            try:
                # We don't enforce base_dir here as users can save anywhere via GUI dialog
                filename = validate_file_path(filename, allowed_extensions=[".pdf"])
            except ValidationError as ve:
                messagebox.showerror("Security Error", str(ve))
                return

            # Prepare data for report
            result_path = generate_pdf_report(
                self.app.username,
                self.app.current_score,
                self.app.current_max_score,
                self.app.current_percentage,
                self.app.age,
                self.app.responses,
                self.app.questions,
                self.app.sentiment_score if hasattr(self.app, 'sentiment_score') else None,
                filepath=filename
            )
            
            if result_path:
                messagebox.showinfo("Success", f"Report saved successfully:\n{result_path}")
                # Optional: Open the file
                # import os
                # os.startfile(result_path) 
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate PDF:\n{str(e)}")
            logging.error(f"PDF Export failed: {e}")

    def show_results(self) -> None:
        """Main method to show results - calls show_visual_results"""
        self.show_visual_results()

    def show_visual_results(self) -> None:
        """Modern, elegant results page with responsive design"""
        self.app.clear_screen()
        self.app.root.state('zoomed')
        
        colors = self.app.colors
        
        # Main container - fills entire window
        main_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        main_frame.pack(fill="both", expand=True)
        
        # Create scrollable canvas (Hidden Scrollbar)
        canvas = tk.Canvas(main_frame, bg=colors.get("bg", "#0F172A"), highlightthickness=0)
        scrollable = tk.Frame(canvas, bg=colors.get("bg", "#0F172A"))
        
        # Create window and store its ID for resizing
        canvas_window = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        
        # Responsive: Update canvas width when window resizes
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Robust mouse wheel binding (Conditional)
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    # Only scroll if content > view
                    if scrollable.winfo_reqheight() > canvas.winfo_height():
                        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass

        def _bind_mouse(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_mouse(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mouse)
        canvas.bind("<Leave>", _unbind_mouse)
        scrollable.bind("<Enter>", _bind_mouse)
        scrollable.bind("<Leave>", _unbind_mouse)
        
        # ===== HEADER BAR with Menu Button =====
        header_bar = tk.Frame(scrollable, bg="#22C55E")
        header_bar.pack(fill="x")
        
        header_inner = tk.Frame(header_bar, bg="#22C55E")
        header_inner.pack(fill="x", padx=20, pady=15)
        
        # Menu button on left
        menu_btn = tk.Button(
            header_inner,
            text="\u2630 Menu",
            font=("Segoe UI", 10),
            bg="#16A34A", fg="white",
            activebackground="#15803D", activeforeground="white",
            relief="flat", cursor="hand2",
            command=self.app.create_welcome_screen,
            padx=12, pady=4
        )
        menu_btn.pack(side="left")
        
        # Title centered
        title_frame = tk.Frame(header_inner, bg="#22C55E")
        title_frame.pack(expand=True)
        
        tk.Label(
            title_frame,
            text="\U0001f389 Assessment Complete!",
            font=("Segoe UI", 22, "bold"),
            bg="#22C55E", fg="white"
        ).pack()
        
        tk.Label(
            title_frame,
            text=f"Congratulations {self.app.username}!",
            font=("Segoe UI", 11),
            bg="#22C55E", fg="white"
        ).pack()
        
        # ===== CENTER CONTENT (max 800px width) =====
        content_wrapper = tk.Frame(scrollable, bg=colors.get("bg", "#0F172A"))
        content_wrapper.pack(fill="x", pady=30)
        
        # Limit content width for elegant look
        content = tk.Frame(content_wrapper, bg=colors.get("bg", "#0F172A"))
        content.pack(anchor="center")
        
        # Section Header
        tk.Label(
            content,
            text="Your Results Are Ready",
            font=("Segoe UI", 18, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=(0, 20))
        
        # ===== SCORE CARD =====
        score_card = tk.Frame(
            content,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        score_card.pack(pady=10, padx=20, ipadx=60, ipady=20)
        
        card_inner = tk.Frame(score_card, bg=colors.get("surface", "#FFFFFF"))
        card_inner.pack(padx=40, pady=25)
        
        tk.Label(
            card_inner,
            text="Your EQ Score",
            font=("Segoe UI", 14),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#64748B")
        ).pack()
        
        # Score display
        score_frame = tk.Frame(card_inner, bg=colors.get("surface", "#FFFFFF"))
        score_frame.pack(pady=10)
        
        tk.Label(
            score_frame,
            text=str(self.app.current_score),
            font=("Segoe UI", 48, "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg="#22C55E"
        ).pack(side="left")
        
        tk.Label(
            score_frame,
            text=f" / {self.app.current_max_score}",
            font=("Segoe UI", 20),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_tertiary", "#94A3B8")
        ).pack(side="left", pady=(15, 0))
        
        # Average
        avg = self.app.current_score / len(self.app.responses) if self.app.responses else 0
        tk.Label(
            card_inner,
            text=f"Average: {avg:.1f} per question",
            font=("Segoe UI", 11),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#64748B")
        ).pack(pady=(5, 10))
        
        # Interpretation
        if self.app.current_percentage >= 80:
            interp, icolor = "Excellent emotional awareness!", "#22C55E"
        elif self.app.current_percentage >= 65:
            interp, icolor = "Good EQ with room for growth", "#3B82F6"
        elif self.app.current_percentage >= 50:
            interp, icolor = "Average - keep practicing!", "#F59E0B"
        else:
            interp, icolor = "Building skills together", "#EF4444"
        
        tk.Label(
            card_inner,
            text=interp,
            font=("Segoe UI", 12, "italic"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=icolor
        ).pack()

        # Sentiment Score Display in Main Card
        if hasattr(self.app, 'sentiment_score') and self.app.sentiment_score is not None:
            tk.Frame(card_inner, height=1, bg=colors.get("border", "#E2E8F0")).pack(fill="x", pady=15)
            
            s_score = self.app.sentiment_score
            s_color = "#22C55E" if s_score > 20 else "#EF4444" if s_score < -20 else "#F59E0B"
            s_text = "Positive" if s_score > 20 else "Negative" if s_score < -20 else "Neutral"
            
            tk.Label(
                card_inner,
                text="Sentiment Analysis",
                font=("Segoe UI", 11),
                bg=colors.get("surface", "#FFFFFF"),
                fg=colors.get("text_secondary", "#64748B")
            ).pack()
            
            tk.Label(
                card_inner,
                text=f"{s_score:+.1f} ({s_text})",
                font=("Segoe UI", 16, "bold"),
                bg=colors.get("surface", "#FFFFFF"),
                fg=s_color
            ).pack(pady=(5, 0))
        
        # ===== ACTION BUTTONS (Modern, Slim Design) =====
        tk.Label(
            content,
            text="What would you like to do?",
            font=("Segoe UI", 14, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=(30, 15))
        
        # Button container with 3-column grid
        btn_frame = tk.Frame(content, bg=colors.get("bg", "#0F172A"))
        btn_frame.pack()
        
        actions = [
            ("\U0001f4ca Dashboard", "#14B8A6", self.app.open_dashboard_flow if hasattr(self.app, 'open_dashboard_flow') else None),
            ("\U0001f4c8 Analysis", "#EC4899", self.show_detailed_analysis),
            ("\U0001f916 AI Insights", "#8B5CF6", self.show_ml_analysis if hasattr(self.app, 'ml_predictor') and self.app.ml_predictor else None),
            ("💼 Satisfaction", "#178240", self.show_satisfaction_survey),
            ("\U0001f4c4 Export PDF", "#06B6D4", self.export_results_pdf),
            ("\U0001f504 Retake Test", "#3B82F6", self.reset_test),
            ("\U0001f4dc History", "#F97316", self.show_history_screen),
        ]
        
        for i, (text, color, cmd) in enumerate(actions):
            row, col = i // 3, i % 3
            
            btn = tk.Button(
                btn_frame,
                text=text,
                font=("Segoe UI", 11),
                bg=color, fg="white",
                activebackground=color, activeforeground="white",
                relief="flat",
                cursor="hand2" if cmd else "arrow",
                command=cmd if cmd else lambda: messagebox.showinfo("Info", "Feature not available"),
                width=14, pady=8
            )
            btn.grid(row=row, column=col, padx=6, pady=6)
            
            if cmd:
                btn.bind("<Enter>", lambda e, b=btn, c=color: b.configure(bg=self._lighten(c)))
                btn.bind("<Leave>", lambda e, b=btn, c=color: b.configure(bg=c))
        
        # ===== BACK TO MENU BUTTON =====
        tk.Button(
            content,
            text="← Back to Menu",
            font=("Segoe UI", 11),
            bg=colors.get("surface", "#1E293B"),
            fg=colors.get("text_primary", "#F8FAFC"),
            activebackground=colors.get("surface", "#1E293B"),
            relief="flat",
            cursor="hand2",
            command=self.app.create_welcome_screen,
            width=20, pady=8
        ).pack(pady=(25, 40))
        
        # Pack canvas (Hidden Scrollbar)
        canvas.pack(side="left", fill="both", expand=True)
    
    def _lighten(self, color):
        """Lighten a hex color"""
        try:
            r = min(255, int(color[1:3], 16) + 25)
            g = min(255, int(color[3:5], 16) + 25)
            b = min(255, int(color[5:7], 16) + 25)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color
    
    def show_detailed_analysis(self):
        """Show detailed analysis page with progress bar, sentiment, benchmarks"""
        # Create popup window
        detail_win = tk.Toplevel(self.app.root)
        detail_win.title("Detailed Analysis")
        detail_win.geometry("800x600")
        detail_win.configure(bg=self.app.colors.get("bg", "#0F172A"))
        
        # Center window
        detail_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 800) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 600) // 2
        detail_win.geometry(f"+{x}+{y}")
        
        colors = self.app.colors
        
        # Scrollable container (Hidden Scrollbar)
        canvas = tk.Canvas(detail_win, bg=colors.get("bg", "#0F172A"), highlightthickness=0)
        scrollable = tk.Frame(canvas, bg=colors.get("bg", "#0F172A"))
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw", width=780)
        
        # Mouse wheel - bind only to this window's widgets (Conditional)
        def _on_mousewheel(event):
            try:
                if scrollable.winfo_reqheight() > canvas.winfo_height():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable.bind("<MouseWheel>", _on_mousewheel)
        
        # Cleanup on close
        def on_close():
            try:
                canvas.unbind("<MouseWheel>")
                scrollable.unbind("<MouseWheel>")
            except:
                pass
            detail_win.destroy()
        
        detail_win.protocol("WM_DELETE_WINDOW", on_close)
        
        # Header
        tk.Label(
            scrollable,
            text="📈 Detailed Analysis",
            font=("Segoe UI", 22, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=20)
        
        # Get benchmark data
        comparisons = self.get_benchmark_comparison()
        
        # === PROGRESS BAR SECTION ===
        self._create_progress_section(scrollable, colors)
        
        # === SENTIMENT SECTION ===
        if hasattr(self.app, 'sentiment_score') and self.app.sentiment_score is not None:
            self._create_sentiment_section(scrollable, colors)
        
        # === BENCHMARK SECTION ===
        if comparisons:
            self._create_benchmark_section(scrollable, colors, comparisons)
        
        # === EQ CATEGORIES ===
        self._create_categories_section(scrollable, colors)
        
        # Close button
        tk.Button(
            scrollable,
            text="Close",
            font=("Segoe UI", 12),
            bg=colors.get("primary", "#3B82F6"),
            fg="white",
            relief="flat",
            command=on_close,
            width=15, pady=8
        ).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
    
    def _create_progress_section(self, parent, colors):
        """Create EQ progress bar section"""
        frame = tk.Frame(parent, bg=colors.get("surface", "#FFFFFF"))
        frame.pack(fill="x", padx=20, pady=10)
        
        inner = tk.Frame(frame, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(inner, text="EQ Score Progress", font=("Segoe UI", 14, "bold"),
                 bg=colors.get("surface", "#FFFFFF"), fg=colors.get("text_primary", "#0F172A")).pack(anchor="w")
        
        # Progress bar
        bar_canvas = tk.Canvas(inner, width=700, height=30, bg="#E5E7EB", highlightthickness=0)
        bar_canvas.pack(pady=10)
        
        fill = (self.app.current_percentage / 100) * 700
        if self.app.current_percentage >= 80:
            bar_color = "#22C55E"
        elif self.app.current_percentage >= 65:
            bar_color = "#3B82F6"
        elif self.app.current_percentage >= 50:
            bar_color = "#F59E0B"
        else:
            bar_color = "#EF4444"
        
        bar_canvas.create_rectangle(0, 0, fill, 30, fill=bar_color, outline="")
        bar_canvas.create_text(350, 15, text=f"{self.app.current_percentage:.1f}%", font=("Segoe UI", 12, "bold"), fill="white" if fill > 350 else "black")
    
    def _create_sentiment_section(self, parent, colors):
        """Create sentiment analysis section"""
        frame = tk.Frame(parent, bg=colors.get("surface", "#FFFFFF"))
        frame.pack(fill="x", padx=20, pady=10)
        
        inner = tk.Frame(frame, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(inner, text="Emotional Sentiment", font=("Segoe UI", 14, "bold"),
                 bg=colors.get("surface", "#FFFFFF"), fg=colors.get("text_primary", "#0F172A")).pack(anchor="w")
        
        if self.app.sentiment_score > 20:
            s_color, s_text = "#22C55E", "Positive"
        elif self.app.sentiment_score < -20:
            s_color, s_text = "#EF4444", "Negative"
        else:
            s_color, s_text = "#F59E0B", "Neutral"
        
        tk.Label(inner, text=f"{self.app.sentiment_score:+.1f} ({s_text})", font=("Segoe UI", 20, "bold"),
                 bg=colors.get("surface", "#FFFFFF"), fg=s_color).pack(anchor="w", pady=5)
    
    def _create_benchmark_section(self, parent, colors, comparisons):
        """Create benchmark analysis section"""
        frame = tk.Frame(parent, bg=colors.get("surface", "#FFFFFF"))
        frame.pack(fill="x", padx=20, pady=10)
        
        inner = tk.Frame(frame, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(inner, text="Benchmark Analysis", font=("Segoe UI", 14, "bold"),
                 bg=colors.get("surface", "#FFFFFF"), fg=colors.get("text_primary", "#0F172A")).pack(anchor="w")
        
        if "global" in comparisons:
            comp = comparisons["global"]
            tk.Label(inner, text=f"Your Score: {comp['your_score']} | Global Avg: {comp['avg_score']}",
                     font=("Segoe UI", 12), bg=colors.get("surface", "#FFFFFF"),
                     fg=colors.get("text_secondary", "#64748B")).pack(anchor="w", pady=5)
            tk.Label(inner, text=f"Percentile: {comp['percentile']:.0f}th",
                     font=("Segoe UI", 12, "bold"), bg=colors.get("surface", "#FFFFFF"),
                     fg="#3B82F6").pack(anchor="w")
    
    def _create_categories_section(self, parent, colors):
        """Create EQ categories section"""
        frame = tk.Frame(parent, bg=colors.get("surface", "#FFFFFF"))
        frame.pack(fill="x", padx=20, pady=10)
        
        inner = tk.Frame(frame, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=20, pady=15)
        
        tk.Label(inner, text="EQ Categories", font=("Segoe UI", 14, "bold"),
                 bg=colors.get("surface", "#FFFFFF"), fg=colors.get("text_primary", "#0F172A")).pack(anchor="w", pady=(0, 10))
        
        categories = ["Self-Awareness", "Self-Regulation", "Motivation", "Empathy", "Social Skills"]
        for cat in categories:
            row = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
            row.pack(fill="x", pady=3)
            
            tk.Label(row, text=cat, font=("Segoe UI", 11), width=15, anchor="w",
                     bg=colors.get("surface", "#FFFFFF"), fg=colors.get("text_primary", "#0F172A")).pack(side="left")
            
            score = min(100, self.app.current_percentage + random.uniform(-10, 10))
            bar = tk.Canvas(row, width=400, height=18, bg="#E5E7EB", highlightthickness=0)
            bar.pack(side="left", padx=10)
            
            color = "#22C55E" if score >= 70 else "#F59E0B" if score >= 50 else "#EF4444"
            bar.create_rectangle(0, 0, (score/100)*400, 18, fill=color, outline="")
            bar.create_text(200, 9, text=f"{score:.0f}%", font=("Segoe UI", 9), fill="white" if score > 50 else "black")

    def show_ml_analysis(self):
        """Show AI-powered analysis in a popup window"""
        if not hasattr(self.app, 'ml_predictor') or not self.app.ml_predictor:
            messagebox.showerror("Error", "AI Model not loaded.")
            return
            
        try:
            # 1. Get Prediction
            result = self.app.ml_predictor.predict_with_explanation(
                self.app.responses,
                self.app.age,
                self.app.current_score,
                sentiment_score=self.app.sentiment_score if hasattr(self.app, 'sentiment_score') else None
            )
            
            colors = self.app.colors
            
            # 2. Create Layout
            popup = tk.Toplevel(self.app.root)
            popup.title("🧠 SoulSense AI Analysis")
            popup.geometry("650x750")
            popup.configure(bg=colors.get("bg", "#F5F5F5"))

            # Main Scrollable Frame
            canvas = tk.Canvas(popup, bg=colors.get("bg", "#F5F5F5"), highlightthickness=0)
            scrollbar = tk.Scrollbar(popup, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=colors.get("bg", "#F5F5F5"))

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=630)
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Mouse wheel with focus handling
            def _on_mousewheel(event):
                try:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                except tk.TclError:
                    pass
            
            def _on_enter(event):
                try:
                    canvas.focus_set()
                    canvas.bind_all("<MouseWheel>", _on_mousewheel)
                except tk.TclError:
                    pass

            def _on_leave(event):
                try:
                    canvas.unbind_all("<MouseWheel>")
                except tk.TclError:
                    pass

            scrollable_frame.bind("<Enter>", _on_enter)
            scrollable_frame.bind("<Leave>", _on_leave)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # --- CARD 1: OVERVIEW ---
            risk_color = "#D32F2F" if result.get('prediction') == 2 else "#FBC02D" if result.get('prediction') == 1 else "#388E3C"
            # Adjust bg color based on theme
            if hasattr(self.app, 'current_theme') and self.app.current_theme == "dark":
                bg_color = "#450a0a" if result.get('prediction') == 2 else "#422006" if result.get('prediction') == 1 else "#052e16"
                card_bg = colors.get("surface", "#1E293B")
                text_color = colors.get("text_primary", "#F8FAFC")
                subtext_color = colors.get("text_secondary", "#94A3B8")
            else:
                bg_color = "#FFEBEE" if result.get('prediction') == 2 else "#FFFDE7" if result.get('prediction') == 1 else "#E8F5E9"
                card_bg = "white"
                text_color = "#333333"
                subtext_color = "#555"
            
            card1 = tk.Frame(scrollable_frame, bg=card_bg, bd=1, relief="solid")
            card1.pack(fill="x", padx=20, pady=10)
            
            # Header
            header_frame = tk.Frame(card1, bg=risk_color, height=80)
            header_frame.pack(fill="x")
            
            tk.Label(
                header_frame, 
                text=result.get('prediction_label', 'Unknown').upper(), 
                font=("Arial", 18, "bold"),
                bg=risk_color,
                fg="white"
            ).pack(pady=10)
            
            tk.Label(
                header_frame,
                text=f"Confidence: {result.get('confidence', 0):.1%}",
                font=("Arial", 12),
                bg=risk_color,
                fg="white"
            ).pack(pady=(0, 10))

            tk.Label(
                card1, 
                text="Based on your inputs, the AI model suggests:", 
                font=("Arial", 11, "italic"),
                bg=card_bg,
                fg=subtext_color
            ).pack(pady=15)

            # --- CARD 2: ACTION PLAN ---
            tk.Label(scrollable_frame, text="RECOMMENDED ACTIONS", font=("Arial", 14, "bold"), 
                     bg=colors.get("bg", "#F5F5F5"), fg=colors.get("text_primary", "#333")).pack(anchor="w", padx=25, pady=(15,5))
            
            card2 = tk.Frame(scrollable_frame, bg=card_bg, bd=0, highlightbackground=colors.get("border", "#ddd"), highlightthickness=1)
            card2.pack(fill="x", padx=20)

            if 'recommendations' in result and result['recommendations']:
                for tip in result['recommendations']:
                    row = tk.Frame(card2, bg="white")
                    row.pack(fill="x", pady=10, padx=15)
                    
                    tk.Label(row, text="≡ƒö╣", font=("Arial", 12), bg="white", fg=risk_color).pack(side="left", anchor="n")
                    tk.Label(
                        row, 
                        text=tip, 
                        font=("Arial", 11), 
                        bg="white", 
                        fg="#333", 
                        wraplength=500, 
                        justify="left"
                    ).pack(side="left", padx=10)
            else:
                tk.Label(card2, text="No specific recommendations available.", bg="white").pack(pady=20)

            # --- CARD 3: TOP FACTORS ---
            tk.Label(scrollable_frame, text="INFLUENCING FACTORS", font=("Arial", 14, "bold"), 
                     bg=colors.get("bg", "#F5F5F5"), fg=colors.get("text_primary", "#333")).pack(anchor="w", padx=25, pady=(20,5))
            
            card3 = tk.Frame(scrollable_frame, bg=card_bg, bd=0, highlightbackground=colors.get("border", "#ddd"), highlightthickness=1)
            card3.pack(fill="x", padx=20, pady=10)

            # Filter out non-5-point scale features for clean visualization
            visual_features = result.get('features', {})
            if visual_features:
                visual_features = {k: v for k, v in visual_features.items() 
                                 if k not in ['total_score', 'age', 'average_score']}
            
            sorted_features = sorted(visual_features.items(), key=lambda x: result.get('feature_importance', {}).get(x[0], 0), reverse=True)[:3]
            
            for feature, value in sorted_features:
                imp = result.get('feature_importance', {}).get(feature, 0)
                f_name = feature.replace('_', ' ').title()
                
                f_row = tk.Frame(card3, bg=card_bg)
                f_row.pack(fill="x", pady=8, padx=15)
                
                # Label Row (Name + Value)
                label_row = tk.Frame(f_row, bg=card_bg)
                label_row.pack(fill="x", pady=(0, 2))
                
                tk.Label(
                    label_row, 
                    text=f_name, 
                    font=("Segoe UI", 11, "bold"), 
                    bg=card_bg, 
                    fg=text_color
                ).pack(side="left")
                
                # Format Score
                if feature == 'sentiment_score':
                    score_text = f"{value:+.1f}"
                elif feature == 'total_score':
                    score_text = f"{value/25*100:.0f}/100"
                else:
                    # Assume 5-point scale
                    score_text = f"{value*20:.0f}/100"
                
                tk.Label(
                    label_row, 
                    text=score_text, 
                    font=("Segoe UI", 11, "bold"), 
                    bg=card_bg, 
                    fg=subtext_color
                ).pack(side="right")
                
                # Progress Bar
                bar_bg = tk.Frame(f_row, bg="#F0F2F5", height=12, width=400)
                bar_bg.pack(fill="x", pady=2)
                bar_bg.pack_propagate(False)
                
                fill_width = int(520 * imp * 3.5) # Scale to available width
                # Note: fill_width is relative to parent, simplified here as frame width isn't fixed yet
                # We use a fractional width approach or fixed max
                
                tk.Frame(
                    bar_bg, 
                    bg="#4CAF50" if imp < 0.1 else "#2196F3" if imp < 0.3 else "#FF9800", # Color by impact
                    height=12, 
                    width=fill_width
                ).pack(side="left")

            # Close Button
            btn_close = tk.Button(
                scrollable_frame,
                text="Close Analysis",
                command=popup.destroy,
                font=("Segoe UI", 12, "bold"),
                bg="#546E7A", # Blue Grey
                fg="white", 
                activebackground="#455A64",
                activeforeground="white",
                relief="flat",
                cursor="hand2",
                width=20,
                pady=10
            )
            btn_close.pack(pady=30)
            
            # Hover for close
            btn_close.bind("<Enter>", lambda e: btn_close.configure(bg="#455A64"))
            btn_close.bind("<Leave>", lambda e: btn_close.configure(bg="#546E7A"))
            
        except Exception as e:
            logging.error("AI Analysis failed", exc_info=True)
            messagebox.showerror("Analysis Error", f"Could not generate AI report.\n{e}")

    def show_history_screen(self):
        """Show history of all tests for the current user"""
        self.app.clear_screen()
        
        colors = self.app.colors
        
        # Header with back button
        header_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        header_frame.pack(pady=10, fill="x")
        
        tk.Button(
            header_frame,
            text="← Back",
            command=self.app.create_welcome_screen,
            font=("Arial", 10),
            bg=colors.get("surface", "#1E293B"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(side="left", padx=10)
        
        tk.Label(
            header_frame,
            text="Test History" + (f" for {self.app.username}" if self.app.username else ""),
            font=("Arial", 16, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(side="left", padx=50)
        
        conn = get_connection()
        cursor = conn.cursor()

        # Get history data
        if not self.app.username:
            cursor.execute(
                """
                SELECT DISTINCT username FROM scores 
                ORDER BY timestamp DESC 
                LIMIT 5
                """
            )
            users = cursor.fetchall()
            
            if not users:
                tk.Label(
                    self.app.root,
                    text="No test history found. Please take a test first.",
                    font=("Arial", 12),
                    bg=colors.get("bg", "#0F172A"),
                    fg=colors.get("text_primary", "#F8FAFC")
                ).pack(pady=50)
                
                tk.Button(
                    self.app.root,
                    text="Back to Main",
                    command=self.app.create_welcome_screen,
                    font=("Arial", 12)
                ).pack(pady=20)
                return
            
            # Show user selection
            user_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
            user_frame.pack(pady=20)
            
            tk.Label(
                user_frame,
                text="Select a user to view their history:",
                font=("Arial", 12),
                bg=colors.get("bg", "#0F172A"),
                fg=colors.get("text_primary", "#F8FAFC")
            ).pack(pady=10)
            
            for user in users:
                username = user[0]
                user_btn = tk.Button(
                    user_frame,
                    text=username,
                    command=lambda u=username: self.view_user_history(u),
                    font=("Arial", 12),
                    width=20
                )
                user_btn.pack(pady=5)
            
            return
        
        # If username is set, show that user's history
        self.display_user_history(self.app.username)

    def view_user_history(self, username):
        """View history for a specific user"""
        self.app.username = username
        self.display_user_history(username)

    def display_user_history(self, username):
        """Display history for a specific user"""
        self.app.clear_screen()
        
        colors = self.app.colors
        
        conn = get_connection()
        cursor = conn.cursor()

        # Get history data
        cursor.execute(
            """
            SELECT id, total_score, age, timestamp 
            FROM scores 
            WHERE username = ? 
            ORDER BY timestamp DESC
            """,
            (username,)
        )
        history = cursor.fetchall()
        
        # Header with back button
        header_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        header_frame.pack(pady=10, fill="x")
        
        tk.Button(
            header_frame,
            text="← Back",
            command=self.show_history_screen,
            font=("Arial", 10),
            bg=colors.get("surface", "#1E293B"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(side="left", padx=10)
        
        tk.Label(
            header_frame,
            text=f"Test History for {username}",
            font=("Arial", 16, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(side="left", padx=50)
        
        if not history:
            tk.Label(
                self.app.root,
                text="No test history found.",
                font=("Arial", 12),
                bg=colors.get("bg", "#0F172A"),
                fg=colors.get("text_primary", "#F8FAFC")
            ).pack(pady=50)
            
            tk.Button(
                self.app.root,
                text="Back to History",
                command=self.show_history_screen,
                font=("Arial", 12)
            ).pack(pady=20)
            return
        
        # Get user_id for Deep Dive results
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        user_id = row[0] if row else None

        deep_dives = []
        if user_id:
            cursor.execute(
                "SELECT assessment_type, total_score, timestamp, details FROM assessment_results WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,)
            )
            deep_dives = cursor.fetchall()

        # Create scrollable frame for history
        canvas = tk.Canvas(self.app.root, bg=colors.get("bg", "#0F172A"), highlightthickness=0)
        scrollbar = tk.Scrollbar(self.app.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=colors.get("bg", "#0F172A"))
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # --- SECTION: STANDARD EQ TESTS ---
        tk.Label(scrollable_frame, text="Standard EQ Assessments", font=("Arial", 14, "bold"), 
                 bg=colors.get("bg", "#0F172A"), fg=colors.get("text_primary", "#F8FAFC")).pack(anchor="w", padx=20, pady=(10, 5))

        # Display each test result
        for idx, (test_id, score, age, timestamp) in enumerate(history):
            # Calculate percentage (stateless approximation based on current settings)
            # Ideally max_score should be stored in DB, but falling back to settings for now
            question_count = self.app.settings.get("question_count", 10)
            max_score = question_count * 4
            percentage = (score / max_score) * 100 if max_score > 0 else 0
            
            test_frame = tk.Frame(scrollable_frame, bg=colors.get("surface", "#1E293B"), relief="groove", borderwidth=2)
            test_frame.pack(fill="x", padx=20, pady=5)
            
            # Format date
            try:
                date_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
            except:
                date_str = str(timestamp)
            
            # Test info
            info_frame = tk.Frame(test_frame, bg=colors.get("surface", "#1E293B"))
            info_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(
                info_frame,
                text=f"Test #{test_id}",
                font=("Arial", 11, "bold"),
                anchor="w",
                bg=colors.get("surface", "#1E293B"),
                fg=colors.get("text_primary", "#F8FAFC")
            ).pack(side="left", padx=5)
            
            tk.Label(
                info_frame,
                text=f"Score: {score}/{max_score} ({percentage:.1f}%)",
                font=("Arial", 10),
                anchor="w",
                bg=colors.get("surface", "#1E293B"),
                fg=colors.get("text_primary", "#F8FAFC")
            ).pack(side="left", padx=20)
            
            if age:
                tk.Label(
                    info_frame,
                    text=f"Age: {age}",
                    font=("Arial", 10),
                    anchor="w",
                    bg=colors.get("surface", "#1E293B"),
                    fg=colors.get("text_primary", "#F8FAFC")
                ).pack(side="left", padx=20)
            
            tk.Label(
                info_frame,
                text=date_str,
                font=("Arial", 9),
                anchor="w",
                bg=colors.get("surface", "#1E293B"),
                fg=colors.get("text_secondary", "#94A3B8")
            ).pack(side="right", padx=5)
            
            # Progress bar visualization
            progress_frame = tk.Frame(test_frame, bg=colors.get("surface", "#1E293B"))
            progress_frame.pack(fill="x", padx=10, pady=2)
            
            # Progress bar using tkinter canvas
            bar_canvas = tk.Canvas(progress_frame, height=20, bg=colors.get("bg", "#0F172A"), highlightthickness=0)
            bar_canvas.pack(fill="x")
            
            # Draw progress bar
            bar_width = 300
            fill_width = (percentage / 100) * bar_width
            
            # Background
            bar_canvas.create_rectangle(0, 0, bar_width, 20, fill="#cccccc", outline="")
            # Fill (green for current/latest test, blue for others)
            fill_color = "#4CAF50" if idx == 0 else "#2196F3"
            bar_canvas.create_rectangle(0, 0, fill_width, 20, fill=fill_color, outline="")
            # Percentage text
            text_color = "white"
            bar_canvas.create_text(bar_width/2, 10, text=f"{percentage:.1f}%", fill=text_color)
        
        # --- SECTION: DEEP DIVE ASSESSMENTS ---
        if deep_dives:
            tk.Label(scrollable_frame, text="Deep Dive Insights", font=("Arial", 14, "bold"), 
                     bg=colors.get("bg", "#0F172A"), fg=colors.get("text_primary", "#F8FAFC")).pack(anchor="w", padx=20, pady=(20, 5))
            
            for d_type, d_score, d_ts, d_details in deep_dives:
                dd_frame = tk.Frame(scrollable_frame, bg=colors.get("surface", "#1E293B"), relief="groove", borderwidth=1)
                dd_frame.pack(fill="x", padx=20, pady=5)
                
                # Header
                h_frame = tk.Frame(dd_frame, bg=colors.get("surface", "#1E293B"))
                h_frame.pack(fill="x", padx=10, pady=8)
                
                type_map = {
                    "career_clarity": "🚀 Career Clarity",
                    "work_satisfaction": "💼 Work Satisfaction",
                    "strengths_deep_dive": "💪 Strengths Finder"
                }
                title = type_map.get(d_type, d_type.replace("_", " ").title())
                
                tk.Label(h_frame, text=title, font=("Segoe UI", 12, "bold"), bg=colors.get("surface", "#1E293B"), 
                         fg=colors.get("text_primary", "#F8FAFC")).pack(side="left")
                         
                tk.Label(h_frame, text=f"Score: {d_score}/100", font=("Segoe UI", 12, "bold"), 
                         bg=colors.get("surface", "#1E293B"), fg=colors.get("primary", "#3B82F6")).pack(side="right")
                
                # Date
                try:
                    d_date = datetime.fromisoformat(d_ts).strftime("%Y-%m-%d %H:%M")
                except:
                    d_date = str(d_ts)
                tk.Label(h_frame, text=d_date, font=("Segoe UI", 9), bg=colors.get("surface", "#1E293B"), 
                         fg=colors.get("text_secondary", "#94A3B8")).pack(side="right", padx=15)

                # Details Expander (Static for now)
                # Parse JSON if needed, but simple score is enough for summary

        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        button_frame.pack(pady=20)
        
        if len(history) >= 2:
            tk.Button(
                button_frame,
                text="Compare All Tests",
                command=self.show_comparison_screen,
                font=("Arial", 12)
            ).pack(side="left", padx=10)
        
        tk.Button(
            button_frame,
            text="Back to Main",
            command=self.app.create_welcome_screen,
            font=("Arial", 12)
        ).pack(side="left", padx=10)

    def show_comparison_screen(self):
        """Show visual comparison of current test with previous attempts"""
        self.app.clear_screen()
        
        colors = self.app.colors
        
        conn = get_connection()
        cursor = conn.cursor()

        # Get all test data for the current user
        cursor.execute(
            """
            SELECT id, total_score, timestamp 
            FROM scores 
            WHERE username = ? 
            ORDER BY timestamp ASC
            """,
            (self.app.username,)
        )
        all_tests = cursor.fetchall()
        
        if len(all_tests) < 2:
            messagebox.showinfo("No Comparison", "You need at least 2 tests to compare.")
            self.app.create_welcome_screen()
            return
        
        # Header with back button
        header_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        header_frame.pack(pady=10, fill="x")
        
        tk.Button(
            header_frame,
            text="← Back",
            command=self.show_history_screen,
            font=("Arial", 10),
            bg=colors.get("surface", "#1E293B"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(side="left", padx=10)
        
        tk.Label(
            header_frame,
            text=f"Test Comparison for {self.app.username}",
            font=("Arial", 16, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(side="left", padx=50)
        
        tk.Label(
            self.app.root,
            text=f"Showing {len(all_tests)} tests over time",
            font=("Arial", 12),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=5)
        
        # Prepare data for visualization
        test_numbers = list(range(1, len(all_tests) + 1))
        scores = [test[1] for test in all_tests]
        # Use settings for consistency
        question_count = self.app.settings.get("question_count", 10)
        max_score = question_count * 4
        percentages = [(score / max_score) * 100 if max_score > 0 else 0 for score in scores]
        
        # Create main comparison frame
        comparison_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        comparison_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Left side: Bar chart visualization
        left_frame = tk.Frame(comparison_frame, bg=colors.get("bg", "#0F172A"))
        left_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        tk.Label(
            left_frame,
            text="Score Comparison",
            font=("Arial", 14, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=10)
        
        # Create bar chart using tkinter canvas
        chart_canvas = tk.Canvas(left_frame, bg=colors.get("chart_bg", "#1E293B"), height=300)
        chart_canvas.pack(fill="both", expand=True, pady=10)
        
        # Draw bar chart
        chart_width = 400
        chart_height = 250
        bar_width = 30
        spacing = 20
        
        # Find max value for scaling
        max_value = max(scores)
        scale_factor = chart_height * 0.8 / max_value if max_value > 0 else 1
        
        # Draw bars
        for i, (test_num, score, percentage) in enumerate(zip(test_numbers, scores, percentages)):
            x = i * (bar_width + spacing) + 50
            bar_height = score * scale_factor
            y = chart_height - bar_height
            
            # Color: green for current/latest test, blue for others
            color = "#22C55E" if i == len(test_numbers) - 1 else "#3B82F6"
            
            # Draw bar
            chart_canvas.create_rectangle(x, y, x + bar_width, chart_height, fill=color, outline="black")
            
            # Draw test number below bar
            chart_canvas.create_text(x + bar_width/2, chart_height + 15, 
                                   text=f"Test {test_num}", 
                                   fill=colors.get("chart_fg", "#F8FAFC"))
            
            # Draw score above bar
            chart_canvas.create_text(x + bar_width/2, y - 15, 
                                   text=f"{score}", 
                                   fill=colors.get("chart_fg", "#F8FAFC"), 
                                   font=("Arial", 10, "bold"))
            
            # Draw percentage inside bar
            chart_canvas.create_text(x + bar_width/2, y + bar_height/2, 
                                   text=f"{percentage:.0f}%", 
                                   fill="white", 
                                   font=("Arial", 9, "bold"))
        
        # Draw Y-axis labels
        for i in range(0, max_score + 1, 10):
            y = chart_height - (i * scale_factor)
            chart_canvas.create_text(30, y, text=str(i), fill=colors.get("chart_fg", "#F8FAFC"))
            chart_canvas.create_line(40, y, 45, y, fill=colors.get("chart_fg", "#F8FAFC"))
        
        chart_canvas.create_text(20, 15, text="Score", fill=colors.get("chart_fg", "#F8FAFC"), angle=90)
        
        # Right side: Statistics and improvement
        right_frame = tk.Frame(comparison_frame, bg=colors.get("bg", "#0F172A"))
        right_frame.pack(side="right", fill="both", expand=True, padx=10)
        
        tk.Label(
            right_frame,
            text="Statistics & Improvement",
            font=("Arial", 14, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=10)
        
        # Calculate statistics
        first_score = scores[0]
        last_score = scores[-1]
        best_score = max(scores)
        worst_score = min(scores)
        avg_score = sum(scores) / len(scores)
        improvement = last_score - first_score
        improvement_percent = ((last_score - first_score) / first_score * 100) if first_score > 0 else 0
        
        # Display statistics
        stats_text = f"""
        First Test: {first_score} ({percentages[0]:.1f}%)
        Latest Test: {last_score} ({percentages[-1]:.1f}%)
        Best Score: {best_score} ({max(percentages):.1f}%)
        Worst Score: {worst_score} ({min(percentages):.1f}%)
        Average: {avg_score:.1f} ({(sum(percentages)/len(percentages)):.1f}%)
        """
        
        stats_label = tk.Label(
            right_frame,
            text=stats_text.strip(),
            font=("Arial", 12),
            justify="left",
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        )
        stats_label.pack(pady=10, padx=20, anchor="w")
        
        # Improvement indicator
        improvement_frame = tk.Frame(right_frame, bg=colors.get("bg", "#0F172A"))
        improvement_frame.pack(pady=20, padx=20, fill="x")
        
        improvement_color = "#22C55E" if improvement > 0 else "#EF4444" if improvement < 0 else "#F59E0B"
        improvement_symbol = "↑" if improvement > 0 else "↓" if improvement < 0 else "→"
        
        tk.Label(
            improvement_frame,
            text="Overall Improvement:",
            font=("Arial", 12, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(anchor="w")
        
        improvement_text = f"{improvement_symbol} {improvement:+.1f} points ({improvement_percent:+.1f}%)"
        improvement_label = tk.Label(
            improvement_frame,
            text=improvement_text,
            font=("Arial", 12, "bold"),
            fg=improvement_color,
            bg=colors.get("bg", "#0F172A")
        )
        improvement_label.pack(pady=5)
        
        # Interpretation of improvement
        if improvement > 10:
            interpretation = "Excellent progress! Keep up the good work."
        elif improvement > 5:
            interpretation = "Good improvement. You're getting better!"
        elif improvement > 0:
            interpretation = "Slight improvement. Every bit counts!"
        elif improvement == 0:
            interpretation = "Consistent performance. Try to push further next time."
        else:
            interpretation = "Need to focus on improvement. Review your responses."
        
        tk.Label(
            improvement_frame,
            text=interpretation,
            font=("Arial", 10),
            wraplength=200,
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(pady=10)
        
        # Trend visualization (simple arrow indicators)
        trend_frame = tk.Frame(right_frame, bg=colors.get("bg", "#0F172A"))
        trend_frame.pack(pady=10)
        
        tk.Label(
            trend_frame,
            text="Score Trend:",
            font=("Arial", 11, "bold"),
            bg=colors.get("bg", "#0F172A"),
            fg=colors.get("text_primary", "#F8FAFC")
        ).pack(anchor="w")
        
        # Create simple trend line
        trend_canvas = tk.Canvas(trend_frame, width=200, height=80, bg=colors.get("chart_bg", "#1E293B"))
        trend_canvas.pack(pady=10)
        
        # Draw trend line
        points = []
        for i, percentage in enumerate(percentages):
            x = i * (180 / (len(percentages) - 1)) + 10 if len(percentages) > 1 else 100
            y = 70 - (percentage * 60 / 100)
            points.append((x, y))
        
        if len(points) > 1:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                color = "#22C55E" if y2 < y1 else "#EF4444" if y2 > y1 else "#F59E0B"
                trend_canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
        
        for i, (x, y) in enumerate(points):
            color = "#22C55E" if i == len(points) - 1 else "#3B82F6"
            trend_canvas.create_oval(x-3, y-3, x+3, y+3, fill=color, outline="black")
        
        # Buttons at bottom
        button_frame = tk.Frame(self.app.root, bg=colors.get("bg", "#0F172A"))
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="View Detailed History",
            command=self.show_history_screen,
            font=("Arial", 12)
        ).pack(side="left", padx=10)
        
        tk.Button(
            button_frame,
            text="Take Another Test",
            command=self.reset_test,
            font=("Arial", 12)
        ).pack(side="left", padx=10)
        
        tk.Button(
            button_frame,
            text="Back to Main",
            command=self.app.create_welcome_screen,
            font=("Arial", 12)
        ).pack(side="left", padx=10)

    def reset_test(self):
        """Reset test variables and start over"""
        # Only clear user info if NOT logged in
        if not self.app.current_user_id:
            self.app.username = ""
            self.app.age = None
            self.app.age_group = None
            self.app.profession = None
            
        self.app.current_question = 0
        self.app.responses = []
        self.app.current_score = 0
        self.app.current_max_score = 0
        self.app.current_percentage = 0
        
        # Start fresh
        if self.app.current_user_id:
            self.app.start_test()
        else:
            self.app.auth.create_username_screen()