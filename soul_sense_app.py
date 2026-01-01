import sqlite3
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime
from textblob import TextBlob
import pandas as pd

# Step 1: Create/connect to SQLite database
conn = sqlite3.connect("soulsense_db.db")
cursor = conn.cursor()

# Step 2: Create table to store final score
cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    total_score INTEGER
)
""")

# Table for Mood Journal with AI analysis
cursor.execute("""
CREATE TABLE IF NOT EXISTS mood_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    date TEXT,
    entry TEXT,
    sentiment_score REAL,
    sentiment_label TEXT
)
""")

conn.commit()

# Step 3: Define 20 Soul Sense questions
questions = [
    "You can recognize your emotions as they happen.",
    "You manage to stay calm even under pressure.",
    "You are aware of how your emotions affect others.",
    "You can motivate yourself to pursue long-term goals.",
    "You stay optimistic even after facing setbacks.",
    "You are able to express your feelings clearly.",
    "You handle conflict effectively and calmly.",
    "You find it easy to empathize with others' emotions.",
    "You adapt well to changing situations.",
    "You keep your promises and commitments.",
    "You actively listen to others when they speak.",
    "You accept constructive criticism without being defensive.",
    "You remain positive in emotionally difficult situations.",
    "You recognize stress in others and offer support.",
    "You maintain strong relationships over time.",
    "You can identify your emotional triggers.",
    "You take responsibility for your actions.",
    "You resolve misunderstandings diplomatically.",
    "You stay focused and productive when under pressure.",
    "You show appreciation and gratitude regularly."
]

# Sentiment analysis dictionaries
positive_words = {
    "happy": 1.0, "calm": 0.8, "relaxed": 0.7, "confident": 0.9,
    "hopeful": 1.0, "grateful": 0.9, "excited": 1.0, "content": 0.6
}

negative_words = {
    "sad": -1.0, "anxious": -1.0, "stressed": -1.2, "angry": -1.1,
    "tired": -0.6, "depressed": -1.5, "worried": -0.9, "overwhelmed": -1.2
}

def analyze_sentiment(text):
    text_lower = text.lower()

    # Base NLP polarity
    blob_score = TextBlob(text).sentiment.polarity

    # Keyword-based emotional score
    keyword_score = 0
    for word, weight in positive_words.items():
        if word in text_lower:
            keyword_score += weight

    for word, weight in negative_words.items():
        if word in text_lower:
            keyword_score += weight

    # Combine scores (weighted)
    final_score = (0.6 * blob_score) + (0.4 * keyword_score)

    # Clamp score to [-1, 1]
    final_score = max(min(final_score, 1), -1)

    # Labeling
    if final_score >= 0.4:
        label = "Strongly Positive"
    elif final_score >= 0.15:
        label = "Mildly Positive"
    elif final_score <= -0.4:
        label = "Strongly Negative"
    elif final_score <= -0.15:
        label = "Mildly Negative"
    else:
        label = "Neutral"

    return final_score, label

def emotional_trend(username):
    df = view_emotional_patterns(username)

    if df.empty or len(df) < 3:
        return "Not enough data to determine emotional trend."

    avg_score = df["sentiment_score"].mean()

    if avg_score > 0.2:
        return "Overall emotional trend is Positive."
    elif avg_score < -0.2:
        return "Overall emotional trend indicates emotional stress."
    else:
        return "Overall emotional trend is emotionally balanced."

def view_emotional_patterns(username):
    df = pd.read_sql_query("""
        SELECT date, sentiment_label, sentiment_score
        FROM mood_journal
        WHERE username = ?
        ORDER BY date
    """, conn, params=(username,))
    return df

def emotional_pattern_summary(username):
    df = view_emotional_patterns(username)

    if df.empty:
        return "No emotional history available."

    counts = df["sentiment_label"].value_counts()
    dominant = counts.idxmax()

    return f"Dominant emotional pattern over time: {dominant}"

# Step 4: GUI Application
class SoulSenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test & Journal")
        self.username = ""
        self.current_question = 0
        self.responses = []

        self.create_username_screen()

    def create_username_screen(self):
        self.clear_screen()

        tk.Label(self.root, text="Enter Your Name:", font=("Arial", 14)).pack(pady=20)
        self.name_entry = tk.Entry(self.root, font=("Arial", 14))
        self.name_entry.pack(pady=10)

        tk.Button(self.root, text="Start EQ Test", command=self.start_test, font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="Go to Journal", command=self.show_journal_screen, font=("Arial", 12)).pack(pady=10)

    def show_journal_screen(self):
        self.username = self.name_entry.get().strip()
        if self.username == "":
            messagebox.showwarning("Input Error", "Please enter your name to access the journal.")
            return

        self.clear_screen()

        tk.Label(self.root, text=f"Welcome to Journal, {self.username}!", font=("Arial", 16)).pack(pady=10)

        tk.Label(self.root, text="Write your daily emotional reflection:", font=("Arial", 12)).pack(pady=5)
        self.journal_text = scrolledtext.ScrolledText(self.root, width=50, height=10, font=("Arial", 12))
        self.journal_text.pack(pady=10)

        tk.Button(self.root, text="Save Entry & Analyze", command=self.save_journal_entry, font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="View Emotional Patterns", command=self.view_patterns, font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="Back to Main", command=self.create_username_screen, font=("Arial", 12)).pack(pady=10)

    def save_journal_entry(self):
        entry_text = self.journal_text.get("1.0", tk.END).strip()
        if entry_text == "":
            messagebox.showwarning("Input Error", "Please write something in your journal.")
            return

        score, label = analyze_sentiment(entry_text)
        date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
        INSERT INTO mood_journal (username, date, entry, sentiment_score, sentiment_label)
        VALUES (?, ?, ?, ?, ?)
        """, (self.username, date, entry_text, score, label))

        conn.commit()

        messagebox.showinfo("Entry Saved", f"AI Analysis:\nSentiment: {label}\nScore: {round(score, 2)}")

        self.journal_text.delete("1.0", tk.END)

    def view_patterns(self):
        df = view_emotional_patterns(self.username)
        if df.empty:
            messagebox.showinfo("Patterns", "No journal entries yet.")
            return

        pattern_window = tk.Toplevel(self.root)
        pattern_window.title("Emotional Patterns")
        pattern_window.geometry("600x400")

        text_area = scrolledtext.ScrolledText(pattern_window, width=70, height=20, font=("Arial", 10))
        text_area.pack(pady=10)

        summary = emotional_pattern_summary(self.username)
        trend = emotional_trend(self.username)

        text_area.insert(tk.END, f"{summary}\n\n{trend}\n\nRecent Entries:\n")
        for _, row in df.tail(10).iterrows():
            text_area.insert(tk.END, f"{row['date']}: {row['sentiment_label']} ({round(row['sentiment_score'], 2)})\n")

        text_area.config(state=tk.DISABLED)

    def start_test(self):
        self.username = self.name_entry.get().strip()
        if self.username == "":
            messagebox.showwarning("Input Error", "Please enter your name to start the test.")
        else:
            self.show_question()

    def show_question(self):
        self.clear_screen()

        if self.current_question < len(questions):
            q_text = questions[self.current_question]
            tk.Label(self.root, text=f"Q{self.current_question + 1}: {q_text}", wraplength=400, font=("Arial", 14)).pack(pady=20)

            self.answer_var = tk.IntVar()

            for val, text in enumerate(["Never (1)", "Sometimes (2)", "Often (3)", "Always (4)"], start=1):
                tk.Radiobutton(self.root, text=text, variable=self.answer_var, value=val, font=("Arial", 12)).pack(anchor="w", padx=50)

            tk.Button(self.root, text="Next", command=self.save_answer, font=("Arial", 12)).pack(pady=20)

        else:
            self.finish_test()

    def save_answer(self):
        ans = self.answer_var.get()
        if ans == 0:
            messagebox.showwarning("Input Error", "Please select an answer before proceeding.")
        else:
            q_text = questions[self.current_question]
            self.responses.append((self.username, self.current_question + 1, q_text, ans))
            self.current_question += 1
            self.show_question()

    def finish_test(self):
        total_score = sum(r[3] for r in self.responses)

        # Store only final score in the database
        cursor.execute("INSERT INTO scores (username, total_score) VALUES (?, ?)", (self.username, total_score))
        conn.commit()

        interpretation = ""

        if total_score >= 65:
            interpretation = "Excellent Emotional Intelligence!"
        elif total_score >= 50:
            interpretation = "Good Emotional Intelligence."
        elif total_score >= 35:
            interpretation = "Average Emotional Intelligence."
        else:
            interpretation = "You may want to work on your Emotional Intelligence."

        self.clear_screen()

        tk.Label(self.root, text=f"Thank you, {self.username}!", font=("Arial", 16)).pack(pady=10)
        tk.Label(self.root, text=f"Your total EQ score is: {total_score} / 80", font=("Arial", 14)).pack(pady=10)
        tk.Label(self.root, text=interpretation, font=("Arial", 14), fg="blue").pack(pady=10)

        tk.Button(self.root, text="Go to Journal", command=self.show_journal_screen, font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="Exit", command=self.exit_test, font=("Arial", 12)).pack(pady=20)

    def exit_test(self):
        # Ensure database connection is closed first
        conn.close()
        self.root.quit()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

# Step 5: Main Loop
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x400")
    app = SoulSenseApp(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_test)
    root.mainloop()
