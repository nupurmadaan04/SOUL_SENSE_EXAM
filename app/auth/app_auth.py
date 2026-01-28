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

    def show_login_screen(self):
        """Show login popup on startup"""
        login_win = tk.Toplevel(self.app.root)
        login_win.title("SoulSense Login")
        login_win.geometry("400x500")
        login_win.configure(bg=self.app.colors["bg"])
        login_win.transient(self.app.root)
        login_win.grab_set()

        # Prevent closing without login
        login_win.protocol("WM_DELETE_WINDOW", lambda: self.app.root.destroy())

        # Center
        login_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 400) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 500) // 2
        login_win.geometry(f"+{x}+{y}")

        # Logo/Title
        tk.Label(login_win, text="SoulSense AI", font=("Segoe UI", 24, "bold"),
                 bg=self.app.colors["bg"], fg=self.app.colors["primary"]).pack(pady=(40, 10))

        tk.Label(login_win, text="Login to continue", font=("Segoe UI", 12),
                 bg=self.app.colors["bg"], fg=self.app.colors["text_secondary"]).pack(pady=(0, 30))

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
        password_entry.pack(fill="x", pady=(5, 20))

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
            user = username_entry.get().strip()
            pwd = password_entry.get().strip()

            if not user or not pwd:
                tk.messagebox.showerror("Error", "Please enter username and password")
                return

            success, msg = self.auth_manager.register_user(user, pwd)
            if success:
                tk.messagebox.showinfo("Success", "Account created! You can now login.")
            else:
                tk.messagebox.showerror("Registration Failed", msg)

        # Buttons
        tk.Button(login_win, text="Login", command=do_login,
                 font=("Segoe UI", 12, "bold"), bg=self.app.colors["primary"], fg="white",
                 width=20).pack(pady=10)

        tk.Button(login_win, text="Create Account", command=do_register,
                 font=("Segoe UI", 10), bg=self.app.colors["bg"], fg=self.app.colors["primary"],
                 bd=0, cursor="hand2").pack()

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

    def _post_login_init(self):
        """Initialize UI after login"""
        if hasattr(self.app, 'sidebar'):
            self.app.sidebar.update_user_info()
            self.app.sidebar.pack(side="left", fill="y")
            self.app.sidebar.select_item("home")
        else:
            self.app.view_manager.switch_view("home")
