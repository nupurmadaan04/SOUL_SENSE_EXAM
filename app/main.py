import tkinter as tk
from tkinter import messagebox, ttk
import logging
import sys
from datetime import datetime
import json
import os

# --- NEW IMPORTS FOR GRAPHS ---
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.db import get_session
from app.models import Score, Response, User
from app.questions import load_questions
from app.utils import compute_age_group
from app.auth import AuthManager
from app import config

# ---------------- LOGGING ----------------
logging.basicConfig(
    filename="logs/soulsense.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Application started")

# ---------------- THEMES ----------------
THEMES = {
    "light": {
        "bg_primary": "#F5F7FA",
        "bg_secondary": "white",
        "text_primary": "#2C3E50",
        "text_secondary": "#7F8C8D",
        "text_input": "#34495E",
        "accent": "#2980B9",
        "success": "#2E7D32",
        "danger": "#C0392B",
        "card_bg": "white",
        "input_bg": "white",
        "input_fg": "black",
        "tooltip_bg": "#FFFFE0",
        "tooltip_fg": "black",
        # Visual Results Specific
        "chart_bg": "#ffffff",
        "chart_fg": "#000000",
        "improvement_good": "#4CAF50",
        "improvement_bad": "#F44336",
        "improvement_neutral": "#FFC107",
        "excellent": "#2196F3",
        "good": "#4CAF50",
        "average": "#FF9800",
        "needs_work": "#F44336"
    },
    "dark": {
        "bg_primary": "#121212",
        "bg_secondary": "#1e1e1e",
        "text_primary": "#ffffff",
        "text_secondary": "#e0e0e0",
        "text_input": "#f0f0f0",
        "accent": "#5DADE2",
        "success": "#58D68D",
        "danger": "#EC7063",
        "card_bg": "#1e1e1e",
        "input_bg": "#2d2d2d",
        "input_fg": "white",
        "tooltip_bg": "#333333",
        "tooltip_fg": "white",
        # Visual Results Specific
        "chart_bg": "#2e2e2e",
        "chart_fg": "#ffffff",
        "improvement_good": "#4CAF50",
        "improvement_bad": "#F44336",
        "improvement_neutral": "#FFC107",
        "excellent": "#2196F3",
        "good": "#4CAF50",
        "average": "#FF9800",
        "needs_work": "#F44336"
    }
}

class SplashScreen:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.geometry("450x300")
        
        try:
            theme = config.THEME
        except AttributeError:
            theme = "light"

        bg = "#121212" if theme == "dark" else "#F5F7FA"
        fg = "#ffffff" if theme == "dark" else "#2C3E50"
        
        self.root.configure(bg=bg)
        
        x = (self.root.winfo_screenwidth() // 2) - 225
        y = (self.root.winfo_screenheight() // 2) - 150
        self.root.geometry(f"+{x}+{y}")

        container = tk.Frame(self.root, bg=bg)
        container.pack(expand=True)

        tk.Label(
            container,
            text="🧠",
            font=("Arial", 40),
            bg=bg
        ).pack(pady=(10, 5))

        tk.Label(
            container,
            text="Soul Sense EQ Test",
            font=("Arial", 20, "bold"),
            fg=fg,
            bg=bg
        ).pack(pady=5)

        tk.Label(
            container,
            text="Assess your Emotional Intelligence",
            font=("Arial", 10),
            fg="#7F8C8D",
            bg=bg
        ).pack(pady=5)

        self.loading_label = tk.Label(
            container,
            text="Loading...",
            font=("Arial", 10),
            fg="#555",
            bg=bg
        )
        self.loading_label.pack(pady=15)

    def close_after_delay(self, delay_ms, callback):
        self.root.after(delay_ms, callback)

class SoulSenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        self.root.geometry("800x600") # Increased size for visual results
        
        # Load Theme
        self.current_theme_name = config.THEME
        self.colors = THEMES.get(self.current_theme_name, THEMES["light"])
        
        self.root.configure(bg=self.colors["bg_primary"])
        self.username = ""
        self.age = None
        self.education = None
        self.age_group = None
        self.auth_manager = AuthManager()

        self.current_question = 0
        self.total_questions = 0
        self.responses = []
        
        # Scoring state
        self.current_score = 0
        self.current_max_score = 0
        self.current_percentage = 0

        self.create_login_screen()

    # ---------- HELPERS ----------
    def show_loading(self, message="Loading..."):
        """Overlay a loading screen"""
        self.loading_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        self.loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        tk.Label(
            self.loading_frame,
            text="⏳",
            font=("Arial", 40),
            bg=self.colors["bg_primary"]
        ).pack(expand=True, pady=(0, 10))
        
        tk.Label(
            self.loading_frame,
            text=message,
            font=("Arial", 16),
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"]
        ).pack(expand=True)
        
        self.root.update()

    def hide_loading(self):
        """Remove loading screen"""
        if hasattr(self, 'loading_frame'):
            self.loading_frame.destroy()
            del self.loading_frame

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme_name == "light" else "light"
        
        # Update app state
        self.current_theme_name = new_theme
        self.colors = THEMES.get(self.current_theme_name, THEMES["light"])
        self.root.configure(bg=self.colors["bg_primary"])
        
        # Update Config
        try:
            current_config = config.load_config()
            current_config["ui"]["theme"] = new_theme
            config.save_config(current_config)
            messagebox.showinfo("Theme Changed", "Theme changed! Please restart the application to fully apply changes.")
        except Exception as e:
            logging.error(f"Failed to save theme: {e}")

    def clear_screen(self):
        for widget in self.root.winfo_children():
            # Don't destroy loading frame if it exists
            if hasattr(self, 'loading_frame') and widget == self.loading_frame:
                continue
            widget.destroy()

    def darken_color(self, color):
        """Helper for button active states (from upstream)"""
        if color.startswith("#") and len(color) == 7:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        return color
        
    def force_exit(self):
        self.root.destroy()
        sys.exit(0)

    # ---------- SCREENS ----------
    def create_login_screen(self):
        self.clear_screen()
        
        card = tk.Frame(
            self.root,
            bg=self.colors["card_bg"],
            padx=30,
            pady=25
        )
        card.pack(pady=50)
        
        header_frame = tk.Frame(card, bg=self.colors["card_bg"])
        header_frame.pack(fill="x", pady=(0, 8))
        
        tk.Label(
            header_frame,
            text="🧠 Soul Sense",
            font=("Arial", 22, "bold"),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"]
        ).pack(side="left")
        
        # Theme Toggle
        tk.Button(
            header_frame,
            text="🌓",
            command=self.toggle_theme,
            font=("Arial", 12),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            cursor="hand2"
        ).pack(side="right", padx=5)

        # Settings Button
        tk.Button(
            header_frame,
            text="⚙️",
            command=self.show_settings,
            font=("Arial", 12),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            cursor="hand2"
        ).pack(side="right", padx=5)
        
        tk.Label(
            card,
            text="Please login to continue",
            font=("Arial", 11),
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"]
        ).pack(pady=(0, 20))
        
        # Form
        tk.Label(card, text="Username", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.login_username_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.login_username_entry.pack(pady=5)
        
        tk.Label(card, text="Password", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.login_password_entry = ttk.Entry(card, font=("Arial", 12), width=30, show="*")
        self.login_password_entry.pack(pady=5)
        
        button_frame = tk.Frame(card, bg=self.colors["card_bg"])
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Login",
            command=self.handle_login,
            font=("Arial", 12, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            button_frame,
            text="Sign Up",
            command=self.create_signup_screen,
            font=("Arial", 12),
            bg=self.colors["accent"],
            fg="white",
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="left")

    def show_settings(self):
        """Settings Window (Adapted from Upstream)"""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("400x300")
        settings_win.configure(bg=self.colors["bg_primary"])
        
        x = self.root.winfo_x() + (self.root.winfo_width() - settings_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - settings_win.winfo_height()) // 2
        settings_win.geometry(f"+{x}+{y}")
        
        tk.Label(
            settings_win,
            text="System Config",
            font=("Arial", 16, "bold"),
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"]
        ).pack(pady=15)
        
        tk.Label(
            settings_win,
            text=f"Current Theme: {self.current_theme_name}",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"]
        ).pack(pady=5)

        tk.Label(
            settings_win,
            text="Database: " + config.DB_FILENAME,
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"]
        ).pack(pady=5)

        tk.Button(
            settings_win,
            text="Close",
            command=settings_win.destroy,
            bg=self.colors["accent"],
            fg="white"
        ).pack(pady=20)
    
    def create_signup_screen(self):
        self.clear_screen()
        card = tk.Frame(self.root, bg=self.colors["card_bg"], padx=30, pady=25)
        card.pack(pady=50)
        
        tk.Label(card, text="🧠 Create Account", font=("Arial", 22, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_primary"]).pack(pady=(0, 8))
        
        tk.Label(card, text="Username", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.signup_username_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.signup_username_entry.pack(pady=5)
        
        tk.Label(card, text="Password", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.signup_password_entry = ttk.Entry(card, font=("Arial", 12), width=30, show="*")
        self.signup_password_entry.pack(pady=5)
        
        tk.Label(card, text="Confirm Password", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.signup_confirm_entry = ttk.Entry(card, font=("Arial", 12), width=30, show="*")
        self.signup_confirm_entry.pack(pady=5)
        
        button_frame = tk.Frame(card, bg=self.colors["card_bg"])
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Create Account", command=self.handle_signup, font=("Arial", 12, "bold"), bg=self.colors["success"], fg="white", relief="flat", padx=20, pady=8).pack(side="left", padx=(0, 10))
        tk.Button(button_frame, text="Back to Login", command=self.create_login_screen, font=("Arial", 12), bg="#757575", fg="white", relief="flat", padx=20, pady=8).pack(side="left")
    
    def handle_login(self):
        username = self.login_username_entry.get().strip()
        password = self.login_password_entry.get()
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return
        success, message = self.auth_manager.login_user(username, password)
        if success:
            self.username = username
            logging.info(f"User logged in: {username}")
            self.create_username_screen()
        else:
            messagebox.showerror("Login Failed", message)
    
    def handle_signup(self):
        username = self.signup_username_entry.get().strip()
        password = self.signup_password_entry.get()
        confirm_password = self.signup_confirm_entry.get()
        if not username or not password or not confirm_password:
            messagebox.showwarning("Input Error", "Please fill in all fields.")
            return
        if password != confirm_password:
            messagebox.showwarning("Input Error", "Passwords do not match.")
            return
        success, message = self.auth_manager.register_user(username, password)
        if success:
            messagebox.showinfo("Success", "Account created successfully! Please login.")
            self.create_login_screen()
        else:
            messagebox.showerror("Registration Failed", message)
    
    def handle_logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.auth_manager.logout_user()
            self.username = ""
            logging.info("User logged out")
            self.create_login_screen()

    def create_username_screen(self):
        self.clear_screen()
        card = tk.Frame(self.root, bg=self.colors["card_bg"], padx=30, pady=25)
        card.pack(pady=30)

        tk.Label(card, text="🧠 Soul Sense EQ Test", font=("Arial", 22, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_primary"]).pack(pady=(0, 8))
        
        logout_frame = tk.Frame(card, bg=self.colors["card_bg"])
        logout_frame.pack(fill="x", pady=(0, 10))
        tk.Label(logout_frame, text=f"Logged in as: {self.username}", bg=self.colors["card_bg"], fg=self.colors["text_secondary"], font=("Arial", 10)).pack(side="left")
        tk.Button(logout_frame, text="Logout", command=self.handle_logout, font=("Arial", 10), bg=self.colors["danger"], fg="white", relief="flat", padx=15, pady=5).pack(side="right")
        
        # View History Option (Merged from Upstream)
        tk.Button(logout_frame, text="History", command=self.show_history_screen, font=("Arial", 10), bg=self.colors["accent"], fg="white", relief="flat", padx=15, pady=5).pack(side="right", padx=5)

        tk.Label(card, text="Enter Name", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.name_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.name_entry.insert(0, self.username)
        self.name_entry.configure(state='readonly')
        self.name_entry.pack(pady=5)

        tk.Label(card, text="Enter Age", bg=self.colors["card_bg"], fg=self.colors["text_input"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
        self.age_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.age_entry.pack(pady=5)

        tk.Button(card, text="Start EQ Test →", command=self.start_test, font=("Arial", 12, "bold"), bg=self.colors["success"], fg="white", relief="flat", padx=20, pady=8).pack(pady=25)

    def validate_age_input(self, age_str):
        if not age_str: return False, None, "Please enter your age."
        try:
            val = int(age_str)
            if val <= 0: return False, None, "Age must be positive."
            if val > 120: return False, None, "Age implies you are a vampire/ghost."
            return True, val, None
        except ValueError:
            return False, None, "Age must be numeric."

    def start_test(self):
        self.username = self.name_entry.get().strip()
        age_str = self.age_entry.get().strip()
        
        ok, age, err = self.validate_age_input(age_str)
        if not ok:
            messagebox.showwarning("Input Error", err)
            return
            
        self.age = age
        self.age_group = compute_age_group(age)

        # Loading Indicator (My Feature)
        self.show_loading("Loading Questions...")
        
        try:
            rows = load_questions(age=self.age) # [(id, text, tooltip)]
            self.questions = [(q[1], q[2]) for q in rows]
            self.total_questions = len(self.questions)
            
            if not self.questions:
                raise RuntimeError("No questions loaded")
        except Exception:
            self.hide_loading()
            logging.error("Failed to load questions", exc_info=True)
            messagebox.showerror("Error", "No questions available for your age group.")
            return

        self.hide_loading()
        logging.info("Session started | user=%s | age=%s", self.username, self.age)
        self.show_question()

    def show_question(self):
        self.clear_screen()
        
        if self.current_question >= len(self.questions):
            self.finish_test()
            return

        q_text, q_tooltip = self.questions[self.current_question]
        
        question_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        question_frame.pack(pady=20)

        tk.Label(
            question_frame,
            text=f"Q{self.current_question + 1}: {q_text}",
            wraplength=400,
            font=("Arial", 12),
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"]
        ).pack(side="left")
        
        if q_tooltip:
            tooltip_btn = tk.Label(question_frame, text="ℹ️", font=("Arial", 12), fg=self.colors["accent"], bg=self.colors["bg_primary"], cursor="hand2")
            tooltip_btn.pack(side="left", padx=5)
            
            def on_enter(e):
                self.tooltip_w = tk.Toplevel(self.root)
                self.tooltip_w.wm_overrideredirect(True)
                x = e.widget.winfo_rootx() + 20
                y = e.widget.winfo_rooty() + 20
                self.tooltip_w.wm_geometry(f"+{x}+{y}")
                tk.Label(self.tooltip_w, text=q_tooltip, bg=self.colors["tooltip_bg"], fg=self.colors["tooltip_fg"], relief="solid", borderwidth=1, padx=5, pady=3).pack()
            
            def on_leave(e):
                if hasattr(self, 'tooltip_w'): self.tooltip_w.destroy()
            
            tooltip_btn.bind("<Enter>", on_enter)
            tooltip_btn.bind("<Leave>", on_leave)

        self.answer_var = tk.IntVar()
        
        for val, txt in enumerate(["Never", "Sometimes", "Often", "Always"], 1):
            tk.Radiobutton(self.root, text=f"{txt} ({val})", variable=self.answer_var, value=val, bg=self.colors["bg_primary"], fg=self.colors["text_primary"], selectcolor=self.colors["bg_secondary"]).pack(anchor="w", padx=100)

        # Nav Buttons
        btn_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="Next", command=self.save_answer, font=("Arial", 12), bg=self.colors["success"], fg="white").pack(side="left")

    def save_answer(self):
        try:
            ans = self.answer_var.get()
            if ans == 0:
                messagebox.showwarning("Input Error", "Please select an answer.")
                return
        except: return

        self.responses.append(ans)
        
        # Save response to DB (Using ORM)
        session = get_session()
        try:
            # Note: We don't have question_id tracked easily in this list structure, just index + 1 for now
            # In a real app we'd track real IDs
            response = Response(
                username=self.username,
                question_id=self.current_question + 1,
                response_value=ans,
                age_group=self.age_group,
                timestamp=datetime.utcnow().isoformat()
            )
            session.add(response)
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

        self.current_question += 1
        self.show_question()

    def finish_test(self):
        # Loading Indicator (My Feature)
        self.show_loading("Analyzing Emotional Intelligence...")
        self.root.after(100, self._process_results)

    def _process_results(self):
        # Calculate scores
        self.current_score = sum(self.responses)
        self.current_max_score = len(self.responses) * 4
        if self.current_max_score > 0:
            self.current_percentage = (self.current_score / self.current_max_score) * 100
        else:
            self.current_percentage = 0

        # Save Score to DB (ORM)
        session = get_session()
        try:
            score = Score(
                username=self.username,
                age=self.age,
                total_score=self.current_score
            )
            session.add(score)
            session.commit()
        except Exception:
            logging.error("Failed to store final score", exc_info=True)
            session.rollback()
        finally:
            session.close()
            
        self.hide_loading()
        # Navigate to Visual Results (Upstream Feature, Integrated)
        self.show_visual_results()

    # ---------------- INTEGRATED UPSTREAM FEATURES (Visuals/History) ----------------
    def show_visual_results(self):
        self.clear_screen()
        main_frame = tk.Frame(self.root, bg=self.colors["bg_primary"], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text=f"Test Results for {self.username}", font=("Arial", 18, "bold"), bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack(pady=10)
        
        score_text = f"{self.current_score}/{self.current_max_score}"
        tk.Label(main_frame, text=score_text, font=("Arial", 36, "bold"), bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack()
        
        # Simple Progress Bar
        bar_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        bar_frame.pack(pady=20)
        
        canvas = tk.Canvas(bar_frame, width=400, height=30, bg="white", highlightthickness=0)
        canvas.pack()
        
        fill_width = (self.current_percentage / 100.0) * 400
        # Color based on score
        color = self.colors["improvement_good"] if self.current_percentage >= 65 else self.colors["improvement_neutral"] if self.current_percentage >= 50 else self.colors["improvement_bad"]
        
        canvas.create_rectangle(0, 0, 400, 30, fill="#e0e0e0", outline="")
        canvas.create_rectangle(0, 0, fill_width, 30, fill=color, outline="")
        
        interpret = "Excellent" if self.current_percentage >= 80 else "Good" if self.current_percentage >= 65 else "Average" if self.current_percentage >= 50 else "Needs Work"
        tk.Label(main_frame, text=f"{interpret} ({self.current_percentage:.1f}%)", font=("Arial", 14), bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack(pady=10)
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=self.colors["bg_primary"])
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="View History", command=self.show_history_screen, font=("Arial", 11), bg=self.colors["accent"], fg="white").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Main Menu", command=self.create_username_screen, font=("Arial", 11), bg=self.colors["text_secondary"], fg="white").pack(side="left", padx=10)


    def show_history_screen(self):
        """History Screen (Refactored to use SQLAlchemy)"""
        self.clear_screen()
        
        header_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        header_frame.pack(fill="x", pady=10)
        
        tk.Button(header_frame, text="← Back", command=self.create_username_screen, font=("Arial", 10)).pack(side="left", padx=10)
        tk.Label(header_frame, text=f"History: {self.username}", font=("Arial", 16, "bold"), bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack(side="left", padx=20)
        
        session = get_session()
        try:
            # ORM Query: Get user's scores
            scores_data = session.query(Score).filter_by(username=self.username).order_by(Score.id.desc()).limit(10).all()
        finally:
            session.close()

        if not scores_data:
            tk.Label(self.root, text="No history found.", bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack(pady=50)
            return

        # List
        canvas = tk.Canvas(self.root, bg=self.colors["bg_primary"])
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors["bg_primary"])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")
        
        for s in scores_data:
            f = tk.Frame(scroll_frame, bg="white", pady=10, padx=10, relief="groove", bd=1)
            f.pack(fill="x", pady=5)
            
            # Since my Score model didn't have timestamp originally, handling potential absence
            # Assuming id acts as proxy for time order
            tk.Label(f, text=f"Test ID: {s.id}", font=("Arial", 10, "bold")).pack(side="left")
            tk.Label(f, text=f"Score: {s.total_score}", font=("Arial", 10)).pack(side="right", padx=20)

if __name__ == "__main__":
    splash_root = tk.Tk()
    splash = SplashScreen(splash_root)
    
    def launch_main_app():
        splash.root.destroy()
        root = tk.Tk()
        app = SoulSenseApp(root)
        root.mainloop()

    splash.close_after_delay(2000, launch_main_app)
    splash_root.mainloop()
