import tkinter as tk
from app import auth
from app.logger import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.main import SoulSenseApp

class AppAuth:
    def __init__(self, app: 'SoulSenseApp'):
        self.app = app
        self.auth_manager = auth.AuthManager()
        self.logger = get_logger(__name__)
        self.start_login_flow()

    def _generate_captcha(self):
        """Generate a random 5-character CAPTCHA code"""
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(5))

    def show_login_screen(self):
        """Show login popup on startup"""
        login_win = tk.Toplevel(self.app.root)
        login_win.title("SoulSense Login")
        login_win.geometry("400x580")  # Increased height for CAPTCHA
        login_win.configure(bg=self.app.colors["bg"])
        login_win.transient(self.app.root)
        login_win.grab_set()

        # Prevent closing without login
        login_win.protocol("WM_DELETE_WINDOW", lambda: self.app.root.destroy())

        # Center
        login_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 400) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 580) // 2
        login_win.geometry(f"+{x}+{y}")

        # Logo/Title
        tk.Label(login_win, text="SoulSense AI", font=("Segoe UI", 24, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["primary"]).pack(pady=(40, 10))

        tk.Label(login_win, text="Login to continue", font=("Segoe UI", 12),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"]).pack(pady=(0, 30))

        # CAPTCHA Section
        captcha_frame = tk.Frame(login_win, bg=self.app.colors["bg"])
        captcha_frame.pack(fill="x", padx=40, pady=(0, 20))

        tk.Label(captcha_frame, text="Security Verification", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")

        # CAPTCHA state
        captcha_code = [self._generate_captcha()]  # Use list to make it mutable

        # CAPTCHA Display
        captcha_display_frame = tk.Frame(captcha_frame, bg=self.app.colors["bg"])
        captcha_display_frame.pack(fill="x", pady=(5, 10))

        captcha_label = tk.Label(captcha_display_frame, text=captcha_code[0],
                                font=("Courier New", 18, "bold"),
                                bg="#f0f0f0", fg="#333333", relief="solid", borderwidth=2)
        captcha_label.pack(side="left", padx=(0, 10), ipady=5, ipadx=20)

        # Refresh CAPTCHA button
        def refresh_captcha():
            captcha_code[0] = self._generate_captcha()
            captcha_label.config(text=captcha_code[0])
            captcha_entry.delete(0, tk.END)
            captcha_error_label.config(text="")

        refresh_btn = tk.Button(captcha_display_frame, text="↻", command=refresh_captcha,
                               font=("Segoe UI", 12), bg=self.app.colors["primary"], fg="white",
                               width=3, cursor="hand2")
        refresh_btn.pack(side="left")

        # CAPTCHA Input
        tk.Label(captcha_frame, text="Enter CAPTCHA code", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w", pady=(10, 5))
        captcha_entry = tk.Entry(captcha_frame, font=("Segoe UI", 12))
        captcha_entry.pack(fill="x", pady=(0, 5))

        # CAPTCHA Error Label
        captcha_error_label = tk.Label(captcha_frame, text="", font=("Segoe UI", 9),
                                      bg=self.app.colors["bg"], fg="red")
        captcha_error_label.pack(anchor="w")

        # Form
        entry_frame = tk.Frame(login_win, bg=self.app.colors["bg"])
        entry_frame.pack(fill="x", padx=40)

        tk.Label(entry_frame, text="Username", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        username_entry = tk.Entry(entry_frame, font=("Segoe UI", 12))
        username_entry.pack(fill="x", pady=(5, 15))

        tk.Label(entry_frame, text="Password", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        password_entry = tk.Entry(entry_frame, font=("Segoe UI", 12), show="*")
        password_entry.pack(fill="x", pady=(5, 15))

        # Show Password checkbox
        show_password_var = tk.BooleanVar()
        def toggle_password_visibility():
            show_char = "" if show_password_var.get() else "*"
            password_entry.config(show=show_char)

        show_password_cb = tk.Checkbutton(entry_frame, text="Show Password", variable=show_password_var,
                                         command=toggle_password_visibility, font=("Segoe UI", 10),
                                         bg=self.app.colors["bg"], fg=self.app.colors["text_primary"])
        show_password_cb.pack(anchor="w", pady=(0, 10))

        def do_login():
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()
            captcha_input = captcha_entry.get().strip()

            if not user or not pwd:
                tk.messagebox.showerror("Error", "Please enter username and password")
                return

            # Validate CAPTCHA first
            if not captcha_input:
                captcha_error_label.config(text="Please enter the CAPTCHA code")
                return

            if captcha_input.upper() != captcha_code[0]:
                captcha_error_label.config(text="Invalid CAPTCHA. Please try again!")
                # Regenerate CAPTCHA on failure
                captcha_code[0] = self._generate_captcha()
                captcha_label.config(text=captcha_code[0])
                captcha_entry.delete(0, tk.END)
                return

            # CAPTCHA is valid, proceed with authentication
            success, msg = self.auth_manager.login_user(user, pwd)
            if success:
                self.app.username = user
                self._load_user_settings(user)
                login_win.destroy()
                self._post_login_init()
            else:
                captcha_error_label.config(text="Invalid username or password.")
                # Regenerate CAPTCHA on login failure
                captcha_code[0] = self._generate_captcha()
                captcha_label.config(text=captcha_code[0])
                captcha_entry.delete(0, tk.END)

        def do_register():
            self.show_signup_screen()

        # Buttons
        tk.Button(login_win, text="Login", command=do_login,
                 font=("Segoe UI", 12, "bold"), bg=self.app.colors["primary"], fg="white",
                 width=20).pack(pady=10)

        tk.Button(login_win, text="Create Account", command=do_register,
                 font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                 bd=0, cursor="hand2").pack()

    def show_signup_screen(self):
        """Show signup popup window"""
        signup_win = tk.Toplevel(self.app.root)
        signup_win.title("Create Account - SoulSense")
        signup_win.geometry("450x600")
        signup_win.configure(bg=self.app.colors["bg"])
        signup_win.transient(self.app.root)
        signup_win.grab_set()

        # Center
        signup_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 450) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 600) // 2
        signup_win.geometry(f"+{x}+{y}")

        # Title
        tk.Label(signup_win, text="Create Account", font=("Segoe UI", 20, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["primary"]).pack(pady=(30, 10))

        tk.Label(signup_win, text="Join SoulSense AI", font=("Segoe UI", 12),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"]).pack(pady=(0, 20))

        # Form
        form_frame = tk.Frame(signup_win, bg=self.app.colors["bg"])
        form_frame.pack(fill="x", padx=40)

        # Name
        tk.Label(form_frame, text="Name", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        name_entry = tk.Entry(form_frame, font=("Segoe UI", 12))
        name_entry.pack(fill="x", pady=(5, 15))

        # Email
        tk.Label(form_frame, text="Email", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        email_entry = tk.Entry(form_frame, font=("Segoe UI", 12))
        email_entry.pack(fill="x", pady=(5, 15))

        # Age
        tk.Label(form_frame, text="Age", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        age_entry = tk.Entry(form_frame, font=("Segoe UI", 12))
        age_entry.pack(fill="x", pady=(5, 15))

        # Gender
        tk.Label(form_frame, text="Gender", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        gender_var = tk.StringVar(value="Prefer not to say")
        gender_options = ["Male", "Female", "Other", "Prefer not to say"]
        gender_menu = tk.OptionMenu(form_frame, gender_var, *gender_options)
        gender_menu.config(font=("Segoe UI", 12), bg=self.app.colors["bg"], fg=self.app.colors["text_primary"])
        gender_menu.pack(fill="x", pady=(5, 15))

        # Password
        tk.Label(form_frame, text="Password", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        password_entry = tk.Entry(form_frame, font=("Segoe UI", 12), show="*")
        password_entry.pack(fill="x", pady=(5, 15))

        # Confirm Password
        tk.Label(form_frame, text="Confirm Password", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        confirm_password_entry = tk.Entry(form_frame, font=("Segoe UI", 12), show="*")
        confirm_password_entry.pack(fill="x", pady=(5, 20))

        def do_signup():
            name = name_entry.get().strip()
            email = email_entry.get().strip()
            age_str = age_entry.get().strip()
            gender = gender_var.get()
            password = password_entry.get()
            confirm_password = confirm_password_entry.get()

            # Validations
            if not name:
                tk.messagebox.showerror("Error", "Name is required")
                return
            if not email:
                tk.messagebox.showerror("Error", "Email is required")
                return
            if not age_str:
                tk.messagebox.showerror("Error", "Age is required")
                return
            if not age_str.isdigit():
                tk.messagebox.showerror("Error", "Age must be a number")
                return
            age = int(age_str)
            if age < 13 or age > 120:
                tk.messagebox.showerror("Error", "Age must be between 13 and 120")
                return
            if not password:
                tk.messagebox.showerror("Error", "Password is required")
                return
            if password != confirm_password:
                tk.messagebox.showerror("Error", "Passwords do not match")
                return

            # Register user
            success, msg = self.auth_manager.register_user(name, email, age, gender, password)
            if success:
                tk.messagebox.showinfo("Success", "Account created successfully! You can now login.")
                signup_win.destroy()
            else:
                tk.messagebox.showerror("Registration Failed", msg)

        # Buttons
        button_frame = tk.Frame(signup_win, bg=self.app.colors["bg"])
        button_frame.pack(fill="x", padx=40, pady=20)

        tk.Button(button_frame, text="Create Account", command=do_signup,
                 font=("Segoe UI", 12, "bold"), bg=self.app.colors["primary"], fg="white",
                 width=20).pack()

        tk.Button(button_frame, text="Back to Login", command=signup_win.destroy,
                 font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                 bd=0, cursor="hand2").pack(pady=(10, 0))

    def _load_user_settings(self, username: str):
        """Load settings from DB for user"""
        try:
            from app.db import get_session
            from app.models import User

            session = get_session()
            user_obj = session.query(User).filter_by(username=username).first()
            if user_obj:
                self.app.current_user_id = int(user_obj.id)
                if user_obj.settings:
                    self.app.settings = {
                        "theme": user_obj.settings.theme,
                        "question_count": user_obj.settings.question_count,
                        "sound_enabled": user_obj.settings.sound_enabled
                    }
                    # Apply Theme immediately
                    if self.app.settings.get("theme"):
                        self.app.apply_theme(self.app.settings["theme"])
            session.close()
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")

    def start_login_flow(self):
        """Start the login flow"""
        self.app.root.after(100, self.show_login_screen)

    def _post_login_init(self):
        """Initialize UI after login"""
        if hasattr(self.app, 'sidebar'):
            self.app.sidebar.update_user_info()
            self.app.sidebar.pack(side="left", fill="y")
            self.app.sidebar.select_item("home")
        else:
            self.app.view_manager.switch_view("home")
