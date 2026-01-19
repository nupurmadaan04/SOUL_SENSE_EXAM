"""
Admin Interface for Managing Questions and Categories
Provides GUI and CLI for CRUD operations on questions database
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import json
import bcrypt

# Safe import for Matplotlib
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# Add parent directory to path to allow importing app
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import DB_PATH

class QuestionDatabase:
    """Handles database operations for questions"""
    
    def __init__(self, db_path="soulsense_db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize questions table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create questions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            age_min INTEGER DEFAULT 12,
            age_max INTEGER DEFAULT 100,
            difficulty INTEGER DEFAULT 3,
            weight REAL DEFAULT 1.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
        """)
        
        # Create admin users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
    
    def add_question(self, text, category="General", age_min=12, age_max=100, 
                    difficulty=3, weight=1.0):
        """Add a new question to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT INTO questions (text, category, age_min, age_max, difficulty, weight)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (text, category, age_min, age_max, difficulty, weight))
            
            conn.commit()
            question_id = cursor.lastrowid
            return question_id
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to add question: {e}")
        finally:
            conn.close()
    
    def update_question(self, question_id, text=None, category=None, age_min=None, 
                       age_max=None, difficulty=None, weight=None):
        """Update an existing question"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if text is not None:
            updates.append("text = ?")
            values.append(text)
        if category is not None:
            updates.append("category = ?")
            values.append(category)
        if age_min is not None:
            updates.append("age_min = ?")
            values.append(age_min)
        if age_max is not None:
            updates.append("age_max = ?")
            values.append(age_max)
        if difficulty is not None:
            updates.append("difficulty = ?")
            values.append(difficulty)
        if weight is not None:
            updates.append("weight = ?")
            values.append(weight)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        values.append(question_id)
        
        try:
            query = f"UPDATE questions SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to update question: {e}")
        finally:
            conn.close()
    
    def delete_question(self, question_id):
        """Delete a question (soft delete - sets is_active to 0)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE questions SET is_active = 0 WHERE id = ?", (question_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to delete question: {e}")
        finally:
            conn.close()
    
    def get_all_questions(self, include_inactive=False):
        """Get all questions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if include_inactive:
            cursor.execute("SELECT * FROM questions ORDER BY id")
        else:
            cursor.execute("SELECT * FROM questions WHERE is_active = 1 ORDER BY id")
        
        columns = [desc[0] for desc in cursor.description]
        questions = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return questions
    
    def get_question_by_id(self, question_id):
        """Get a specific question by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            question = dict(zip(columns, row))
        else:
            question = None
        
        conn.close()
        return question
    
    def get_categories(self):
        """Get all unique categories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT category FROM questions WHERE is_active = 1")
        categories = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return categories
    
    def get_all_users(self):
        """Get all users with preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, username, advice_language, advice_tone, created_at FROM users ORDER BY username")
            columns = [desc[0] for desc in cursor.description]
            users = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Table doesn't exist or columns missing
            users = []
        
        conn.close()
        return users
    
    def update_user_preferences(self, username, language, tone):
        """Update user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET advice_language = ?, advice_tone = ? WHERE username = ?",
                         (language, tone, username))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Failed to update preferences: {e}")
        finally:
            conn.close()
    
    def _hash_password(self, password):
        """Hash password using bcrypt with configurable rounds (default: 12)."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def _verify_password(self, password, password_hash):
        """Verify password against bcrypt hash. Also supports legacy SHA-256 hashes."""
        # Check if it's a bcrypt hash (starts with $2)
        if password_hash.startswith('$2'):
            try:
                return bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception:
                return False
        else:
            # Legacy SHA-256 hash support for backward compatibility
            import hashlib
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            return legacy_hash == password_hash
    
    def _upgrade_password_hash(self, username, password):
        """Upgrade a legacy SHA-256 hash to bcrypt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_hash = self._hash_password(password)
        try:
            cursor.execute(
                "UPDATE admin_users SET password_hash = ? WHERE username = ?",
                (new_hash, username)
            )
            conn.commit()
        finally:
            conn.close()
    
    def verify_admin(self, username, password):
        """Verify admin credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT password_hash FROM admin_users WHERE username = ?
        """, (username,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return False
        
        password_hash = row[0]
        is_valid = self._verify_password(password, password_hash)
        
        # If valid and using legacy hash, upgrade to bcrypt
        if is_valid and not password_hash.startswith('$2'):
            self._upgrade_password_hash(username, password)
        
        return is_valid
    
    def create_admin(self, username, password):
        """Create a new admin user with bcrypt-hashed password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self._hash_password(password)
        
        try:
            cursor.execute("""
            INSERT INTO admin_users (username, password_hash)
            VALUES (?, ?)
            """, (username, password_hash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Username already exists
        finally:
            conn.close()


class AdminInterface:
    """GUI Admin Interface for managing questions"""
    
    def __init__(self):
        self.db = QuestionDatabase()
        self.current_user = None
        self.create_login_window()
    
    def create_login_window(self):
        """Create admin login window"""
        self.login_window = tk.Tk()
        self.login_window.title("Admin Login")
        self.login_window.geometry("400x300")
        
        # Title
        tk.Label(self.login_window, text="SoulSense Admin Panel", 
                font=("Arial", 18, "bold")).pack(pady=20)
        
        # Login frame
        login_frame = tk.Frame(self.login_window)
        login_frame.pack(pady=20)
        
        tk.Label(login_frame, text="Username:", font=("Arial", 12)).grid(row=0, column=0, pady=10, padx=10, sticky="e")
        self.username_entry = tk.Entry(login_frame, font=("Arial", 12), width=20)
        self.username_entry.grid(row=0, column=1, pady=10, padx=10)
        
        tk.Label(login_frame, text="Password:", font=("Arial", 12)).grid(row=1, column=0, pady=10, padx=10, sticky="e")
        self.password_entry = tk.Entry(login_frame, font=("Arial", 12), width=20, show="*")
        self.password_entry.grid(row=1, column=1, pady=10, padx=10)
        
        # Buttons
        button_frame = tk.Frame(self.login_window)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Login", command=self.login,
                 bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                 width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Create Admin", command=self.create_admin,
                 bg="#2196F3", fg="white", font=("Arial", 12),
                 width=12).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        self.login_window.mainloop()
    
    def login(self):
        """Handle admin login"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        if self.db.verify_admin(username, password):
            self.current_user = username
            self.login_window.destroy()
            self.create_main_window()
        else:
            messagebox.showerror("Error", "Invalid credentials")
    
    def create_admin(self):
        """Create new admin account"""
        dialog = tk.Toplevel(self.login_window)
        dialog.title("Create Admin Account")
        dialog.geometry("400x250")
        
        tk.Label(dialog, text="Create New Admin", font=("Arial", 14, "bold")).pack(pady=10)
        
        form_frame = tk.Frame(dialog)
        form_frame.pack(pady=10)
        
        tk.Label(form_frame, text="Username:", font=("Arial", 11)).grid(row=0, column=0, pady=10, padx=10, sticky="e")
        new_username = tk.Entry(form_frame, font=("Arial", 11), width=20)
        new_username.grid(row=0, column=1, pady=10, padx=10)
        
        tk.Label(form_frame, text="Password:", font=("Arial", 11)).grid(row=1, column=0, pady=10, padx=10, sticky="e")
        new_password = tk.Entry(form_frame, font=("Arial", 11), width=20, show="*")
        new_password.grid(row=1, column=1, pady=10, padx=10)
        
        tk.Label(form_frame, text="Confirm:", font=("Arial", 11)).grid(row=2, column=0, pady=10, padx=10, sticky="e")
        confirm_password = tk.Entry(form_frame, font=("Arial", 11), width=20, show="*")
        confirm_password.grid(row=2, column=1, pady=10, padx=10)
        
        def create():
            username = new_username.get()
            password = new_password.get()
            confirm = confirm_password.get()
            
            if not username or not password:
                messagebox.showerror("Error", "All fields required")
                return
            
            if password != confirm:
                messagebox.showerror("Error", "Passwords don't match")
                return
            
            if len(password) < 4:
                messagebox.showerror("Error", "Password must be at least 4 characters")
                return
            
            if self.db.create_admin(username, password):
                messagebox.showinfo("Success", "Admin account created successfully!")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Username already exists")
        
        tk.Button(dialog, text="Create", command=create,
                 bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                 width=12).pack(pady=10)
    
    def create_main_window(self):
        """Create main admin interface"""
        self.main_window = tk.Tk()
        self.main_window.title(f"SoulSense Admin Studio - {self.current_user}")
        self.main_window.geometry("1000x800")
        self.apply_theme() # Apply modern styles
        self.main_window.configure(bg="#F0F2F5")

    def apply_theme(self):
        """Apply modern, professional styles"""
        style = ttk.Style()
        style.theme_use('clam') # Clam supports color customization

        # Colors
        PRIMARY = "#2C3E50" # Dark Slate
        ACCENT = "#3498DB"  # Bright Blue
        BG_LIGHT = "#FFFFFF"
        TEXT_DARK = "#2C3E50"
        
        # Configure TFrame
        style.configure("TFrame", background="#F0F2F5")
        style.configure("Card.TFrame", background=BG_LIGHT, relief="flat", borderwidth=0)
        
        # Configure TLabel
        style.configure("TLabel", background="#F0F2F5", foreground=TEXT_DARK, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground=PRIMARY, background="#F0F2F5")
        style.configure("Subheader.TLabel", font=("Segoe UI", 14, "bold"), foreground="#7F8C8D", background="#F0F2F5")
        
        # Configure TButton
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background=ACCENT, foreground="white", borderwidth=0)
        style.map("TButton", background=[("active", "#2980B9")])
        
        # Configure TNotebook
        style.configure("TNotebook", background="#F0F2F5", tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", padding=[15, 5], font=("Segoe UI", 11), background="#E0E0E0", foreground="#555")
        style.map("TNotebook.Tab", background=[("selected", PRIMARY)], foreground=[("selected", "white")])
        self.main_window.geometry("1000x700")
        
        # Title
        tk.Label(self.main_window, text="Question Management System",
                font=("Arial", 18, "bold")).pack(pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.main_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: View Questions
        view_frame = ttk.Frame(notebook)
        notebook.add(view_frame, text="📋 View Questions")
        self.create_view_tab(view_frame)
        
        # Tab 2: Add Question
        add_frame = ttk.Frame(notebook)
        notebook.add(add_frame, text="➕ Add Question")
        self.create_add_tab(add_frame)
        
        # Tab 3: Edit Question
        edit_frame = ttk.Frame(notebook)
        notebook.add(edit_frame, text="✏️ Edit Question")
        self.create_edit_tab(edit_frame)
        
        # Tab 4: Categories
        cat_frame = ttk.Frame(notebook)
        notebook.add(cat_frame, text="🏷️ Categories")
        self.create_categories_tab(cat_frame)
        
        self.main_window.mainloop()
    
    def create_view_tab(self, parent):
        """Create view questions tab"""
        # Controls frame
        controls = tk.Frame(parent)
        controls.pack(pady=10, fill=tk.X, padx=10)
        
        tk.Label(controls, text="Filter by Category:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        
        self.category_filter = ttk.Combobox(controls, values=["All"] + self.db.get_categories(),
                                           state="readonly", width=15)
        self.category_filter.set("All")
        self.category_filter.pack(side=tk.LEFT, padx=5)
        
        tk.Button(controls, text="Refresh", command=self.refresh_questions_list,
                 bg="#2196F3", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(controls, text="Show Inactive", command=lambda: self.refresh_questions_list(True),
                 bg="#FF9800", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        # Treeview for questions
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        self.questions_tree = ttk.Treeview(tree_frame, 
                                          columns=("ID", "Text", "Category", "Age Range", "Difficulty", "Weight", "Status"),
                                          show="headings",
                                          yscrollcommand=vsb.set,
                                          xscrollcommand=hsb.set)
        
        vsb.config(command=self.questions_tree.yview)
        hsb.config(command=self.questions_tree.xview)
        
        # Configure columns
        self.questions_tree.heading("ID", text="ID")
        self.questions_tree.heading("Text", text="Question Text")
        self.questions_tree.heading("Category", text="Category")
        self.questions_tree.heading("Age Range", text="Age Range")
        self.questions_tree.heading("Difficulty", text="Difficulty")
        self.questions_tree.heading("Weight", text="Weight")
        self.questions_tree.heading("Status", text="Status")
        
        self.questions_tree.column("ID", width=50)
        self.questions_tree.column("Text", width=400)
        self.questions_tree.column("Category", width=100)
        self.questions_tree.column("Age Range", width=100)
        self.questions_tree.column("Difficulty", width=80)
        self.questions_tree.column("Weight", width=70)
        self.questions_tree.column("Status", width=80)
        
        # Grid layout
        self.questions_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Load questions
        self.refresh_questions_list()
    
    def refresh_questions_list(self, include_inactive=False):
        """Refresh the questions list"""
        # Clear existing items
        for item in self.questions_tree.get_children():
            self.questions_tree.delete(item)
        
        # Get questions
        questions = self.db.get_all_questions(include_inactive)
        
        # Filter by category if selected
        selected_category = self.category_filter.get()
        if selected_category != "All":
            questions = [q for q in questions if q['category'] == selected_category]
        
        # Populate tree
        for q in questions:
            status = "Active" if q['is_active'] == 1 else "Inactive"
            self.questions_tree.insert("", tk.END, values=(
                q['id'],
                q['text'][:80] + "..." if len(q['text']) > 80 else q['text'],
                q['category'],
                f"{q['age_min']}-{q['age_max']}",
                q['difficulty'],
                q['weight'],
                status
            ))
    
    def create_add_tab(self, parent):
        """Create add question tab"""
        form_frame = tk.Frame(parent)
        form_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        # Question text
        tk.Label(form_frame, text="Question Text:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="nw", pady=10)
        self.add_text = scrolledtext.ScrolledText(form_frame, width=60, height=4, font=("Arial", 11))
        self.add_text.grid(row=0, column=1, pady=10, padx=10)
        
        # Category
        tk.Label(form_frame, text="Category:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        self.add_category = ttk.Combobox(form_frame, values=self.db.get_categories() + ["New..."], width=25)
        self.add_category.grid(row=1, column=1, sticky="w", pady=10, padx=10)
        self.add_category.set("General")
        
        # Age range
        age_frame = tk.Frame(form_frame)
        age_frame.grid(row=2, column=1, sticky="w", pady=10, padx=10)
        
        tk.Label(form_frame, text="Age Range:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=10)
        tk.Label(age_frame, text="Min:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.add_age_min = tk.Spinbox(age_frame, from_=12, to=100, width=10)
        self.add_age_min.delete(0, tk.END)
        self.add_age_min.insert(0, "12")
        self.add_age_min.pack(side=tk.LEFT, padx=5)
        
        tk.Label(age_frame, text="Max:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.add_age_max = tk.Spinbox(age_frame, from_=12, to=100, width=10)
        self.add_age_max.delete(0, tk.END)
        self.add_age_max.insert(0, "100")
        self.add_age_max.pack(side=tk.LEFT, padx=5)
        
        # Difficulty
        tk.Label(form_frame, text="Difficulty (1-5):", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=10)
        self.add_difficulty = tk.Spinbox(form_frame, from_=1, to=5, width=10)
        self.add_difficulty.delete(0, tk.END)
        self.add_difficulty.insert(0, "3")
        self.add_difficulty.grid(row=3, column=1, sticky="w", pady=10, padx=10)
        
        # Weight
        tk.Label(form_frame, text="Weight:", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky="w", pady=10)
        self.add_weight = tk.Spinbox(form_frame, from_=0.1, to=5.0, increment=0.1, width=10)
        self.add_weight.delete(0, tk.END)
        self.add_weight.insert(0, "1.0")
        self.add_weight.grid(row=4, column=1, sticky="w", pady=10, padx=10)
        
        # Buttons
        button_frame = tk.Frame(form_frame)
        button_frame.grid(row=5, column=1, pady=20, sticky="w", padx=10)
        
        tk.Button(button_frame, text="Add Question", command=self.add_question,
                 bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                 width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Clear", command=self.clear_add_form,
                 bg="#757575", fg="white", font=("Arial", 12),
                 width=10).pack(side=tk.LEFT, padx=5)
    
    def add_question(self):
        """Add a new question"""
        text = self.add_text.get("1.0", tk.END).strip()
        category = self.add_category.get()
        
        if not text:
            messagebox.showerror("Error", "Question text is required")
            return
        
        if category == "New...":
            category = tk.simpledialog.askstring("New Category", "Enter category name:")
            if not category:
                return
        
        try:
            age_min = int(self.add_age_min.get())
            age_max = int(self.add_age_max.get())
            difficulty = int(self.add_difficulty.get())
            weight = float(self.add_weight.get())
            
            if age_min > age_max:
                messagebox.showerror("Error", "Min age cannot be greater than max age")
                return
            
            question_id = self.db.add_question(text, category, age_min, age_max, difficulty, weight)
            messagebox.showinfo("Success", f"Question added successfully! ID: {question_id}")
            self.clear_add_form()
            self.refresh_questions_list()
            
        except ValueError as e:
            messagebox.showerror("Error", "Invalid input values")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear_add_form(self):
        """Clear the add question form"""
        self.add_text.delete("1.0", tk.END)
        self.add_category.set("General")
        self.add_age_min.delete(0, tk.END)
        self.add_age_min.insert(0, "12")
        self.add_age_max.delete(0, tk.END)
        self.add_age_max.insert(0, "100")
        self.add_difficulty.delete(0, tk.END)
        self.add_difficulty.insert(0, "3")
        self.add_weight.delete(0, tk.END)
        self.add_weight.insert(0, "1.0")
    
    def create_edit_tab(self, parent):
        """Create edit question tab"""
        tk.Label(parent, text="Select a question to edit", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        # Question selector
        selector_frame = tk.Frame(parent)
        selector_frame.pack(pady=10)
        
        tk.Label(selector_frame, text="Question ID:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.edit_id = tk.Entry(selector_frame, width=10, font=("Arial", 11))
        self.edit_id.pack(side=tk.LEFT, padx=5)
        
        tk.Button(selector_frame, text="Load", command=self.load_question_for_edit,
                 bg="#2196F3", fg="white", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        
        # Edit form (similar to add form)
        self.edit_form_frame = tk.Frame(parent)
        self.edit_form_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        # Question text
        tk.Label(self.edit_form_frame, text="Question Text:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="nw", pady=10)
        self.edit_text = scrolledtext.ScrolledText(self.edit_form_frame, width=60, height=4, font=("Arial", 11))
        self.edit_text.grid(row=0, column=1, pady=10, padx=10)
        
        # Category
        tk.Label(self.edit_form_frame, text="Category:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        self.edit_category = ttk.Combobox(self.edit_form_frame, values=self.db.get_categories(), width=25)
        self.edit_category.grid(row=1, column=1, sticky="w", pady=10, padx=10)
        
        # Age range
        age_frame = tk.Frame(self.edit_form_frame)
        age_frame.grid(row=2, column=1, sticky="w", pady=10, padx=10)
        
        tk.Label(self.edit_form_frame, text="Age Range:", font=("Arial", 12, "bold")).grid(row=2, column=0, sticky="w", pady=10)
        tk.Label(age_frame, text="Min:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.edit_age_min = tk.Spinbox(age_frame, from_=12, to=100, width=10)
        self.edit_age_min.pack(side=tk.LEFT, padx=5)
        
        tk.Label(age_frame, text="Max:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.edit_age_max = tk.Spinbox(age_frame, from_=12, to=100, width=10)
        self.edit_age_max.pack(side=tk.LEFT, padx=5)
        
        # Difficulty
        tk.Label(self.edit_form_frame, text="Difficulty (1-5):", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=10)
        self.edit_difficulty = tk.Spinbox(self.edit_form_frame, from_=1, to=5, width=10)
        self.edit_difficulty.grid(row=3, column=1, sticky="w", pady=10, padx=10)
        
        # Weight
        tk.Label(self.edit_form_frame, text="Weight:", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky="w", pady=10)
        self.edit_weight = tk.Spinbox(self.edit_form_frame, from_=0.1, to=5.0, increment=0.1, width=10)
        self.edit_weight.grid(row=4, column=1, sticky="w", pady=10, padx=10)
        
        # Buttons
        button_frame = tk.Frame(self.edit_form_frame)
        button_frame.grid(row=5, column=1, pady=20, sticky="w", padx=10)
        
        tk.Button(button_frame, text="Update", command=self.update_question,
                 bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                 width=12).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Delete", command=self.delete_question,
                 bg="#F44336", fg="white", font=("Arial", 12, "bold"),
                 width=12).pack(side=tk.LEFT, padx=5)
    
    def load_question_for_edit(self):
        """Load question data for editing"""
        try:
            question_id = int(self.edit_id.get())
            question = self.db.get_question_by_id(question_id)
            
            if not question:
                messagebox.showerror("Error", "Question not found")
                return
            
            # Populate form
            self.edit_text.delete("1.0", tk.END)
            self.edit_text.insert("1.0", question['text'])
            self.edit_category.set(question['category'])
            
            self.edit_age_min.delete(0, tk.END)
            self.edit_age_min.insert(0, str(question['age_min']))
            
            self.edit_age_max.delete(0, tk.END)
            self.edit_age_max.insert(0, str(question['age_max']))
            
            self.edit_difficulty.delete(0, tk.END)
            self.edit_difficulty.insert(0, str(question['difficulty']))
            
            self.edit_weight.delete(0, tk.END)
            self.edit_weight.insert(0, str(question['weight']))
            
        except ValueError:
            messagebox.showerror("Error", "Invalid question ID")
    
    def update_question(self):
        """Update the question"""
        try:
            question_id = int(self.edit_id.get())
            text = self.edit_text.get("1.0", tk.END).strip()
            category = self.edit_category.get()
            age_min = int(self.edit_age_min.get())
            age_max = int(self.edit_age_max.get())
            difficulty = int(self.edit_difficulty.get())
            weight = float(self.edit_weight.get())
            
            if not text:
                messagebox.showerror("Error", "Question text is required")
                return
            
            if age_min > age_max:
                messagebox.showerror("Error", "Min age cannot be greater than max age")
                return
            
            if self.db.update_question(question_id, text, category, age_min, age_max, difficulty, weight):
                messagebox.showinfo("Success", "Question updated successfully!")
                self.refresh_questions_list()
            else:
                messagebox.showerror("Error", "Failed to update question")
                
        except ValueError:
            messagebox.showerror("Error", "Invalid input values")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_question(self):
        """Delete the question"""
        try:
            question_id = int(self.edit_id.get())
            
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this question?"):
                if self.db.delete_question(question_id):
                    messagebox.showinfo("Success", "Question deleted successfully!")
                    self.refresh_questions_list()
                    # Clear form
                    self.edit_text.delete("1.0", tk.END)
                    self.edit_id.delete(0, tk.END)
                else:
                    messagebox.showerror("Error", "Failed to delete question")
                    
        except ValueError:
            messagebox.showerror("Error", "Invalid question ID")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def create_categories_tab(self, parent):
        """Create categories management tab"""
        tk.Label(parent, text="Category Statistics", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        # Stats frame
        stats_frame = tk.Frame(parent)
        stats_frame.pack(pady=20, fill=tk.BOTH, expand=True, padx=20)
        
        # Treeview for categories
        self.cat_tree = ttk.Treeview(stats_frame, 
                                    columns=("Category", "Question Count"),
                                    show="headings",
                                    height=15)
        
        self.cat_tree.heading("Category", text="Category")
        self.cat_tree.heading("Question Count", text="Number of Questions")
        
        self.cat_tree.column("Category", width=200)
        self.cat_tree.column("Question Count", width=150)
        
        self.cat_tree.pack(fill=tk.BOTH, expand=True)
        
        # Refresh button
        tk.Button(parent, text="Refresh Statistics", command=self.refresh_category_stats,
                 bg="#2196F3", fg="white", font=("Arial", 12)).pack(pady=10)
        
        # Load stats
        self.refresh_category_stats()
    
    def refresh_category_stats(self):
        """Refresh category statistics"""
        # Clear existing items
        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)
        
        # Get questions
        questions = self.db.get_all_questions()
        
        # Count by category
        category_counts = {}
        for q in questions:
            cat = q['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Populate tree
        for category, count in sorted(category_counts.items()):
            self.cat_tree.insert("", tk.END, values=(category, count))
    
    def create_preferences_tab(self, parent):
        """Create user preferences management tab"""
        tk.Label(parent, text="User Preferences Management", font=("Arial", 14, "bold")).pack(pady=10)
        
        controls = tk.Frame(parent)
        controls.pack(pady=10)
        
        tk.Button(controls, text="Refresh", command=self.refresh_user_prefs,
                 bg="#2196F3", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        self.prefs_tree = ttk.Treeview(tree_frame, columns=("Username", "Language", "Tone", "Created"),
                                       show="headings", yscrollcommand=vsb.set)
        vsb.config(command=self.prefs_tree.yview)
        
        self.prefs_tree.heading("Username", text="Username")
        self.prefs_tree.heading("Language", text="Advice Language")
        self.prefs_tree.heading("Tone", text="Advice Tone")
        self.prefs_tree.heading("Created", text="Created At")
        
        self.prefs_tree.column("Username", width=150)
        self.prefs_tree.column("Language", width=150)
        self.prefs_tree.column("Tone", width=150)
        self.prefs_tree.column("Created", width=200)
        
        self.prefs_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        tk.Button(parent, text="Edit Selected User", command=self.edit_user_prefs,
                 bg="#4CAF50", fg="white", font=("Arial", 11)).pack(pady=10)
        
        self.refresh_user_prefs()
    
    def refresh_user_prefs(self):
        """Refresh user preferences list"""
        for item in self.prefs_tree.get_children():
            self.prefs_tree.delete(item)
        
        users = self.db.get_all_users()
        if not users:
            # Show message if no users found
            self.prefs_tree.insert("", tk.END, values=("No users found", "-", "-", "-"))
            return
        
        for u in users:
            self.prefs_tree.insert("", tk.END, values=(
                u['username'],
                u.get('advice_language', 'en'),
                u.get('advice_tone', 'friendly'),
                u.get('created_at', 'N/A')
            ))
    
    def edit_user_prefs(self):
        """Edit selected user preferences"""
        selected = self.prefs_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a user first")
            return
        
        values = self.prefs_tree.item(selected[0])['values']
        username = values[0]
        
        dialog = tk.Toplevel(self.main_window)
        dialog.title(f"Edit Preferences - {username}")
        dialog.geometry("400x250")
        
        tk.Label(dialog, text=f"User: {username}", font=("Arial", 12, "bold")).pack(pady=10)
        
        tk.Label(dialog, text="Language:", font=("Arial", 11)).pack(pady=5)
        lang_var = tk.StringVar(value=values[1])
        ttk.Combobox(dialog, textvariable=lang_var, values=['en', 'hi', 'es'], state="readonly").pack()
        
        tk.Label(dialog, text="Tone:", font=("Arial", 11)).pack(pady=5)
        tone_var = tk.StringVar(value=values[2])
        ttk.Combobox(dialog, textvariable=tone_var, values=['professional', 'friendly', 'direct', 'empathetic'], state="readonly").pack()
        
        def save():
            if self.db.update_user_preferences(username, lang_var.get(), tone_var.get()):
                messagebox.showinfo("Success", "Preferences updated!")
                self.refresh_user_prefs()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update")
        
        tk.Button(dialog, text="Save", command=save, bg="#4CAF50", fg="white", width=10).pack(pady=20)

    def create_analytics_tab(self, parent):
        """Create analytics dashboard tab"""
        if not PLOTTING_AVAILABLE:
            error_frame = tk.Frame(parent)
            error_frame.pack(expand=True, fill=tk.BOTH)
            tk.Label(error_frame, 
                    text="⚠️ Analytics Unavailable\n\nPlease install 'matplotlib' and 'seaborn' to view charts.\nRun: pip install matplotlib seaborn",
                    font=("Arial", 14), fg="red").pack(expand=True)
            return

        # Main container with scrollbar
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Title and Refresh
        header_frame = tk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(header_frame, text="Exam Analytics Dashboard", 
                font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        
        tk.Button(header_frame, text="🔄 Refresh Data", command=lambda: self.refresh_analytics(self.charts_frame),
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

        # Content Frame (Placeholders for charts)
        self.charts_frame = tk.Frame(scrollable_frame)
        self.charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initial Load
        self.refresh_analytics(self.charts_frame)

    def refresh_analytics(self, parent_frame):
        """Refresh and redraw all charts"""
        # Clear existing widgets
        for widget in parent_frame.winfo_children():
            widget.destroy()
            
        try:
            # Connect to REAL user database (soulsense.db) not questions DB
            # Note: Admin tool usually manages questions, but analytics needs USER scores.
            # We'll need to connect to the main app DB path.
            from app.config import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            
            # --- Summary Stats ---
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), AVG(total_score) FROM scores")
            total_exams, avg_score = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(DISTINCT username) FROM scores")
            active_users = cursor.fetchone()[0]
            
            summary_frame = tk.Frame(parent_frame, bg="#f0f0f0", bd=1, relief="solid")
            summary_frame.pack(fill=tk.X, pady=10)
            
            stats = [
                ("Total Exams", total_exams or 0),
                ("Avg Score", f"{avg_score:.1f}" if avg_score else "N/A"),
                ("Active Users", active_users or 0)
            ]
            
            for i, (label, value) in enumerate(stats):
                f = tk.Frame(summary_frame, bg="white", padx=20, pady=10)
                f.grid(row=0, column=i, sticky="ew", padx=10, pady=10)
                tk.Label(f, text=label, font=("Arial", 10, "bold"), bg="white", fg="#666").pack()
                tk.Label(f, text=str(value), font=("Arial", 20, "bold"), bg="white", fg="#2196F3").pack()
                
            summary_frame.grid_columnconfigure(0, weight=1)
            summary_frame.grid_columnconfigure(1, weight=1)
            summary_frame.grid_columnconfigure(2, weight=1)
            
            # --- Chart Style Configuration ---
            # Modern Professional Palette
            COLOR_MAIN = "#34495E"
            COLOR_ACCENT = "#3498DB" 
            COLOR_HIGHTLIGHT = "#E74C3C"
            COLOR_BG = "#F0F2F5"
            plt.style.use('seaborn-v0_8-whitegrid') # Cleaner grid style

            # Helper to style axes
            def style_ax(ax):
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_color('#BDC3C7')
                ax.spines['bottom'].set_color('#BDC3C7')
                ax.tick_params(colors='#7F8C8D')
                ax.yaxis.label.set_color('#2C3E50')
                ax.xaxis.label.set_color('#2C3E50')
                ax.title.set_color('#2C3E50')
                ax.grid(True, linestyle=':', alpha=0.6)

            # --- Chart 1: Score Distribution (Modern Histogram) ---
            try:
                cursor.execute("SELECT total_score FROM scores WHERE total_score IS NOT NULL")
                scores = [r[0] for r in cursor.fetchall()]
                
                if scores:
                    fig1 = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_BG)
                    ax1 = fig1.add_subplot(111)
                    # Modern bars
                    ax1.hist(scores, bins=12, color="#2ECC71", alpha=0.8, rwidth=0.85, edgecolor='white')
                    ax1.set_title("Distribution of Exam Scores", fontsize=12, fontweight='bold', pad=15)
                    ax1.set_xlabel("Total Score", fontsize=10)
                    ax1.set_ylabel("Frequency", fontsize=10)
                    style_ax(ax1)
                    
                    chart1_frame = ttk.Frame(self.charts_frame, style="Card.TFrame")
                    chart1_frame.pack(fill=tk.X, pady=10) # Using self.charts_frame directly as it's passed as parent_frame usually? 
                    # Wait, function arg is parent_frame. Use that.
                    canvas1 = FigureCanvasTkAgg(fig1, master=chart1_frame)
                    canvas1.draw()
                    canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            except Exception as e:
                print(f"DEBUG: Chart 1 Error: {e}")
                tk.Label(parent_frame, text=f"Error loading Histogram: {e}", fg="red").pack()

            # --- Chart 2: Age Demographics (Modern Donut Chart) ---
            try:
                cursor.execute("SELECT age FROM scores WHERE age IS NOT NULL")
                ages = [r[0] for r in cursor.fetchall()]
                
                if ages:
                    age_groups = {'Child': 0, 'Teen': 0, 'Adult': 0, 'Senior': 0}
                    for age in ages:
                        if age < 13: age_groups['Child'] += 1
                        elif age < 20: age_groups['Teen'] += 1
                        elif age < 60: age_groups['Adult'] += 1
                        else: age_groups['Senior'] += 1
                    
                    labels = [k for k, v in age_groups.items() if v > 0]
                    values = [v for k, v in age_groups.items() if v > 0]
                    
                    if values:
                        fig2 = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_BG)
                        ax2 = fig2.add_subplot(111)
                        # Donut chart
                        wedges, texts, autotexts = ax2.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, 
                                pctdistance=0.85, colors=['#F1C40F', '#E67E22', '#3498DB', '#9B59B6'])
                        
                        # Add Circle for Donut
                        centre_circle = plt.Circle((0,0),0.70,fc=COLOR_BG)
                        ax2.add_artist(centre_circle)
                        
                        ax2.set_title("User Age Demographics", fontsize=12, fontweight='bold', pad=15)
                        
                        # Style text
                        for text in texts: text.set_color('#555')
                        for autotext in autotexts: autotext.set_color('white')
                        
                        chart2_frame = ttk.Frame(parent_frame, style="Card.TFrame")
                        chart2_frame.pack(fill=tk.X, pady=10)
                        canvas2 = FigureCanvasTkAgg(fig2, master=chart2_frame)
                        canvas2.draw()
                        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            except Exception as e:
                 print(f"DEBUG: Chart 2 Error: {e}")
                 tk.Label(parent_frame, text=f"Error loading Pie Chart: {e}", fg="red").pack()

            # --- Chart 3: Score Trend Over Time (Modern Line) ---
            try:
                cursor.execute("SELECT timestamp, total_score FROM scores WHERE timestamp IS NOT NULL ORDER BY timestamp")
                trend_data = cursor.fetchall()
                if trend_data:
                    from datetime import datetime
                    # ... (Group by date logic)
                    date_map = {} 
                    for ts, score in trend_data:
                        try:
                            dt = datetime.fromisoformat(ts)
                            date_str = dt.strftime("%Y-%m-%d")
                            if date_str not in date_map: date_map[date_str] = []
                            date_map[date_str].append(score)
                        except: continue
                    dates = sorted(date_map.keys())
                    avg_scores = [sum(date_map[d])/len(date_map[d]) for d in dates]

                    if dates:
                        fig3 = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_BG)
                        ax3 = fig3.add_subplot(111)
                        # Area chart style
                        ax3.fill_between(dates, avg_scores, color=COLOR_ACCENT, alpha=0.1)
                        ax3.plot(dates, avg_scores, marker='o', color=COLOR_ACCENT, linewidth=2, markersize=6)
                        
                        ax3.set_title("Score Trend (Daily Average)", fontsize=12, fontweight='bold', pad=15)
                        ax3.set_ylabel("Avg Score", fontsize=10)
                        ax3.tick_params(axis='x', rotation=45)
                        style_ax(ax3)
                        fig3.tight_layout()

                        chart3_frame = ttk.Frame(parent_frame, style="Card.TFrame")
                        chart3_frame.pack(fill=tk.X, pady=10)
                        canvas3 = FigureCanvasTkAgg(fig3, master=chart3_frame)
                        canvas3.draw()
                        canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            except Exception as e:
                 print(f"DEBUG: Chart 3 Error: {e}")
                 tk.Label(parent_frame, text=f"Error loading Trend Chart: {e}", fg="red").pack()

            # --- Chart 4: Correlation (Modern Scatter) ---
            try:
                cursor.execute("SELECT sentiment_score, total_score FROM scores WHERE sentiment_score IS NOT NULL AND total_score IS NOT NULL")
                scatter_data = cursor.fetchall()
                if scatter_data:
                    sentiments = [r[0] for r in scatter_data]
                    exam_scores = [r[1] for r in scatter_data]
                    if sentiments:
                        fig4 = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_BG)
                        ax4 = fig4.add_subplot(111)
                        ax4.scatter(sentiments, exam_scores, alpha=0.6, c=sentiments, cmap='viridis', s=60, edgecolor='white')
                        ax4.set_title("Sentiment vs. Score Correlation", fontsize=12, fontweight='bold', pad=15)
                        ax4.set_xlabel("Sentiment Score", fontsize=10)
                        ax4.set_ylabel("Exam Score", fontsize=10)
                        style_ax(ax4)
                        
                        chart4_frame = ttk.Frame(parent_frame, style="Card.TFrame")
                        chart4_frame.pack(fill=tk.X, pady=10)
                        canvas4 = FigureCanvasTkAgg(fig4, master=chart4_frame)
                        canvas4.draw()
                        canvas4.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            except Exception as e:
                print(f"DEBUG: Chart 4 Error: {e}")
                tk.Label(parent_frame, text=f"Error loading Scatter Chart: {e}", fg="red").pack()

            conn.close()

        except Exception as e:
            print(f"DEBUG: General Analytics Error: {e}")
            tk.Label(parent_frame, text=f"Error loading analytics: {e}", fg="red").pack(pady=20)


def main():
    """Run the admin interface"""
    app = AdminInterface()


if __name__ == "__main__":
    main()
