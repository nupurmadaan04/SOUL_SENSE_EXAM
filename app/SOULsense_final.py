import sqlite3
import tkinter as tk
from tkinter import messagebox
import random

class SoulSenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soul Sense EQ Test")
        self.root.geometry("600x400")
        self.username = ""
        self.age = None
        self.current_question = 0
        self.responses = []
        self.num_questions = 15

        # 
        self.user_history = {}  # stores username: list of question indices already used
        
        self.setup_database()
        self.load_questions()
        
        try:
            from journal_feature import JournalFeature
            self.journal = JournalFeature(root)
            self.journal_available = True
        except ImportError:
            self.journal = None
            self.journal_available = False
        
        self.create_username_screen()

    def setup_database(self):
        self.conn = sqlite3.connect("soulsense_db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            age INTEGER,
            total_score INTEGER,
            normalized_score INTEGER,
            num_questions INTEGER
        )
        """)
        self.conn.commit()

    def load_questions(self):
        try:
            with open('question_bank.txt', 'r') as f:
                self.all_questions = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            messagebox.showerror("Error", "question_bank.txt file not found!")
            self.root.quit()
    def select_questions(self):
     if self.username not in self.user_history:
        self.user_history[self.username] = []
     if not hasattr(self, 'all_questions') or not self.all_questions:
        messagebox.showerror("Error", "No questions loaded!")
        self.questions = []
        return
     all_indices = list(range(len(self.all_questions)))

     recent_indices = self.user_history[self.username][-self.num_questions*2:]  
     available_indices = [i for i in all_indices if i not in recent_indices]
     if len(available_indices) < self.num_questions:
        available_indices = all_indices

     selected_indices = random.sample(available_indices, min(self.num_questions, len(available_indices)))
     self.questions = [self.all_questions[i] for i in selected_indices]

     self.user_history[self.username].extend(selected_indices)

     random.shuffle(self.questions)
    def create_username_screen(self):
        self.clear_screen()
        
        tk.Label(self.root, text="Soul Sense EQ Test", font=("Arial", 18, "bold"), fg="blue").pack(pady=20)
        
        tk.Label(self.root, text="Enter Your Name:", font=("Arial", 14)).pack(pady=10)
        self.name_entry = tk.Entry(self.root, font=("Arial", 14), width=25)
        self.name_entry.pack(pady=5)
        
        tk.Label(self.root, text="Enter Your Age (optional):", font=("Arial", 14)).pack(pady=10)
        self.age_entry = tk.Entry(self.root, font=("Arial", 14), width=25)
        self.age_entry.pack(pady=5)
        
        tk.Label(self.root, text="Number of Questions:", font=("Arial", 14)).pack(pady=10)
        self.question_var = tk.IntVar(value=15)
        
        question_frame = tk.Frame(self.root)
        question_frame.pack(pady=5)
        
        for num in [10, 12, 15]:
            tk.Radiobutton(question_frame, text=f"{num} questions", variable=self.question_var, 
                         value=num, font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        
        tk.Button(self.root, text="Start Test", command=self.start_test, 
                 font=("Arial", 14), bg="green", fg="white", width=15).pack(pady=30)

    def start_test(self):
     self.username = self.name_entry.get().strip()
     age_str = self.age_entry.get().strip()

     if not self.username:
        messagebox.showwarning("Input Error", "Please enter your name.")
        return

     if age_str:
        try:
            self.age = int(age_str)
            if self.age < 1 or self.age > 120:
                messagebox.showwarning("Input Error", "Please enter a valid age (1-120).")
                return
        except ValueError:
            messagebox.showwarning("Input Error", "Age must be a number.")
            return

     self.num_questions = self.question_var.get()

     self.select_questions()
     print("USERNAME:", self.username)
     print("NUM QUESTIONS:", self.num_questions)
     print("QUESTIONS LOADED:", self.questions)

     if not self.questions:
        messagebox.showerror("Error", "No questions available to start the test!")
        return

     self.current_question = 0
     self.responses = []
     self.show_question()

    def show_question(self):
        self.clear_screen()
        
        if self.current_question < len(self.questions):
            tk.Label(self.root, text=f"Question {self.current_question + 1} of {len(self.questions)}", 
                    font=("Arial", 12), fg="gray").pack(pady=10)
            
            tk.Label(self.root, text=self.questions[self.current_question], 
                    wraplength=500, font=("Arial", 14), justify="center").pack(pady=20)
            
            self.answer_var = tk.IntVar()
            
            options_frame = tk.Frame(self.root)
            options_frame.pack(pady=20)
            
            for val, text in enumerate(["Never (1)", "Sometimes (2)", "Often (3)", "Always (4)"], start=1):
                tk.Radiobutton(options_frame, text=text, variable=self.answer_var, 
                             value=val, font=("Arial", 12)).pack(anchor="w", pady=5)
            
            tk.Button(self.root, text="Next", command=self.save_answer, 
                     font=("Arial", 12), bg="blue", fg="white", width=10).pack(pady=30)
        else:
            self.finish_test()

    def save_answer(self):
        ans = self.answer_var.get()
        if ans == 0:
            messagebox.showwarning("Input Error", "Please select an answer before proceeding.")
        else:
            self.responses.append(ans)
            self.current_question += 1
            self.show_question()

    def finish_test(self):
        raw_score = sum(self.responses)
        normalized_score = round((raw_score / (self.num_questions * 4)) * 80)
        
        self.cursor.execute("INSERT INTO scores (username, age, total_score, normalized_score, num_questions) VALUES (?, ?, ?, ?, ?)", 
                           (self.username, self.age, raw_score, normalized_score, self.num_questions))
        self.conn.commit()
        
        if normalized_score >= 65:
            interpretation = "Excellent Emotional Intelligence!"
            color = "green"
        elif normalized_score >= 50:
            interpretation = "Good Emotional Intelligence."
            color = "blue"
        elif normalized_score >= 35:
            interpretation = "Average Emotional Intelligence."
            color = "orange"
        else:
            interpretation = "You may want to work on your Emotional Intelligence."
            color = "red"
        
        self.show_results(raw_score, normalized_score, interpretation, color)

    def show_results(self, raw_score, normalized_score, interpretation, color):
        self.clear_screen()
        
        tk.Label(self.root, text="Test Complete!", font=("Arial", 18, "bold"), fg="blue").pack(pady=20)
        tk.Label(self.root, text=f"Thank you, {self.username}!", font=("Arial", 16)).pack(pady=10)
        tk.Label(self.root, text=f"Questions: {self.num_questions} | Raw: {raw_score}/{self.num_questions * 4}", 
                font=("Arial", 12), fg="gray").pack(pady=5)
        tk.Label(self.root, text=f"EQ Score: {normalized_score} / 80", 
                font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(self.root, text=interpretation, font=("Arial", 14), fg=color).pack(pady=10)
        
        self.show_all_results()
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=30)
        
        if self.journal_available:
            tk.Button(button_frame, text="Open Journal", command=self.open_journal, 
                     font=("Arial", 12), bg="#2196F3", fg="white", width=12).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Take Test Again", command=self.create_username_screen, 
                 font=("Arial", 12), bg="green", fg="white", width=12).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Exit", command=self.exit_test, 
                 font=("Arial", 12), bg="red", fg="white", width=12).pack(side=tk.LEFT, padx=10)

    def show_all_results(self):
        print(f"\n{'='*50}")
        print("ALL EQ TEST RESULTS")
        print(f"{'='*50}")
        print(f"{'Name':<15} {'Age':<5} {'Q#':<5} {'Raw':<8} {'Norm':<8}")
        print(f"{'-'*50}")
        
        self.cursor.execute("SELECT username, age, total_score, normalized_score, num_questions FROM scores ORDER BY rowid DESC")
        rows = self.cursor.fetchall()
        
        for row in rows:
            age = str(row[1]) if row[1] else "N/A"
            norm = row[3] if len(row) > 3 and row[3] else "N/A"
            questions = row[4] if len(row) > 4 and row[4] else "N/A"
            print(f"{row[0]:<15} {age:<5} {questions:<5} {row[2]:<8} {norm:<8}")
        
        print(f"{'='*50}")

    def open_journal(self):
        if self.journal:
            self.journal.open_journal_window(self.username)

    def exit_test(self):
        self.conn.close()
        self.root.quit()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SoulSenseApp(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_test)
    root.mainloop()