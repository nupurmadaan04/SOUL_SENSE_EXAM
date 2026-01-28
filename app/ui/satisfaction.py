# app/ui/satisfaction.py - Fixed version
import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
from typing import List, Optional
import logging

from app.db import get_session
from app.models import SatisfactionRecord
from app.questions import SATISFACTION_QUESTIONS, SATISFACTION_OPTIONS
from app.i18n_manager import get_i18n

class SatisfactionSurvey:
    """Modal survey for work/study satisfaction"""
    
    def __init__(self, parent, username: str, user_id: Optional[int] = None, 
                 eq_score_id: Optional[int] = None, language: str = "en"):
        self.parent = parent
        self.username = username
        self.user_id = user_id
        self.eq_score_id = eq_score_id
        self.language = language
        self.i18n = get_i18n()
        self.responses = {}
        self.window = None
        
    def show(self):
        """Show the satisfaction survey as modal dialog"""
        self.window = tk.Toplevel(self.parent)
        
        # FIXED: Use window title directly (simplified)
        self.window.title("Work/Study Satisfaction Survey")
        self.window.geometry("700x800")
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Make it modal
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Apply theme - FIXED: Don't use UIStyles if it causes issues
        try:
            # Simple theme application without UIStyles
            from app.ui.styles import UIStyles
            # Create a dummy object with root attribute
            class DummyApp:
                def __init__(self, window):
                    self.root = window
                    self.current_theme = "light"
            
            dummy_app = DummyApp(self.window)
            styles = UIStyles(dummy_app)
            styles.apply_theme("light")
        except ImportError:
            # Fallback to basic styling
            self.window.configure(bg="white")
        except Exception as e:
            logging.warning(f"Could not apply theme to satisfaction survey: {e}")
            self.window.configure(bg="white")
        
        # Create scrollable canvas
        self.canvas = tk.Canvas(self.window, highlightthickness=0, bg="white")
        scrollbar = tk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        scrollable_frame = tk.Frame(self.canvas, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=680)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            if self.canvas and self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Build survey
        self._build_survey(scrollable_frame)
        
        # Pack layout
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Center window
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - 700) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - 800) // 2
        self.window.geometry(f"+{x}+{y}")
        
    def _build_survey(self, parent):
        """Build survey questions"""
        # Header
        header_frame = tk.Frame(parent, bg="#3B82F6")
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            header_frame,
            text="💼 Work/Study Satisfaction Survey",
            font=("Segoe UI", 16, "bold"),
            bg="#3B82F6",
            fg="white"
        ).pack(pady=20)
        
        tk.Label(
            header_frame,
            text="Help us understand your professional/academic satisfaction",
            font=("Segoe UI", 11),
            bg="#3B82F6",
            fg="white"
        ).pack(pady=(0, 20))
        
        # Question 1: Overall Satisfaction (1-10)
        q1_frame = tk.Frame(parent, relief=tk.GROOVE, bd=2, bg="white")
        q1_frame.pack(fill="x", padx=20, pady=10)
        
        # Get question text safely
        q1_text = SATISFACTION_QUESTIONS.get("satisfaction_level", {}).get(self.language, 
                    "Overall, how satisfied are you with your current work or study situation?")
        
        tk.Label(
            q1_frame,
            text="1. " + q1_text,
            font=("Segoe UI", 12, "bold"),
            wraplength=600,
            justify="left",
            bg="white"
        ).pack(anchor="w", padx=10, pady=10)
        
        # Scale 1-10
        scale_var = tk.IntVar(value=5)
        scale_frame = tk.Frame(q1_frame, bg="white")
        scale_frame.pack(padx=10, pady=5)
        
        for i in range(1, 11):
            tk.Radiobutton(
                scale_frame,
                text=str(i),
                variable=scale_var,
                value=i,
                font=("Segoe UI", 10),
                bg="white",
                command=lambda v=i: self.responses.update({"satisfaction_score": v})
            ).pack(side="left", padx=3)
        
        self.responses["satisfaction_score"] = 5
        
        # Labels for scale ends
        labels_frame = tk.Frame(q1_frame, bg="white")
        labels_frame.pack(padx=10, pady=5)
        
        tk.Label(
            labels_frame,
            text="Very Dissatisfied",
            font=("Segoe UI", 9, "italic"),
            fg="#666666",
            bg="white"
        ).pack(side="left")
        
        tk.Label(
            labels_frame,
            text="Very Satisfied",
            font=("Segoe UI", 9, "italic"),
            fg="#666666",
            bg="white"
        ).pack(side="right")
        
        # Question 2: Context
        q2_frame = tk.Frame(parent, relief=tk.GROOVE, bd=2, bg="white")
        q2_frame.pack(fill="x", padx=20, pady=10)
        
        q2_text = SATISFACTION_QUESTIONS.get("satisfaction_context", {}).get(self.language,
                    "Which of the following best describes your current situation?")
        
        tk.Label(
            q2_frame,
            text="2. " + q2_text,
            font=("Segoe UI", 12, "bold"),
            wraplength=600,
            justify="left",
            bg="white"
        ).pack(anchor="w", padx=10, pady=10)
        
        context_var = tk.StringVar()
        context_options = SATISFACTION_OPTIONS.get("context_options", {}).get(self.language, [
            "Full-time employment",
            "Part-time employment", 
            "Self-employed/Freelancer",
            "Full-time student",
            "Part-time student",
            "Unemployed seeking work",
            "Other"
        ])
        
        for i, option in enumerate(context_options):
            tk.Radiobutton(
                q2_frame,
                text=option,
                variable=context_var,
                value=option,
                font=("Segoe UI", 10),
                bg="white",
                command=lambda v=option: self.responses.update({"context": v})
            ).pack(anchor="w", padx=20, pady=2)
        
        self.responses["context"] = context_options[0] if context_options else ""
        
        # Question 3: Positive Factors (Checkboxes)
        q3_frame = tk.Frame(parent, relief=tk.GROOVE, bd=2, bg="white")
        q3_frame.pack(fill="x", padx=20, pady=10)
        
        q3_text = SATISFACTION_QUESTIONS.get("positive_factors", {}).get(self.language,
                    "What are the most positive aspects? (Select all that apply)")
        
        tk.Label(
            q3_frame,
            text="3. " + q3_text,
            font=("Segoe UI", 12, "bold"),
            wraplength=600,
            justify="left",
            bg="white"
        ).pack(anchor="w", padx=10, pady=10)
        
        positive_options = SATISFACTION_OPTIONS.get("positive_factor_options", {}).get(self.language, [
            "Good salary/compensation",
            "Work-life balance",
            "Supportive colleagues/peers",
            "Interesting/challenging work",
            "Career growth opportunities",
            "Flexible schedule",
            "Good management/supervision",
            "Positive work environment",
            "Learning opportunities"
        ])
        
        for option in positive_options:
            var = tk.BooleanVar()
            tk.Checkbutton(
                q3_frame,
                text=option,
                variable=var,
                font=("Segoe UI", 10),
                bg="white",
                onvalue=True,
                offvalue=False,
                command=lambda v=var, o=option: self._update_list("positive_factors", o, v.get())
            ).pack(anchor="w", padx=20, pady=2)
        
        # Question 4: Negative Factors
        q4_frame = tk.Frame(parent, relief=tk.GROOVE, bd=2, bg="white")
        q4_frame.pack(fill="x", padx=20, pady=10)
        
        q4_text = SATISFACTION_QUESTIONS.get("negative_factors", {}).get(self.language,
                    "What are the most challenging aspects? (Select all that apply)")
        
        tk.Label(
            q4_frame,
            text="4. " + q4_text,
            font=("Segoe UI", 12, "bold"),
            wraplength=600,
            justify="left",
            bg="white"
        ).pack(anchor="w", padx=10, pady=10)
        
        negative_options = SATISFACTION_OPTIONS.get("negative_factor_options", {}).get(self.language, [
            "Low salary/compensation",
            "Poor work-life balance",
            "Toxic work environment",
            "Lack of career growth",
            "Unsupportive management",
            "High stress levels",
            "Lack of recognition",
            "Poor communication",
            "Unclear expectations"
        ])
        
        for option in negative_options:
            var = tk.BooleanVar()
            tk.Checkbutton(
                q4_frame,
                text=option,
                variable=var,
                font=("Segoe UI", 10),
                bg="white",
                onvalue=True,
                offvalue=False,
                command=lambda v=var, o=option: self._update_list("negative_factors", o, v.get())
            ).pack(anchor="w", padx=20, pady=2)
        
        # Question 5: Improvement Suggestions
        q5_frame = tk.Frame(parent, relief=tk.GROOVE, bd=2, bg="white")
        q5_frame.pack(fill="x", padx=20, pady=10)
        
        q5_text = SATISFACTION_QUESTIONS.get("improvement_suggestions", {}).get(self.language,
                    "What would most improve your satisfaction?")
        
        tk.Label(
            q5_frame,
            text="5. " + q5_text,
            font=("Segoe UI", 12, "bold"),
            wraplength=600,
            justify="left",
            bg="white"
        ).pack(anchor="w", padx=10, pady=10)
        
        improvement_var = tk.StringVar()
        improvement_options = SATISFACTION_OPTIONS.get("improvement_options", {}).get(self.language, [
            "Better compensation",
            "More flexible hours",
            "Clearer career path",
            "Better management",
            "More training/development",
            "Improved work environment",
            "Better work-life balance",
            "More recognition/feedback"
        ])
        
        for option in improvement_options:
            tk.Radiobutton(
                q5_frame,
                text=option,
                variable=improvement_var,
                value=option,
                font=("Segoe UI", 10),
                bg="white",
                command=lambda v=option: self.responses.update({"improvement_suggestion": v})
            ).pack(anchor="w", padx=20, pady=2)
        
        # Duration (optional)
        q6_frame = tk.Frame(parent, relief=tk.GROOVE, bd=2, bg="white")
        q6_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(
            q6_frame,
            text="6. How many months have you been in this role/study program? (Optional)",
            font=("Segoe UI", 12, "bold"),
            wraplength=600,
            justify="left",
            bg="white"
        ).pack(anchor="w", padx=10, pady=10)
        
        duration_frame = tk.Frame(q6_frame, bg="white")
        duration_frame.pack(padx=20, pady=5)
        
        duration_var = tk.StringVar()
        tk.Entry(
            duration_frame,
            textvariable=duration_var,
            width=10,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=5)
        
        tk.Label(
            duration_frame,
            text="months",
            font=("Segoe UI", 10),
            bg="white"
        ).pack(side="left")
        
        # Submit Button
        submit_frame = tk.Frame(parent, bg="white")
        submit_frame.pack(pady=30)
        
        tk.Button(
            submit_frame,
            text="Submit Survey",
            command=self.submit,
            font=("Segoe UI", 12, "bold"),
            bg="#10B981",
            fg="white",
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack()
        
        tk.Button(
            submit_frame,
            text="Skip for Now",
            command=self.on_close,
            font=("Segoe UI", 10),
            bg="#EF4444",
            fg="white",
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(pady=10)
        
    def _update_list(self, key: str, item: str, add: bool):
        """Update list responses (for checkboxes)"""
        if key not in self.responses:
            self.responses[key] = []
        
        if add:
            if item not in self.responses[key]:
                self.responses[key].append(item)
        else:
            if item in self.responses[key]:
                self.responses[key].remove(item)
    
    def submit(self):
        """Submit survey results to database"""
        try:
            # Validate required fields
            if "satisfaction_score" not in self.responses:
                messagebox.showerror("Error", "Please select your overall satisfaction score.")
                return
            
            # Prepare data
            record = SatisfactionRecord(
                username=self.username,
                user_id=self.user_id,
                satisfaction_score=self.responses["satisfaction_score"],
                context=self.responses.get("context", ""),
                positive_factors=json.dumps(self.responses.get("positive_factors", [])),
                negative_factors=json.dumps(self.responses.get("negative_factors", [])),
                improvement_suggestions=self.responses.get("improvement_suggestion", ""),
                eq_score_id=self.eq_score_id
            )
            
            # Determine category
            context = self.responses.get("context", "").lower()
            if "student" in context or "study" in context:
                record.satisfaction_category = "academic"
            elif "work" in context or "employment" in context or "job" in context:
                record.satisfaction_category = "work"
            else:
                record.satisfaction_category = "other"
            
            # Save to database
            session = get_session()
            try:
                session.add(record)
                session.commit()
                
                # Show thank you message
                messagebox.showinfo(
                    "Thank You!",
                    "Thank you for completing the satisfaction survey!\n\n"
                    "Your responses will help provide better career/academic guidance."
                )
                
                # Close window
                self.on_close()
                
            except Exception as e:
                session.rollback()
                logging.error(f"Failed to save satisfaction survey: {e}")
                raise e
            finally:
                session.close()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save survey: {str(e)}")
    
    def on_close(self):
        """Close the survey window"""
        if self.window:
            try:
                # Unbind mouse wheel
                self.window.unbind_all("<MouseWheel>")
            except:
                pass
            self.window.destroy()