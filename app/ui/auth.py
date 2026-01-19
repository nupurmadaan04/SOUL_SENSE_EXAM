"""
Soul Sense Auth/Welcome Screen Module
Premium UI with modern aesthetics
"""

import tkinter as tk
from tkinter import ttk
import logging
import random
from typing import Any, Optional, Callable
from app.constants import (
    FONT_FAMILY_PRIMARY, FONT_SIZE_XS, FONT_SIZE_SM, FONT_SIZE_MD, 
    FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_XXL, FONT_SIZE_HERO
)


class AuthManager:
    """Manages authentication and welcome screens with premium styling"""
    
    def __init__(self, app: Any) -> None:
        self.app = app
        self.root = app.root
        self.styles = app.ui_styles

    def create_welcome_screen(self) -> None:
        """Create premium welcome screen with hero section and cards"""
        self.app.clear_screen()
        
        colors = self.app.colors
        
        # Main container with gradient-like effect (using frame layers)
        main_container = tk.Frame(self.root, bg=colors["bg"])
        main_container.pack(fill="both", expand=True)
        
        # Hero Section (top gradient area)
        hero_frame = tk.Frame(
            main_container, 
            bg=colors.get("primary", "#3B82F6"),
            height=150
        )
        hero_frame.pack(fill="x")
        hero_frame.pack_propagate(False)
        
        # App Title in Hero
        title_label = tk.Label(
            hero_frame,
            text="Soul Sense",
            font=self.styles.get_font("hero", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        )
        title_label.pack(pady=(40, 5))
        
        # Subtitle
        subtitle_label = tk.Label(
            hero_frame,
            text="Emotional Intelligence Assessment",
            font=self.styles.get_font("md"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        )
        subtitle_label.pack()
        
        # Content Frame (below hero)
        content_frame = tk.Frame(main_container, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Welcome Card
        welcome_card = tk.Frame(
            content_frame,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        welcome_card.pack(fill="x", pady=10)
        
        # Card Inner Padding
        card_inner = tk.Frame(welcome_card, bg=colors.get("surface", "#FFFFFF"))
        card_inner.pack(fill="x", padx=20, pady=15)
        
        intro_text = (
            "Discover your emotional intelligence through science-backed assessment. "
            "Answer honestly — there are no right or wrong answers."
        )
        
        intro_label = tk.Label(
            card_inner,
            text=intro_text,
            font=self.styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569"),
            wraplength=500,
            justify="center"
        )
        intro_label.pack()
        
        # Tips Section (if available)
        if hasattr(self.app, 'tips') and self.app.tips:
            tip_frame = tk.Frame(
                content_frame,
                bg=colors.get("primary_light", "#DBEAFE"),
                highlightbackground=colors.get("primary", "#3B82F6"),
                highlightthickness=1
            )
            tip_frame.pack(fill="x", pady=10)
            
            tip_inner = tk.Frame(tip_frame, bg=colors.get("primary_light", "#DBEAFE"))
            tip_inner.pack(fill="x", padx=15, pady=10)
            
            tip_label = tk.Label(
                tip_inner,
                text=f"💡 {random.choice(self.app.tips)}",
                font=self.styles.get_font("sm", "italic"),
                bg=colors.get("primary_light", "#DBEAFE"),
                fg=colors.get("text_primary", "#0F172A"),
                wraplength=480
            )
            tip_label.pack()
        
        # Action Buttons Section
        buttons_frame = tk.Frame(content_frame, bg=colors["bg"])
        buttons_frame.pack(pady=20)
        
        # Primary Action: Start Assessment
        start_btn = tk.Button(
            buttons_frame,
            text="\u25b6  Start Assessment",
            command=self.app.on_start_test_click,
            font=self.styles.get_font("md", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("primary_hover", "#2563EB"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=22,
            pady=12,
            borderwidth=0
        )
        start_btn.pack(pady=8)
        start_btn.bind("<Enter>", lambda e: start_btn.configure(bg=colors.get("primary_hover", "#2563EB")))
        start_btn.bind("<Leave>", lambda e: start_btn.configure(bg=colors.get("primary", "#3B82F6")))
        
        # Secondary Actions Row
        secondary_frame = tk.Frame(buttons_frame, bg=colors["bg"])
        secondary_frame.pack(pady=5)
        
        # Journal Button
        journal_btn = tk.Button(
            secondary_frame,
            text="\U0001f4d6 Journal",
            command=self.app.open_journal_flow,
            font=self.styles.get_font("sm"),
            bg=colors.get("success", "#10B981"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("success_hover", "#059669"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=14,
            pady=8,
            borderwidth=0
        )
        journal_btn.pack(side="left", padx=5)
        journal_btn.bind("<Enter>", lambda e: journal_btn.configure(bg=colors.get("success_hover", "#059669")))
        journal_btn.bind("<Leave>", lambda e: journal_btn.configure(bg=colors.get("success", "#10B981")))
        
        # Dashboard Button
        dashboard_btn = tk.Button(
            secondary_frame,
            text="\U0001f4ca Dashboard",
            command=self.app.open_dashboard_flow,
            font=self.styles.get_font("sm"),
            bg=colors.get("secondary", "#8B5CF6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("secondary_hover", "#7C3AED"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=14,
            pady=8,
            borderwidth=0
        )
        dashboard_btn.pack(side="left", padx=5)
        dashboard_btn.bind("<Leave>", lambda e: dashboard_btn.configure(bg=colors.get("secondary", "#8B5CF6")))
        
        # Profile Button (New)
        profile_btn = tk.Button(
            secondary_frame,
            text="👤 Profile",
            command=self.app.open_profile_flow,
            font=self.styles.get_font("sm"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("primary_hover", "#2563EB"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=14,
            pady=8,
            borderwidth=0
        )
        profile_btn.pack(side="left", padx=5)
        profile_btn.bind("<Enter>", lambda e: profile_btn.configure(bg=colors.get("primary_hover", "#2563EB")))
        profile_btn.bind("<Leave>", lambda e: profile_btn.configure(bg=colors.get("primary", "#3B82F6")))
        
        # Tertiary Actions Row
        tertiary_frame = tk.Frame(buttons_frame, bg=colors["bg"])
        tertiary_frame.pack(pady=5)
        
        # History Button
        history_btn = tk.Button(
            tertiary_frame,
            text="History",
            command=self.app.show_history_screen,
            font=self.styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569"),
            activebackground=colors.get("surface_hover", "#F8FAFC"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            cursor="hand2",
            width=10,
            pady=6,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        history_btn.pack(side="left", padx=4)
        history_btn.bind("<Enter>", lambda e: history_btn.configure(bg=colors.get("surface_hover", "#F8FAFC")))
        history_btn.bind("<Leave>", lambda e: history_btn.configure(bg=colors.get("surface", "#FFFFFF")))
        
        # Settings Button
        settings_btn = tk.Button(
            tertiary_frame,
            text="\u2699 Settings",
            command=self.app.show_settings,
            font=self.styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569"),
            activebackground=colors.get("surface_hover", "#F8FAFC"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            cursor="hand2",
            width=10,
            pady=6,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        settings_btn.pack(side="left", padx=4)
        settings_btn.bind("<Enter>", lambda e: settings_btn.configure(bg=colors.get("surface_hover", "#F8FAFC")))
        settings_btn.bind("<Leave>", lambda e: settings_btn.configure(bg=colors.get("surface", "#FFFFFF")))
        
        # Exit Button
        exit_btn = tk.Button(
            tertiary_frame,
            text="Exit",
            command=self.app.force_exit,
            font=self.styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("error", "#EF4444"),
            activebackground=colors.get("error_light", "#FEE2E2"),
            activeforeground=colors.get("error", "#EF4444"),
            relief="flat",
            cursor="hand2",
            width=8,
            pady=6,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        exit_btn.pack(side="left", padx=4)
        exit_btn.bind("<Enter>", lambda e: exit_btn.configure(bg=colors.get("error_light", "#FEE2E2")))
        exit_btn.bind("<Leave>", lambda e: exit_btn.configure(bg=colors.get("surface", "#FFFFFF")))

    def create_username_screen(self, callback: Optional[Callable[[], None]] = None) -> None:
        """Create premium username input screen"""
        self.app.clear_screen()
        self.callback = callback  # Store callback for post-login action
        
        colors = self.app.colors
        
        # Main container
        main_frame = tk.Frame(self.root, bg=colors["bg"])
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=colors.get("primary", "#3B82F6"), height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(
            header_frame,
            text="Let's Get Started",
            font=self.styles.get_font("xl", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        )
        header_label.pack(pady=25)
        
        # Content
        content_frame = tk.Frame(main_frame, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=60, pady=30)
        
        # Form Card
        form_card = tk.Frame(
            content_frame,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        form_card.pack(fill="x", pady=10)
        
        form_inner = tk.Frame(form_card, bg=colors.get("surface", "#FFFFFF"))
        form_inner.pack(fill="x", padx=30, pady=25)
        
        # Username Field
        username_label = tk.Label(
            form_inner,
            text="Your Name",
            font=self.styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        username_label.pack(anchor="w", pady=(0, 5))
        
        self.username_entry = tk.Entry(
            form_inner,
            font=self.styles.get_font("md"),
            bg=colors.get("entry_bg", "#FFFFFF"),
            fg=colors.get("entry_fg", "#0F172A"),
            insertbackground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            highlightthickness=2,
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightcolor=colors.get("primary", "#3B82F6")
        )
        self.username_entry.pack(fill="x", pady=(0, 15), ipady=8)
        
        # Age Field
        age_label = tk.Label(
            form_inner,
            text="Your Age",
            font=self.styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        age_label.pack(anchor="w", pady=(10, 5))
        
        self.age_entry = tk.Entry(
            form_inner,
            font=self.styles.get_font("md"),
            bg=colors.get("entry_bg", "#FFFFFF"),
            fg=colors.get("entry_fg", "#0F172A"),
            insertbackground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            highlightthickness=2,
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightcolor=colors.get("primary", "#3B82F6")
        )
        self.age_entry.pack(fill="x", pady=(0, 15), ipady=8)
        
        # Profession Field
        profession_label = tk.Label(
            form_inner,
            text="Profession (Optional)",
            font=self.styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        profession_label.pack(anchor="w", pady=(10, 5))
        
        # Profession Field (Dropdown)
        professions = ["Student", "Engineer", "Teacher", "Doctor", "Artist", "Manager", "Other"]
        self.profession_entry = ttk.Combobox(
            form_inner,
            values=professions,
            font=self.styles.get_font("sm"),
            state="readonly"
        )
        self.profession_entry.pack(fill="x", pady=(0, 20), ipady=4)
        self.profession_entry.set("Student") # Default
        
        # Buttons
        buttons_frame = tk.Frame(content_frame, bg=colors["bg"])
        buttons_frame.pack(pady=15)
        
        # Continue Button
        action_text = "Login & Return" if callback else "Start Test →"
        continue_btn = tk.Button(
            buttons_frame,
            text=action_text,
            command=self.submit_user_info,
            font=self.styles.get_font("md", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("primary_hover", "#2563EB"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=20,
            pady=10,
            borderwidth=0
        )
        continue_btn.pack(side="left", padx=5)
        continue_btn.bind("<Enter>", lambda e: continue_btn.configure(bg=colors.get("primary_hover", "#2563EB")))
        continue_btn.bind("<Leave>", lambda e: continue_btn.configure(bg=colors.get("primary", "#3B82F6")))
        
        # Back Button
        back_btn = tk.Button(
            buttons_frame,
            text="← Back",
            command=self.app.create_welcome_screen,
            font=self.styles.get_font("sm"),
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
        back_btn.pack(side="left", padx=5)
        back_btn.bind("<Enter>", lambda e: back_btn.configure(bg=colors.get("surface_hover", "#F8FAFC")))
        back_btn.bind("<Leave>", lambda e: back_btn.configure(bg=colors.get("surface", "#FFFFFF")))
        
        # Focus on username field
        self.username_entry.focus()
        
        # Apply validation limits
        from app.validation import MAX_USERNAME_LENGTH, MAX_AGE_LENGTH
        from app.ui.validation_ui import setup_entry_limit
        setup_entry_limit(self.username_entry, MAX_USERNAME_LENGTH)
        setup_entry_limit(self.age_entry, MAX_AGE_LENGTH)

    def submit_user_info(self) -> None:
        """Validate and submit user info"""
        from app.utils import compute_age_group
        from tkinter import messagebox
        from app.validation import validate_required, validate_age, sanitize_text
        
        # Sanitize entries
        username = sanitize_text(self.username_entry.get())
        age_str = sanitize_text(self.age_entry.get())
        profession = sanitize_text(self.profession_entry.get())
        
        # Validation
        valid_name, msg_name = validate_required(username, "Name")
        if not valid_name:
            messagebox.showwarning("Missing Information", msg_name)
            return

        valid_age, msg_age = validate_age(age_str)
        if not valid_age:
            messagebox.showwarning("Invalid Age", msg_age)
            return
        
        age = int(age_str) # Safe now
        
        # Store user info
        self.app.username = username
        self.app.age = age
        self.app.age_group = compute_age_group(age)
        self.app.profession = profession if profession else "Not specified"
        
        logging.info(
            f"Session started | user={username} | age={age} | "
            f"age_group={self.app.age_group} | profession={self.app.profession} | "
            f"questions={len(self.app.questions)}"
        )
        
        # Check/Create User in DB for Settings Persistence
        try:
            from app.db import safe_db_context
            from app.models import User
            from datetime import datetime
            
            with safe_db_context() as session:
                user = session.query(User).filter_by(username=username).first()
                
                if not user:
                    # Implicit Registration
                    user = User(
                        username=username,
                        password_hash="guest_access", 
                        created_at=datetime.utcnow().isoformat(),
                        last_login=datetime.utcnow().isoformat()
                    )
                    session.add(user)
                    # safe_db_context will commit on exit
                    logging.info(f"Created new user for settings: {username}")
                    
                    # RESET SETTINGS FOR NEW USER (As requested)
                    # Ensure we start with defaults
                    # Note: load_user_settings will load from DB, which are defaults for new user. 
                    # Guest settings in self.app.settings will be overwritten. This is CORRECT.
                    
                else:
                    user.last_login = datetime.utcnow().isoformat()
                    # safe_db_context will commit on exit
                
                # Flush to get ID if new
                session.flush()
                # Load User Settings (Applies Theme etc)
                self.app.load_user_settings(user.id)
            
        except Exception as e:
            logging.error(f"Failed to load user settings: {e}")

        # Navigate
        if hasattr(self, 'callback') and self.callback:
            self.callback()
        else:
            self.app.start_test()
