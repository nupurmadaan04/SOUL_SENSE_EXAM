import tkinter as tk
from app import auth
from app.logger import get_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.main import SoulSenseApp

class PasswordStrengthMeter(tk.Frame):
    """A visual indicator for password strength."""
    def __init__(self, parent, colors, **kwargs):
        super().__init__(parent, bg=colors["bg"], **kwargs)
        self.colors = colors
        
        # Labels and segments container
        self.segments_frame = tk.Frame(self, bg=colors["bg"])
        self.segments_frame.pack(fill="x", pady=(5, 0))
        
        # 5 segments for 5 levels
        self.segments = []
        for _ in range(5):
            seg = tk.Frame(self.segments_frame, height=4, width=40, bg="#E0E0E0")
            seg.pack(side="left", padx=1, expand=True, fill="x")
            self.segments.append(seg)
            
        self.label = tk.Label(self, text="Password Strength", font=("Segoe UI", 9), 
                             bg=colors["bg"], fg=colors["text_secondary"])
        self.label.pack(anchor="w")

    def update_strength(self, password):
        score = 0
        if len(password) >= 8: score += 1
        if any(c.isupper() for c in password): score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(not c.isalnum() for c in password): score += 1
        
        # Colors: Gray, Red, Orange, Gold, YellowGreen, Green
        strength_colors = ["#E0E0E0", "#EF4444", "#F59E0B", "#FBBF24", "#84CC16", "#10B981"]
        strength_texts = ["Too Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
        
        color = strength_colors[score]
        text = strength_texts[score]
        
        # Update segments
        for i in range(5):
            if i < score:
                self.segments[i].configure(bg=color)
            else:
                self.segments[i].configure(bg="#E0E0E0")
                
        self.label.configure(text=f"Strength: {text}", fg=color if score > 0 else self.colors["text_secondary"])

class AppAuth:
    def __init__(self, app: 'SoulSenseApp'):
        self.app = app
        self.auth_manager = auth.AuthManager()
        self.logger = get_logger(__name__)
        self.start_login_flow()

    def show_login_screen(self):
        """Show login popup on startup"""
        login_win = tk.Toplevel(self.app.root)
        login_win.title("SoulSense Login")
        
        # Responsive sizing
        screen_width = login_win.winfo_screenwidth()
        screen_height = login_win.winfo_screenheight()
        window_width = min(400, int(screen_width * 0.3))
        window_height = min(520, int(screen_height * 0.5))
        
        login_win.geometry(f"{window_width}x{window_height}")
        login_win.minsize(350, 450)
        login_win.resizable(True, True)
        login_win.configure(bg=self.app.colors["bg"])
        login_win.transient(self.app.root)
        login_win.grab_set()

        # Prevent closing without login
        login_win.protocol("WM_DELETE_WINDOW", lambda: self.app.root.destroy())

        # Center
        login_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - window_width) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - window_height) // 2
        login_win.geometry(f"+{x}+{y}")

        # Logo/Title
        tk.Label(login_win, text="SoulSense AI", font=("Segoe UI", 24, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["primary"]).pack(pady=(40, 10))

        tk.Label(login_win, text="Login to continue", font=("Segoe UI", 12),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"]).pack(pady=(0, 30))

        # Form
        entry_frame = tk.Frame(login_win, bg=self.app.colors["bg"])
        entry_frame.pack(fill="x", padx=40)

        tk.Label(entry_frame, text="Email or Username", font=("Segoe UI", 10, "bold"),
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

            if not user or not pwd:
                tk.messagebox.showerror("Error", "Please enter username and password")
                return

            success, msg = self.auth_manager.login_user(user, pwd)
            if success:
                self.app.username = user
                self._load_user_settings(user)
                login_win.destroy()
                self._post_login_init()
            else:
                tk.messagebox.showerror("Login Failed", msg)

        def do_register():
            self.show_signup_screen()

        # Buttons
        tk.Button(login_win, text="Login", command=do_login,
                 font=("Segoe UI", 12, "bold"), bg=self.app.colors["primary"], fg="white",
                 width=20).pack(pady=10)
                 
        # Keyboard usability: Bind Enter to login
        login_win.bind("<Return>", lambda e: do_login())

        tk.Button(login_win, text="Create Account", command=do_register,
                 font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                 bd=0, cursor="hand2").pack()

    def show_signup_screen(self):
        """Show signup popup window"""
        signup_win = tk.Toplevel(self.app.root)
        signup_win.title("Create Account - SoulSense")
        
        # Responsive sizing
        screen_width = signup_win.winfo_screenwidth()
        screen_height = signup_win.winfo_screenheight()
        window_width = min(550, int(screen_width * 0.45))
        window_height = min(700, int(screen_height * 0.75))
        
        signup_win.geometry(f"{window_width}x{window_height}")
        signup_win.minsize(500, 700)
        signup_win.resizable(True, True)
        signup_win.configure(bg=self.app.colors["bg"])
        signup_win.transient(self.app.root)
        signup_win.grab_set()

        # Center the window
        signup_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - window_width) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - window_height) // 2
        signup_win.geometry(f"+{x}+{y}")

        # Header with gradient-like effect
        header_frame = tk.Frame(signup_win, bg=self.app.colors.get("primary", "#3B82F6"), height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # App icon/title in header
        title_label = tk.Label(header_frame, text="🧠 SoulSense AI", font=("Segoe UI", 18, "bold"),
                              bg=self.app.colors.get("primary", "#3B82F6"), fg="white")
        title_label.pack(pady=(15, 5))

        subtitle_label = tk.Label(header_frame, text="Create Your Account", font=("Segoe UI", 11),
                                 bg=self.app.colors.get("primary", "#3B82F6"), fg="white")
        subtitle_label.pack()

        # Main content area
        content_frame = tk.Frame(signup_win, bg=self.app.colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Welcome message
        welcome_label = tk.Label(content_frame, text="Join thousands of users discovering their emotional intelligence!",
                                font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"],
                                wraplength=window_width-60, justify="center")
        welcome_label.pack(pady=(0, 20))

        # Form container with subtle border (compact layout)
        form_container = tk.Frame(content_frame, bg=self.app.colors.get("surface", "#FFFFFF"),
                                 highlightbackground=self.app.colors.get("border", "#E2E8F0"),
                                 highlightthickness=1)
        form_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Form frame with grid layout for compact design (2 columns)
        form_frame = tk.Frame(form_container, bg=self.app.colors.get("surface", "#FFFFFF"))
        form_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # Configuration grid weights for responsive layout
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)

        # Row 0: First Name & Last Name
        fn_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        fn_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 8))
        tk.Label(fn_frame, text="👤 First Name", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        first_name_entry = tk.Entry(fn_frame, font=("Segoe UI", 10), bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        first_name_entry.pack(fill="x", ipady=4)

        ln_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        ln_frame.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=(0, 8))
        tk.Label(ln_frame, text="👥 Last Name", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        last_name_entry = tk.Entry(ln_frame, font=("Segoe UI", 10), bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        last_name_entry.pack(fill="x", ipady=4)

        # Row 1: Username & Email
        un_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        un_frame.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 8))
        tk.Label(un_frame, text="🏷️ Username", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        username_signup_entry = tk.Entry(un_frame, font=("Segoe UI", 10), bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        username_signup_entry.pack(fill="x", ipady=4)

        em_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        em_frame.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=(0, 8))
        tk.Label(em_frame, text="📧 Email", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        email_entry = tk.Entry(em_frame, font=("Segoe UI", 10), bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        email_entry.pack(fill="x", ipady=4)

        # Row 2: Age & Gender
        ag_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        ag_frame.grid(row=2, column=0, sticky="ew", padx=(0, 5), pady=(0, 8))
        tk.Label(ag_frame, text="🎂 Age", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        age_entry = tk.Entry(ag_frame, font=("Segoe UI", 10), bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        age_entry.pack(fill="x", ipady=4)

        ge_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        ge_frame.grid(row=2, column=1, sticky="ew", padx=(5, 0), pady=(0, 8))
        tk.Label(ge_frame, text="⚧ Gender", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        gender_var = tk.StringVar(value="Prefer not to say")
        gender_options = ["Male", "Female", "Other", "Prefer not to say"]
        gender_menu = tk.OptionMenu(ge_frame, gender_var, *gender_options)
        gender_menu.config(font=("Segoe UI", 10), bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", bd=0)
        gender_menu.pack(fill="x", ipady=2)

        # Row 3: Password (spans both)
        pw_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        pw_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        tk.Label(pw_frame, text="🔒 Password", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        password_entry = tk.Entry(pw_frame, font=("Segoe UI", 10), show="*", bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        password_entry.pack(fill="x", ipady=4)

        # Row 4: Confirm Password (spans both)
        cp_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        cp_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        tk.Label(cp_frame, text="🔒 Confirm Password", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        confirm_password_entry = tk.Entry(cp_frame, font=("Segoe UI", 10), show="*", bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        confirm_password_entry.pack(fill="x", ipady=4)
        
        # Show Password for Confirm Password field
        show_confirm_var = tk.BooleanVar()
        def toggle_confirm_visibility():
            show_char = "" if show_confirm_var.get() else "*"
            confirm_password_entry.config(show=show_char)
        
        show_confirm_cb = tk.Checkbutton(cp_frame, text="👁 Show Password", variable=show_confirm_var,
                                        command=toggle_confirm_visibility, font=("Segoe UI", 8),
                                        bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_secondary"],
                                        activebackground=self.app.colors.get("surface", "#FFFFFF"),
                                        activeforeground=self.app.colors["text_primary"],
                                        selectcolor=self.app.colors.get("primary", "#3B82F6"))
        show_confirm_cb.pack(anchor="w")

        # Terms and Conditions (Parity with Web)
        terms_var = tk.BooleanVar(value=True)
        terms_cb = tk.Checkbutton(form_frame, text="I accept the Terms and Conditions", variable=terms_var,
                                 font=("Segoe UI", 9), bg=self.app.colors.get("surface", "#FFFFFF"),
                                 fg=self.app.colors["text_secondary"], activebackground=self.app.colors.get("surface", "#FFFFFF"))
        terms_cb.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 10))

        def do_signup():
            first_name = first_name_entry.get().strip()
            last_name = last_name_entry.get().strip()
            username = username_signup_entry.get().strip()
            email = email_entry.get().strip()
            age_str = age_entry.get().strip()
            gender = gender_var.get()
            password = password_entry.get()
            confirm_password = confirm_password_entry.get()

            # Validations
            if not terms_var.get():
                tk.messagebox.showerror("Error", "You must accept the Terms and Conditions")
                return
            if not first_name:
                tk.messagebox.showerror("Error", "First name is required")
                return
            if not username:
                tk.messagebox.showerror("Error", "Username is required")
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
            success, msg = self.auth_manager.register_user(username, email, first_name, last_name, age, gender, password)
            if success:
                tk.messagebox.showinfo("Success", "Account created successfully! You can now login.")
                signup_win.destroy()
            else:
                tk.messagebox.showerror("Registration Failed", msg)

        # Buttons with modern styling
        button_frame = tk.Frame(content_frame, bg=self.app.colors["bg"])
        button_frame.pack(fill="x", padx=20, pady=20)

        # Create Account button with hover effects
        create_btn = tk.Button(button_frame, text="🚀 Create Account", command=do_signup,
                              font=("Segoe UI", 12, "bold"), bg=self.app.colors.get("primary", "#3B82F6"),
                              fg="white", relief="flat", cursor="hand2", width=20, pady=8,
                              activebackground=self.app.colors.get("primary_hover", "#2563EB"),
                              activeforeground="white", borderwidth=0)
        create_btn.pack()
        
        # Add hover effect
        def on_enter_create(e):
            create_btn.config(bg=self.app.colors.get("primary_hover", "#2563EB"))
        def on_leave_create(e):
            create_btn.config(bg=self.app.colors.get("primary", "#3B82F6"))
        
        create_btn.bind("<Enter>", on_enter_create)
        create_btn.bind("<Leave>", on_leave_create)

        # Keyboard usability: Bind Enter to signup
        signup_win.bind("<Return>", lambda e: do_signup())

        # Back to Login button
        back_btn = tk.Button(button_frame, text="← Back to Login", command=signup_win.destroy,
                            font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"],
                            bd=0, cursor="hand2", activeforeground=self.app.colors["primary"])
        back_btn.pack(pady=(15, 0))
        
        # Add hover effect for back button
        def on_enter_back(e):
            back_btn.config(fg=self.app.colors["primary"])
        def on_leave_back(e):
            back_btn.config(fg=self.app.colors["text_secondary"])
        
        back_btn.bind("<Enter>", on_enter_back)
        back_btn.bind("<Leave>", on_leave_back)

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
        
        # Phase 0.2: Onboarding check - Delay by 3s to avoid SQLite lock contention with sidebar loading
        self.app.root.after(3000, self._check_onboarding_completion)

    def _check_onboarding_completion(self):
        """Prompt user to complete profile if missing key data."""
        try:
            from app.services.profile_service import ProfileService
            user = ProfileService.get_user_profile(self.app.username)
            if user and user.personal_profile:
                pp = user.personal_profile
                if not pp.first_name or not pp.email:
                    tk.messagebox.showinfo(
                        "Complete Your Profile",
                        f"Welcome {self.app.username}!\n\n"
                        "Please complete your profile (First Name and Email) in the Profile settings to unlock all features."
                    )
        except Exception as e:
            self.logger.error(f"Onboarding check failed: {e}")
