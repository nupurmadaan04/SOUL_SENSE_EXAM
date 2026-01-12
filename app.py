import sqlite3
import tkinter as tk
from tkinter import messagebox
import time

#BUTTON ANIMATION
def animated_button(parent, text, command,
                    bg="#4CAF50", hover_bg="#43A047", active_bg="#388E3C",
                    fg="white", font=("Arial", 14, "bold"), width=15):

    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, font=font, width=width,
                    relief="flat", activebackground=active_bg)

    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg, cursor="hand2"))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    btn.bind("<ButtonPress-1>", lambda e: btn.config(bg=active_bg))
    btn.bind("<ButtonRelease-1>", lambda e: btn.config(bg=hover_bg))
    return btn

#DATABASE
conn = sqlite3.connect("soulsense_db.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    age INTEGER,
    total_score INTEGER,
    avg_response REAL,
    max_response INTEGER,
    min_response INTEGER,
    score_variance REAL,
    questions_attempted INTEGER,
    completion_ratio REAL,
    avg_time_per_question REAL,
    time_taken_seconds INTEGER
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

#ANALYTICS
def compute_analytics(responses, time_taken, total):
    n = len(responses)
    if n == 0:
        return dict(avg=0, max=0, min=0, variance=0,
                    attempted=0, completion=0, avg_time=0)

    avg = sum(responses) / n
    variance = sum((x - avg) ** 2 for x in responses) / n

    return {
        "avg": round(avg, 2),
        "max": max(responses),
        "min": min(responses),
        "variance": round(variance, 2),
        "attempted": n,
        "completion": round(n / total, 2),
        "avg_time": round(time_taken / n, 2)
    }

#SPLASH SCREEN
def show_splash():
    splash = tk.Tk()
    splash.title("SoulSense")
    splash.geometry("500x300")
    splash.configure(bg="#1E1E2F")
    splash.resizable(False, False)

    tk.Label(splash, text="SoulSense",
             font=("Arial", 32, "bold"),
             fg="white", bg="#1E1E2F").pack(pady=40)

    tk.Label(splash, text="Emotional Awareness Assessment",
             font=("Arial", 14),
             fg="#CCCCCC", bg="#1E1E2F").pack()
    tk.Label(
        splash,
        text="Loading...",
        font=("Arial", 15),
        fg="white",
        bg="#1E1E2F"
    ).pack(pady=30)

    splash.after(2500, lambda: (splash.destroy(), show_user_details()))
    splash.mainloop()

#USER DETAILS
# USER DETAILS (Updated for Feature 1)
def show_user_details():
    root = tk.Tk()
    root.title("SoulSense - User Details")
    root.geometry("450x450") # Increased height to fit new field
    root.resizable(False, False)

    username = tk.StringVar()
    age = tk.StringVar()
    stressors = tk.StringVar() # New variable for Feature 1

    tk.Label(root, text="SoulSense Assessment",
             font=("Arial", 20, "bold")).pack(pady=20)

    tk.Label(root, text="Enter your name:", font=("Arial", 12)).pack()
    tk.Entry(root, textvariable=username, font=("Arial", 14)).pack(pady=5)

    tk.Label(root, text="Enter your age:", font=("Arial", 12)).pack()
    tk.Entry(root, textvariable=age, font=("Arial", 14)).pack(pady=5)

    # --- FEATURE 1: STRESSOR INPUT ---
    tk.Label(root, text="Mention recent major stressors (Optional):", 
             font=("Arial", 12), fg="#555").pack(pady=(10, 0))
    tk.Label(root, text="(e.g., exams, deadlines, transitions)", 
             font=("Arial", 9, "italic"), fg="#777").pack()
    tk.Entry(root, textvariable=stressors, font=("Arial", 14), width=30).pack(pady=5)

    def start():
        if not username.get().strip():
            messagebox.showwarning("Name Required", "Please enter your name.")
            return
        if not age.get().isdigit():
            messagebox.showwarning("Invalid Age", "Please enter a valid age.")
            return
        
        user_name = username.get()
        user_age = int(age.get())
        user_stressors = stressors.get().strip()
        
        root.destroy()
        # Pass stressors to the quiz
        start_quiz(user_name, user_age, user_stressors)

    animated_button(root, "Start Assessment", start, width=20).pack(pady=25)
    root.mainloop()

#QUIZ
# QUIZ (Fixed: Now accepts user_stressors)
def start_quiz(username, age, user_stressors):
    # Filter questions by age
    qs = [q for q in questions if q["age_min"] <= age <= q["age_max"]]
    
    if not qs:
        messagebox.showinfo("No Questions", "No questions available for your age.")
        return
    
    # FEATURE 1 LOGIC: Check if user provided stressors
    is_overwhelmed = len(user_stressors) > 0
    
    quiz = tk.Tk()
    quiz.title("SoulSense Quiz")
    quiz.geometry("750x680") # Increased height slightly for the banner
    quiz.resizable(False, False)

    # Display supportive banner if stressors exist
    if is_overwhelmed:
        support_label = tk.Label(quiz, 
                                 text=f"Supporting you through: {user_stressors} 🌿\nWe've adjusted the pace for you.",
                                 font=("Arial", 12, "italic"), 
                                 bg="#E3F2FD", 
                                 fg="#1565C0", 
                                 pady=10) # Fixed here
        support_label.pack(fill="x", pady=(0, 10))

    responses, score, current = [], 0, 0
    var = tk.IntVar()
    start_time = time.time()

    timer_label = tk.Label(quiz, font=("Arial", 14, "bold"), fg="#1E88E5")
    timer_label.pack(pady=5)

    def update_timer():
        elapsed = int(time.time() - start_time)
        m, s = divmod(elapsed, 60)
        timer_label.config(text=f"Time: {m:02d}:{s:02d}")
        quiz.after(1000, update_timer)

    update_timer()

    question_label = tk.Label(quiz, wraplength=700,
                              font=("Arial", 16, "bold"))
    question_label.pack(pady=20)

    options = [
        "1. Strongly Disagree",
        "2. Disagree",
        "3. Neutral",
        "4. Agree",
        "5. Strongly Agree"
    ]

    for i, text in enumerate(options, start=1):
        tk.Radiobutton(quiz, text=text,
                       variable=var, value=i,
                       font=("Arial", 14)).pack(anchor="w", padx=60)

    def load_question():
        question_label.config(
            text=f"Q{current + 1}. {qs[current]['text']}"
        )

    def finish(title):
        elapsed = int(time.time() - start_time)
        analytics = compute_analytics(responses, elapsed, len(qs))

        cursor.execute("""
            INSERT INTO scores VALUES (
                NULL,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            username, age, score,
            analytics["avg"], analytics["max"], analytics["min"],
            analytics["variance"], analytics["attempted"],
            analytics["completion"], analytics["avg_time"], elapsed
        ))
        conn.commit()

        messagebox.showinfo(
            title,
            f"Score: {score}\n"
            f"Questions Attempted: {analytics['attempted']}\n"
            f"Time Taken: {elapsed} seconds"
        )
        quiz.destroy()
        # Note: Do not close conn here if you want to run multiple assessments
        # conn.close() 

    def next_question():
        nonlocal current, score
        if var.get() == 0:
            messagebox.showwarning("Selection Required",
                                   "Please select an option.")
            return
        responses.append(var.get())
        score += var.get()
        var.set(0)
        current += 1
        if current < len(qs):
            load_question()
        else:
            finish("Assessment Completed")

    animated_button(quiz, "Next", next_question).pack(pady=15)
    animated_button(
        quiz, "Stop Test",
        lambda: finish("Assessment Stopped"),
        bg="#E53935", hover_bg="#D32F2F", active_bg="#B71C1C"
    ).pack()

    load_question()
    quiz.mainloop()

#START
show_splash()
