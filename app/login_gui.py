import tkinter as tk
from tkinter import messagebox
from app.auth import AuthManager

class LoginWindow:
    def __init__(self, parent_callback):
        self.parent_callback = parent_callback
        self.auth_manager = AuthManager()
        self.root = tk.Tk()
        self.root.title("Soul Sense - Login")
        self.root.geometry("400x300")
        self.create_login_screen()
    
    def create_login_screen(self):
        """Create login interface"""
        self.clear_screen()
        
        tk.Label(self.root, text="Soul Sense EQ Test", font=("Arial", 18, "bold")).pack(pady=20)
        
        # Login form
        tk.Label(self.root, text="Username:", font=("Arial", 12)).pack(pady=5)
        self.username_entry = tk.Entry(self.root, font=("Arial", 12), width=25)
        self.username_entry.pack(pady=5)
        
        tk.Label(self.root, text="Password:", font=("Arial", 12)).pack(pady=5)
        self.password_entry = tk.Entry(self.root, font=("Arial", 12), width=25, show="*")
        self.password_entry.pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Login", command=self.login, 
                 font=("Arial", 12), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Sign Up", command=self.create_signup_screen, 
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda e: self.login())
    
    def create_signup_screen(self):
        """Create signup interface"""
        self.clear_screen()
        
        tk.Label(self.root, text="Create Account", font=("Arial", 18, "bold")).pack(pady=20)
        
        tk.Label(self.root, text="Username:", font=("Arial", 12)).pack(pady=5)
        self.username_entry = tk.Entry(self.root, font=("Arial", 12), width=25)
        self.username_entry.pack(pady=5)
        
        tk.Label(self.root, text="Password:", font=("Arial", 12)).pack(pady=5)
        self.password_entry = tk.Entry(self.root, font=("Arial", 12), width=25, show="*")
        self.password_entry.pack(pady=5)
        
        tk.Label(self.root, text="Confirm Password:", font=("Arial", 12)).pack(pady=5)
        self.confirm_password_entry = tk.Entry(self.root, font=("Arial", 12), width=25, show="*")
        self.confirm_password_entry.pack(pady=5)
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Create Account", command=self.signup, 
                 font=("Arial", 12), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Back to Login", command=self.create_login_screen, 
                 font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
    
    def login(self):
        """Handle user login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password")
            return
        
        success, message = self.auth_manager.authenticate_user(username, password)
        
        if success:
            self.root.destroy()
            self.parent_callback(username)
        else:
            messagebox.showerror("Login Failed", message)
    
    def signup(self):
        """Handle user registration"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        
        if not username or not password or not confirm_password:
            messagebox.showwarning("Input Error", "Please fill all fields")
            return
        
        if password != confirm_password:
            messagebox.showerror("Password Error", "Passwords do not match")
            return
        
        success, message = self.auth_manager.register_user(username, password)
        
        if success:
            messagebox.showinfo("Success", "Account created successfully! Please login.")
            self.create_login_screen()
        else:
            messagebox.showerror("Registration Failed", message)
    
    def clear_screen(self):
        """Clear all widgets from screen"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show(self):
        """Show login window"""
        self.root.mainloop()