import tkinter as tk
from tkinter import messagebox as tmb
from app import auth
from app.auth import session_storage
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
        from app.validation import is_weak_password
        
        score = 0
        if len(password) >= 8: score += 1
        if any(c.isupper() for c in password): score += 1
        if any(c.islower() for c in password): score += 1
        if any(c.isdigit() for c in password): score += 1
        if any(not c.isalnum() for c in password): score += 1
        
        # Override: if password is in the weak/common list, cap strength at 1
        is_common = password and is_weak_password(password)
        if is_common:
            score = min(score, 1)
        
        # Colors: Gray, Red, Orange, Gold, YellowGreen, Green
        strength_colors = ["#E0E0E0", "#EF4444", "#F59E0B", "#FBBF24", "#84CC16", "#10B981"]
        strength_texts = ["Too Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
        
        color = strength_colors[score]
        text = strength_texts[score]
        if is_common:
            text = "Weak - Common Password"
        
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

    def _secure_password_entry(self, entry_widget):
        """
        SECURITY HARDENING:
        Prevents Copy, Paste, Cut, and Right-Click Context Menu on password fields.
        """
        def block_event(event):
            return "break"

        # Block Ctrl+C, Ctrl+V, Ctrl+X
        entry_widget.bind("<Control-c>", block_event)
        entry_widget.bind("<Control-v>", block_event)
        entry_widget.bind("<Control-x>", block_event)
        
        # Block Right Click (Button-3 on Windows/Linux, Button-2 on some Macs)
        entry_widget.bind("<Button-3>", block_event) 
        entry_widget.bind("<Button-2>", block_event)

    def show_login_screen(self):
        """Show login popup on startup"""
        import requests
        import uuid
        
        # Fetch CAPTCHA
        captcha_code = ""
        session_id = ""
        try:
            response = requests.get('http://localhost:8000/api/v1/auth/captcha', timeout=5)
            if response.status_code == 200:
                data = response.json()
                captcha_code = data.get('captcha_code', '')
                session_id = data.get('session_id', '')
        except Exception as e:
            self.logger.error(f"Failed to fetch CAPTCHA: {e}")
            captcha_code = "ERROR"
            session_id = str(uuid.uuid4())
        
        login_win = tk.Toplevel(self.app.root)
        self.login_window = login_win # Store reference for other methods
        login_win.title("SoulSense Login")
        
        # Responsive sizing
        screen_width = login_win.winfo_screenwidth()
        screen_height = login_win.winfo_screenheight()
        window_width = min(400, int(screen_width * 0.3))
        window_height = min(600, int(screen_height * 0.6)) # Increased height
        
        login_win.geometry(f"{window_width}x{window_height}")
        login_win.minsize(350, 550) # Increased min height from 450 to 550
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
        username_entry.pack(fill="x", pady=(5, 5))
        
        # Email validation error label for login (only shows for email-like input)
        login_email_error_label = tk.Label(entry_frame, text="", font=("Segoe UI", 8), 
                                           bg=self.app.colors["bg"], fg="#EF4444")
        login_email_error_label.pack(anchor="w", pady=(0, 2))
        
        # Email domain suggestion label (Issue #617)
        login_email_suggestion_label = tk.Label(entry_frame, text="", font=("Segoe UI", 8, "italic"), 
                                                bg=self.app.colors["bg"], fg="#3B82F6")
        login_email_suggestion_label.pack(anchor="w", pady=(0, 5))
        
        # Real-time email validation for login (only if input looks like an email)
        def validate_login_email_realtime(event=None):
            from app.validation import validate_email_strict, suggest_email_domain
            identifier = username_entry.get().strip()
            # Only validate if it looks like an email (contains @)
            if '@' in identifier:
                is_valid, error_msg = validate_email_strict(identifier)
                if is_valid:
                    login_email_error_label.config(text="")
                else:
                    login_email_error_label.config(text=error_msg)
                
                # Check for domain suggestions (Issue #617)
                suggestion = suggest_email_domain(identifier)
                if suggestion:
                    login_email_suggestion_label.config(text=f"💡 Did you mean {suggestion}?")
                else:
                    login_email_suggestion_label.config(text="")
            else:
                login_email_error_label.config(text="")
                login_email_suggestion_label.config(text="")
        
        username_entry.bind("<KeyRelease>", validate_login_email_realtime)
        username_entry.bind("<FocusOut>", validate_login_email_realtime)


        tk.Label(entry_frame, text="Password", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w")
        password_entry = tk.Entry(entry_frame, font=("Segoe UI", 12), show="*")
        password_entry.pack(fill="x", pady=(5, 5))

        # Check Caps Lock Function
        def check_caps_lock(event):
            # On Windows, bit 0 (0x0001) is Shift, bit 1 (0x0002) is Caps Lock.
            # However, event.state behaves differently across OS. 
            # Reliable method for Windows/Linux usually involves checking the state bitmask.
            # Caps Lock bit is typically 0x0002.
            
            # Note: For KeyRelease event, the state might be lagging or different depending on exact key.
            # But generally checking specific bit works.
            
            # ALSO: event.keycode 20 is Caps Lock key itself.
            
            # Simple heuristic for Tkinter:
            if event.keysym == 'Caps_Lock':
                # If the key pressed IS Caps Lock, we might need to assume it TOGGLED state.
                # But event.state reflects state BEFORE the key press usually.
                # Actually, worst case we can't be 100% sure without ctypes on Windows, 
                # but standard practice is checking event.state & 0x0002.
                pass 
                
            try:
                # 0x2 is Caps Lock on most systems (Windows/Linux/Mac)
                is_caps = (int(event.state) & 0x0002) != 0
                
                # If the event itself is Caps_Lock press, the state might be inverted in this event context?
                # Let's rely on the state bit.
                
                if is_caps:
                     self.caps_warning_label.pack(anchor="w", pady=(0, 5))
                else:
                     self.caps_warning_label.pack_forget()
            except Exception:
                pass


        password_entry.bind("<KeyPress>", check_caps_lock)
        password_entry.bind("<KeyRelease>", check_caps_lock)
        password_entry.bind("<FocusIn>", check_caps_lock)
        password_entry.bind("<FocusOut>", lambda e: self.caps_warning_label.pack_forget())

        
        # Password error label for empty password feedback
        login_password_error_label = tk.Label(entry_frame, text="", font=("Segoe UI", 8), 
                                              bg=self.app.colors["bg"], fg="#EF4444")
        login_password_error_label.pack(anchor="w", pady=(0, 2)) # Reduced padding

        # Caps Lock Warning Label
        self.caps_warning_label = tk.Label(entry_frame, text="⚠️ Caps Lock is ON", font=("Segoe UI", 8, "bold"), 
                                      bg=self.app.colors["bg"], fg="#F59E0B")
        # Do not pack initially, or pack hidden. Better to pack_forget initially.
        # But for layout stability, maybe pack it and set text empty? 
        # Requirement says "Hide warning when Caps Lock is OFF". 
        # I'll use pack normally but manage visibility via pack/pack_forget or config text.
        # Let's use config text="" to keep layout simpler or pack_forget to save space. 
        # Given "Show/Hide", I will use pack_forget/pack.


        # --- APPLY SECURITY HARDENING (Login) ---
        self._secure_password_entry(password_entry)

        # CAPTCHA Section
        tk.Label(entry_frame, text="CAPTCHA Verification", font=("Segoe UI", 10, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w", pady=(10, 5))
        
        captcha_frame = tk.Frame(entry_frame, bg=self.app.colors["bg"])
        captcha_frame.pack(fill="x", pady=(0, 5))
        
        captcha_display = tk.Label(captcha_frame, text=captcha_code, font=("Courier", 16, "bold"),
                                  bg="#F3F4F6", fg="#1F2937", relief="solid", width=8)
        captcha_display.pack(side="left", padx=(0, 5))
        
        def refresh_captcha():
            nonlocal captcha_code, session_id
            try:
                response = requests.get('http://localhost:8000/api/v1/auth/captcha', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    captcha_code = data.get('captcha_code', '')
                    session_id = data.get('session_id', '')
                    captcha_display.config(text=captcha_code)
                    captcha_entry.delete(0, tk.END)
            except Exception as e:
                self.logger.error(f"Failed to refresh CAPTCHA: {e}")
        
        refresh_btn = tk.Button(captcha_frame, text="🔄", command=refresh_captcha,
                               font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["text_primary"])
        refresh_btn.pack(side="left")
        
        captcha_entry = tk.Entry(entry_frame, font=("Segoe UI", 12))
        captcha_entry.pack(fill="x", pady=(5, 5))
        
        captcha_error_label = tk.Label(entry_frame, text="", font=("Segoe UI", 8), 
                                      bg=self.app.colors["bg"], fg="#EF4444")
        captcha_error_label.pack(anchor="w", pady=(0, 5))

        # Show Password checkbox
        show_password_var = tk.BooleanVar()
        def toggle_password_visibility():
            show_char = "" if show_password_var.get() else "*"
            password_entry.config(show=show_char)

        show_password_cb = tk.Checkbutton(entry_frame, text="Show Password", variable=show_password_var,
                                         command=toggle_password_visibility, font=("Segoe UI", 10),
                                         bg=self.app.colors["bg"], fg=self.app.colors["text_primary"])
        show_password_cb.pack(anchor="w", pady=(0, 5))

        # Remember Me checkbox
        remember_me_var = tk.BooleanVar()
        remember_me_cb = tk.Checkbutton(entry_frame, text="Remember me", variable=remember_me_var,
                                       font=("Segoe UI", 10),
                                       bg=self.app.colors["bg"], fg=self.app.colors["text_primary"])
        remember_me_cb.pack(anchor="w", pady=(0, 10))

        # Rate Limit Warning Label (Issue #565)
        rate_limit_label = tk.Label(entry_frame, text="", font=("Segoe UI", 9, "bold"), 
                                    bg=self.app.colors["bg"], fg="#EF4444")
        rate_limit_label.pack(anchor="w", pady=(0, 5))
        
        # Track countdown timer ID for cleanup
        self._rate_limit_timer_id = None
        
        def update_countdown(remaining_seconds, login_btn):
            """Update countdown timer every second."""
            if remaining_seconds > 0:
                rate_limit_label.config(text=f"⏳ Too many attempts. Please wait {remaining_seconds} seconds...")
                login_btn.config(state="disabled", bg="#9CA3AF")
                self._rate_limit_timer_id = login_win.after(1000, lambda: update_countdown(remaining_seconds - 1, login_btn))
            else:
                # Countdown finished - re-enable login
                rate_limit_label.config(text="")
                login_btn.config(state="normal", bg=self.app.colors["primary"])
                self._rate_limit_timer_id = None

        def do_login(event=None):
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()
            captcha_input = captcha_entry.get().strip()
            
            # Clear previous error messages
            login_email_error_label.config(text="")
            login_password_error_label.config(text="")
            captcha_error_label.config(text="")
            
            # Field-specific validation with inline errors
            has_error = False
            if not user:
                login_email_error_label.config(text="Email or Username is required")
                username_entry.focus_set()
                has_error = True
            if not pwd:
                login_password_error_label.config(text="Password is required")
                if not has_error:
                    password_entry.focus_set()
                has_error = True
            if not captcha_input:
                captcha_error_label.config(text="CAPTCHA is required")
                if not has_error:
                    captcha_entry.focus_set()
                has_error = True
            
            if has_error:
                return

            # Validate CAPTCHA and login via backend API
            try:
                response = requests.post('http://localhost:8000/api/v1/auth/login', 
                                       json={
                                           'identifier': user,
                                           'password': pwd,
                                           'captcha_input': captcha_input,
                                           'session_id': session_id
                                       }, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    # Store token for session management
                    self.session_token = data.get('access_token')
                    self.app.username = user
                    # Save session if Remember Me is checked
                    session_storage.save_session(user, remember_me_var.get())
                    self._load_user_settings(user)
                    login_win.destroy()
                    self._post_login_init()
                elif response.status_code == 401:
                    error_data = response.json()
                    code = error_data.get('detail', {}).get('code')
                    if code == 'AUTH003':
                        captcha_error_label.config(text="Invalid CAPTCHA. Please try again!")
                        refresh_captcha()  # Regenerate CAPTCHA
                    else:
                        tmb.showerror("Login Failed", error_data.get('detail', {}).get('message', 'Invalid credentials'))
                else:
                    error_data = response.json()
                    tmb.showerror("Login Failed", error_data.get('detail', {}).get('message', 'Login failed'))
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Login request failed: {e}")
                # Fallback to local auth if backend is unavailable
                success, msg, err_code = self.auth_manager.login_user(user, pwd)
                
                if success:
                    self.app.username = user
                    # Save session if Remember Me is checked
                    session_storage.save_session(user, remember_me_var.get())
                    self._load_user_settings(user)
                    login_win.destroy()
                    self._post_login_init()
                elif err_code == "AUTH_2FA_REQUIRED":
                    # 2FA Required
                    self.show_2fa_login_dialog(user, login_win)
                elif err_code == "AUTH002":
                    # Rate limit exceeded - show countdown
                    remaining = self.auth_manager.get_lockout_remaining_seconds(user)
                    if remaining > 0:
                        update_countdown(remaining, login_btn)
                    else:
                        rate_limit_label.config(text="⏳ Too many attempts. Please wait and try again.")
                else:
                    tmb.showerror("Login Failed", msg)

        # Added this function for the Esc key
        def clear_fields(event=None):
            username_entry.delete(0, tk.END)
            password_entry.delete(0, tk.END)
            username_entry.focus_set()        

        def do_register():
            self.show_signup_screen()

        # Buttons - store reference for rate limit control
        login_btn = tk.Button(login_win, text="Login", command=do_login,
                 font=("Segoe UI", 12, "bold"), bg=self.app.colors["primary"], fg="white",
                 width=20)
        login_btn.pack(pady=10)
                 
        # Keyboard usability: Bind Enter to login
        login_win.bind("<Return>", lambda e: do_login())
        self.login_window.bind("<Return>", lambda e: do_login()) # Changed login_win to self.login_window

        tk.Button(self.login_window, text="Create Account", command=do_register, # Changed login_win to self.login_window
                 font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                 bd=0, cursor="hand2").pack()
        # --- BIND KEYS TO ACTIONS ---
        self.login_window.bind('<Return>', do_login)   # Enter Key -> Logs in # Changed login_win to self.login_window
        self.login_window.bind('<Escape>', clear_fields) # Esc Key -> Clears text # Changed login_win to self.login_window

        # Forgot Password button
        tk.Button(self.login_window, text="Forgot Password?", command=self.show_forgot_password,
                 font=("Segoe UI", 9), bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"],
                 bd=0, cursor="hand2").pack(pady=(5, 0))

    def show_forgot_password(self):
        """Show Forgot Password Dialog"""
        if hasattr(self, 'login_window') and self.login_window:
            self.login_window.destroy()
            
        fp_window = tk.Toplevel(self.app.root)
        fp_window.title("Reset Password")
        fp_window.geometry("400x300")
        fp_window.configure(bg=self.app.colors["bg"])
        
        # Center the window
        screen_width = fp_window.winfo_screenwidth()
        screen_height = fp_window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        fp_window.geometry(f"400x300+{x}+{y}")
        
        # UI Elements
        tk.Label(fp_window, text="Forgot Password", font=("Segoe UI", 16, "bold"), 
                bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(pady=20)
                
        tk.Label(fp_window, text="Enter your email address to receive a reset code.", 
                font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"]).pack(pady=(0, 20))
        
        email_var = tk.StringVar()
        tk.Label(fp_window, text="Email", font=("Segoe UI", 10, "bold"), 
                bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w", padx=40)
        email_entry = tk.Entry(fp_window, textvariable=email_var, font=("Segoe UI", 10), width=30)
        email_entry.pack(pady=5)
        email_entry.focus()
        
        def on_send():
            email = email_var.get()
            if not email:
                tmb.showerror("Error", "Please enter your email.")
                return
                
            success, msg = self.auth_manager.initiate_password_reset(email)
            if success:
                tmb.showinfo("Success", msg)
                fp_window.destroy()
                self.show_verify_otp(email)
            else:
                tmb.showerror("Error", msg)
        
        tk.Button(fp_window, text="Send Code", command=on_send, 
                 bg=self.app.colors["primary"], fg="white", font=("Segoe UI", 10, "bold"), 
                 padx=20, pady=5, relief="flat").pack(pady=20)
                 
        # Back to Login
        tk.Button(fp_window, text="Back to Login", 
                 command=lambda: [fp_window.destroy(), self.show_login_screen()],
                 bg=self.app.colors["bg"], fg=self.app.colors["primary"], 
                 font=("Segoe UI", 9), relief="flat", cursor="hand2").pack()

    def show_verify_otp(self, email):
        """Show OTP Verification Dialog"""
        otp_window = tk.Toplevel(self.app.root)
        otp_window.title("Verify Code")
        otp_window.geometry("400x380")
        otp_window.configure(bg=self.app.colors["bg"])
        
        # Center
        screen_width = otp_window.winfo_screenwidth()
        screen_height = otp_window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 380) // 2
        otp_window.geometry(f"400x380+{x}+{y}")
        
        tk.Label(otp_window, text="Enter Verification Code", font=("Segoe UI", 14, "bold"), 
                bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(pady=20)
                
        tk.Label(otp_window, text=f"Code sent to {email}", 
                font=("Segoe UI", 9), bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"]).pack(pady=(0, 20))
        
        code_var = tk.StringVar()
        entry = tk.Entry(otp_window, textvariable=code_var, font=("Segoe UI", 14), width=10, justify="center")
        entry.pack(pady=10)
        
        # Attempts counter label
        attempts_label = tk.Label(otp_window, text="3 attempts remaining", font=("Segoe UI", 9),
                                  bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"])
        attempts_label.pack(pady=(0, 5))
        
        def update_attempts_label():
            """Update the attempts label based on remaining attempts."""
            try:
                from app.db import get_session
                from app.models import User, PersonalProfile
                from app.auth.otp_manager import OTPManager
                session = get_session()
                # Find user by email
                profile = session.query(PersonalProfile).filter_by(email=email.lower().strip()).first()
                if profile:
                    user = session.query(User).filter_by(id=profile.user_id).first()
                    if user:
                        remaining = OTPManager.get_remaining_attempts(user.id, "RESET_PASSWORD", db_session=session)
                        if remaining > 0:
                            attempts_label.config(text=f"{remaining} attempt(s) remaining", fg="#F59E0B")
                        else:
                            attempts_label.config(text="Code locked - Please resend", fg="#EF4444")
                            entry.config(state="disabled")
                    else:
                        pass
                else:
                    pass
                session.close()
            except Exception:
                pass
        
        def on_verify():
            code = code_var.get().strip()
            if len(code) != 6 or not code.isdigit():
                tmb.showerror("Error", "Code must be 6 numeric digits.")
                return
            
            # Verify OTP before proceeding
            try:
                from app.db import get_session
                from app.models import User, PersonalProfile
                from app.auth.otp_manager import OTPManager
                session = get_session()
                # Find user by email
                profile = session.query(PersonalProfile).filter_by(email=email.lower().strip()).first()
                if not profile:
                    tmb.showerror("Error", "Invalid request.", parent=otp_window)
                    session.close()
                    return
                
                user = session.query(User).filter_by(id=profile.user_id).first()
                if not user:
                    tmb.showerror("Error", "Invalid request.", parent=otp_window)
                    session.close()
                    return
                
                # Check if OTP is locked first
                is_locked, lock_msg = OTPManager.is_otp_locked(user.id, "RESET_PASSWORD", db_session=session)
                if is_locked:
                    tmb.showerror("Code Locked", lock_msg, parent=otp_window)
                    update_attempts_label()
                    session.close()
                    return
                
                # Verify the OTP
                success, verify_msg = OTPManager.verify_otp(user.id, code, "RESET_PASSWORD", db_session=session)
                session.close()
                
                if success:
                    otp_window.destroy()
                    self.show_reset_password_dialog(email, code)
                else:
                    tmb.showerror("Verification Failed", verify_msg, parent=otp_window)
                    update_attempts_label()
                    
            except Exception as e:
                tmb.showerror("Error", f"Verification error: {e}", parent=otp_window)

        tk.Button(otp_window, text="Verify", command=on_verify, 
                 bg=self.app.colors["primary"], fg="white", font=("Segoe UI", 10, "bold"), 
                 padx=20, pady=5).pack(pady=(15, 5))

        # --- Resend OTP with Cooldown ---
        resend_frame = tk.Frame(otp_window, bg=self.app.colors["bg"])
        resend_frame.pack(pady=(5, 5))

        cooldown_label = tk.Label(resend_frame, text="", font=("Segoe UI", 9),
                                  bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"])
        cooldown_label.pack()

        resend_btn = tk.Button(resend_frame, text="Resend Code", font=("Segoe UI", 9, "bold"),
                               bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                               relief="flat", cursor="hand2")
        resend_btn.pack(pady=(2, 0))

        _resend_timer_id = [None]

        def start_cooldown(seconds):
            """Disable resend button and show countdown."""
            if seconds > 0:
                resend_btn.config(state="disabled", fg="#9CA3AF", cursor="arrow")
                cooldown_label.config(text=f"Resend available in {seconds}s")
                _resend_timer_id[0] = otp_window.after(1000, lambda: start_cooldown(seconds - 1))
            else:
                resend_btn.config(state="normal", fg=self.app.colors["primary"], cursor="hand2")
                cooldown_label.config(text="Didn't receive a code?")
                _resend_timer_id[0] = None

        def on_resend():
            success, msg = self.auth_manager.initiate_password_reset(email)
            if success:
                tmb.showinfo("Code Sent", "A new verification code has been sent.", parent=otp_window)
                start_cooldown(60)
            else:
                tmb.showerror("Error", msg, parent=otp_window)

        resend_btn.config(command=on_resend)

        # Start with cooldown active (OTP was just sent)
        start_cooldown(60)
                 
        # Change Email option
        tk.Button(otp_window, text="Change Email", 
                 command=lambda: [otp_window.destroy(), self.show_forgot_password()],
                 bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                 font=("Segoe UI", 9), relief="flat", cursor="hand2").pack(pady=(5, 10))

    def show_reset_password_dialog(self, email, code):
        """Show New Password Dialog"""
        reset_window = tk.Toplevel(self.app.root)
        reset_window.title("Set New Password")
        reset_window.geometry("400x400")
        reset_window.configure(bg=self.app.colors["bg"])
        
        # Center
        screen_width = reset_window.winfo_screenwidth()
        screen_height = reset_window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 400) // 2
        reset_window.geometry(f"400x400+{x}+{y}")
        
        tk.Label(reset_window, text="New Password", font=("Segoe UI", 16, "bold"), 
                bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(pady=20)
        
        pass_var = tk.StringVar()
        tk.Label(reset_window, text="Password", font=("Segoe UI", 10, "bold"), 
                bg=self.app.colors["bg"], fg=self.app.colors["text_primary"]).pack(anchor="w", padx=40)
        pass_entry = tk.Entry(reset_window, textvariable=pass_var, show="•", font=("Segoe UI", 10), width=30)
        pass_entry.pack(pady=5)
        
        # Reuse meter
        meter = PasswordStrengthMeter(reset_window, self.app.colors)
        meter.pack(padx=40, pady=5, fill="x")
        
        def check_strength(*args):
            meter.update_strength(pass_var.get())
        pass_var.trace("w", check_strength)
        
        def on_reset():
            new_pass = pass_var.get()
            success, msg = self.auth_manager.complete_password_reset(email, code, new_pass)
            if success:
                tmb.showinfo("Success", msg)
                reset_window.destroy()
                self.show_login_screen()
            else:
                tmb.showerror("Error", msg)
                # If code is invalid, might need to restart flow
                if "expired" in msg.lower():
                    reset_window.destroy()
                    self.show_forgot_password()

        tk.Button(reset_window, text="Set Password", command=on_reset, 
                 bg=self.app.colors["primary"], fg="white", font=("Segoe UI", 10, "bold"), 
                 padx=20, pady=5).pack(pady=20)

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
        
        # Email validation error label
        email_error_label = tk.Label(em_frame, text="", font=("Segoe UI", 8), 
                                     bg=self.app.colors.get("surface", "#FFFFFF"), fg="#EF4444")
        email_error_label.pack(anchor="w")
        
        # Email domain suggestion label (Issue #617)
        email_suggestion_label = tk.Label(em_frame, text="", font=("Segoe UI", 8, "italic"), 
                                          bg=self.app.colors.get("surface", "#FFFFFF"), fg="#3B82F6")
        email_suggestion_label.pack(anchor="w")
        
        # Real-time email validation function
        def validate_email_realtime(event=None):
            from app.validation import validate_email_strict, suggest_email_domain
            email = email_entry.get().strip()
            if not email:
                email_error_label.config(text="")
                email_suggestion_label.config(text="")
                email_entry.config(highlightbackground=self.app.colors.get("border", "#E2E8F0"), highlightcolor=self.app.colors.get("border", "#E2E8F0"))
                return
            is_valid, error_msg = validate_email_strict(email)
            if is_valid:
                email_error_label.config(text="")
                email_entry.config(highlightbackground="#10B981", highlightcolor="#10B981")
            else:
                email_error_label.config(text=error_msg)
                email_entry.config(highlightbackground="#EF4444", highlightcolor="#EF4444")
            
            # Check for domain suggestions (Issue #617)
            suggestion = suggest_email_domain(email)
            if suggestion:
                email_suggestion_label.config(text=f"💡 Did you mean {suggestion}?")
            else:
                email_suggestion_label.config(text="")
        
        # Bind validation to key release and focus out events
        email_entry.bind("<KeyRelease>", validate_email_realtime)
        email_entry.bind("<FocusOut>", validate_email_realtime)


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
        gender_options = ["M", "F", "Other", "Prefer not to say"]
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

        # --- APPLY SECURITY HARDENING (Signup) ---
        self._secure_password_entry(password_entry)

        # Row 4: Confirm Password (spans both)
        cp_frame = tk.Frame(form_frame, bg=self.app.colors.get("surface", "#FFFFFF"))
        cp_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        tk.Label(cp_frame, text="🔒 Confirm Password", font=("Segoe UI", 9, "bold"),
                 bg=self.app.colors.get("surface", "#FFFFFF"), fg=self.app.colors["text_primary"]).pack(anchor="w")
        confirm_password_entry = tk.Entry(cp_frame, font=("Segoe UI", 10), show="*", bg=self.app.colors.get("entry_bg", "#F8FAFC"), relief="flat", highlightthickness=1)
        confirm_password_entry.pack(fill="x", ipady=4)
        
        # --- APPLY SECURITY HARDENING (Confirm Signup) ---
        self._secure_password_entry(confirm_password_entry)

        # Password mismatch inline error label
        password_mismatch_label = tk.Label(cp_frame, text="", font=("Segoe UI", 8), 
                                           bg=self.app.colors.get("surface", "#FFFFFF"), fg="#EF4444")
        password_mismatch_label.pack(anchor="w")
        
        # Real-time password match validation
        def validate_password_match_realtime(event=None):
            pwd = password_entry.get()
            confirm_pwd = confirm_password_entry.get()
            if not confirm_pwd:
                password_mismatch_label.config(text="")
                confirm_password_entry.config(highlightbackground=self.app.colors.get("border", "#E2E8F0"), highlightcolor=self.app.colors.get("border", "#E2E8F0"))
            elif pwd == confirm_pwd:
                password_mismatch_label.config(text="")
                confirm_password_entry.config(highlightbackground="#10B981", highlightcolor="#10B981")
            else:
                password_mismatch_label.config(text="Passwords do not match")
                confirm_password_entry.config(highlightbackground="#EF4444", highlightcolor="#EF4444")
        
        confirm_password_entry.bind("<KeyRelease>", validate_password_match_realtime)
        confirm_password_entry.bind("<FocusOut>", validate_password_match_realtime)
        password_entry.bind("<KeyRelease>", validate_password_match_realtime)
        
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
                email_entry.focus_set()
                return
            # Strict email validation
            from app.validation import validate_email_strict
            email_valid, email_error = validate_email_strict(email)
            if not email_valid:
                tk.messagebox.showerror("Error", email_error)
                email_entry.focus_set()
                return
            if not age_str:
                tmb.showerror("Error", "Age is required")
                return
            if not age_str.isdigit():
                tmb.showerror("Error", "Age must be a number")
                return
            age = int(age_str)
            if age < 13 or age > 120:
                tmb.showerror("Error", "Age must be between 13 and 120")
                return
            if not password:
                tmb.showerror("Error", "Password is required")
                return
            # Block weak/common passwords
            from app.validation import is_weak_password
            if is_weak_password(password):
                tmb.showerror("Error", "This password is too common. Please choose a stronger password.")
                password_entry.focus_set()
                return
            if password != confirm_password:
                tmb.showerror("Error", "Passwords do not match")
                return

            # Register user
            success, msg, _ = self.auth_manager.register_user(username, email, first_name, last_name, age, gender, password)
            if success:
                tmb.showinfo("Success", "Account created successfully! You can now login.")
                signup_win.destroy()
            else:
                tmb.showerror("Registration Failed", msg)

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
        """Start the login flow - check for saved session first"""
        # Check for saved session (Remember Me)
        saved_username = session_storage.get_saved_username()
        if saved_username:
            # Auto-login with saved session
            self.logger.info(f"Auto-login with saved session for: {saved_username}")
            self.app.username = saved_username
            self.auth_manager.current_user = saved_username
            self._load_user_settings(saved_username)
            self.app.root.after(100, self._post_login_init)
        else:
            # Show login screen
            self.app.root.after(100, self.show_login_screen)

    def _post_login_init(self):
        """Initialize UI after login"""
        # PR 2: Start idle monitoring
        if hasattr(self.app, 'start_idle_watch'):
            self.app.start_idle_watch()
            
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

    def show_2fa_login_dialog(self, username, parent_window):
        """Show OTP dialog for 2FA login"""
        try:
           parent_window.withdraw() # Hide login window
        except: pass

        dialog = tk.Toplevel(self.app.root)
        dialog.title("2FA Verification")
        dialog.geometry("350x340")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # Center
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - 350) // 2
        y = (screen_height - 340) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Two-Factor Authentication", font=("Segoe UI", 12, "bold"), pady=15).pack()
        tk.Label(dialog, text=f"Enter the verification code sent to your\nemail associated with {username}", 
                 justify="center", fg="#666").pack(pady=(0, 15))
        
        code_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=code_var, font=("Segoe UI", 14), justify="center", width=10)
        entry.pack(pady=5)
        entry.focus()
        
        # Attempts counter label
        attempts_label = tk.Label(dialog, text="3 attempts remaining", font=("Segoe UI", 9), fg="#666")
        attempts_label.pack(pady=(0, 5))
        
        def update_attempts_label():
            """Update the attempts label based on remaining attempts."""
            try:
                from app.db import get_session
                from app.models import User
                session = get_session()
                user = session.query(User).filter_by(username=username).first()
                if user:
                    from app.auth.otp_manager import OTPManager
                    remaining = OTPManager.get_remaining_attempts(user.id, "LOGIN_CHALLENGE", db_session=session)
                    if remaining > 0:
                        attempts_label.config(text=f"{remaining} attempt(s) remaining", fg="#F59E0B")
                    else:
                        attempts_label.config(text="Code locked - Please resend", fg="#EF4444")
                        entry.config(state="disabled")
                session.close()
            except Exception:
                pass
        
        def on_verify(event=None):
            code = code_var.get().strip()
            if len(code) != 6 or not code.isdigit():
                tmb.showerror("Error", "Code must be 6 numeric digits", parent=dialog)
                return
                
            success, msg, _ = self.auth_manager.verify_2fa_login(username, code)
            
            if success:
                self.app.username = username
                self.auth_manager.current_user = username
                self._load_user_settings(username)
                
                dialog.destroy()
                try:
                    parent_window.destroy()
                except: pass
                
                self._post_login_init()
            else:
                tmb.showerror("Verification Failed", msg, parent=dialog)
                update_attempts_label()
                
        def on_cancel():
            dialog.destroy()
            try:
                parent_window.deiconify() # Show login window again
            except: 
                self.show_login_screen()

        tk.Button(dialog, text="Verify", command=on_verify, 
                 bg=self.app.colors["primary"], fg="white", font=("Segoe UI", 10, "bold"), 
                 padx=20, pady=5).pack(pady=(10, 5))

        # --- Resend OTP with Cooldown ---
        resend_frame = tk.Frame(dialog, bg=dialog.cget("bg"))
        resend_frame.pack(pady=(5, 5))

        cooldown_label = tk.Label(resend_frame, text="", font=("Segoe UI", 9), fg="#666",
                                  bg=dialog.cget("bg"))
        cooldown_label.pack()

        resend_btn = tk.Button(resend_frame, text="Resend Code", font=("Segoe UI", 9, "bold"),
                               bg=dialog.cget("bg"), fg=self.app.colors["primary"],
                               relief="flat", cursor="hand2")
        resend_btn.pack(pady=(2, 0))

        _resend_timer_id = [None]

        def start_cooldown(seconds):
            """Disable resend button and show countdown."""
            if seconds > 0:
                resend_btn.config(state="disabled", fg="#9CA3AF", cursor="arrow")
                cooldown_label.config(text=f"Resend available in {seconds}s")
                _resend_timer_id[0] = dialog.after(1000, lambda: start_cooldown(seconds - 1))
            else:
                resend_btn.config(state="normal", fg=self.app.colors["primary"], cursor="hand2")
                cooldown_label.config(text="Didn't receive a code?")
                _resend_timer_id[0] = None

        def on_resend():
            success, msg = self.auth_manager.resend_2fa_login_otp(username)
            if success:
                tmb.showinfo("Code Sent", msg, parent=dialog)
                start_cooldown(60)
            else:
                tmb.showerror("Error", msg, parent=dialog)

        resend_btn.config(command=on_resend)

        # Start with cooldown active (OTP was just sent during login)
        start_cooldown(60)
                 
        tk.Button(dialog, text="Cancel", command=on_cancel, relief="flat", fg="#666").pack(pady=(5, 0))
        
        dialog.bind("<Return>", on_verify)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
