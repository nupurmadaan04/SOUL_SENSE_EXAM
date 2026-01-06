# import tkinter as tk
# from tkinter import messagebox
# from datetime import datetime
# import logging

# from app.db import get_connection
# from app.questions import load_questions
# from app.utils import compute_age_group
# from app.models import (
#     ensure_scores_schema,
#     ensure_responses_schema,
#     ensure_question_bank_schema
# )

# # --------------------------------------------------
# # Logging
# # --------------------------------------------------
# logging.basicConfig(
#     filename="logs/soulsense.log",
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # --------------------------------------------------
# # DB setup (run once on startup)
# # --------------------------------------------------
# def initialize_db():
#     conn = get_connection()
#     cursor = conn.cursor()

#     ensure_question_bank_schema(cursor)
#     ensure_scores_schema(cursor)
#     ensure_responses_schema(cursor)

#     conn.commit()
#     conn.close()


# # --------------------------------------------------
# # Tkinter App
# # --------------------------------------------------
# class SoulSenseApp:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Soul Sense Exam")
#         self.root.geometry("600x400")

#         self.username = ""
#         self.age = None
#         self.age_group = "unknown"

#         self.questions = load_questions()  # [(id, text), ...]
#         self.current_index = 0
#         self.responses = []

#         self.build_user_info_screen()

#     # -------------------------
#     # Screen 1: User Info
#     # -------------------------
#     def build_user_info_screen(self):
#         self.clear_screen()

#         tk.Label(self.root, text="Soul Sense Exam", font=("Arial", 18)).pack(pady=20)

#         tk.Label(self.root, text="Username").pack()
#         self.username_entry = tk.Entry(self.root)
#         self.username_entry.pack()

#         tk.Label(self.root, text="Age").pack()
#         self.age_entry = tk.Entry(self.root)
#         self.age_entry.pack()

#         tk.Button(self.root, text="Start Exam", command=self.start_exam).pack(pady=20)

#     def start_exam(self):
#         self.username = self.username_entry.get().strip()
#         age_raw = self.age_entry.get().strip()

#         if not self.username:
#             messagebox.showerror("Error", "Username required")
#             return

#         try:
#             self.age = int(age_raw)
#         except Exception:
#             self.age = None

#         self.age_group = compute_age_group(self.age)
#         logging.info(f"User started exam: {self.username}, age_group={self.age_group}")

#         self.build_question_screen()

#     # -------------------------
#     # Screen 2: Questions
#     # -------------------------
#     def build_question_screen(self):
#         self.clear_screen()

#         q_id, q_text = self.questions[self.current_index]

#         tk.Label(
#             self.root,
#             text=f"Question {self.current_index + 1} of {len(self.questions)}",
#             font=("Arial", 12)
#         ).pack(pady=10)

#         tk.Label(
#             self.root,
#             text=q_text,
#             wraplength=500,
#             font=("Arial", 14)
#         ).pack(pady=20)

#         self.answer_var = tk.IntVar(value=0)

#         for i in range(1, 6):
#             tk.Radiobutton(
#                 self.root,
#                 text=str(i),
#                 variable=self.answer_var,
#                 value=i
#             ).pack(anchor="w", padx=200)

#         tk.Button(self.root, text="Next", command=self.save_and_next).pack(pady=20)

#     def save_and_next(self):
#         value = self.answer_var.get()

#         if value == 0:
#             messagebox.showerror("Error", "Please select an answer")
#             return

#         q_id, _ = self.questions[self.current_index]

#         self.responses.append({
#             "question_id": q_id,
#             "value": value
#         })

#         self.current_index += 1

#         if self.current_index >= len(self.questions):
#             self.finish_exam()
#         else:
#             self.build_question_screen()

#     # -------------------------
#     # Finish + Save to DB
#     # -------------------------
#     def finish_exam(self):
#         conn = get_connection()
#         cursor = conn.cursor()

#         timestamp = datetime.utcnow().isoformat()

#         for r in self.responses:
#             cursor.execute(
#                 """
#                 INSERT INTO responses
#                 (username, question_id, response_value, age_group, timestamp)
#                 VALUES (?, ?, ?, ?, ?)
#                 """,
#                 (
#                     self.username,
#                     r["question_id"],
#                     r["value"],
#                     self.age_group,
#                     timestamp
#                 )
#             )

#         conn.commit()
#         conn.close()

#         logging.info(f"Exam completed for {self.username}")

#         self.clear_screen()
#         tk.Label(
#             self.root,
#             text="Thank you for completing the exam!",
#             font=("Arial", 16)
#         ).pack(pady=50)

#         tk.Button(self.root, text="Exit", command=self.root.quit).pack()

#     # -------------------------
#     # Utility
#     # -------------------------
#     def clear_screen(self):
#         for widget in self.root.winfo_children():
#             widget.destroy()


# # --------------------------------------------------
# # Entry point
# # --------------------------------------------------
# if __name__ == "__main__":
#     initialize_db()

#     root = tk.Tk()
#     app = SoulSenseApp(root)
#     root.mainloop()






import tkinter as tk
from tkinter import messagebox ,ttk  #imported the ttk
import logging
import sys
from datetime import datetime

from app.db import get_connection
from app.models import (
    ensure_scores_schema,
    ensure_responses_schema,
    ensure_question_bank_schema
)
from app.questions import load_questions
from app.utils import compute_age_group

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

conn.commit()

# ---------------- LOAD QUESTIONS FROM DB ----------------
try:
    rows = load_questions()  # [(id, text)]
    questions = [q[1] for q in rows]   # preserve text only
    
    '''
    reading only 10 for testing
    '''
    
    questions = questions[:10]
    
    if not questions:
        
        raise RuntimeError("Question bank empty")

    logging.info("Loaded %s questions from DB", len(questions))

except Exception:
    logging.critical("Failed to load questions from DB", exc_info=True)
    messagebox.showerror("Fatal Error", "Question bank could not be loaded.")
    sys.exit(1)

# ---------------- GUI ----------------
class SoulSenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        self.root.geometry("600x500")   # Same GUI window dimensions
        self.root.configure(bg="#F5F7FA")
        self.username = ""
        self.age = None
        self.education = None
        self.age_group = None


        self.current_question = 0
        self.total_questions = len(questions) #length of the questions
        self.responses = []

        self.create_username_screen()

    # ---------- SCREENS ----------
    def create_username_screen(self):
        self.clear_screen()

        card = tk.Frame(
            self.root,
            bg="white",
            padx=30,
            pady=25
        )
        card.pack(pady=30)

        tk.Label(
    card,
    text="🧠 Soul Sense EQ Test",
    font=("Arial", 22, "bold"),
    bg="white",
    fg="#2C3E50"
).pack(pady=(0, 8))


        tk.Label(
            card,
            text="Answer honestly to understand your emotional intelligence",
            font=("Arial", 11),
            bg="white",
            fg="#7F8C8D"
        ).pack(pady=(0, 20))


        # Name
        tk.Label(
    card,
    text="Enter Name",
    bg="white",
    fg="#34495E",
    font=("Arial", 11, "bold")
).pack(anchor="w", pady=(5, 2))

        self.name_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.name_entry.pack(pady=5)

        # Age
        tk.Label(
    card,
    text="Enter Age",
    bg="white",
    fg="#34495E",
    font=("Arial", 11, "bold")
).pack(anchor="w", pady=(5, 2))
        self.age_entry = ttk.Entry(card, font=("Arial", 12), width=30)
        self.age_entry.pack(pady=5)

        # Education (NEW)
        tk.Label(
    card,
    text="Your Name",
    bg="white",
    fg="#34495E",
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
    bg="#4CAF50",
    fg="white",
    activebackground="#43A047",
    activeforeground="white",
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

        logging.info(
            "Session started | user=%s | age=%s | education=%s | age_group=%s",
            self.username, self.age, self.education, self.age_group
        )


        self.show_question()

    def show_question(self):
        self.clear_screen()
        # -------- Progress Bar --------
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=5)

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            maximum=self.total_questions,
            value=self.current_question
        )
        self.progress.pack()

        self.progress_label = tk.Label(
            progress_frame,
            text=f"{self.current_question}/{self.total_questions} Completed",
            font=("Arial", 10)
        )
        self.progress_label.pack()


        if self.current_question >= len(questions):
            self.finish_test()
            return

        q = questions[self.current_question]
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
if __name__ == "__main__":
    root = tk.Tk()
    app = SoulSenseApp(root)
    root.protocol("WM_DELETE_WINDOW", app.force_exit)
    root.mainloop()
