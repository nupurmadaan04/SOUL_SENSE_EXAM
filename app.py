import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import time
import json
from datetime import datetime

# BUTTON ANIMATION
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

# DATABASE
conn = sqlite3.connect("soulsense_db.db")
cursor = conn.cursor()

# Create main scores table
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

# Create work/study satisfaction table
cursor.execute("""
CREATE TABLE IF NOT EXISTS work_study_satisfaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    user_id INTEGER,
    motivation_score INTEGER,
    engagement_score INTEGER,
    progress_score INTEGER,
    environment_score INTEGER,
    balance_score INTEGER,
    overall_score REAL,
    weighted_average REAL,
    context_type TEXT,
    occupation TEXT,
    tenure_months INTEGER,
    interpretation TEXT,
    recommendations TEXT,
    insights TEXT,
    assessment_date TEXT,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES scores(id)
)
""")

# Create satisfaction benchmarks table
cursor.execute("""
CREATE TABLE IF NOT EXISTS satisfaction_benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    industry_sector TEXT,
    role_type TEXT,
    experience_level TEXT,
    benchmark_motivation REAL,
    benchmark_engagement REAL,
    benchmark_progress REAL,
    benchmark_environment REAL,
    benchmark_balance REAL,
    benchmark_overall REAL,
    sample_size INTEGER,
    std_dev REAL,
    last_updated TEXT
)
""")

conn.commit()

# SATISFACTION QUESTIONS
satisfaction_questions = [
    {
        "id": 101,
        "text": "How motivated are you to engage in your work/studies?",
        "category": "motivation",
        "description": "Your drive and enthusiasm for daily tasks",
        "scale_labels": {
            1: "Not at all motivated",
            2: "Slightly motivated", 
            3: "Moderately motivated",
            4: "Very motivated",
            5: "Extremely motivated"
        }
    },
    {
        "id": 102, 
        "text": "How engaged do you feel during work/study activities?",
        "category": "engagement",
        "description": "Your focus and immersion in activities",
        "scale_labels": {
            1: "Completely disengaged",
            2: "Often distracted",
            3: "Sometimes engaged",
            4: "Usually engaged",
            5: "Fully immersed"
        }
    },
    {
        "id": 103,
        "text": "How satisfied are you with your progress and achievements?",
        "category": "progress",
        "description": "Feeling of accomplishment and growth",
        "scale_labels": {
            1: "Very dissatisfied",
            2: "Dissatisfied",
            3: "Neutral",
            4: "Satisfied",
            5: "Very satisfied"
        }
    },
    {
        "id": 104,
        "text": "How satisfied are you with your work/study environment?",
        "category": "environment",
        "description": "Physical and social setting",
        "scale_labels": {
            1: "Very poor",
            2: "Poor",
            3: "Acceptable",
            4: "Good",
            5: "Excellent"
        }
    },
    {
        "id": 105,
        "text": "How satisfied are you with your work-study-life balance?",
        "category": "balance",
        "description": "Balance between responsibilities and personal life",
        "scale_labels": {
            1: "Very unbalanced",
            2: "Unbalanced",
            3: "Somewhat balanced",
            4: "Well balanced",
            5: "Perfectly balanced"
        }
    }
]

# EMOTIONAL INTELLIGENCE QUESTIONS (original)
questions = [
    {"text": "You can recognize your emotions as they happen.", "age_min": 12, "age_max": 25},
    {"text": "You find it easy to understand why you feel a certain way.", "age_min": 14, "age_max": 30},
    {"text": "You can control your emotions even in stressful situations.", "age_min": 15, "age_max": 35},
    {"text": "You reflect on your emotional reactions to situations.", "age_min": 13, "age_max": 28},
    {"text": "You are aware of how your emotions affect others.", "age_min": 16, "age_max": 40}
]

# SATISFACTION SCORE CALCULATOR
class SatisfactionCalculator:
    """Calculate work/study satisfaction scores"""
    
    @staticmethod
    def calculate_score(responses):
        """Calculate satisfaction score from responses (1-5 scale)"""
        weights = {
            101: 0.30,  # motivation
            102: 0.25,  # engagement
            103: 0.20,  # progress
            104: 0.15,  # environment
            105: 0.10   # balance
        }
        
        total_weighted = 0
        domain_scores = {}
        
        for qid, response in responses.items():
            if qid in weights:
                weighted_score = response * weights[qid]
                total_weighted += weighted_score
                
                # Find question category
                for q in satisfaction_questions:
                    if q["id"] == qid:
                        domain_scores[q["category"]] = {
                            "raw": response,
                            "weighted": weighted_score,
                            "interpretation": SatisfactionCalculator.interpret_domain_score(response)
                        }
                        break
        
        # Calculate overall scores
        weighted_average = total_weighted
        overall_score = weighted_average * 20  # Convert to 0-100 scale
        
        interpretation = SatisfactionCalculator.interpret_overall_score(overall_score)
        
        return {
            "overall_score": round(overall_score, 1),
            "weighted_average": round(weighted_average, 2),
            "domain_scores": domain_scores,
            "interpretation": interpretation,
            "recommendations": SatisfactionCalculator.generate_recommendations(domain_scores, overall_score)
        }
    
    @staticmethod
    def interpret_domain_score(score):
        """Interpret individual domain scores"""
        if score == 1:
            return "Very Low - Significant concern"
        elif score == 2:
            return "Low - Needs improvement"
        elif score == 3:
            return "Moderate - Room for growth"
        elif score == 4:
            return "High - Generally positive"
        elif score == 5:
            return "Very High - Excellent"
        return "Unknown"
    
    @staticmethod
    def interpret_overall_score(score):
        """Interpret overall satisfaction score (0-100)"""
        if score >= 80:
            return {
                "level": "High Satisfaction",
                "description": "Strong engagement and positive experience",
                "color": "#4CAF50"
            }
        elif score >= 60:
            return {
                "level": "Moderate Satisfaction", 
                "description": "Generally positive with room for enhancement",
                "color": "#FFC107"
            }
        elif score >= 40:
            return {
                "level": "Low Satisfaction",
                "description": "Significant areas of dissatisfaction",
                "color": "#FF9800"
            }
        else:
            return {
                "level": "Critical Dissatisfaction",
                "description": "Urgent attention needed",
                "color": "#F44336"
            }
    
    @staticmethod
    def generate_recommendations(domain_scores, overall_score):
        """Generate personalized recommendations"""
        recommendations = []
        
        # Overall recommendations
        if overall_score < 40:
            recommendations.append({
                "priority": "critical",
                "title": "Seek Immediate Support",
                "description": "Consider speaking with a supervisor, advisor, or counselor.",
                "actions": ["Schedule support meeting", "Explore work/study alternatives"]
            })
        elif overall_score < 60:
            recommendations.append({
                "priority": "high",
                "title": "Address Key Concerns",
                "description": "Focus on improving 1-2 areas with the lowest scores.",
                "actions": ["Identify top improvement areas", "Set specific goals"]
            })
        
        # Domain-specific recommendations
        for domain, data in domain_scores.items():
            if data["raw"] <= 2:
                if domain == "balance":
                    recommendations.append({
                        "priority": "high",
                        "title": "Improve Work-Life Balance",
                        "description": "Set clearer boundaries between responsibilities and personal time.",
                        "actions": ["Schedule downtime", "Learn to say no to non-essentials"]
                    })
                elif domain == "motivation":
                    recommendations.append({
                        "priority": "medium",
                        "title": "Boost Motivation",
                        "description": "Reconnect with your goals and find meaning in tasks.",
                        "actions": ["Break tasks into smaller steps", "Align work with personal values"]
                    })
        
        return recommendations[:3]  # Return top 3 recommendations

# ANALYTICS
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

# SPLASH SCREEN
def show_splash():
    splash = tk.Tk()
    splash.title("SoulSense")
    splash.geometry("500x300")
    splash.configure(bg="#1E1E2F")
    splash.resizable(False, False)

    tk.Label(splash, text="SoulSense",
             font=("Arial", 32, "bold"),
             fg="white", bg="#1E1E2F").pack(pady=40)

    tk.Label(splash, text="Emotional Awareness & Satisfaction Assessment",
             font=("Arial", 14),
             fg="#CCCCCC", bg="#1E1E2F").pack()
    
    tk.Label(splash, text="Now with Work/Study Satisfaction Measurement",
             font=("Arial", 10, "italic"),
             fg="#4CAF50", bg="#1E1E2F").pack(pady=5)
    
    tk.Label(splash, text="Loading...",
             font=("Arial", 15),
             fg="white", bg="#1E1E2F").pack(pady=30)

    splash.after(2500, lambda: (splash.destroy(), show_main_menu()))
    splash.mainloop()

# MAIN MENU
def show_main_menu():
    menu = tk.Tk()
    menu.title("SoulSense - Main Menu")
    menu.geometry("500x400")
    menu.configure(bg="#1E1E2F")
    menu.resizable(False, False)

    tk.Label(menu, text="SoulSense Assessment Suite",
             font=("Arial", 24, "bold"),
             fg="white", bg="#1E1E2F").pack(pady=30)

    tk.Label(menu, text="Choose an assessment type:",
             font=("Arial", 14),
             fg="#CCCCCC", bg="#1E1E2F").pack(pady=10)

    # Emotional Intelligence Assessment Button
    animated_button(menu, "Emotional Intelligence", 
                   lambda: (menu.destroy(), show_user_details("eq")),
                   bg="#2196F3", hover_bg="#1976D2", active_bg="#0D47A1",
                   width=25).pack(pady=10)

    # Work/Study Satisfaction Assessment Button
    animated_button(menu, "Work/Study Satisfaction",
                   lambda: (menu.destroy(), show_user_details("satisfaction")),
                   bg="#4CAF50", hover_bg="#43A047", active_bg="#388E3C",
                   width=25).pack(pady=10)

    # Combined Assessment Button
    animated_button(menu, "Complete Assessment (Both)",
                   lambda: (menu.destroy(), show_user_details("combined")),
                   bg="#9C27B0", hover_bg="#7B1FA2", active_bg="#4A148C",
                   width=25).pack(pady=10)

    # View History Button
    animated_button(menu, "View Assessment History",
                   lambda: (menu.destroy(), show_history()),
                   bg="#FF9800", hover_bg="#F57C00", active_bg="#E65100",
                   width=25).pack(pady=10)

    # Exit Button
    animated_button(menu, "Exit",
                   lambda: menu.destroy(),
                   bg="#757575", hover_bg="#616161", active_bg="#424242",
                   width=20).pack(pady=20)

    menu.mainloop()

# USER DETAILS (Updated for multiple assessment types)
def show_user_details(assessment_type="eq"):
    root = tk.Tk()
    root.title(f"SoulSense - {assessment_type.replace('_', ' ').title()} Assessment")
    root.geometry("500x550" if assessment_type in ["satisfaction", "combined"] else "450x450")
    root.resizable(False, False)

    username = tk.StringVar()
    age = tk.StringVar()
    occupation = tk.StringVar()
    context_type = tk.StringVar(value="work")
    tenure_months = tk.StringVar()

    tk.Label(root, text=f"{assessment_type.replace('_', ' ').title()} Assessment",
             font=("Arial", 20, "bold")).pack(pady=20)

    tk.Label(root, text="Enter your name:", font=("Arial", 12)).pack()
    tk.Entry(root, textvariable=username, font=("Arial", 14)).pack(pady=5)

    tk.Label(root, text="Enter your age:", font=("Arial", 12)).pack()
    tk.Entry(root, textvariable=age, font=("Arial", 14)).pack(pady=5)

    # Additional fields for satisfaction assessment
    if assessment_type in ["satisfaction", "combined"]:
        tk.Label(root, text="Current occupation/role:", font=("Arial", 12)).pack()
        tk.Entry(root, textvariable=occupation, font=("Arial", 14), 
                width=30).pack(pady=5)

        tk.Label(root, text="Context:", font=("Arial", 12)).pack()
        context_frame = tk.Frame(root)
        context_frame.pack()
        tk.Radiobutton(context_frame, text="Work", variable=context_type, 
                      value="work", font=("Arial", 12)).pack(side="left", padx=10)
        tk.Radiobutton(context_frame, text="Study", variable=context_type, 
                      value="study", font=("Arial", 12)).pack(side="left", padx=10)
        tk.Radiobutton(context_frame, text="Both", variable=context_type, 
                      value="both", font=("Arial", 12)).pack(side="left", padx=10)

        tk.Label(root, text="Months in current role (optional):", 
                font=("Arial", 12)).pack()
        tk.Entry(root, textvariable=tenure_months, font=("Arial", 14)).pack(pady=5)

    def start():
        if not username.get().strip():
            messagebox.showwarning("Name Required", "Please enter your name.")
            return
        if not age.get().isdigit():
            messagebox.showwarning("Invalid Age", "Please enter a valid age.")
            return
        
        user_name = username.get()
        user_age = int(age.get())
        
        user_data = {
            "name": user_name,
            "age": user_age,
            "assessment_type": assessment_type
        }
        
        if assessment_type in ["satisfaction", "combined"]:
            user_data["occupation"] = occupation.get()
            user_data["context_type"] = context_type.get()
            if tenure_months.get().isdigit():
                user_data["tenure_months"] = int(tenure_months.get())
        
        root.destroy()
        
        if assessment_type == "eq":
            start_eq_quiz(user_name, user_age)
        elif assessment_type == "satisfaction":
            start_satisfaction_assessment(user_data)
        elif assessment_type == "combined":
            start_combined_assessment(user_data)

    animated_button(root, "Start Assessment", start, width=20).pack(pady=25)
    root.mainloop()

# EMOTIONAL INTELLIGENCE QUIZ (original, updated)
def start_eq_quiz(username, age):
    # Filter questions by age
    qs = [q for q in questions if q["age_min"] <= age <= q["age_max"]]
    
    if not qs:
        messagebox.showinfo("No Questions", "No questions available for your age.")
        return
    
    quiz = tk.Tk()
    quiz.title("SoulSense - Emotional Intelligence Assessment")
    quiz.geometry("750x650")
    quiz.resizable(False, False)

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
            f"Emotional Intelligence Assessment Completed!\n\n"
            f"Score: {score}\n"
            f"Questions Attempted: {analytics['attempted']}\n"
            f"Time Taken: {elapsed} seconds\n\n"
            f"Results saved to database."
        )
        quiz.destroy()
        show_main_menu()

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

# SATISFACTION ASSESSMENT
def start_satisfaction_assessment(user_data):
    quiz = tk.Tk()
    quiz.title("SoulSense - Work/Study Satisfaction Assessment")
    quiz.geometry("800x700")
    quiz.resizable(False, False)

    # Display user context
    context_frame = tk.Frame(quiz, bg="#E3F2FD", relief="raised", borderwidth=2)
    context_frame.pack(fill="x", padx=10, pady=10)
    
    context_text = f"Assessing: {user_data['context_type'].title()} Satisfaction"
    if user_data.get('occupation'):
        context_text += f" | Role: {user_data['occupation']}"
    
    tk.Label(context_frame, text=context_text,
             font=("Arial", 12, "bold"),
             bg="#E3F2FD", fg="#1565C0").pack(pady=5)

    responses = {}
    current = 0
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

    # Question frame
    question_frame = tk.Frame(quiz)
    question_frame.pack(pady=20, padx=20, fill="both", expand=True)

    question_label = tk.Label(question_frame, wraplength=750,
                              font=("Arial", 16, "bold"), justify="left")
    question_label.pack(pady=10)

    description_label = tk.Label(question_frame, wraplength=750,
                                 font=("Arial", 12), fg="#666", justify="left")
    description_label.pack(pady=5)

    # Scale labels
    scale_frame = tk.Frame(quiz)
    scale_frame.pack(pady=10)
    
    scale_labels = ["Very Low", "Low", "Moderate", "High", "Very High"]
    for i, label in enumerate(scale_labels, start=1):
        tk.Label(scale_frame, text=f"{i}. {label}",
                font=("Arial", 10), fg="#555").pack(side="left", padx=15)

    # Radio buttons
    radio_frame = tk.Frame(quiz)
    radio_frame.pack(pady=20)
    
    for i in range(1, 6):
        tk.Radiobutton(radio_frame, text=str(i),
                      variable=var, value=i,
                      font=("Arial", 14),
                      width=3).pack(side="left", padx=10)

    def load_question():
        nonlocal current
        if current < len(satisfaction_questions):
            q = satisfaction_questions[current]
            question_label.config(text=f"Q{current + 1}. {q['text']}")
            description_label.config(text=q['description'])
            var.set(0)
        else:
            finish_assessment()

    def finish_assessment():
        nonlocal current
        if var.get() == 0 and current < len(satisfaction_questions):
            messagebox.showwarning("Selection Required", 
                                 "Please select an option for the current question.")
            return
        
        # Save current response
        if var.get() > 0:
            responses[satisfaction_questions[current]["id"]] = var.get()
        
        elapsed = int(time.time() - start_time)
        
        # Calculate satisfaction score
        score_result = SatisfactionCalculator.calculate_score(responses)
        
        # Save to database
        try:
            # Get user ID from scores table
            cursor.execute("SELECT id FROM scores WHERE username = ? ORDER BY id DESC LIMIT 1", 
                         (user_data["name"],))
            result = cursor.fetchone()
            user_id = result[0] if result else None
            
            cursor.execute("""
                INSERT INTO work_study_satisfaction VALUES (
                    NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
            """, (
                user_data["name"],
                user_id,
                responses.get(101, 0),
                responses.get(102, 0),
                responses.get(103, 0),
                responses.get(104, 0),
                responses.get(105, 0),
                score_result["overall_score"],
                score_result["weighted_average"],
                user_data.get("context_type", "work"),
                user_data.get("occupation", ""),
                user_data.get("tenure_months"),
                score_result["interpretation"]["level"],
                json.dumps(score_result["recommendations"]),
                "",
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            
            # Show results
            show_satisfaction_results(score_result, user_data, elapsed)
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Error saving results: {str(e)}")
        
        quiz.destroy()

    def next_question():
        nonlocal current
        if var.get() == 0:
            messagebox.showwarning("Selection Required",
                                   "Please select an option.")
            return
        
        # Save response
        responses[satisfaction_questions[current]["id"]] = var.get()
        
        current += 1
        if current < len(satisfaction_questions):
            load_question()
        else:
            finish_assessment()

    # Navigation buttons
    button_frame = tk.Frame(quiz)
    button_frame.pack(pady=20)
    
    if current < len(satisfaction_questions) - 1:
        animated_button(button_frame, "Next", next_question).pack(side="left", padx=10)
    else:
        animated_button(button_frame, "Finish", finish_assessment, 
                       bg="#4CAF50", hover_bg="#43A047").pack(side="left", padx=10)
    
    animated_button(button_frame, "Cancel",
                   lambda: (quiz.destroy(), show_main_menu()),
                   bg="#757575", hover_bg="#616161").pack(side="left", padx=10)

    load_question()
    quiz.mainloop()

def show_satisfaction_results(score_result, user_data, time_taken):
    """Display satisfaction assessment results"""
    results = tk.Tk()
    results.title("SoulSense - Satisfaction Results")
    results.geometry("800x700")
    results.configure(bg="#F5F5F5")
    
    # Header
    header = tk.Frame(results, bg="#1E1E2F", height=100)
    header.pack(fill="x")
    header.pack_propagate(False)
    
    tk.Label(header, text="Work/Study Satisfaction Results",
             font=("Arial", 24, "bold"),
             fg="white", bg="#1E1E2F").pack(pady=30)
    
    # Main content
    content = tk.Frame(results, bg="#F5F5F5")
    content.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Overall score with color-coded visualization
    score_frame = tk.Frame(content, bg="white", relief="raised", borderwidth=2)
    score_frame.pack(fill="x", pady=10)
    
    interpretation = score_result["interpretation"]
    
    score_canvas = tk.Canvas(score_frame, width=300, height=150, bg="white", 
                            highlightthickness=0)
    score_canvas.pack(pady=20)
    
    # Draw gauge
    x, y, radius = 150, 80, 60
    score = score_result["overall_score"]
    
    # Background arc
    score_canvas.create_arc(x-radius, y-radius, x+radius, y+radius,
                          start=180, extent=180,
                          outline="#E0E0E0", width=15, style="arc")
    
    # Score arc
    score_angle = (score / 100) * 180
    score_canvas.create_arc(x-radius, y-radius, x+radius, y+radius,
                          start=180, extent=score_angle,
                          outline=interpretation["color"], width=15, style="arc")
    
    # Score text
    score_canvas.create_text(x, y-15, text=f"{score:.1f}",
                           font=("Arial", 28, "bold"), fill=interpretation["color"])
    score_canvas.create_text(x, y+15, text="Satisfaction Score",
                           font=("Arial", 12), fill="#666")
    
    # Interpretation
    tk.Label(score_frame, text=interpretation["level"],
             font=("Arial", 16, "bold"), fg=interpretation["color"],
             bg="white").pack()
    tk.Label(score_frame, text=interpretation["description"],
             font=("Arial", 12), fg="#666", bg="white",
             wraplength=600).pack(pady=5)
    
    # Domain scores
    domains_frame = tk.LabelFrame(content, text="Domain Scores", 
                                 font=("Arial", 14, "bold"),
                                 bg="#F5F5F5", fg="#333")
    domains_frame.pack(fill="x", pady=20)
    
    for domain, data in score_result["domain_scores"].items():
        domain_frame = tk.Frame(domains_frame, bg="#F5F5F5")
        domain_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(domain_frame, text=domain.title(),
                font=("Arial", 12, "bold"), bg="#F5F5F5",
                width=15, anchor="w").pack(side="left")
        
        # Score bar
        bar_canvas = tk.Canvas(domain_frame, width=200, height=20, bg="#F5F5F5",
                              highlightthickness=0)
        bar_canvas.pack(side="left", padx=10)
        
        bar_width = (data["raw"] / 5) * 200
        bar_color = "#4CAF50" if data["raw"] >= 4 else "#FFC107" if data["raw"] >= 3 else "#F44336"
        bar_canvas.create_rectangle(0, 5, bar_width, 15, fill=bar_color, outline="")
        
        tk.Label(domain_frame, text=f"{data['raw']}/5 - {data['interpretation']}",
                font=("Arial", 10), bg="#F5F5F5").pack(side="left", padx=10)
    
    # Recommendations
    if score_result["recommendations"]:
        rec_frame = tk.LabelFrame(content, text="Recommendations",
                                 font=("Arial", 14, "bold"),
                                 bg="#F5F5F5", fg="#333")
        rec_frame.pack(fill="x", pady=10)
        
        for i, rec in enumerate(score_result["recommendations"], 1):
            rec_item = tk.Frame(rec_frame, bg="#F5F5F5")
            rec_item.pack(fill="x", padx=10, pady=5, anchor="w")
            
            priority_color = "#F44336" if rec["priority"] == "critical" else "#FF9800" if rec["priority"] == "high" else "#4CAF50"
            tk.Label(rec_item, text=f"●", font=("Arial", 14),
                    fg=priority_color, bg="#F5F5F5").pack(side="left")
            
            tk.Label(rec_item, text=rec["title"], font=("Arial", 12, "bold"),
                    bg="#F5F5F5").pack(side="left", padx=5)
            tk.Label(rec_item, text=f"- {rec['description']}",
                    font=("Arial", 11), bg="#F5F5F5", fg="#666",
                    wraplength=600).pack(anchor="w", padx=30)
    
    # Actions
    action_frame = tk.Frame(content, bg="#F5F5F5")
    action_frame.pack(pady=20)
    
    animated_button(action_frame, "Back to Menu",
                   lambda: (results.destroy(), show_main_menu()),
                   width=20).pack(side="left", padx=10)
    
    animated_button(action_frame, "View History",
                   lambda: (results.destroy(), show_history()),
                   bg="#2196F3", hover_bg="#1976D2", width=20).pack(side="left", padx=10)
    
    animated_button(action_frame, "Take Another Assessment",
                   lambda: (results.destroy(), show_user_details("satisfaction")),
                   bg="#4CAF50", hover_bg="#43A047", width=25).pack(side="left", padx=10)
    
    results.mainloop()

# COMBINED ASSESSMENT
def start_combined_assessment(user_data):
    # Start with EQ assessment, then satisfaction
    def eq_completed():
        start_satisfaction_assessment(user_data)
    
    # For simplicity, we'll just start satisfaction for now
    # In a full implementation, you would chain the assessments
    start_satisfaction_assessment(user_data)

# VIEW HISTORY
def show_history():
    history = tk.Tk()
    history.title("SoulSense - Assessment History")
    history.geometry("900x600")
    
    # Create notebook for tabs
    notebook = ttk.Notebook(history)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    
    # EQ Scores Tab
    eq_frame = ttk.Frame(notebook)
    notebook.add(eq_frame, text="Emotional Intelligence")
    
    # Create treeview for EQ scores
    eq_tree = ttk.Treeview(eq_frame, columns=("ID", "Name", "Age", "Score", "Time", "Date"), 
                          show="headings", height=15)
    eq_tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Configure columns
    eq_tree.heading("ID", text="ID")
    eq_tree.heading("Name", text="Name")
    eq_tree.heading("Age", text="Age")
    eq_tree.heading("Score", text="Score")
    eq_tree.heading("Time", text="Time (s)")
    eq_tree.heading("Date", text="Date")
    
    for col in ("ID", "Name", "Age", "Score", "Time", "Date"):
        eq_tree.column(col, width=100)
    
    # Fetch EQ scores
    cursor.execute("SELECT id, username, age, total_score, time_taken_seconds FROM scores")
    for row in cursor.fetchall():
        eq_tree.insert("", "end", values=row)
    
    # Satisfaction Scores Tab
    sat_frame = ttk.Frame(notebook)
    notebook.add(sat_frame, text="Work/Study Satisfaction")
    
    # Create treeview for satisfaction scores
    sat_tree = ttk.Treeview(sat_frame, columns=("ID", "Name", "Overall", "Motivation", "Engagement", 
                                               "Progress", "Environment", "Balance", "Date"), 
                           show="headings", height=15)
    sat_tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Configure columns
    columns = [("ID", 50), ("Name", 100), ("Overall", 80), ("Motivation", 80), 
               ("Engagement", 80), ("Progress", 80), ("Environment", 80), 
               ("Balance", 80), ("Date", 120)]
    
    for col, width in columns:
        sat_tree.heading(col, text=col)
        sat_tree.column(col, width=width)
    
    # Fetch satisfaction scores
    cursor.execute("""
        SELECT id, username, overall_score, motivation_score, engagement_score, 
               progress_score, environment_score, balance_score, assessment_date 
        FROM work_study_satisfaction
    """)
    for row in cursor.fetchall():
        sat_tree.insert("", "end", values=row)
    
    # Actions frame
    actions_frame = tk.Frame(history)
    actions_frame.pack(pady=10)
    
    animated_button(actions_frame, "Back to Menu",
                   lambda: (history.destroy(), show_main_menu()),
                   width=15).pack(side="left", padx=10)
    
    animated_button(actions_frame, "Export Data",
                   lambda: export_data(),
                   bg="#2196F3", hover_bg="#1976D2", width=15).pack(side="left", padx=10)
    
    animated_button(actions_frame, "Clear History",
                   lambda: clear_history(history),
                   bg="#F44336", hover_bg="#D32F2F", width=15).pack(side="left", padx=10)
    
    history.mainloop()

def export_data():
    """Export assessment data to CSV"""
    import csv
    from tkinter import filedialog
    
    filename = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    if filename:
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Write EQ scores
                writer.writerow(["=== Emotional Intelligence Scores ==="])
                writer.writerow(["ID", "Name", "Age", "Score", "Avg Response", 
                               "Max", "Min", "Variance", "Attempted", "Completion", 
                               "Avg Time", "Total Time"])
                
                cursor.execute("SELECT * FROM scores")
                for row in cursor.fetchall():
                    writer.writerow(row)
                
                # Write satisfaction scores
                writer.writerow([])
                writer.writerow(["=== Work/Study Satisfaction Scores ==="])
                writer.writerow(["ID", "Name", "User ID", "Motivation", "Engagement", 
                               "Progress", "Environment", "Balance", "Overall Score",
                               "Weighted Avg", "Context", "Occupation", "Tenure Months",
                               "Interpretation", "Assessment Date"])
                
                cursor.execute("SELECT * FROM work_study_satisfaction")
                for row in cursor.fetchall():
                    writer.writerow(row)
                
                messagebox.showinfo("Export Successful", 
                                  f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {str(e)}")

def clear_history(parent):
    """Clear assessment history"""
    if messagebox.askyesno("Confirm Clear", 
                          "Are you sure you want to clear all assessment history?\nThis cannot be undone."):
        try:
            cursor.execute("DELETE FROM scores")
            cursor.execute("DELETE FROM work_study_satisfaction")
            conn.commit()
            messagebox.showinfo("Cleared", "Assessment history cleared.")
            parent.destroy()
            show_main_menu()
        except Exception as e:
            messagebox.showerror("Clear Failed", f"Error: {str(e)}")

# START APPLICATION
if __name__ == "__main__":
    show_splash()