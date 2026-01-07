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
from app.models import Score, Response
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

# Note: DB Init is handled by app.db.check_db_state() on import

# ---------------- THEMES ----------------
THEMES = {
    "light": {
        "bg_primary": "#F5F7FA",
        "bg_secondary": "white",
        "text_primary": "#2C3E50",
        "text_secondary": "#7F8C8D",
        "text_input": "#34495E",
        "accent": "#3498DB",
        "success": "#4CAF50",
        "danger": "#E74C3C",
        "card_bg": "white",
        "input_bg": "white",
        "input_fg": "black",
        "tooltip_bg": "#FFFFE0",
        "tooltip_fg": "black"
    },
    "dark": {
        "bg_primary": "#1a1a1a",
        "bg_secondary": "#2d2d2d",
        "text_primary": "#ffffff",
        "text_secondary": "#b0b0b0",
        "text_input": "#e0e0e0",
        "accent": "#5DADE2",
        "success": "#58D68D",
        "danger": "#EC7063",
        "card_bg": "#2d2d2d",
        "input_bg": "#3d3d3d",
        "input_fg": "white",
        "tooltip_bg": "#333333",
        "tooltip_fg": "white"
    }
}

class SplashScreen:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # remove title bar
        self.root.geometry("450x300")
        
        # Load theme from config
        theme = config.THEME
        # Simple local theme logic for splash
        bg = "#1a1a1a" if theme == "dark" else "#F5F7FA"
        fg = "#ffffff" if theme == "dark" else "#2C3E50"
        
        self.root.configure(bg=bg)

        # Center window
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

        # Simple loading text
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

# ---------------- GUI ----------------
class SoulSenseApp:
    def return_to_home(self):
        confirm = messagebox.askyesno(
            "Return to Home",
            "Are you sure you want to return to the home screen?\nYour current progress will be lost."
        )

        if not confirm:
            return

        # ---- RESET TEST STATE ----
        self.current_question = 0
        self.responses = [] 
        self.answer_var = None
        self.age = None
        self.age_group = None

        logging.info("User returned to home screen during test")

        if self.auth_manager.is_logged_in():
            self.create_username_screen()
        else:
            self.create_login_screen()

    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        self.root.geometry("600x500")
        
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

        self.create_login_screen()

    # ---------- HELPERS ----------
    def toggle_theme(self):
        # Determine new theme
        new_theme = "dark" if self.current_theme_name == "light" else "light"
        
        # Update app state
        self.current_theme_name = new_theme
        self.colors = THEMES.get(self.current_theme_name, THEMES["light"])
        self.root.configure(bg=self.colors["bg_primary"])
        
        # Save to config
        try:
            current_config = config.load_config()
            current_config["ui"]["theme"] = new_theme
            config.save_config(current_config)
            messagebox.showinfo("Theme Changed", "Theme changed! Please restart the application to fully apply changes.")
        except Exception as e:
            logging.error(f"Failed to save theme: {e}")
            
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
        
        # Header with Theme Toggle & Settings Button
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

        # Settings Button (Merged from Upstream)
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
        
        # Username
        tk.Label(
            card,
            text="Username",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        
        self.login_username_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.login_username_entry.pack(pady=5)
        
        # Password
        tk.Label(
            card,
            text="Password",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        
        self.login_password_entry = ttk.Entry(card, font=("Arial", 12), width=30, show="*")
        self.login_password_entry.pack(pady=5)
        
        # Buttons
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
        """Show settings configuration window (Merged Feature)"""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("400x300")
        settings_win.configure(bg=self.colors["bg_primary"])
        
        # Center window
        x = self.root.winfo_x() + (self.root.winfo_width() - settings_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - settings_win.winfo_height()) // 2
        settings_win.geometry(f"+{x}+{y}")
        
        tk.Label(
            settings_win,
            text="Settings",
            font=("Arial", 16, "bold"),
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"]
        ).pack(pady=15)
        
        # Current Config Display
        tk.Label(
            settings_win,
            text=f"Current Theme: {self.current_theme_name}",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"]
        ).pack(pady=5)

        tk.Label(
            settings_win,
            text="Modify 'config.json' to change database paths or other settings.",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            font=("Arial", 9, "italic")
        ).pack(pady=20)
        
        tk.Button(
            settings_win,
            text="Close",
            command=settings_win.destroy,
            bg=self.colors["accent"],
            fg="white"
        ).pack(pady=10)
    
    def create_signup_screen(self):
        self.clear_screen()
        
        card = tk.Frame(
            self.root,
            bg=self.colors["card_bg"],
            padx=30,
            pady=25
        )
        card.pack(pady=50)
        
        tk.Label(
            card,
            text="🧠 Create Account",
            font=("Arial", 22, "bold"),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"]
        ).pack(pady=(0, 8))
        
        tk.Label(
            card,
            text="Join Soul Sense EQ Test",
            font=("Arial", 11),
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"]
        ).pack(pady=(0, 20))
        
        # Username
        tk.Label(
            card,
            text="Username",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        
        self.signup_username_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.signup_username_entry.pack(pady=5)
        
        # Password
        tk.Label(
            card,
            text="Password",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        
        self.signup_password_entry = ttk.Entry(card, font=("Arial", 12), width=30, show="*")
        self.signup_password_entry.pack(pady=5)
        
        # Confirm Password
        tk.Label(
            card,
            text="Confirm Password",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        
        self.signup_confirm_entry = ttk.Entry(card, font=("Arial", 12), width=30, show="*")
        self.signup_confirm_entry.pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(card, bg=self.colors["card_bg"])
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Create Account",
            command=self.handle_signup,
            font=("Arial", 12, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            button_frame,
            text="Back to Login",
            command=self.create_login_screen,
            font=("Arial", 12),
            bg="#757575",
            fg="white",
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="left")
    
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
        confirm = messagebox.askyesno(
            "Logout",
            "Are you sure you want to logout?"
        )
        
        if confirm:
            self.auth_manager.logout_user()
            self.username = ""
            logging.info("User logged out")
            self.create_login_screen()
    
    def create_username_screen(self):
        self.clear_screen()

        card = tk.Frame(
            self.root,
            bg=self.colors["card_bg"],
            padx=30,
            pady=25
        )
        card.pack(pady=30)

        tk.Label(
            card,
            text="🧠 Soul Sense EQ Test",
            font=("Arial", 22, "bold"),
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"]
        ).pack(pady=(0, 8))


        tk.Label(
            card,
            text="Answer honestly to understand your emotional intelligence",
            font=("Arial", 11),
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"]
        ).pack(pady=(0, 20))

        # Logout button
        logout_frame = tk.Frame(card, bg=self.colors["card_bg"])
        logout_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            logout_frame,
            text=f"Logged in as: {self.auth_manager.current_user}",
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
            font=("Arial", 10)
        ).pack(side="left")
        
        tk.Button(
            logout_frame,
            text="Logout",
            command=self.handle_logout,
            font=("Arial", 10),
            bg=self.colors["danger"],
            fg="white",
            relief="flat",
            padx=15,
            pady=5
        ).pack(side="right")


        # Name
        tk.Label(
            card,
            text="Enter Name",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))

        self.name_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.name_entry.insert(0, self.username) # Prefill username from login
        self.name_entry.configure(state='readonly') # Make it readonly
        self.name_entry.pack(pady=5)

        # Age
        tk.Label(
            card,
            text="Enter Age",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        self.age_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.age_entry.pack(pady=5)

        # Education (NEW)
        tk.Label(
            card,
            text="Education",
            bg=self.colors["card_bg"],
            fg=self.colors["text_input"],
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(5, 2))
        self.education_combo = ttk.Combobox(
            card,
            state="readonly",
            width=28,
            values=[
                "School Student",
                "Undergraduate",
                "Postgraduate",
                "Working Professional",
                "Other"
            ]
        )
        self.education_combo.pack(pady=5)
        self.education_combo.set("Select your education")

        tk.Button(
            card,
            text="Start EQ Test →",
            command=self.start_test,
            font=("Arial", 12, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            padx=20,
            pady=8
        ).pack(pady=25)


    # ---------- VALIDATION ----------
    def validate_name_input(self, name):
        if not name:
            return False, "Please enter your name."
        if not all(c.isalpha() or c.isspace() for c in name):
            return False, "Name must contain only letters and spaces."
        return True, None

    def validate_age_input(self, age_str):
        if age_str == "":
            return True, None, None
        try:
            age = int(age_str)
            if not (1 <= age <= 120):
                return False, None, "Age must be between 1 and 120."
            return True, age, None
        except ValueError:
            return False, None, "Age must be numeric."

    # ---------- FLOW ----------
    def start_test(self):
        # Username comes from login/entry
        self.username = self.name_entry.get().strip()
        age_str = self.age_entry.get().strip()
        self.education = self.education_combo.get()


        ok, err = self.validate_name_input(self.username)
        if not ok:
            messagebox.showwarning("Input Error", err)
            return
        if not self.education or self.education == "Select your education":
            messagebox.showwarning("Input Error", "Please select your education level.")
            return


        ok, age, err = self.validate_age_input(age_str)
        if not ok:
            messagebox.showwarning("Input Error", err)
            return

        self.age = age
        self.age_group = compute_age_group(age)

        # -------- LOAD AGE-APPROPRIATE QUESTIONS --------
        try:
            print(self.age)
            rows = load_questions(age=self.age)  # [(id, text, tooltip)]
            
            # Store (text, tooltip) tuples
            self.questions = [(q[1], q[2]) for q in rows]

            # temporary limit based on config (merged feature idea)
            self.total_questions = len(self.questions)

            if not self.questions:
                raise RuntimeError("No questions loaded")

        except Exception:
            logging.error("Failed to load age-appropriate questions", exc_info=True)
            messagebox.showerror(
                "Error",
                "No questions available for your age group."
            )
            return

        logging.info(
            "Session started | user=%s | age=%s | education=%s | age_group=%s",
            self.username, self.age, self.education, self.age_group
        )


        self.show_question()

    def show_question(self):
        self.clear_screen()
        
        # --- NEW: Progress Bar ---
        progress_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        progress_frame.pack(fill="x", pady=5, padx=10)

        tk.Button(
            progress_frame,
            text="🏠 Home",
            command=self.return_to_home,
            bg=self.colors["bg_secondary"],
            relief="flat"
        ).pack(side="right")
        
        tk.Button(
            progress_frame,
            text="Logout",
            command=self.handle_logout,
            font=("Arial", 10),
            bg=self.colors["danger"],
            fg="white",
            relief="flat",
            padx=10,
            pady=5
        ).pack(side="right", padx=(0, 5))


        max_val = self.total_questions if self.total_questions > 0 else 10

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            maximum=max_val,
            value=self.current_question
        )
        self.progress.pack()

        self.progress_label = tk.Label(
            progress_frame,
            text=f"{self.current_question}/{self.total_questions} Completed",
            font=("Arial", 10),
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"]
        )
        self.progress_label.pack()

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
            tooltip_btn = tk.Label(
                question_frame,
                text="ℹ️",
                font=("Arial", 12),
                fg=self.colors["accent"],
                bg=self.colors["bg_primary"],
                cursor="hand2"
            )
            tooltip_btn.pack(side="left", padx=5)
            
            # Simple tooltip functionality
            def on_enter(e):
                self.tooltip_w = tk.Toplevel(self.root)
                self.tooltip_w.wm_overrideredirect(True)
                x = e.widget.winfo_rootx() + 20
                y = e.widget.winfo_rooty() + 20
                self.tooltip_w.wm_geometry(f"+{x}+{y}")
                label = tk.Label(
                    self.tooltip_w, 
                    text=q_tooltip, 
                    bg=self.colors["tooltip_bg"], 
                    fg=self.colors["tooltip_fg"],
                    relief="solid", 
                    borderwidth=1, 
                    padx=5, 
                    pady=3
                )
                label.pack()
                
            def on_leave(e):
                if hasattr(self, 'tooltip_w'):
                    self.tooltip_w.destroy()
            
            tooltip_btn.bind("<Enter>", on_enter)
            tooltip_btn.bind("<Leave>", on_leave)

        self.answer_var = tk.IntVar()

        for val, txt in enumerate(["Never", "Sometimes", "Often", "Always"], 1):
            tk.Radiobutton(
                self.root,
                text=f"{txt} ({val})",
                variable=self.answer_var,
                value=val,
                bg=self.colors["bg_primary"],
                fg=self.colors["text_primary"],
                selectcolor=self.colors["bg_secondary"]
            ).pack(anchor="w", padx=100)

        tk.Button(self.root, text="Next", command=self.save_answer).pack(pady=15)

    def save_answer(self):
        try:
            ans = self.answer_var.get()
            if ans == 0:
                messagebox.showwarning("Input Error", "Please select an answer.")
                return
        except Exception: 
            messagebox.showwarning("Input Error", "Invalid selection.")
            return

        self.responses.append(ans)

        qid = self.current_question + 1
        
        session = get_session()
        try:
            response = Response(
                username=self.username,
                question_id=qid,
                response_value=ans,
                age_group=self.age_group,
                timestamp=datetime.utcnow().isoformat()
            )
            session.add(response)
            session.commit()
        except Exception:
            logging.error("Failed to store response", exc_info=True)
            session.rollback()
        finally:
            session.close()

        self.current_question += 1
        self.show_question()

    # ---------------- NEW: GRAPH GENERATION ----------------
    def create_radar_chart(self, parent_frame, categories, values):
        """
        Creates a Radar/Spider chart embedded in a Tkinter frame.
        """
        N = len(categories)
        values_closed = values + [values[0]]
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += [angles[0]]

        fig = plt.Figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(111, polar=True)

        plt.xticks(angles[:-1], categories)
        
        ax.plot(angles, values_closed, linewidth=2, linestyle='solid', color='blue')
        ax.fill(angles, values_closed, 'blue', alpha=0.1)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        return canvas.get_tk_widget()

    def finish_test(self):
        total_score = sum(self.responses)
        
        # --- NEW: SIMULATE CATEGORIES (Splitting questions) ---
        r = self.responses
        cat1_score = sum(r[0:3]) if len(r) > 0 else 0
        cat2_score = sum(r[3:6]) if len(r) > 3 else 0
        cat3_score = sum(r[6:10]) if len(r) > 6 else 0

        # Normalize to scale of 10 for graph
        vals_normalized = [
            (cat1_score / 12) * 10,
            (cat2_score / 12) * 10,
            (cat3_score / 16) * 10
        ]
        categories = ["Self-Awareness", "Empathy", "Social Skills"]

        # Save to DB
        session = get_session()
        try:
            score = Score(
                username=self.username,
                age=self.age,
                total_score=total_score
            )
            session.add(score)
            session.commit()
        except Exception:
            logging.error("Failed to store final score", exc_info=True)
            session.rollback()
        finally:
            session.close()

        interpretation = (
            "Excellent Emotional Intelligence!" if total_score >= 30 else
            "Good Emotional Intelligence." if total_score >= 20 else
            "Average Emotional Intelligence." if total_score >= 15 else
            "Room for improvement."
        )

        # --- UPDATED: Build Result Screen ---
        self.clear_screen()
        self.root.geometry("800x600") # Resize for results
        self.root.configure(bg=self.colors["bg_primary"])

        # Left Side: Text Results
        left_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        left_frame.pack(side=tk.LEFT, padx=20, fill=tk.Y)

        tk.Label(left_frame, text=f"Results for {self.username}", font=("Arial", 18, "bold"), bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack(pady=20)
        tk.Label(
            left_frame,
            text=f"Total Score: {total_score}",
            font=("Arial", 16),
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"]
        ).pack(pady=10)
        tk.Label(left_frame, text=interpretation, font=("Arial", 14), fg=self.colors["accent"], bg=self.colors["bg_primary"], wraplength=250).pack(pady=10)

        tk.Label(left_frame, text="Breakdown:", font=("Arial", 12, "bold"), bg=self.colors["bg_primary"], fg=self.colors["text_primary"]).pack(pady=(20,5))
        tk.Label(left_frame, text=f"Self-Awareness: {cat1_score}/12", bg=self.colors["bg_primary"], fg=self.colors["text_secondary"]).pack()
        tk.Label(left_frame, text=f"Empathy: {cat2_score}/12", bg=self.colors["bg_primary"], fg=self.colors["text_secondary"]).pack()
        tk.Label(left_frame, text=f"Social Skills: {cat3_score}/16", bg=self.colors["bg_primary"], fg=self.colors["text_secondary"]).pack()

        button_frame = tk.Frame(left_frame, bg=self.colors["bg_primary"])
        button_frame.pack(pady=40)
        
        tk.Button(
            button_frame,
            text="Logout",
            command=self.handle_logout,
            font=("Arial", 12),
            bg=self.colors["danger"],
            fg="white",
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            button_frame,
            text="Exit",
            command=self.force_exit,
            font=("Arial", 12),
            bg="#ffcccc", # Keep this or verify lighter accent
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="left")

        # Right Side: Graph
        right_frame = tk.Frame(self.root, bg=self.colors["card_bg"])
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(right_frame, text="Visual Analysis", bg=self.colors["card_bg"], fg=self.colors["text_primary"], font=("Arial", 12)).pack(pady=5)
        
        # Embed the chart
        chart_widget = self.create_radar_chart(right_frame, categories, vals_normalized)

    def force_exit(self):
        self.root.destroy()
        sys.exit(0)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

# ---------------- MAIN ----------------
if __name__ == "__main__":
    splash_root = tk.Tk()
    splash = SplashScreen(splash_root)
    
    def launch_main_app():
        splash.root.destroy()
        root = tk.Tk()
        app = SoulSenseApp(root)
        root.mainloop()

    splash.close_after_delay(2500, launch_main_app)
    splash_root.mainloop()
