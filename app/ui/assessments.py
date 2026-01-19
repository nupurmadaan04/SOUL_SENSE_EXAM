
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import json
from datetime import datetime

from app.services.question_curator import QuestionCurator
from app.models import AssessmentResult, get_session

# Configure logging
logger = logging.getLogger(__name__)

class AssessmentHub:
    """
    Main Menu View for Assessments.
    Allows manual selection of Deep Dive tests.
    """
    def __init__(self, parent, app_engine):
        self.parent = parent # The content_frame from Dashboard/Main
        self.app = app_engine # The SoulSenseApp instance
        self.colors = self.app.colors
        # self.fonts = self.app.fonts # Deprecated
        
    def render(self):
        # Clear parent
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        # Title
        tk.Label(self.parent, text="Deep Dive Assessments", font=self.app.ui_styles.get_font("h1"), 
                 bg=self.colors["bg"], fg=self.colors["text_primary"]).pack(pady=(20, 10), anchor="w", padx=30)
                 
        tk.Label(self.parent, text="Explore specific areas of your life with focused assessments.", 
                 font=self.app.ui_styles.get_font("body"), bg=self.colors["bg"], fg=self.colors["text_secondary"]).pack(anchor="w", padx=30)

        # Settings Frame (Question Count)
        settings_frame = tk.Frame(self.parent, bg=self.colors["surface"], pady=10, padx=20)
        settings_frame.pack(fill="x", padx=30, pady=20)
        
        tk.Label(settings_frame, text="Session Length:", font=self.app.ui_styles.get_font("h3"), 
                 bg=self.colors["surface"], fg=self.colors["text_primary"]).pack(side="left")
        
        self.length_var = tk.StringVar(value="10")
        
        # Style radio buttons
        style = ttk.Style()
        style.configure("TRadiobutton", background=self.colors["surface"], foreground=self.colors["text_primary"], font=self.app.ui_styles.get_font("xs"),)
        
        ttk.Radiobutton(settings_frame, text="Short (5)", variable=self.length_var, value="5", style="TRadiobutton").pack(side="left", padx=10)
        ttk.Radiobutton(settings_frame, text="Medium (10)", variable=self.length_var, value="10", style="TRadiobutton").pack(side="left", padx=10)
        ttk.Radiobutton(settings_frame, text="Long (20)", variable=self.length_var, value="20", style="TRadiobutton").pack(side="left", padx=10)

        # Cards Container
        cards_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        cards_frame.pack(fill="both", expand=True, padx=30)
        
        # Render Cards
        self._create_card(cards_frame, "Career Clarity", "career_clarity", 
                          "Assess your career path, goals, and professional growth.", "🚀")
        self._create_card(cards_frame, "Work Satisfaction", "work_satisfaction", 
                          "Evaluate your happiness, stress, and fulfillment at work.", "💼")
        self._create_card(cards_frame, "Strengths Deep Dive", "strengths_deep_dive", 
                          "Identify and leverage your core personal strengths.", "💪")

    def _create_card(self, parent, title, key, desc, icon):
        card = tk.Frame(parent, bg=self.colors["surface"], padx=20, pady=20)
        card.pack(fill="x", pady=10)
        
        # Icon + Title
        header = tk.Frame(card, bg=self.colors["surface"])
        header.pack(fill="x")
        
        tk.Label(header, text=icon, font=self.app.ui_styles.get_font("xl"), bg=self.colors["surface"]).pack(side="left", padx=(0, 15))
        
        info = tk.Frame(header, bg=self.colors["surface"])
        info.pack(side="left", fill="x", expand=True)
        
        tk.Label(info, text=title, font=self.app.ui_styles.get_font("h3"), bg=self.colors["surface"], 
                 fg=self.colors["text_primary"]).pack(anchor="w")
        tk.Label(info, text=desc, font=self.app.ui_styles.get_font("body"), bg=self.colors["surface"], 
                 fg=self.colors["text_secondary"], wraplength=500, justify="left").pack(anchor="w", pady=(5,0))
        
        # Action Button
        btn = tk.Button(header, text="Start", font=self.app.ui_styles.get_font("xs", "bold"),
                        bg=self.colors["primary"], fg="#fff", width=12,
                        command=lambda: self.start_assessment(key))
        btn.pack(side="right")

    def start_assessment(self, assessment_type):
        count = int(self.length_var.get())
        
        # Use embedded runner
        AssessmentRunnerView(self.parent, self.app, assessment_type, count, on_finish=self.render)

class RecommendationView:
    """
    Post-Exam View (Embedded).
    Recommends Deep Dives based on results.
    """
    def __init__(self, parent, app, recommendations, callback_done):
        self.parent = parent
        self.app = app
        self.colors = app.colors
        self.callback_done = callback_done # Function to call when closed/finished
        self.recommendations = recommendations
        self.selected_tests = {} # map key -> BooleanVar
        
        self._render()

    def _render(self):
        # Clear screen first
        for widget in self.parent.winfo_children():
            widget.destroy()

        # Header
        tk.Label(self.parent, text="🔍 One More Thing...", font=self.app.ui_styles.get_font("xl", "bold"),
                 bg=self.colors["bg"], fg=self.colors["text_primary"]).pack(pady=(40, 20))
                 
        tk.Label(self.parent, text="Based on your results, we recommend a deep dive:", 
                 font=self.app.ui_styles.get_font("md"), bg=self.colors["bg"], fg=self.colors["text_secondary"]).pack()
                 
        # Content
        frame = tk.Frame(self.parent, bg=self.colors["bg"], pady=40)
        frame.pack(fill="both", expand=True, padx=80)
        
        DISPLAY_NAMES = {
            "career_clarity": "Career Clarity Check 🚀",
            "work_satisfaction": "Work Satisfaction Audit 💼",
            "strengths_deep_dive": "Strengths Finder 💪"
        }
        
        # Checkboxes for recommended tests
        for rec in self.recommendations:
            var = tk.BooleanVar(value=True) # Check by default
            self.selected_tests[rec] = var
            
            cb = tk.Checkbutton(frame, text=DISPLAY_NAMES.get(rec, rec), variable=var,
                                font=self.app.ui_styles.get_font("md"), bg=self.colors["bg"], fg=self.colors["text_primary"],
                                selectcolor=self.colors["bg"], activebackground=self.colors["bg"])
            cb.pack(anchor="w", pady=10)
            
        # Other options (collapsed or smaller)
        other_lbl = tk.Label(frame, text="Or choose another:", font=self.app.ui_styles.get_font("sm", "bold"), 
                 bg=self.colors["bg"], fg=self.colors["text_secondary"])
        other_lbl.pack(anchor="w", pady=(30, 10))
        
        all_types = ["career_clarity", "work_satisfaction", "strengths_deep_dive"]
        for t in all_types:
            if t not in self.recommendations:
                var = tk.BooleanVar(value=False)
                self.selected_tests[t] = var
                tk.Checkbutton(frame, text=DISPLAY_NAMES.get(t, t).replace(" 🚀", "").replace(" 💼", "").replace(" 💪", ""), 
                              variable=var, font=self.app.ui_styles.get_font("sm"), bg=self.colors["bg"], fg=self.colors["text_secondary"],
                              selectcolor=self.colors["bg"]).pack(anchor="w")

        # Length Selector
        len_frame = tk.Frame(self.parent, bg=self.colors["bg"])
        len_frame.pack(fill="x", padx=80, pady=20)
        tk.Label(len_frame, text="Length:", font=self.app.ui_styles.get_font("sm"), bg=self.colors["bg"], fg=self.colors["text_secondary"]).pack(side="left")
        self.count_var = tk.StringVar(value="5")
        
        ttk.Combobox(len_frame, textvariable=self.count_var, values=["5", "10", "20"], width=5, state="readonly").pack(side="left", padx=10)

        # Buttons
        btn_frame = tk.Frame(self.parent, bg=self.colors["bg"], pady=40)
        btn_frame.pack(fill="x")
        
        # "No Thanks"
        tk.Button(btn_frame, text="Skip to Results", command=self.close, 
                  font=self.app.ui_styles.get_font("sm"), bg=self.colors["bg"], fg=self.colors["text_secondary"], 
                  relief="flat").pack(side="left", padx=80)
                  
        # "Start"
        tk.Button(btn_frame, text="Start Deep Dive", command=self.start,
                  font=self.app.ui_styles.get_font("md", "bold"), bg=self.colors["primary"], fg="#fff", width=20, pady=10).pack(side="right", padx=80)

    def start(self):
        # Collect selected tests
        to_run = [k for k, v in self.selected_tests.items() if v.get()]
        count = int(self.count_var.get())
        
        if not to_run:
            self.close()
            return

        # Launch Runner Queue in same container
        AssessmentQueueRunner(self.parent, self.app, to_run, count, self.handle_queue_finished)

    def handle_queue_finished(self, result_ids=None):
        if self.callback_done:
            self.callback_done(result_ids)

    def close(self):
        if self.callback_done:
            self.callback_done()

class AssessmentRunnerView:
    """
    Runs a single assessment (Embedded View).
    """
    def __init__(self, parent, app, assessment_type, count, on_finish=None):
        self.parent = parent
        self.app = app
        self.colors = app.colors
        self.on_finish = on_finish
        
        self.assessment_type = assessment_type
        self.count = count
        self.questions = QuestionCurator.get_questions(assessment_type, count)
        self.answers = {} # Question Text -> Score (1-5)
        self.current_idx = 0
        
        self._build_ui()
        self._load_question()

    def _build_ui(self):
        # Clear container
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.parent, variable=self.progress_var, maximum=self.count)
        self.progress.pack(fill="x")
        
        # Question Area
        self.q_frame = tk.Frame(self.parent, bg=self.colors["bg"], padx=60, pady=60)
        self.q_frame.pack(fill="both", expand=True)
        
        self.lbl_counter = tk.Label(self.q_frame, text="", font=self.app.ui_styles.get_font("sm", "bold"), 
                                   bg=self.colors["bg"], fg=self.colors["primary"])
        self.lbl_counter.pack(anchor="w")
        
        self.lbl_q = tk.Label(self.q_frame, text="", font=self.app.ui_styles.get_font("h2"), 
                             bg=self.colors["bg"], fg=self.colors["text_primary"], wraplength=700, justify="left")
        self.lbl_q.pack(pady=(30, 50), anchor="w")
        
        # Choices (Likert Scale 1-5)
        self.choice_var = tk.IntVar(value=0)
        choices_frame = tk.Frame(self.q_frame, bg=self.colors["bg"])
        choices_frame.pack(fill="x")
        
        options = [
            (1, "Strongly Disagree"),
            (2, "Disagree"),
            (3, "Neutral"),
            (4, "Agree"),
            (5, "Strongly Agree")
        ]
        
        for val, text in options:
            row = tk.Frame(choices_frame, bg=self.colors["surface"], pady=15, padx=20)
            row.pack(fill="x", pady=8)
            # Bind click on row
            row.bind("<Button-1>", lambda e, v=val: self.select_option(v))
            
            rb = tk.Radiobutton(row, text=text, variable=self.choice_var, value=val, 
                                font=self.app.ui_styles.get_font("md"), bg=self.colors["surface"], fg=self.colors["text_primary"],
                                activebackground=self.colors["surface"], selectcolor=self.colors["surface"],
                                command=lambda v=val: self.select_option(v),
                                takefocus=1) # Enable focus
            rb.bind("<space>", lambda e, v=val: self.select_option(v)) # Bind Space to select
            rb.pack(side="left")
            
            # Helper to make label clickable too
            lbl = tk.Label(row, text="", bg=self.colors["surface"]) # Spacer/Hitbox
            lbl.pack(side="left", fill="both", expand=True)
            lbl.bind("<Button-1>", lambda e, v=val: self.select_option(v))

            # Accessibility: Bind Space/Return on Row to select
            row.bind("<space>", lambda e, v=val: self.select_option(v))
            row.bind("<Return>", lambda e, v=val: self.select_option(v))

        # Nav Buttons
        btn_frame = tk.Frame(self.parent, bg=self.colors["bg"], pady=40)
        btn_frame.pack(fill="x")
        
        self.btn_next = tk.Button(btn_frame, text="Next", command=self.next_question,
                                 font=self.app.ui_styles.get_font("md", "bold"), bg=self.colors["primary"], fg="#fff", width=18, pady=10,
                                 takefocus=1) # Enable focus
        self.btn_next.pack()
        self.btn_next["state"] = "disabled" # Disable until selected
        
        # Bind Global Enter to Next if valid
        self.parent.bind_all("<Return>", lambda e: self.next_question() if self.btn_next["state"] == "normal" else None)

    def select_option(self, val):
        self.choice_var.set(val)
        self.btn_next["state"] = "normal"
        self.btn_next.config(bg=self.colors["primary"])
        self.btn_next.focus_set() # Move focus to Next button automatically

    def next_question(self):
        # Save Answer
        q_text = self.questions[self.current_idx]
        self.answers[q_text] = self.choice_var.get()
        
        self.current_idx += 1
        
        if self.current_idx >= len(self.questions):
            self.finish()
        else:
            self._load_question()

    def _load_question(self):
        self.progress_var.set(self.current_idx)
        self.choice_var.set(0)
        self.btn_next["state"] = "disabled"
        self.btn_next.config(bg=self.colors.get("disabled", "#ccc"))
        
        q_text = self.questions[self.current_idx]
        self.lbl_counter.config(text=f"Question {self.current_idx + 1} / {len(self.questions)}")
        self.lbl_q.config(text=q_text)

    def finish(self):
        res_id = self._save_results()
        if self.on_finish:
            # Check if callback expects iteration arguments (for queue runner)
            # Simple check: try passing ID, if fails (TypeError), pass nothing
            try:
                self.on_finish(res_id)
            except TypeError:
                self.on_finish()

    def _save_results(self):
        # Calculate score (simple sum normalized to 100 for now)
        # Max score = count * 5. Min = count * 1.
        raw_score = sum(self.answers.values())
        max_possible = len(self.questions) * 5
        normalized = int((raw_score / max_possible) * 100) if max_possible > 0 else 0
        
        logger.info(f"Saving assessment {self.assessment_type}: {normalized}%")
        
        try:
            with get_session() as session:
                user_id = self.app.current_user_id
                if not user_id:
                    logger.error("No current user to save results!")
                    return

                res = AssessmentResult(
                    user_id=user_id,
                    assessment_type=self.assessment_type,
                    total_score=normalized,
                    details=json.dumps(self.answers)
                )
                session.add(res)
                session.commit()
                session.add(res)
                session.commit()
                # Suppress popup for seamless embedded flow, or show a toast?
                # For now just log it. The final view will show results.
                logger.info(f"Assessment result committed to DB with ID: {res.id}")
                return res.id
        except Exception as e:
            logger.error(f"Failed to save assessment: {e}")
            messagebox.showerror("Error", "Failed to save results.")
            return None

class AssessmentQueueRunner:
    """
    Helper to run multiple assessments in sequence.
    """
    def __init__(self, parent, app, types, count, final_callback):
        self.parent = parent
        self.app = app
        self.queue = types
        self.count = count
        self.final_callback = final_callback
        
        self.count = count
        self.final_callback = final_callback
        self.result_ids = []
        
        self._run_next()
        
    def _run_next(self, result_id=None):
        if result_id:
            self.result_ids.append(result_id)

        if not self.queue:
            if self.final_callback:
                self.final_callback(self.result_ids)
            return
            
        next_type = self.queue.pop(0)
        # Run view in place
        AssessmentRunnerView(self.parent, self.app, next_type, self.count, self._run_next)
