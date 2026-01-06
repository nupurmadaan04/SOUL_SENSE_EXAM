import tkinter as tk
from tkinter import messagebox, ttk
import logging
import sys
from datetime import datetime

# --- NEW IMPORTS FOR GRAPHS ---
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.db import get_connection
from app.models import (
    ensure_scores_schema,
    ensure_responses_schema,
    ensure_question_bank_schema,
    ensure_users_schema
)
from app.questions import load_questions
from app.utils import compute_age_group
from app.auth import create_user, authenticate_user

# ---------------- LOGGING ----------------
logging.basicConfig(
    filename="logs/soulsense.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Application started")

# ---------------- DB INIT ----------------
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    total_score INTEGER,
    age INTEGER
)
""")

ensure_scores_schema(cursor)
ensure_responses_schema(cursor)
ensure_question_bank_schema(cursor)
ensure_users_schema(cursor)

conn.commit()

# ---------------- GUI ----------------
class SoulSenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        # Modified size to fit Graph
        self.root.geometry("500x400")

        self.username = ""
        self.age = None
        self.age_group = None
        self.logged_in = False

        self.questions = []
        self.current_question = 0
        self.total_questions = 0
        self.responses = []

        self.create_login_screen()

    # ---------- SCREENS ----------
    def create_login_screen(self):
        self.clear_screen()
        
        tk.Label(self.root, text="Soul Sense EQ Test", font=("Arial", 18, "bold")).pack(pady=20)
        
        tk.Label(self.root, text="Username:", font=("Arial", 12)).pack(pady=5)
        self.login_username = tk.Entry(self.root, font=("Arial", 12))
        self.login_username.pack(pady=5)
        
        tk.Label(self.root, text="Password:", font=("Arial", 12)).pack(pady=5)
        self.login_password = tk.Entry(self.root, font=("Arial", 12), show="*")
        self.login_password.pack(pady=5)
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Login", command=self.login, font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Sign Up", command=self.create_signup_screen, font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
    
    def create_signup_screen(self):
        self.clear_screen()
        
        tk.Label(self.root, text="Create Account", font=("Arial", 18, "bold")).pack(pady=20)
        
        tk.Label(self.root, text="Username:", font=("Arial", 12)).pack(pady=5)
        self.signup_username = tk.Entry(self.root, font=("Arial", 12))
        self.signup_username.pack(pady=5)
        
        tk.Label(self.root, text="Password:", font=("Arial", 12)).pack(pady=5)
        self.signup_password = tk.Entry(self.root, font=("Arial", 12), show="*")
        self.signup_password.pack(pady=5)
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Create Account", command=self.signup, font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Back to Login", command=self.create_login_screen, font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
    
    def login(self):
        username = self.login_username.get().strip()
        password = self.login_password.get()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return
        
        success, message = authenticate_user(username, password)
        if success:
            self.username = username
            self.logged_in = True
            self.create_username_screen()
        else:
            messagebox.showerror("Login Failed", message)
    
    def signup(self):
        username = self.signup_username.get().strip()
        password = self.signup_password.get()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return
        
        if len(password) < 4:
            messagebox.showwarning("Input Error", "Password must be at least 4 characters.")
            return
        
        success, message = create_user(username, password)
        if success:
            messagebox.showinfo("Success", "Account created successfully! Please login.")
            self.create_login_screen()
        else:
            messagebox.showerror("Signup Failed", message)
    
    def logout(self):
        self.logged_in = False
        self.username = ""
        self.create_login_screen()

    def create_username_screen(self):
        self.clear_screen()

        # Add logout button
        logout_frame = tk.Frame(self.root)
        logout_frame.pack(anchor="ne", padx=10, pady=5)
        tk.Label(logout_frame, text=f"Logged in as: {self.username}", font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Button(logout_frame, text="Logout", command=self.logout, font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)

        tk.Label(self.root, text="Enter Your Age (optional):", font=("Arial", 14)).pack(pady=20)
        self.age_entry = tk.Entry(self.root, font=("Arial", 14))
        self.age_entry.pack(pady=5)

        tk.Button(self.root, text="Start Test", command=self.start_test).pack(pady=15)

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
        if not self.logged_in:
            messagebox.showerror("Access Denied", "Please login first.")
            self.create_login_screen()
            return
            
        age_str = self.age_entry.get().strip()

        ok, age, err = self.validate_age_input(age_str)
        if not ok:
            messagebox.showwarning("Input Error", err)
            return

        self.age = age
        self.age_group = compute_age_group(age)

        # -------- LOAD AGE-APPROPRIATE QUESTIONS --------
        # This logic is PRESERVED from the original file
        try:
            print(self.age)
            rows = load_questions(age=self.age)  # [(id, text)]
            self.questions = [q[1] for q in rows]

            # temporary limit (existing behavior)
            self.questions = self.questions[:10]
            
            # Added for Progress Bar logic
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
            "Session started | user=%s | age=%s | age_group=%s | questions=%s",
            self.username,
            self.age,
            self.age_group,
            len(self.questions)
        )

        self.show_question()

    def show_question(self):
        self.clear_screen()
        
        # --- NEW: Progress Bar ---
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=5)

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
            font=("Arial", 10)
        )
        self.progress_label.pack()

        if self.current_question >= len(self.questions):
            self.finish_test()
            return

        q = self.questions[self.current_question]

        tk.Label(
            self.root,
            text=f"Q{self.current_question + 1}: {q}",
            wraplength=400,
            font=("Arial", 12)
        ).pack(pady=20)

        self.answer_var = tk.IntVar()

        for val, txt in enumerate(["Never", "Sometimes", "Often", "Always"], 1):
            tk.Radiobutton(
                self.root,
                text=f"{txt} ({val})",
                variable=self.answer_var,
                value=val
            ).pack(anchor="w", padx=100)

        tk.Button(self.root, text="Next", command=self.save_answer).pack(pady=15)

    def save_answer(self):
        ans = self.answer_var.get()
        if ans == 0:
            messagebox.showwarning("Input Error", "Please select an answer.")
            return

        self.responses.append(ans)

        qid = self.current_question + 1
        ts = datetime.utcnow().isoformat()

        try:
            cursor.execute(
                """
                INSERT INTO responses
                (username, question_id, response_value, age_group, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.username, qid, ans, self.age_group, ts)
            )
            conn.commit()
        except Exception:
            logging.error("Failed to store response", exc_info=True)

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
        try:
            cursor.execute(
                "INSERT INTO scores (username, age, total_score) VALUES (?, ?, ?)",
                (self.username, self.age, total_score)
            )
            conn.commit()
        except Exception:
            logging.error("Failed to store final score", exc_info=True)

        interpretation = (
            "Excellent Emotional Intelligence!" if total_score >= 30 else
            "Good Emotional Intelligence." if total_score >= 20 else
            "Average Emotional Intelligence." if total_score >= 15 else
            "Room for improvement."
        )

        # --- UPDATED: Build Result Screen ---
        self.clear_screen()
        self.root.geometry("800x600") # Resize for results

        # Left Side: Text Results
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, padx=20, fill=tk.Y)

        tk.Label(left_frame, text=f"Results for {self.username}", font=("Arial", 18, "bold")).pack(pady=20)
        tk.Label(
            left_frame,
            text=f"Total Score: {total_score}",
            font=("Arial", 16)
        ).pack(pady=10)
        tk.Label(left_frame, text=interpretation, font=("Arial", 14), fg="blue", wraplength=250).pack(pady=10)

        tk.Label(left_frame, text="Breakdown:", font=("Arial", 12, "bold")).pack(pady=(20,5))
        tk.Label(left_frame, text=f"Self-Awareness: {cat1_score}/12").pack()
        tk.Label(left_frame, text=f"Empathy: {cat2_score}/12").pack()
        tk.Label(left_frame, text=f"Social Skills: {cat3_score}/16").pack()

        tk.Button(left_frame, text="Exit", command=self.force_exit, font=("Arial", 12), bg="#ffcccc").pack(pady=40)

        # Right Side: Graph
        right_frame = tk.Frame(self.root, bg="white")
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(right_frame, text="Visual Analysis", bg="white", font=("Arial", 12)).pack(pady=5)
        
        # Embed the chart
        chart_widget = self.create_radar_chart(right_frame, categories, vals_normalized)
        chart_widget.pack(fill=tk.BOTH, expand=True)

    def force_exit(self):
        try:
            conn.close()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def clear_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

# ---------------- MAIN ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SoulSenseApp(root)
    root.protocol("WM_DELETE_WINDOW", app.force_exit)
    root.mainloop()
