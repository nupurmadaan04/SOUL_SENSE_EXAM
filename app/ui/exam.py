"""
Soul Sense Exam Module
Premium UI with modern question cards and progress tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import time
from datetime import datetime
import statistics
from app.utils import compute_age_group
from app.services.question_curator import QuestionCurator
from app.ui.assessments import RecommendationView


class ExamManager:
    """Manages the exam/question flow with premium styling"""
    
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.answer_var = tk.IntVar()

    def start_test(self):
        """Initialize test state and start the exam"""
        from app.services.exam_service import ExamSession, ExamService
        from tkinter import messagebox
        
        # Check retake restriction (Issue #993)
        user_id = getattr(self.app, 'current_user_id', None)
        is_allowed, message = ExamSession.check_retake_eligibility(user_id)
        
        if not is_allowed:
            messagebox.showwarning(
                "Retake Not Allowed",
                f"{message}\n\nYou have already completed an assessment. "
                "Multiple attempts are not permitted."
            )
            return
        
        # Init or Reset ExamSession
        # 1. Get question limit from settings (Default to 10)
        limit = self.app.settings.get("question_count", 10)
        
        # 2. Slice questions
        # self.app.questions contains all loaded questions
        questions_to_use = self.app.questions[:limit]
        
        self.session = ExamSession(
            username=self.app.username,
            age=self.app.age,
            age_group=self.app.age_group,
            questions=questions_to_use,
            user_id=user_id
        )
        self.session.start_exam()
        
        # Sync simple state for UI if needed (though we should read from session)
        self.app.current_question = 0
        self.app.responses = []
        
        self.show_question()

    def show_question(self):
        """Display current question with premium styling"""
        self.app.clear_screen()
        
        colors = self.app.colors
        
        # Check if test is complete using Session
        if self.session.is_finished():
            self.show_reflection_screen()
            return
        
        # Get data from Session
        q_text, q_tooltip = self.session.get_current_question()
        current_idx, total_count, progress_pct = self.session.get_progress()
        
        # Update app state for backward compat
        self.app.current_question = current_idx - 1
        
        # Main container
        main_frame = tk.Frame(self.root, bg=colors["bg"])
        main_frame.pack(fill="both", expand=True)
        
        # Progress Header
        progress_frame = tk.Frame(main_frame, bg=colors.get("bg_secondary", "#F1F5F9"), height=60)
        progress_frame.pack(fill="x")
        progress_frame.pack_propagate(False)
        
        progress_inner = tk.Frame(progress_frame, bg=colors.get("bg_secondary", "#F1F5F9"))
        progress_inner.pack(fill="x", padx=30, pady=15)
        
        # Question Counter
        counter_label = tk.Label(
            progress_inner,
            text=f"Question {current_idx} of {total_count}",
            font=("Segoe UI", 12, "bold"),
            bg=colors.get("bg_secondary", "#F1F5F9"),
            fg=colors.get("text_primary", "#0F172A")
        )
        counter_label.pack(side="left")
        
        # Progress percentage
        pct_label = tk.Label(
            progress_inner,
            text=f"{int(progress_pct)}% Complete",
            font=("Segoe UI", 11),
            bg=colors.get("bg_secondary", "#F1F5F9"),
            fg=colors.get("text_secondary", "#475569")
        )
        pct_label.pack(side="right")
        
        # Progress Bar
        progress_bar_frame = tk.Frame(main_frame, bg=colors["bg"], height=8)
        progress_bar_frame.pack(fill="x")
        
        style = ttk.Style()
        style.configure(
            "Exam.Horizontal.TProgressbar",
            troughcolor=colors.get("bg_secondary", "#F1F5F9"),
            background=colors.get("primary", "#3B82F6"),
            thickness=6
        )
        
        progress_bar = ttk.Progressbar(
            progress_bar_frame,
            style="Exam.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            value=progress_pct
        )
        progress_bar.pack(fill="x")
        
        # Content Area
        content_frame = tk.Frame(main_frame, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Question Card
        question_card = tk.Frame(
            content_frame,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        question_card.pack(fill="x", pady=10)
        
        card_inner = tk.Frame(question_card, bg=colors.get("surface", "#FFFFFF"))
        card_inner.pack(fill="x", padx=25, pady=20)
        
        # Question Header with tooltip
        q_header_frame = tk.Frame(card_inner, bg=colors.get("surface", "#FFFFFF"))
        q_header_frame.pack(fill="x")
        
        question_label = tk.Label(
            q_header_frame,
            text=q_text,
            font=("Segoe UI", 14),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            wraplength=480,
            justify="left"
        )
        question_label.pack(side="left", anchor="w")
        
        # Tooltip Icon
        tooltip_val = q_tooltip if q_tooltip else "Select the option that best describes you."
        
        info_btn = tk.Button(
            q_header_frame,
            text="ℹ️",
            font=("Segoe UI", 12),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_tertiary", "#94A3B8"),
            relief="flat",
            activebackground=colors.get("surface", "#FFFFFF"),
            activeforeground=colors.get("primary", "#3B82F6"),
            bd=0,
            cursor="hand2",
            command=lambda: self._show_tooltip(tooltip_val)
        )
        info_btn.pack(side="right", padx=5)
        
        # Options Section
        options_frame = tk.Frame(card_inner, bg=colors.get("surface", "#FFFFFF"))
        options_frame.pack(fill="x", pady=(20, 5))
        
        self.answer_var.set(0)  # Reset selection to 0 to avoid auto-select
        
        options = [
            ("Never", 1),
            ("Sometimes", 2),
            ("Often", 3),
            ("Always", 4)
        ]
        
        # Helper to update visual selection state
        def update_selection_visuals():
            selected_val = self.answer_var.get()
            for frame_obj, rb_obj, val in self.option_components:
                if val == selected_val:
                    # Selected State
                    frame_obj.configure(bg=colors.get("primary_light", "#DBEAFE"), highlightbackground=colors.get("primary", "#3B82F6"), highlightthickness=2)
                    rb_obj.configure(bg=colors.get("primary_light", "#DBEAFE"))
                else:
                    # Unselected State
                    frame_obj.configure(bg=colors.get("surface", "#FFFFFF"), highlightbackground=colors.get("border", "#E2E8F0"), highlightthickness=1)
                    rb_obj.configure(bg=colors.get("surface", "#FFFFFF"))
                    
        # Create styled radio buttons
        self.option_buttons = []
        self.option_components = [] # Store tuple of (frame, rb, value)
        
        for i, (text, value) in enumerate(options):
            option_frame = tk.Frame(
                options_frame,
                bg=colors.get("surface", "#FFFFFF"),
                highlightbackground=colors.get("border", "#E2E8F0"),
                highlightthickness=1,
                cursor="hand2"
            )
            option_frame.pack(fill="x", pady=4)
            
            # Select action
            def select_option(v=value):
                self.answer_var.set(v)
                update_selection_visuals()
            
            rb = tk.Radiobutton(
                option_frame,
                text=text,
                variable=self.answer_var,
                value=value,
                command=update_selection_visuals, # Trigger visual update on click
                font=("Segoe UI", 12),
                bg=colors.get("surface", "#FFFFFF"),
                fg=colors.get("text_primary", "#0F172A"),
                selectcolor=colors.get("bg", "#F8FAFC"), # Hide indicator bg or make it neutral
                activebackground=colors.get("surface_hover", "#F8FAFC"),
                activeforeground=colors.get("text_primary", "#0F172A"),
                indicatoron=True,
                tristatevalue=-1, 
                padx=15,
                pady=10,
                anchor="w"
            )
            rb.pack(fill="x")
            
            self.option_components.append((option_frame, rb, value))
            
            # Frame click triggers selection too
            option_frame.bind("<Button-1>", lambda e, v=value: select_option(v))
            
            # Hover effects (modified to respect selection)
            def on_enter(e, frame=option_frame, val=value):
                if self.answer_var.get() != val:
                    frame.configure(highlightbackground=colors.get("primary", "#3B82F6"))
            
            def on_leave(e, frame=option_frame, val=value):
                if self.answer_var.get() != val:
                     # Only reset if not focused
                    if self.root.focus_get() != frame.winfo_children()[0]:
                         frame.configure(highlightbackground=colors.get("border", "#E2E8F0"))
            
            def on_focus(e, frame=option_frame):
                 frame.configure(highlightbackground=colors.get("primary", "#3B82F6"), highlightthickness=2)

            def on_blur(e, frame=option_frame, val=value):
                 # Keep highlight if selected
                 if self.answer_var.get() != val:
                     frame.configure(highlightbackground=colors.get("border", "#E2E8F0"), highlightthickness=1)
                 else:
                     frame.configure(highlightbackground=colors.get("primary", "#3B82F6"), highlightthickness=2)

            option_frame.bind("<Enter>", on_enter)
            option_frame.bind("<Leave>", on_leave)
            
            # Link Focus events
            rb.bind("<Enter>", on_enter)
            rb.bind("<Leave>", on_leave)
            rb.bind("<FocusIn>", on_focus)
            rb.bind("<FocusOut>", on_blur)
            
            # Accessibility: Return on Option -> Submit (Next)
            rb.bind("<Return>", lambda e: self.save_answer())
            
            self.option_buttons.append((option_frame, rb))
            
            # Set initial focus to first option
            if i == 0:
                 rb.focus_set()
        
        # Navigation Buttons
        nav_frame = tk.Frame(content_frame, bg=colors["bg"])
        nav_frame.pack(pady=20)
        
        # Global Enter Key for Next
        self.root.bind("<Return>", lambda e: self.save_answer())
        
        # Back Button (if not first question)
        if current_idx > 1:
            back_btn = tk.Button(
                nav_frame,
                text="← Previous",
                command=self.previous_question,
                font=("Segoe UI", 11),
                bg=colors.get("surface", "#FFFFFF"),
                fg=colors.get("text_secondary", "#475569"),
                activebackground=colors.get("surface_hover", "#F8FAFC"),
                activeforeground=colors.get("text_primary", "#0F172A"),
                relief="flat",
                cursor="hand2",
                width=12,
                pady=8,
                borderwidth=1,
                highlightbackground=colors.get("border", "#E2E8F0")
            )
            back_btn.pack(side="left", padx=5)
            back_btn.bind("<Enter>", lambda e: back_btn.configure(bg=colors.get("surface_hover", "#F8FAFC")))
            back_btn.bind("<Leave>", lambda e: back_btn.configure(bg=colors.get("surface", "#FFFFFF")))
        
        # Next/Finish Button
        is_last = current_idx >= total_count
        next_text = "Finish →" if is_last else "Next →"
        
        next_btn = tk.Button(
            nav_frame,
            text=next_text,
            command=self.save_answer,
            font=("Segoe UI", 12, "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("primary_hover", "#2563EB"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=14,
            pady=10,
            borderwidth=0
        )
        next_btn.pack(side="left", padx=5)
        next_btn.bind("<Enter>", lambda e: next_btn.configure(bg=colors.get("primary_hover", "#2563EB")))
        next_btn.bind("<Leave>", lambda e: next_btn.configure(bg=colors.get("primary", "#3B82F6")))
        
        # Bind Enter key
        self.root.bind("<Return>", lambda e: self.save_answer())

    def _show_tooltip(self, text):
        """Show a simple tooltip message"""
        messagebox.showinfo("Tip", text)

    def previous_question(self):
        """Go to previous question"""
        if self.session.go_back():
            self.show_question()

    def save_answer(self):
        """Save current answer and proceed"""
        # 0. Debounce / Navigation Guard
        if hasattr(self, 'is_navigating') and self.is_navigating:
            return
            
        ans = self.answer_var.get()
        if ans == 0:
            messagebox.showwarning("Select an Answer", "Please select an option before continuing.")
            return
        
        try:
            self.is_navigating = True
            
            # Disable next button visually if possible (optional optimization)
            # here we rely on the flag primarily for speed
            
            self.session.submit_answer(ans)
            self.show_question()
            
            # Reset flag is handled implicitly because show_question redraws the UI
            # or we can reset it here if show_question is synchronous and fast
            self.is_navigating = False
            
        except ValueError as e:
            self.is_navigating = False
            messagebox.showerror("Error", str(e))
        except Exception:
            self.is_navigating = False
            raise

    def show_reflection_screen(self):
        """Show premium reflection screen"""
        self.app.clear_screen()
        
        colors = self.app.colors
        
        # Main container
        main_frame = tk.Frame(self.root, bg=colors["bg"])
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=colors.get("secondary", "#8B5CF6"), height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(
            header_frame,
            text="🌟 Final Reflection",
            font=("Segoe UI", 28, "bold"),
            bg=colors.get("secondary", "#8B5CF6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        )
        header_label.pack(pady=30)
        
        # Content
        content_frame = tk.Frame(main_frame, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Instruction Card
        instruction_card = tk.Frame(
            content_frame,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        instruction_card.pack(fill="x", pady=10)
        
        card_inner = tk.Frame(instruction_card, bg=colors.get("surface", "#FFFFFF"))
        card_inner.pack(fill="x", padx=25, pady=20)
        
        instruction_label = tk.Label(
            card_inner,
            text="Describe a recent situation where you felt emotionally challenged.\nHow did you handle it?",
            font=("Segoe UI", 13),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            wraplength=500,
            justify="center"
        )
        instruction_label.pack()
        
        # Text Area Frame
        text_frame = tk.Frame(content_frame, bg=colors["bg"])
        text_frame.pack(fill="both", expand=True, pady=10)
        
        self.reflection_entry = tk.Text(
            text_frame,
            height=8,
            font=("Segoe UI", 12),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            insertbackground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            highlightthickness=2,
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightcolor=colors.get("primary", "#3B82F6"),
            padx=15,
            pady=15
        )
        self.reflection_entry.pack(fill="both", expand=True)
        
        # Submit Button
        btn_frame = tk.Frame(content_frame, bg=colors["bg"])
        btn_frame.pack(pady=15)
        
        self.submit_btn = tk.Button( # Store ref to disable later
            btn_frame,
            text="✨ Submit & See Results",
            command=self.submit_reflection,
            font=("Segoe UI", 14, "bold"),
            bg=colors.get("success", "#10B981"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("success_hover", "#059669"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=22,
            pady=12,
            borderwidth=0
        )
        self.submit_btn.pack()
        self.submit_btn.bind("<Enter>", lambda e: self.submit_btn.configure(bg=colors.get("success_hover", "#059669")))
        self.submit_btn.bind("<Leave>", lambda e: self.submit_btn.configure(bg=colors.get("success", "#10B981")))
        
        # Skip link
        skip_label = tk.Label(
            btn_frame,
            text="Skip this step",
            font=("Segoe UI", 10, "underline"),
            bg=colors["bg"],
            fg=colors.get("text_tertiary", "#94A3B8"),
            cursor="hand2"
        )
        skip_label.pack(pady=10)
        skip_label.bind("<Button-1>", lambda e: self._skip_reflection())

    def _skip_reflection(self):
        """Skip reflection and finish test"""
        if hasattr(self, 'is_processing') and self.is_processing: return
        self.session.reflection_text = ""
        self.finish_test()

    def submit_reflection(self):
        """Analyze reflection text and finish test"""
        from app.ui.components.loading_overlay import show_loading, hide_loading
        
        # Guard
        if hasattr(self, 'is_processing') and self.is_processing:
            return

        text = self.reflection_entry.get("1.0", tk.END).strip()
        
        if not text:
            if not messagebox.askyesno("Skip?", "You haven't written anything. Do you want to skip?"):
                return
            # If skipping via empty text, just proceed
            self.session.submit_reflection("")
            self.finish_test()
            return
            
        # Start Processing
        self.is_processing = True
        self.submit_btn.configure(state="disabled")
        overlay = show_loading(self.root, "Analyzing Reflection...")
        
        try:
            # Use main app's analyzer if available
            analyzer = getattr(self.app, 'sia', None)
            
            # This might be slow (NLTK or API)
            self.session.submit_reflection(text, analyzer)
            self.finish_test()
            
        except Exception as e:
            logging.error(f"Error submitting reflection: {e}")
            messagebox.showerror("Error", "Analysis failed. Proceeding without analysis.")
            # Fallback
            try:
                self.session.submit_reflection("")
                self.finish_test()
            except:
                pass
        
        finally:
            # Cleanup
            hide_loading(overlay)
            self.is_processing = False
            # We don't need to re-enable button because finish_test clears the screen
            # unless finish_test failed, in which case we might be stuck? 
            # safe to re-enable just in case screen wasn't cleared
            try:
                 if self.submit_btn.winfo_exists():
                    self.submit_btn.configure(state="normal")
            except:
                pass

    def finish_test(self):
        """Calculate final score and save to database - FIXED VERSION"""
        try:
            success = self.session.finish_exam()
            
            if not success:
                messagebox.showerror("Error", "Failed to save exam results.")
                return
            
            # Sync back to Main App for compatibility with ResultsManager
            self.app.current_score = self.session.score
            self.app.responses = self.session.responses
            self.app.response_times = self.session.response_times
            self.app.current_max_score = len(self.session.responses) * 4
            self.app.current_percentage = (self.app.current_score / self.app.current_max_score) * 100 if self.app.current_max_score > 0 else 0
            self.app.sentiment_score = self.session.sentiment_score
            self.app.reflection_text = self.session.reflection_text
            
            # Show satisfaction survey if available
            if hasattr(self.app, 'offer_satisfaction_survey'):
                try:
                    self.app.offer_satisfaction_survey()
                except Exception as e:
                    logging.warning(f"Could not show satisfaction survey: {e}")
            
            # Determine Recommendations
            score_data = {"total_score": self.app.current_score} 
            # In future: fetch stress/energy from recent journal or specific question IDs
            
            recs = QuestionCurator.recommend_tests(self.app, score_data)
            
            if recs:
                # Show Embedded Recommendation View
                RecommendationView(self.root, self.app, recs, callback_done=self.show_embedded_results)
            else:
                # Show results directly
                self.show_embedded_results()
            
        except Exception as e:
            logging.error(f"Error finishing test: {e}")
            # Don't call show_main_menu() since it doesn't exist
            # Just show a completion message
            messagebox.showinfo("Test Complete", 
                               f"Your test is complete! Score: {self.app.current_score}")
            # Clear the screen if possible
            if hasattr(self.app, 'clear_screen'):
                self.app.clear_screen()
    
    def show_embedded_results(self, result_ids=None):
        """Show results embedded in the main window (Web-Style)"""
        from app.services.exam_service import ExamSession
        
        self.app.clear_screen()
        colors = self.app.colors
        
        # Main Container (Scrollable if needed, but results are usually short)
        container = tk.Frame(self.root, bg=colors["bg"])
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # 1. Header Section
        header_frame = tk.Frame(container, bg=colors["bg"])
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(header_frame, text="🎉 Assessment Complete!", 
                 font=("Segoe UI", 28, "bold"), 
                 bg=colors["bg"], fg=colors["text_primary"]).pack(side="left")
                 
        # 2. Score Card (Hero)
        score_card = tk.Frame(container, bg=colors["surface"], pady=30, padx=30,
                             highlightthickness=1, highlightbackground=colors.get("border", "#E2E8F0"))
        score_card.pack(fill="x", pady=10)
        
        # Grid layout for score details
        score_card.columnconfigure(0, weight=1)
        score_card.columnconfigure(1, weight=1)
        
        # Left: Main Score
        score_frame = tk.Frame(score_card, bg=colors["surface"])
        score_frame.grid(row=0, column=0, sticky="ns")
        
        tk.Label(score_frame, text="Your Wellbeing Score", 
                 font=("Segoe UI", 12, "bold"), bg=colors["surface"], 
                 fg=colors["text_secondary"]).pack()
                 
        tk.Label(score_frame, text=f"{int(self.app.current_percentage)}%", 
                 font=("Segoe UI", 64, "bold"), bg=colors["surface"], 
                 fg=colors["primary"]).pack()
                 
        tk.Label(score_frame, text=f"({self.app.current_score}/{self.app.current_max_score} points)", 
                 font=("Segoe UI", 12), bg=colors["surface"], 
                 fg=colors["text_secondary"]).pack()
                 
        # Right: Interpretation
        feedback_frame = tk.Frame(score_card, bg=colors["surface"])
        feedback_frame.grid(row=0, column=1, sticky="nsew", padx=40)
        
        if self.app.current_percentage >= 70:
            title = "🌟 Excellent!"
            desc = "You demonstrate strong emotional resilience and awareness."
            color = colors["success"]
        elif self.app.current_percentage >= 50:
            title = "👍 Good Balance"
            desc = "You have a solid foundation, with some room for growth."
            color = colors["secondary"]
        else:
            title = "🌱 Room to Grow"
            desc = "Consider focusing more on self-care and emotional processing."
            color = colors["accent"] # Warning color?
            
        tk.Label(feedback_frame, text=title, font=("Segoe UI", 24, "bold"), 
                 bg=colors["surface"], fg=color).pack(anchor="w", pady=(10, 5))
                 
        tk.Label(feedback_frame, text=desc, font=("Segoe UI", 14), wraplength=400, justify="left",
                 bg=colors["surface"], fg=colors["text_primary"]).pack(anchor="w")

        # --- Sentiment Insight ---
        sent_score = getattr(self.app, 'sentiment_score', 0)
        if sent_score >= 60:
            s_text = "Positive Mindset ☀"
            s_color = colors.get("success", "#10B981")
        elif sent_score >= 40:
            s_text = "Neutral / Balanced 😐"
            s_color = colors.get("text_secondary", "#94A3B8")
        else:
            s_text = "Needs Attention 🌧"
            s_color = colors.get("accent", "#F59E0B")
            
        tk.Label(feedback_frame, text=f"Sentiment: {s_text} ({int(sent_score)}/100)", 
                 font=("Segoe UI", 12, "bold"), bg=colors["surface"], fg=s_color).pack(anchor="w", pady=(15, 0))

        # --- NEW SECTION: Deep Dive Results (if any) ---
        try:
            from app.services.exam_service import ExamService
            
            deep_dives = []
            if self.app.current_user_id:
                deep_dives = ExamService.get_assessment_results(
                    user_id=self.app.current_user_id,
                    result_ids=result_ids,
                    minutes_lookback=15
                )
                
                if deep_dives:
                    dd_section = tk.Frame(container, bg=colors["bg"])
                    dd_section.pack(fill="x", pady=(20, 10))
                    
                    tk.Label(dd_section, text="🔍 Deep Dive Insights", font=("Segoe UI", 18, "bold"), 
                             bg=colors["bg"], fg=colors["text_primary"]).pack(anchor="w", pady=(0, 10))
                    
                    grid_frame = tk.Frame(dd_section, bg=colors["bg"])
                    grid_frame.pack(fill="x")
                    
                    for i, result in enumerate(deep_dives):
                        # Simple card for each
                        card = tk.Frame(grid_frame, bg=colors["surface"], padx=15, pady=15,
                                      highlightthickness=1, highlightbackground=colors.get("border", "#E2E8F0"))
                        card.pack(side="left", fill="x", expand=True, padx=5)
                        
                        d_name = result.assessment_type.replace("_", " ").title()
                        tk.Label(card, text=d_name, font=("Segoe UI", 12, "bold"), 
                                 bg=colors["surface"], fg=colors["text_primary"]).pack(anchor="w")
                                 
                        tk.Label(card, text=f"Score: {result.total_score}/100", font=("Segoe UI", 16, "bold"), 
                                 bg=colors["surface"], fg=colors["primary"]).pack(anchor="w", pady=5)
        except Exception as e:
            logging.error(f"Failed to load specific deep dives: {e}")


        # 3. Actions Row
        action_frame = tk.Frame(container, bg=colors["bg"])
        action_frame.pack(fill="x", pady=30)
        
        # Helper for Action Buttons
        def create_action_btn(text, cmd, color_key="primary"):
            btn = tk.Button(action_frame, text=text, command=cmd,
                           font=("Segoe UI", 11, "bold"), 
                           bg=colors.get(color_key, "#3B82F6"), 
                           fg=colors.get("text_inverse", "white"),
                           relief="flat", padx=20, pady=10, cursor="hand2")
            btn.pack(side="left", padx=10)
            # Simple hover
            btn.bind("<Enter>", lambda e: btn.configure(bg=colors.get(f"{color_key}_hover", colors[color_key])))
            btn.bind("<Leave>", lambda e: btn.configure(bg=colors.get(color_key, colors[color_key])))
            return btn
            
        # Button: Take Another (only show if no completed assessment)
        # Check retake restriction for current user
        user_id = getattr(self.app, 'current_user_id', None)
        is_allowed, _ = ExamSession.check_retake_eligibility(user_id)
        
        if is_allowed:
            # We need to use lambda to delay execution or bind properly
            create_action_btn("🔄 Retake Assessment", self.start_test, "primary")
        else:
            # Show message that assessment is already completed
            tk.Label(action_frame, 
                    text="✓ Assessment Completed (No retake allowed)",
                    font=("Segoe UI", 11, "italic"),
                    bg=colors["bg"], 
                    fg=colors.get("success", "#10B981")).pack(side="left", padx=10)
        
        # Button: AI Analysis
        def show_ai_analysis():
            reflection = self.app.reflection_text or "No reflection provided."
            sentiment = getattr(self.app, 'sentiment_score', 0)
            msg = f"🧠 AI Analysis:\n\nSentiment Score: {sentiment:.1f}/100\n\nReflection:\n{reflection}\n\n(Deep pattern matching compliant)"
            messagebox.showinfo("SoulSense AI Insights", msg)
            
        create_action_btn("🤖 AI Analysis", show_ai_analysis, "secondary")
        
        # Button: Compare (Placeholder)
        create_action_btn("📈 Compare w/ Previous", 
                         lambda: messagebox.showinfo("History", "Historical comparison charts coming soon!"), 
                         "accent")
                         
        # Button: Export PDF
        create_action_btn("📄 Export PDF", self.export_pdf, "success")

        # Return Home Button (Secondary style, on the right)
        tk.Button(action_frame, text="Close / Dashboard", 
                 command=lambda: self.app.show_home() if hasattr(self.app, 'show_home') else None,
                 font=("Segoe UI", 11), bg=colors["bg"], fg=colors["text_primary"],
                 relief="flat", padx=15, pady=10).pack(side="right")
        
        # Force a refresh if needed
        container.update()

    def export_pdf(self):
        """Export simplified result PDF immediately after test"""
        try:
            from app.services.pdf_generator import generate_pdf_report
            from tkinter import filedialog
            from app.utils.file_validation import validate_file_path, sanitize_filename
            
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_username = sanitize_filename(self.app.username)
            default_name = f"EQ_Report_{safe_username}_{timestamp}.pdf"
            
            # Ask user for location
            filename = filedialog.asksaveasfilename(
                title="Save PDF Report",
                initialfile=default_name,
                defaultextension=".pdf",
                filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
            )
            
            if not filename:
                return # User cancelled

            # Show loading
            self.app.root.config(cursor="watch")
            self.app.root.update()

            try:
                # Fetch Deep Dives if available (for PDF)
                deep_dives = []
                try:
                    from app.services.exam_service import ExamService
                    if self.app.current_user_id:
                        deep_dives = ExamService.get_assessment_results(
                            user_id=self.app.current_user_id,
                            minutes_lookback=15
                        )
                except Exception as e:
                    logging.warning(f"Could not fetch deep dives for PDF: {e}")

                # Prepare data for report using current app state
                result_path = generate_pdf_report(
                    self.app.username,
                    self.app.current_score,
                    self.app.current_max_score,
                    self.app.current_percentage,
                    self.app.age,
                    self.app.responses,
                    self.app.questions,
                    self.app.sentiment_score if hasattr(self.app, 'sentiment_score') else None,
                    filepath=filename,
                    deep_dives=deep_dives # Pass deep dives
                )
                
                messagebox.showinfo("Success", f"Report saved successfully:\n{result_path}")
                
            finally:
                self.app.root.config(cursor="")
                
        except Exception as e:
            logging.error(f"PDF Export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to generate PDF:\n{str(e)}")