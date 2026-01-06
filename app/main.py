import tkinter as tk
from tkinter import messagebox
import logging
import sys
from datetime import datetime

from app.db import get_connection
from app.models import (
    ensure_scores_schema,
    ensure_responses_schema,
    ensure_question_bank_schema,
    ensure_journal_entries_schema
)
from app.questions import load_questions
from app.utils import compute_age_group
from app.login_gui import LoginWindow

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
ensure_journal_entries_schema(cursor)

conn.commit()

# ---------------- GUI ----------------
class SoulSenseApp:
    def __init__(self, root, authenticated_username):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        self.root.geometry("500x350")

        self.username = authenticated_username
        self.age = None
        self.age_group = None

        self.questions = []
        self.current_question = 0
        self.responses = []

        self.create_main_menu()

    # ---------- SCREENS ----------
    def create_main_menu(self):
        """Create main menu with options"""
        self.clear_screen()
        
        tk.Label(self.root, text=f"Welcome, {self.username}!", font=("Arial", 16, "bold")).pack(pady=20)
        
        tk.Button(self.root, text="Take EQ Test", command=self.create_age_screen, 
                 font=("Arial", 14), bg="#4CAF50", fg="white", width=20).pack(pady=10)
        
        tk.Button(self.root, text="Emotional Journal", command=self.open_journal, 
                 font=("Arial", 14), bg="#FF9800", fg="white", width=20).pack(pady=10)
        
        tk.Button(self.root, text="Logout", command=self.logout, 
                 font=("Arial", 14), width=20).pack(pady=10)
    
    def create_age_screen(self):
        """Create age input screen"""
        self.clear_screen()
        
        tk.Label(self.root, text="Enter Your Age (optional):", font=("Arial", 14)).pack(pady=20)
        self.age_entry = tk.Entry(self.root, font=("Arial", 14))
        self.age_entry.pack(pady=10)
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Start Test", command=self.start_test, 
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Back", command=self.create_main_menu, 
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    
    def open_journal(self):
        """Open journal feature"""
        try:
            from journal_feature import JournalFeature
            journal = JournalFeature(self.root, self.username)
        except ImportError:
            messagebox.showinfo("Feature Unavailable", "Journal feature is not available.")
    
    def logout(self):
        """Logout and return to login screen"""
        self.root.destroy()
        start_application()

    def create_username_screen(self):
        self.clear_screen()

        tk.Label(self.root, text="Enter Your Name:", font=("Arial", 14)).pack(pady=10)
        self.name_entry = tk.Entry(self.root, font=("Arial", 14))
        self.name_entry.pack(pady=5)

        tk.Label(self.root, text="Enter Your Age (optional):", font=("Arial", 14)).pack(pady=5)
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
        age_str = self.age_entry.get().strip()

        ok, age, err = self.validate_age_input(age_str)
        if not ok:
            messagebox.showwarning("Input Error", err)
            return

        self.age = age
        self.age_group = compute_age_group(age)

        # -------- LOAD AGE-APPROPRIATE QUESTIONS --------
        try:
            print(self.age)
            rows = load_questions(age=self.age)  # [(id, text)]
            self.questions = [q[1] for q in rows]

            # temporary limit (existing behavior)
            self.questions = self.questions[:10]

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

        if self.current_question >= len(self.questions):
            self.finish_test()
            return

        q = self.questions[self.current_question]

        tk.Label(
            self.root,
            text=f"Q{self.current_question + 1}: {q}",
            wraplength=400
        ).pack(pady=20)

        self.answer_var = tk.IntVar()

        for val, txt in enumerate(["Never", "Sometimes", "Often", "Always"], 1):
            tk.Radiobutton(
                self.root,
                text=f"{txt} ({val})",
                variable=self.answer_var,
                value=val
            ).pack(anchor="w", padx=50)

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

    def finish_test(self):
        total_score = sum(self.responses)

        try:
            cursor.execute(
                "INSERT INTO scores (username, age, total_score) VALUES (?, ?, ?)",
                (self.username, self.age, total_score)
            )
            conn.commit()
        except Exception:
            logging.error("Failed to store final score", exc_info=True)

        interpretation = (
            "Excellent Emotional Intelligence!" if total_score >= 65 else
            "Good Emotional Intelligence." if total_score >= 50 else
            "Average Emotional Intelligence." if total_score >= 35 else
            "You may want to work on your Emotional Intelligence."
        )

        self.clear_screen()
        tk.Label(self.root, text=f"Thank you, {self.username}!", font=("Arial", 16)).pack(pady=10)
        tk.Label(
            self.root,
            text=f"Your total EQ score is: {total_score} / {len(self.responses) * 4}",
            font=("Arial", 14)
        ).pack(pady=10)
        tk.Label(self.root, text=interpretation, font=("Arial", 14), fg="blue").pack(pady=10)

        tk.Button(self.root, text="Exit", command=self.force_exit, font=("Arial", 12)).pack(pady=20)

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
def start_application():
    """Start the application with authentication"""
    def on_login_success(username):
        root = tk.Tk()
        app = SoulSenseApp(root, username)
        root.protocol("WM_DELETE_WINDOW", app.force_exit)
        root.mainloop()
    
    login_window = LoginWindow(on_login_success)
    login_window.show()

if __name__ == "__main__":
    start_application()
