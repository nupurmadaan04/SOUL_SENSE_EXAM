import sqlite3
import tkinter as tk
from tkinter import messagebox

#DATABASE SETUP
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
root.geometry("450x330")
root.resizable(False, False)

username = tk.StringVar()
age = tk.StringVar()

tk.Label(
    root,
    text="SoulSense Assessment",
    font=("Arial", 20, "bold")
).pack(pady=20)

tk.Label(root, text="Enter your name:", font=("Arial", 15)).pack()
tk.Entry(root, textvariable=username, font=("Arial", 15), width=25).pack(pady=8)

tk.Label(root, text="Enter your age:", font=("Arial", 15)).pack()
tk.Entry(root, textvariable=age, font=("Arial", 15), width=25).pack(pady=8)

def submit_details():
    if not username.get() or not age.get().isdigit():
        messagebox.showerror("Error", "Please enter valid name and age")
        return

    root.destroy()
    start_quiz(username.get(), int(age.get()))

tk.Button(
    root,
    text="Start Assessment",
    command=submit_details,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 14, "bold"),
    width=20
).pack(pady=25)

#QUIZ WINDOW
def start_quiz(username, age):
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
                "INSERT INTO scores (username, age, total_score) VALUES (?, ?, ?)",
                (username, age, score)
            )
            conn.commit()

            messagebox.showinfo(
                "Completed",
                f"Thank you {username}!\nYour Emotional Score: {score}"
            )
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
