import sqlite3
import tkinter as tk
from tkinter import messagebox,ttk
from journal_feature import JournalFeature
from analytics_dashboard import AnalyticsDashboard

#DATABASE SETUP
conn = sqlite3.connect("soulsense_db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    age INTEGER,
    education TEXT,
    total_score INTEGER
)
""")

# Add age column if it doesn't exist
try:
    cursor.execute("ALTER TABLE scores ADD COLUMN age INTEGER")
except sqlite3.OperationalError:
    pass  # Column already exists

conn.commit()
try:
    cursor.execute("ALTER TABLE scores ADD COLUMN education TEXT")
except sqlite3.OperationalError:
    pass

conn.commit()
#QUESTIONS
questions = [
    {"text": "You can recognize your emotions as they happen.", "age_min": 12, "age_max": 25},
    {"text": "You find it easy to understand why you feel a certain way.", "age_min": 14, "age_max": 30},
    {"text": "You can control your emotions even in stressful situations.", "age_min": 15, "age_max": 35},
    {"text": "You reflect on your emotional reactions to situations.", "age_min": 13, "age_max": 28},
    {"text": "You are aware of how your emotions affect others.", "age_min": 16, "age_max": 40}
]

#USER DETAILS WINDOW
root = tk.Tk()
root.title("SoulSense - User Details")
root.geometry("450x380")
root.resizable(False, False)

username = tk.StringVar()
age = tk.StringVar()
education = tk.StringVar()

style = ttk.Style()
style.theme_use("clam")

container = ttk.Frame(root, padding=20)
container.pack(expand=True)

ttk.Label(
    container,
    text="🧠 SoulSense EQ Assessment",
    font=("Arial", 20, "bold")
).pack(pady=15)

ttk.Label(container, text="Name", font=("Arial", 12)).pack(anchor="w")
ttk.Entry(container, textvariable=username, font=("Arial", 12), width=30).pack(pady=5)

ttk.Label(container, text="Age", font=("Arial", 12)).pack(anchor="w")
ttk.Entry(container, textvariable=age, font=("Arial", 12), width=30).pack(pady=5)

ttk.Label(container, text="Education Level", font=("Arial", 12)).pack(anchor="w")

education_combo = ttk.Combobox(
    container,
    textvariable=education,
    values=[
        "School Student",
        "Undergraduate",
        "Postgraduate",
        "Working Professional",
        "Other"
    ],
    state="readonly",
    width=28
)
education_combo.pack(pady=5)
education_combo.current(0)


def submit_details():
    if not username.get().strip():
        messagebox.showerror("Error", "Please enter your name")
        return

    if not age.get().isdigit():
        messagebox.showerror("Error", "Please enter a valid age")
        return

    if not education.get():
        messagebox.showerror("Error", "Please select education level")
        return

    root.destroy()
    start_quiz(username.get(), int(age.get()), education.get())

tk.Button(
    root,
    text="Start Assessment",
    command=submit_details,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 14, "bold"),
    width=20
).pack(pady=15)

# Initialize features
journal_feature = JournalFeature(root)

tk.Button(
    root,
    text="📝 Open Journal",
    command=lambda: journal_feature.open_journal_window(username.get() or "Guest"),
    bg="#2196F3",
    fg="white",
    font=("Arial", 12),
    width=20
).pack(pady=5)

tk.Button(
    root,
    text="📊 View Dashboard",
    command=lambda: AnalyticsDashboard(root, username.get() or "Guest").open_dashboard(),
    bg="#FF9800",
    fg="white",
    font=("Arial", 12),
    width=20
).pack(pady=5)

#QUIZ WINDOW
def start_quiz(username, age, education):
    filtered_questions = [
        q for q in questions if q["age_min"] <= age <= q["age_max"]
    ]

    if not filtered_questions:
        messagebox.showinfo("No Questions", "No questions available for your age group.")
        return

    quiz = tk.Tk()
    quiz.title("SoulSense Assessment")
    quiz.geometry("750x500")

    score = 0
    current_q = 0
    var = tk.IntVar()

    question_label = tk.Label(
        quiz,
        text="",
        wraplength=700,
        font=("Arial", 16)
    )
    question_label.pack(pady=25)
    progress = ttk.Label(quiz, text="", font=("Arial", 11))
    progress.pack()

    options = [
        ("Strongly Disagree", 1),
        ("Disagree", 2),
        ("Neutral", 3),
        ("Agree", 4),
        ("Strongly Agree", 5)
    ]

    for text, val in options:
        tk.Radiobutton(
            quiz,
            text=text,
            variable=var,
            value=val,
            font=("Arial", 14)
        ).pack(anchor="w", padx=60, pady=2)

    def load_question():
        question_label.config(text=filtered_questions[current_q]["text"])
        progress.config(text=f"Question {current_q + 1} of {len(filtered_questions)}")


    def next_question():
        nonlocal current_q, score

        if var.get() == 0:
            messagebox.showwarning("Warning", "Please select an option")
            return

        score += var.get()
        var.set(0)
        current_q += 1

        if current_q < len(filtered_questions):
            load_question()
        else:
            cursor.execute(
    "INSERT INTO scores (username, age, education, total_score) VALUES (?, ?, ?, ?)",
    (username, age, education, score)
)

            conn.commit()

            # Show completion message with options
            result = messagebox.askyesno(
                "Completed",
                f"Thank you {username}!\nYour EQ Score: {score}\n\nView your dashboard?"
            )
            
            if result:
                quiz.destroy()
                dashboard = AnalyticsDashboard(None, username)
                dashboard.open_dashboard()
            else:
                quiz.destroy()
            conn.close()

    tk.Button(
        quiz,
        text="Next",
        command=next_question,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 14, "bold"),
        width=15
    ).pack(pady=30)

    load_question()
    quiz.mainloop()

root.mainloop()