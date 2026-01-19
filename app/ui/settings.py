"""
Soul Sense Settings Module
Premium settings modal with modern controls
"""

import tkinter as tk
from tkinter import messagebox
from app.utils import save_settings


class SettingsManager:
    """Manages application settings with premium UI"""
    
    def __init__(self, app):
        self.app = app
        self.root = app.root
        
    def show_settings(self):
        """Show premium settings modal window"""
        colors = self.app.colors
        
        # Create modal window
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("Settings")
        self.settings_win.geometry("480x750")
        self.settings_win.resizable(False, False)
        self.settings_win.configure(bg=colors["bg"])
        
        # Center window on parent
        self.settings_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 750) // 2
        self.settings_win.geometry(f"+{x}+{y}")
        
        # Make modal
        self.settings_win.transient(self.root)
        self.settings_win.grab_set()
        
        # Header
        header_frame = tk.Frame(
            self.settings_win,
            bg=colors.get("primary", "#3B82F6"),
            height=70
        )
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(
            header_frame,
            text="⚙ Settings",
            font=self.app.ui_styles.get_font("xl", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        )
        header_label.pack(pady=20)
        
        # Content
        content_frame = tk.Frame(self.settings_win, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=25, pady=20)
        
        # Settings Sections
        self._create_question_count_section(content_frame, colors)
        self._create_theme_section(content_frame, colors)
        self._create_sound_section(content_frame, colors)
        self._create_experimental_section(content_frame, colors)
        
        # Action Buttons
        self._create_action_buttons(content_frame, colors)
    
    def _create_question_count_section(self, parent, colors):
        """Create question count setting section"""
        section = tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        section.pack(fill="x", pady=8)
        
        inner = tk.Frame(section, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=15, pady=12)
        
        # Label
        label = tk.Label(
            inner,
            text="Number of Questions",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        label.pack(anchor="w")
        
        desc = tk.Label(
            inner,
            text="How many questions to include in each assessment",
            font=self.app.ui_styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc.pack(anchor="w", pady=(2, 8))
        
        # Spinbox
        self.qcount_var = tk.IntVar(value=self.app.settings.get("question_count", 10))
        
        max_questions = 50
        if hasattr(self.app, 'total_questions_count'):
            max_questions = min(50, self.app.total_questions_count)
        
        spin_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        spin_frame.pack(anchor="w")
        
        spinbox = tk.Spinbox(
            spin_frame,
            from_=5,
            to=max_questions,
            textvariable=self.qcount_var,
            font=self.app.ui_styles.get_font("sm"),
            width=8,
            bg=colors.get("entry_bg", "#FFFFFF"),
            fg=colors.get("entry_fg", "#0F172A"),
            buttonbackground=colors.get("primary", "#3B82F6"),
            relief="flat",
            highlightthickness=1,
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightcolor=colors.get("primary", "#3B82F6")
        )
        spinbox.pack(side="left")
        
        questions_label = tk.Label(
            spin_frame,
            text="questions",
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        questions_label.pack(side="left", padx=8)
    
    def _create_theme_section(self, parent, colors):
        """Create theme selection section"""
        section = tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        section.pack(fill="x", pady=8)
        
        inner = tk.Frame(section, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=15, pady=12)
        
        # Label
        label = tk.Label(
            inner,
            text="Theme",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        label.pack(anchor="w")
        
        desc = tk.Label(
            inner,
            text="Choose your preferred color scheme",
            font=self.app.ui_styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc.pack(anchor="w", pady=(2, 8))
        
        # Theme Options
        self.theme_var = tk.StringVar(value=self.app.settings.get("theme", "light"))
        
        options_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        options_frame.pack(anchor="w")
        
        # Light Theme Button
        light_btn = tk.Radiobutton(
            options_frame,
            text="☀ Light",
            variable=self.theme_var,
            value="light",
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            selectcolor=colors.get("primary_light", "#DBEAFE"),
            activebackground=colors.get("surface", "#FFFFFF"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            indicatoron=True,
            padx=10
        )
        light_btn.pack(side="left", padx=(0, 15))
        
        # Dark Theme Button
        dark_btn = tk.Radiobutton(
            options_frame,
            text="🌙 Dark",
            variable=self.theme_var,
            value="dark",
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            selectcolor=colors.get("primary_light", "#DBEAFE"),
            activebackground=colors.get("surface", "#FFFFFF"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            indicatoron=True,
            padx=10
        )
        dark_btn.pack(side="left")
    
    def _create_sound_section(self, parent, colors):
        """Create sound effects toggle section"""
        section = tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        section.pack(fill="x", pady=8)
        
        inner = tk.Frame(section, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=15, pady=12)
        
        # Layout: Label on left, toggle on right
        left_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        left_frame.pack(side="left", fill="x", expand=True)
        
        label = tk.Label(
            left_frame,
            text="Sound Effects",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        label.pack(anchor="w")
        
        desc = tk.Label(
            left_frame,
            text="Enable audio feedback",
            font=self.app.ui_styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc.pack(anchor="w")
        
        # Toggle Checkbox
        self.sound_var = tk.BooleanVar(value=self.app.settings.get("sound_effects", True))
        
        toggle = tk.Checkbutton(
            inner,
            text="",
            variable=self.sound_var,
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("primary", "#3B82F6"),
            selectcolor=colors.get("success", "#10B981"),
            activebackground=colors.get("surface", "#FFFFFF"),
            activeforeground=colors.get("primary", "#3B82F6"),
            indicatoron=True,
            font=self.app.ui_styles.get_font("md"),
        )
        toggle.pack(side="right")
    
    def _create_experimental_section(self, parent, colors):
        """Create experimental features section showing feature flags"""
        try:
            from app.feature_flags import feature_flags
        except ImportError:
            return  # Feature flags not available
        
        section = tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("warning", "#F59E0B"),
            highlightthickness=2
        )
        section.pack(fill="x", pady=8)
        
        inner = tk.Frame(section, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=15, pady=12)
        
        # Header with experimental badge
        header_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        header_frame.pack(anchor="w", fill="x")
        
        label = tk.Label(
            header_frame,
            text="🧪 Experimental Features",
            font=("Segoe UI", 12, "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("warning", "#F59E0B")
        )
        label.pack(side="left")
        
        badge = tk.Label(
            header_frame,
            text="BETA",
            font=("Segoe UI", 8, "bold"),
            bg=colors.get("warning", "#F59E0B"),
            fg="#FFFFFF",
            padx=6,
            pady=2
        )
        badge.pack(side="left", padx=8)
        
        desc = tk.Label(
            inner,
            text="Enable cutting-edge features (may be unstable)",
            font=("Segoe UI", 10),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc.pack(anchor="w", pady=(2, 8))
        
        # Feature flags toggles
        self.flag_vars = {}
        flags_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        flags_frame.pack(anchor="w", fill="x")
        
        # Get all flags and their status
        for flag_name, flag in feature_flags.get_all_flags().items():
            is_enabled = feature_flags.is_enabled(flag_name)
            
            flag_row = tk.Frame(flags_frame, bg=colors.get("surface", "#FFFFFF"))
            flag_row.pack(anchor="w", fill="x", pady=2)
            
            # Status indicator
            status_color = colors.get("success", "#10B981") if is_enabled else colors.get("text_secondary", "#94A3B8")
            status_text = "●" if is_enabled else "○"
            
            status_label = tk.Label(
                flag_row,
                text=status_text,
                font=("Segoe UI", 12),
                bg=colors.get("surface", "#FFFFFF"),
                fg=status_color
            )
            status_label.pack(side="left")
            
            # Flag name
            name_label = tk.Label(
                flag_row,
                text=flag_name.replace("_", " ").title(),
                font=("Segoe UI", 10),
                bg=colors.get("surface", "#FFFFFF"),
                fg=colors.get("text_primary", "#0F172A")
            )
            name_label.pack(side="left", padx=(5, 10))
            
            # Status text
            status_text_label = tk.Label(
                flag_row,
                text="ON" if is_enabled else "OFF",
                font=("Segoe UI", 9, "bold"),
                bg=colors.get("surface", "#FFFFFF"),
                fg=status_color
            )
            status_text_label.pack(side="right")
        
        # Info note
        note = tk.Label(
            inner,
            text="💡 Set SOULSENSE_FF_* env vars or edit config.json to enable",
            font=("Segoe UI", 9, "italic"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#94A3B8")
        )
        note.pack(anchor="w", pady=(8, 0))
    
    def _create_action_buttons(self, parent, colors):
        """Create action buttons section"""
        btn_frame = tk.Frame(parent, bg=colors["bg"])
        btn_frame.pack(fill="x", pady=20)
        
        # Apply Button
        apply_btn = tk.Button(
            btn_frame,
            text="Apply Changes",
            command=self._apply_settings,
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("primary_hover", "#2563EB"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=14,
            pady=10,
            borderwidth=0
        )
        apply_btn.pack(side="left", padx=5)
        apply_btn.bind("<Enter>", lambda e: apply_btn.configure(bg=colors.get("primary_hover", "#2563EB")))
        apply_btn.bind("<Leave>", lambda e: apply_btn.configure(bg=colors.get("primary", "#3B82F6")))
        
        # Reset Button
        reset_btn = tk.Button(
            btn_frame,
            text="Reset",
            command=self._reset_defaults,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569"),
            activebackground=colors.get("surface_hover", "#F8FAFC"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            cursor="hand2",
            width=10,
            pady=8,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        reset_btn.pack(side="left", padx=5)
        reset_btn.bind("<Enter>", lambda e: reset_btn.configure(bg=colors.get("surface_hover", "#F8FAFC")))
        reset_btn.bind("<Leave>", lambda e: reset_btn.configure(bg=colors.get("surface", "#FFFFFF")))
        
        # Cancel Button
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self.settings_win.destroy,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("error", "#EF4444"),
            activebackground=colors.get("error_light", "#FEE2E2"),
            activeforeground=colors.get("error", "#EF4444"),
            relief="flat",
            cursor="hand2",
            width=10,
            pady=8,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        cancel_btn.pack(side="right", padx=5)
        cancel_btn.bind("<Enter>", lambda e: cancel_btn.configure(bg=colors.get("error_light", "#FEE2E2")))
        cancel_btn.bind("<Leave>", lambda e: cancel_btn.configure(bg=colors.get("surface", "#FFFFFF")))
    
    def _apply_settings(self):
        """Apply and save settings"""
        from app.validation import validate_range
        
        # Validation
        q_count = self.qcount_var.get()
        valid_q, msg_q = validate_range(q_count, 5, 50, "Question Count")
        if not valid_q:
            messagebox.showwarning("Invalid Settings", msg_q)
            return

        new_settings = {
            "question_count": q_count,
            "theme": self.theme_var.get(),
            "sound_effects": self.sound_var.get()
        }
        
        # Save settings
        self.app.settings.update(new_settings)
        
        saved_to_db = False
        if hasattr(self.app, 'current_user_id') and self.app.current_user_id:
            try:
                from app.db import update_user_settings
                update_user_settings(self.app.current_user_id, **new_settings)
                saved_to_db = True
            except Exception as e:
                print(f"Failed to save settings to DB: {e}")
        
        # Apply theme immediately
        self.app.apply_theme(new_settings["theme"])

        # Reload questions
        if hasattr(self.app, 'reload_questions'):
            self.app.reload_questions(new_settings["question_count"])
        
        messagebox.showinfo("Success", "Settings saved successfully!")
        self.settings_win.destroy()
        
        # Refresh welcome screen
        self.app.create_welcome_screen()
    
    def _reset_defaults(self):
        """Reset settings to defaults"""
        defaults = {
            "question_count": 10,
            "theme": "light",
            "sound_effects": True
        }
        
        self.qcount_var.set(defaults["question_count"])
        self.theme_var.set(defaults["theme"])
        self.sound_var.set(defaults["sound_effects"])
