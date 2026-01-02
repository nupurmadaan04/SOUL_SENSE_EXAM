import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect("soulsense_db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    age INTEGER,
    total_score INTEGER
)
""")
conn.commit()

# ---------------- QUESTIONS WITH AGE LIMITS ----------------
questions = [
    {
        "text": "You can recognize your emotions as they happen.",
        "age_min": 12,
        "age_max": 25
    },
    {
        "text": "You find it easy to understand why you feel a certain way.",
        "age_min": 14,
        "age_max": 30
    },
    {
        "text": "You can control your emotions even in stressful situations.",
        "age_min": 15,
        "age_max": 35
    },
    {
        "text": "You reflect on your emotional reactions to situations.",
        "age_min": 13,
        "age_max": 28
    },
    {
        "text": "You are aware of how your emotions affect others.",
        "age_min": 16,
        "age_max": 40
    }
]

# ---------------- GET USER DETAILS ----------------
root = tk.Tk()
root.withdraw()

username = simpledialog.askstring("SoulSense", "Enter your name:")
age = simpledialog.askinteger("SoulSense", "Enter your age:")

if not username or not age:
    messagebox.showerror("Error", "Name and age are required!")
    exit()

# ---------------- FILTER QUESTIONS BY AGE ----------------
filtered_questions = [
    q for q in questions if q["age_min"] <= age <= q["age_max"]
]

if not filtered_questions:
    messagebox.showinfo(
        "No Questions Available",
        "No questions available for your age group."
    )
    exit()

# ---------------- QUIZ WINDOW ----------------
quiz = tk.Toplevel()
quiz.title("SoulSense Assessment")
quiz.geometry("600x400")

score = 0
current_q = 0

question_label = tk.Label(
    quiz, text="", wraplength=550, font=("Arial", 14)
)
question_label.pack(pady=20)

var = tk.IntVar()

options = [
    ("Strongly Disagree", 1),
    ("Disagree", 2),
    ("Neutral", 3),
    ("Agree", 4),
    ("Strongly Agree", 5)
]

for text, val in options:
    tk.Radiobutton(
        quiz, text=text, variable=var, value=val
    ).pack(anchor="w")

def next_question():
    global current_q, score

    if var.get() == 0:
        messagebox.showwarning("Warning", "Please select an option")
        return

    score += var.get()
    var.set(0)
    current_q += 1

    if current_q < len(filtered_questions):
        load_question()
    else:
        finish_quiz()

def load_question():
    question_label.config(
        text=filtered_questions[current_q]["text"]
    )

def finish_quiz():
    cursor.execute(
        "INSERT INTO scores (username, age, total_score) VALUES (?, ?, ?)",
        (username, age, score)
    )
    conn.commit()

    messagebox.showinfo(
        "Assessment Complete",
        f"Thank you {username}!\nYour Emotional Score: {score}"
    )
    quiz.destroy()
    conn.close()

tk.Button(
    quiz, text="Next", command=next_question,
    bg="#4CAF50", fg="white", font=("Arial", 12)
).pack(pady=20)

load_question()
quiz.mainloop()
