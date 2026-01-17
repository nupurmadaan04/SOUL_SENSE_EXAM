import tkinter as tk
from typing import Any, Optional, Dict, List
from tkinter import ttk, messagebox, simpledialog
import logging
import json
from datetime import datetime
from app.models import get_session, MedicalProfile, User, PersonalProfile, UserStrengths
# from app.ui.styles import ApplyTheme # Not needed
from app.ui.sidebar import SidebarNav
from app.models import get_session, MedicalProfile, User, PersonalProfile, UserStrengths
from app.ui.sidebar import SidebarNav
from app.ui.components.timeline import LifeTimeline
from app.ui.components.tag_input import TagInput
from tkcalendar import DateEntry
from app.ui.settings import SettingsManager
from app.validation import (
    sanitize_text, validate_email, validate_phone, 
    validate_length, validate_required, validate_dob,
    MAX_TEXT_LENGTH, MAX_ENTRY_LENGTH
)

class UserProfileView:
    def __init__(self, parent_root: tk.Widget, app_instance: Any) -> None:
        self.parent_root = parent_root
        self.app = app_instance
        self.i18n = app_instance.i18n
        self.colors = app_instance.colors
        
        # Embedded View Setup
        # self.window was Toplevel, now we use parent_root (which is content_area)
        self.window = parent_root 
        
        # Main Layout Container
        # Force background to match main theme
        self.main_container = tk.Frame(self.window, bg=self.colors.get("bg"))
        self.main_container.pack(fill="both", expand=True)
        
        # --- LEFT SIDEBAR ---
        self.sidebar = SidebarNav(
            self.main_container, 
            self.app,
        items=[
                {"id": "back", "icon": "←", "label": "Back to Home"},
                {"id": "overview", "icon": "👤", "label": "Overview"},  # Phase 53: New default
                {"id": "medical", "icon": "🏥", "label": self.i18n.get("profile.tab_medical")},
                {"id": "history", "icon": "📜", "label": "Personal History"},
                {"id": "strengths", "icon": "💪", "label": "Strengths & Goals"},
                {"id": "export", "icon": "📤", "label": "Data Export"},
                {"id": "settings", "icon": "⚙️", "label": "Settings"},
            ],
            on_change=self.on_nav_change
        )
        self.sidebar.pack(side="left", fill="y")
        
        # --- RIGHT CONTENT AREA ---
        self.content_area = tk.Frame(self.main_container, bg=self.colors.get("bg"))
        self.content_area.pack(side="left", fill="both", expand=True, padx=30, pady=0)
        
        # Header (Top of Content Area)
        self.header_label = tk.Label(
            self.content_area,
            text="Profile",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors.get("bg"),
            fg=self.colors.get("text_primary")
        )
        self.header_label.pack(anchor="w", pady=(0, 20))
        
        # Content Dynamic Frame with Scrollbar
        container_frame = tk.Frame(self.content_area, bg=self.colors.get("bg"))
        container_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container_frame, bg=self.colors.get("bg"), highlightthickness=0)
        
        # User requested hidden scrollbars but functional scrolling
        self.scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=self.canvas.yview)
        # self.scrollbar.pack(side="right", fill="y") # HIDDEN as requested
        
        self.view_container = tk.Frame(self.canvas, bg=self.colors.get("bg"))
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.view_container, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Ensure inner frame expands to fill width
        def _on_canvas_configure(event):
            # Update the inner frame's width to fill the canvas
            self.canvas.itemconfig(self.canvas_window, width=event.width)
            
        self.canvas.bind("<Configure>", _on_canvas_configure)
        
        # Update scrollregion when content changes
        def _on_frame_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        self.view_container.bind("<Configure>", _on_frame_configure)
        
        # Smart Scroll: Support mousewheel, touchpad on Windows
        def _on_mousewheel(event):
            if self.canvas.winfo_exists():
                # Always try to scroll - Tkinter handles the boundaries automatically
                # Windows uses event.delta
                if hasattr(event, 'delta') and event.delta:
                    # precision touchpads may return small deltas < 120
                    # ensure we scroll at least 1 unit
                    if abs(event.delta) < 120:
                        scroll_amount = -1 if event.delta > 0 else 1
                    else:
                        scroll_amount = int(-1 * (event.delta / 120))
                    self.canvas.yview_scroll(scroll_amount, "units")
                
                # Linux uses Button-4 (up) and Button-5 (down)
                elif hasattr(event, 'num'):
                    if event.num == 4:
                        self.canvas.yview_scroll(-3, "units")
                    elif event.num == 5:
                        self.canvas.yview_scroll(3, "units")
        
        # Bind scroll globally to window so it works even when hovering over child widgets
        # Note: 'add=True' appends binding to existing ones
        self.window.bind_all("<MouseWheel>", _on_mousewheel)
        self.window.bind_all("<Button-4>", _on_mousewheel)  # Linux
        self.window.bind_all("<Button-5>", _on_mousewheel)  # Linux
        
        # Also bind directly to canvas and view_container
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.view_container.bind("<MouseWheel>", _on_mousewheel)
        
        # Views Cache
        self.views = {}
        
        # Initialize default view (Phase 53: Overview as default)
        self.sidebar.select_item("overview")

    def center_window(self) -> None:
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def on_nav_change(self, view_id: str) -> None:
        # Clear current view
        for widget in self.view_container.winfo_children():
            widget.destroy()
            
        # FORCE SCROLL RESET: Reset to top
        self.canvas.yview_moveto(0)
            
        if view_id == "back":
            self.app.switch_view("home")
            return

        if view_id == "overview":
            self.header_label.configure(text="Profile Overview")
            self._render_overview_view()
        elif view_id == "medical":
            self.header_label.configure(text=self.i18n.get("profile.header", name=self.app.username))
            self._render_medical_view()
        elif view_id == "history":
            self.header_label.configure(text="Personal History")
            self._render_history_view()
        elif view_id == "strengths":
            self.header_label.configure(text="Strengths & Goals")
            self._render_strengths_view()
        elif view_id == "export":
            self.header_label.configure(text="Data Export")
            self._render_export_view()
        elif view_id == "settings":
            self.header_label.configure(text="Account Settings")
            self._render_settings_view(self.view_container)

    # ==========================
    # 0. OVERVIEW VIEW (Phase 53: Profile Redesign - Medical Dashboard Style)
    # ==========================
    def _render_overview_view(self):
        """Render the modern medical dashboard-style overview."""
        from datetime import datetime
        
        # Teal accent color (like reference)
        ACCENT = "#009688"  # Teal
        
        # Main 2-Column Layout (Left: Profile Card | Right: Stats Cards)
        # Use pack instead of weight-based grid to allow natural height overflow for scrolling
        main_frame = tk.Frame(self.view_container, bg=self.colors.get("bg"))
        main_frame.pack(fill="x", padx=15, pady=10)  # fill="x" not "both" to allow height overflow
        main_frame.columnconfigure(0, weight=3)  # Left takes more space
        main_frame.columnconfigure(1, weight=2)
        # Don't set rowconfigure weight - let rows have natural height
        
        # Load all data upfront
        user_data = self._load_user_overview_data()
        
        # =====================
        # LEFT COLUMN - ROW 0: PROFILE CARD
        # =====================
        profile_card = tk.Frame(
            main_frame, bg=self.colors.get("card_bg"),
            highlightbackground=self.colors.get("card_border", "#E0E0E0"),
            highlightthickness=1
        )
        profile_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        
        # Profile card inner layout
        profile_inner = tk.Frame(profile_card, bg=self.colors.get("card_bg"))
        profile_inner.pack(fill="both", expand=True, padx=25, pady=20)
        profile_inner.columnconfigure(0, weight=1)  # Avatar + Info
        profile_inner.columnconfigure(1, weight=1)  # Contact Details
        
        # --- Left side: Avatar + Name + Info Grid ---
        left_profile = tk.Frame(profile_inner, bg=self.colors.get("card_bg"))
        left_profile.grid(row=0, column=0, sticky="nsew")
        
        # Circular Avatar using Canvas for true circle
        avatar_size = 110
        avatar_canvas = tk.Canvas(
            left_profile, width=avatar_size, height=avatar_size,
            bg=self.colors.get("card_bg"), highlightthickness=0, cursor="hand2"
        )
        avatar_canvas.pack(anchor="w", pady=(0, 15))
        
        # Draw circular background
        avatar_canvas.create_oval(2, 2, avatar_size-2, avatar_size-2, fill=ACCENT, outline=ACCENT, width=0)
        
        # Try to load actual profile photo
        avatar_path = user_data.get("avatar_path")
        photo_loaded = False
        
        if avatar_path:
            try:
                from PIL import Image, ImageTk, ImageDraw
                import os
                
                if os.path.exists(avatar_path):
                    # Load and resize image
                    img = Image.open(avatar_path)
                    
                    # Center crop to square
                    min_dim = min(img.width, img.height)
                    left = (img.width - min_dim) // 2
                    top = (img.height - min_dim) // 2
                    img = img.crop((left, top, left + min_dim, top + min_dim))
                    
                    # Resize to avatar size
                    img = img.resize((avatar_size - 4, avatar_size - 4), Image.Resampling.LANCZOS)
                    
                    # Create circular mask
                    mask = Image.new("L", (avatar_size - 4, avatar_size - 4), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, avatar_size - 5, avatar_size - 5), fill=255)
                    
                    # Apply mask for circular appearance
                    output = Image.new("RGBA", (avatar_size - 4, avatar_size - 4), (0, 0, 0, 0))
                    output.paste(img.convert("RGBA"), (0, 0))
                    output.putalpha(mask)
                    
                    # Convert to PhotoImage and display on canvas
                    self.avatar_photo = ImageTk.PhotoImage(output)
                    avatar_canvas.create_image(avatar_size//2, avatar_size//2, image=self.avatar_photo, anchor="center")
                    photo_loaded = True
            except Exception as e:
                logging.warning(f"Could not load profile photo: {e}")
        
        # Fallback: Show initial letter if no photo
        if not photo_loaded:
            initial = user_data.get("username", "?")[0].upper()
            avatar_canvas.create_text(
                avatar_size//2, avatar_size//2,
                text=initial, font=("Segoe UI", 42, "bold"),
                fill="white", anchor="center"
            )
        
        # Camera icon (small circle in corner)
        cam_size = 28
        cam_x, cam_y = avatar_size - 18, avatar_size - 18
        avatar_canvas.create_oval(cam_x - cam_size//2, cam_y - cam_size//2, 
                                  cam_x + cam_size//2, cam_y + cam_size//2,
                                  fill="white", outline="#E0E0E0", width=1)
        avatar_canvas.create_text(cam_x, cam_y, text="📷", font=("Segoe UI", 10), anchor="center")
        
        # Bind click on entire canvas to upload
        avatar_canvas.bind("<Button-1>", lambda e: self._upload_profile_photo())
        
        # Name
        tk.Label(
            left_profile, text=user_data.get("username", "User"),
            font=("Segoe UI", 22, "bold"),
            bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")
        ).pack(anchor="w")
        
        # Subtitle (Occupation or "Soul Sense Member")
        subtitle = user_data.get("occupation") or "Soul Sense Member"
        tk.Label(
            left_profile, text=subtitle,
            font=("Segoe UI", 11), bg=self.colors.get("card_bg"), fg=ACCENT
        ).pack(anchor="w", pady=(0, 15))
        
        # Info Grid (DOB, Age, Gender in 2x2)
        info_grid = tk.Frame(left_profile, bg=self.colors.get("card_bg"))
        info_grid.pack(anchor="w", fill="x")
        
        self._create_mini_stat(info_grid, "DOB", user_data.get("dob", "--"), 0, 0)
        self._create_mini_stat(info_grid, "Age", user_data.get("age", "--"), 0, 1)
        self._create_mini_stat(info_grid, "Gender", user_data.get("gender", "--"), 1, 0)
        self._create_mini_stat(info_grid, "Member Since", user_data.get("member_since", "--"), 1, 1)
        
        # Edit Profile Button
        edit_btn = tk.Button(
            left_profile, text="✏️ EDIT PROFILE",
            command=lambda: self.sidebar.select_item("history"),
            font=("Segoe UI", 10, "bold"), bg=ACCENT,
            fg="white", relief="flat", cursor="hand2", padx=20, pady=8
        )
        edit_btn.pack(anchor="w", pady=(20, 0))
        
        # --- Right side: Contact Details ---
        right_profile = tk.Frame(profile_inner, bg=self.colors.get("card_bg"))
        right_profile.grid(row=0, column=1, sticky="nsew", padx=(30, 0))
        
        self._create_contact_row(right_profile, "Home Address", user_data.get("address", "Not set"))
        self._create_contact_row(right_profile, "Phone #", user_data.get("phone", "Not set"))
        self._create_contact_row(right_profile, "Email", user_data.get("email", "Not set"))
        
        # =====================
        # RIGHT COLUMN - ROW 0: MEDICAL INFO / EQ INFO
        # =====================
        right_top = tk.Frame(main_frame, bg=self.colors.get("bg"))
        right_top.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        
        # --- Medical Info Card (adapted from Medications) ---
        medical_card = self._create_overview_card(right_top, "🏥 Medical Info")
        medical_content = tk.Frame(medical_card, bg=self.colors.get("card_bg"))
        medical_content.pack(fill="x", padx=15, pady=(0, 15))
        
        if user_data.get("blood_type"):
            self._create_pill_item(medical_content, f"Blood Type: {user_data.get('blood_type', 'Unknown')}")
        if user_data.get("allergies"):
            self._create_pill_item(medical_content, f"Allergies: {user_data.get('allergies', 'None')[:30]}...")
        if user_data.get("conditions"):
            self._create_pill_item(medical_content, f"Conditions: {user_data.get('conditions', 'None')[:30]}...")
        if not any([user_data.get("blood_type"), user_data.get("allergies"), user_data.get("conditions")]):
            tk.Label(medical_content, text="No medical info set", font=("Segoe UI", 10), 
                    bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
        
        # --- Quick Stats Card (renamed from EQ Vitals) ---
        vitals_card = self._create_overview_card(right_top, "📊 Quick Stats")
        vitals_content = tk.Frame(vitals_card, bg=self.colors.get("card_bg"))
        vitals_content.pack(fill="x", padx=15, pady=(0, 15))
        
        # Row 1: EQ Score + Sentiment
        vitals_row1 = tk.Frame(vitals_content, bg=self.colors.get("card_bg"))
        vitals_row1.pack(fill="x", pady=(0, 10))
        
        self._create_vital_display(vitals_row1, "🧠", "EQ Score", user_data.get("last_eq", "--"), ACCENT, 0)
        self._create_vital_display(vitals_row1, "😊", "Sentiment", user_data.get("sentiment", "--"), "#4CAF50", 1)
        
        # Row 2: Tests Taken + Journals
        vitals_row2 = tk.Frame(vitals_content, bg=self.colors.get("card_bg"))
        vitals_row2.pack(fill="x")
        
        self._create_vital_display(vitals_row2, "📝", "Tests", user_data.get("tests_count", "0"), "#3B82F6", 0)
        self._create_vital_display(vitals_row2, "📔", "Journals", user_data.get("journals_count", "0"), "#F59E0B", 1)
        
        # =====================
        # LEFT COLUMN - ROW 1: NOTES/JOURNAL
        # =====================
        notes_card = tk.Frame(
            main_frame, bg=self.colors.get("card_bg"),
            highlightbackground=self.colors.get("card_border", "#E0E0E0"),
            highlightthickness=1
        )
        notes_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 0))
        
        # Notes header
        notes_header = tk.Frame(notes_card, bg=self.colors.get("card_bg"))
        notes_header.pack(fill="x", padx=20, pady=(15, 10))
        tk.Label(notes_header, text="📝 Notes & Journal", font=("Segoe UI", 14, "bold"),
                bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")).pack(side="left")
        
        notes_content = tk.Frame(notes_card, bg=self.colors.get("card_bg"))
        notes_content.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Show recent journal entries as notes
        if user_data.get("recent_journals"):
            for entry in user_data.get("recent_journals", [])[:3]:
                self._create_note_entry(notes_content, entry["date"], entry["content"])
        else:
            tk.Label(notes_content, text="No journal entries yet.\nStart journaling to see your notes here!",
                    font=("Segoe UI", 11), bg=self.colors.get("card_bg"), fg="gray", justify="left").pack(anchor="w")
        
        # =====================
        # RIGHT COLUMN - ROW 1: RECENT RESULTS
        # =====================
        results_card = self._create_overview_card_gridded(main_frame, "📊 Recent Results", 1, 1)
        results_content = tk.Frame(results_card, bg=self.colors.get("card_bg"))
        results_content.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        if user_data.get("recent_scores"):
            for score in user_data.get("recent_scores", [])[:4]:
                self._create_result_row(results_content, f"EQ Test - Score: {score['score']}", score["date"])
        else:
            tk.Label(results_content, text="No test results yet.", font=("Segoe UI", 10),
                    bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
    
    def _load_user_overview_data(self):
        """Load all user data for overview display."""
        from datetime import datetime
        data = {"username": self.app.username}
        
        try:
            from app.models import Score, JournalEntry, MedicalProfile
            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()
            
            if user:
                # Member since
                if user.created_at:
                    try:
                        created = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                        data["member_since"] = created.strftime("%b %Y")
                    except:
                        data["member_since"] = "--"
                
                # Personal Profile data
                if user.personal_profile:
                    pp = user.personal_profile
                    data["email"] = pp.email or "Not set"
                    data["phone"] = pp.phone or "Not set"
                    data["address"] = pp.address or "Not set"
                    data["occupation"] = pp.occupation
                    data["gender"] = pp.gender or "--"
                    data["avatar_path"] = pp.avatar_path  # Profile photo path
                    if pp.date_of_birth:
                        data["dob"] = pp.date_of_birth
                        try:
                            dob = datetime.strptime(pp.date_of_birth, "%Y-%m-%d")
                            age = (datetime.now() - dob).days // 365
                            data["age"] = f"{age}y"
                        except:
                            data["age"] = "--"
                
                # Medical Profile data
                if user.medical_profile:
                    mp = user.medical_profile
                    data["blood_type"] = mp.blood_type
                    data["allergies"] = mp.allergies
                    data["conditions"] = mp.medical_conditions
                
                # Recent scores
                # Use username for filtering to be robust against missing user_id in historical data
                scores = session.query(Score).filter_by(username=self.app.username).order_by(Score.timestamp.desc()).limit(5).all()
                data["recent_scores"] = [{"score": s.total_score, "date": s.timestamp[:10] if s.timestamp else "--"} for s in scores]
                if scores:
                    data["last_eq"] = str(scores[0].total_score)
                    if scores[0].sentiment_score:
                        data["sentiment"] = f"{scores[0].sentiment_score:.1f}"
                
                # Tests count
                data["tests_count"] = str(session.query(Score).filter_by(username=self.app.username).count())
                
                # Recent journals
                journals = session.query(JournalEntry).filter_by(username=self.app.username).order_by(JournalEntry.entry_date.desc()).limit(3).all()
                data["recent_journals"] = [{"date": j.entry_date[:10] if j.entry_date else "--", "content": (j.content or "")[:100]} for j in journals]
                
                # Journals count
                data["journals_count"] = str(session.query(JournalEntry).filter_by(username=self.app.username).count())
            
            session.close()
        except Exception as e:
            logging.error(f"Error loading overview data: {e}")
        
        return data
    
    def _upload_profile_photo(self):
        """Open file dialog to select and upload a profile photo."""
        from tkinter import filedialog, messagebox
        import shutil
        import os
        
        # Open file dialog
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("All files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Select Profile Photo",
            filetypes=filetypes,
            parent=self.window
        )
        
        if not filepath:
            return  # User cancelled
        
        # Open crop dialog
        self._open_crop_dialog(filepath)
    
    def _open_crop_dialog(self, filepath):
        """Open a dialog to crop the selected image to a square."""
        from PIL import Image, ImageTk
        import os
        
        try:
            original_img = Image.open(filepath)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Could not open image: {e}", parent=self.window)
            return
        
        # Create crop dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("Crop Profile Photo")
        dialog.geometry("500x550")
        dialog.configure(bg=self.colors.get("card_bg"))
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Instructions
        tk.Label(
            dialog, text="Drag to position, scroll to resize",
            font=("Segoe UI", 11), bg=self.colors.get("card_bg"), fg="gray"
        ).pack(pady=(15, 10))
        
        # Calculate display size (max 400px)
        display_size = 400
        scale = min(display_size / original_img.width, display_size / original_img.height)
        display_w = int(original_img.width * scale)
        display_h = int(original_img.height * scale)
        
        display_img = original_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        display_photo = ImageTk.PhotoImage(display_img)
        
        # Canvas for crop area
        canvas = tk.Canvas(dialog, width=display_w, height=display_h, bg="gray", highlightthickness=0)
        canvas.pack(pady=10)
        canvas.create_image(0, 0, image=display_photo, anchor="nw", tags="image")
        canvas.image = display_photo  # Keep reference
        
        # Initial crop square (centered, size = min dimension)
        min_dim = min(display_w, display_h)
        crop_size = int(min_dim * 0.8)
        crop_x = (display_w - crop_size) // 2
        crop_y = (display_h - crop_size) // 2
        
        # Store crop state
        crop_state = {"x": crop_x, "y": crop_y, "size": crop_size, "drag_start": None}
        
        # Draw crop overlay
        def draw_crop():
            canvas.delete("crop")
            x, y, s = crop_state["x"], crop_state["y"], crop_state["size"]
            
            # Darken outside areas (4 rectangles)
            canvas.create_rectangle(0, 0, x, display_h, fill="black", stipple="gray50", tags="crop")
            canvas.create_rectangle(x + s, 0, display_w, display_h, fill="black", stipple="gray50", tags="crop")
            canvas.create_rectangle(x, 0, x + s, y, fill="black", stipple="gray50", tags="crop")
            canvas.create_rectangle(x, y + s, x + s, display_h, fill="black", stipple="gray50", tags="crop")
            
            # Crop circle outline
            canvas.create_oval(x, y, x + s, y + s, outline="white", width=2, tags="crop")
        
        draw_crop()
        
        # Drag handling
        def on_press(event):
            crop_state["drag_start"] = (event.x - crop_state["x"], event.y - crop_state["y"])
        
        def on_drag(event):
            if crop_state["drag_start"]:
                dx, dy = crop_state["drag_start"]
                new_x = max(0, min(display_w - crop_state["size"], event.x - dx))
                new_y = max(0, min(display_h - crop_state["size"], event.y - dy))
                crop_state["x"], crop_state["y"] = new_x, new_y
                draw_crop()
        
        def on_release(event):
            crop_state["drag_start"] = None
        
        def on_scroll(event):
            delta = 10 if event.delta > 0 else -10
            new_size = max(50, min(min(display_w, display_h), crop_state["size"] + delta))
            # Keep centered
            center_x = crop_state["x"] + crop_state["size"] // 2
            center_y = crop_state["y"] + crop_state["size"] // 2
            crop_state["size"] = new_size
            crop_state["x"] = max(0, min(display_w - new_size, center_x - new_size // 2))
            crop_state["y"] = max(0, min(display_h - new_size, center_y - new_size // 2))
            draw_crop()
        
        canvas.bind("<Button-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        canvas.bind("<MouseWheel>", on_scroll)
        
        # Save button
        def save_crop():
            from tkinter import messagebox
            import shutil
            
            try:
                # Calculate actual crop area (scale back to original)
                x = int(crop_state["x"] / scale)
                y = int(crop_state["y"] / scale)
                s = int(crop_state["size"] / scale)
                
                cropped = original_img.crop((x, y, x + s, y + s))
                
                # Create avatars directory
                from app.config import DATA_DIR
                avatars_dir = os.path.join(DATA_DIR, "avatars")
                os.makedirs(avatars_dir, exist_ok=True)
                
                # Save cropped image
                new_path = os.path.join(avatars_dir, f"{self.app.username}_avatar.png")
                cropped.save(new_path, "PNG")
                
                # Update database
                session = get_session()
                user = session.query(User).filter_by(username=self.app.username).first()
                if user:
                    if not user.personal_profile:
                        from app.models import PersonalProfile
                        user.personal_profile = PersonalProfile(user_id=user.id)
                    user.personal_profile.avatar_path = new_path
                    session.commit()
                session.close()
                
                dialog.destroy()
                messagebox.showinfo("Success", "Profile photo updated!", parent=self.window)
                self.sidebar.select_item("overview")  # Refresh
                
            except Exception as e:
                logging.error(f"Error saving cropped photo: {e}")
                messagebox.showerror("Error", f"Could not save photo: {e}", parent=dialog)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors.get("card_bg"))
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            font=("Segoe UI", 10), bg="#E0E0E0", fg="black", relief="flat", padx=20, pady=8
        ).pack(side="left")
        
        tk.Button(
            btn_frame, text="✓ Save Photo", command=save_crop,
            font=("Segoe UI", 10, "bold"), bg="#009688", fg="white", relief="flat", padx=20, pady=8
        ).pack(side="right")
    
    def _create_overview_card(self, parent, title):
        """Create a simple overview card with title."""
        card = tk.Frame(parent, bg=self.colors.get("card_bg"),
                       highlightbackground=self.colors.get("card_border", "#E0E0E0"), highlightthickness=1)
        card.pack(fill="x", pady=(0, 10))
        
        tk.Label(card, text=title, font=("Segoe UI", 13, "bold"),
                bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")).pack(anchor="w", padx=15, pady=(12, 8))
        return card
    
    def _create_overview_card_gridded(self, parent, title, row, col):
        """Create an overview card positioned in grid."""
        card = tk.Frame(parent, bg=self.colors.get("card_bg"),
                       highlightbackground=self.colors.get("card_border", "#E0E0E0"), highlightthickness=1)
        card.grid(row=row, column=col, sticky="nsew", pady=(0, 0))
        
        tk.Label(card, text=title, font=("Segoe UI", 13, "bold"),
                bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")).pack(anchor="w", padx=15, pady=(12, 8))
        return card
    
    def _create_mini_stat(self, parent, label, value, row, col):
        """Create a mini stat display like DOB/Age grid."""
        box = tk.Frame(parent, bg=self.colors.get("card_bg"))
        box.grid(row=row, column=col, sticky="w", padx=(0, 30), pady=3)
        
        tk.Label(box, text=label, font=("Segoe UI", 9), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
        tk.Label(box, text=value, font=("Segoe UI", 12, "bold"), bg=self.colors.get("card_bg"), 
                fg=self.colors.get("text_primary")).pack(anchor="w")
    
    def _create_contact_row(self, parent, label, value):
        """Create a contact info row with label above value."""
        row = tk.Frame(parent, bg=self.colors.get("card_bg"))
        row.pack(fill="x", pady=8)
        
        tk.Label(row, text=label, font=("Segoe UI", 9), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
        tk.Label(row, text=value, font=("Segoe UI", 11, "bold"), bg=self.colors.get("card_bg"),
                fg=self.colors.get("text_primary"), wraplength=200, justify="left").pack(anchor="w")
    
    def _create_pill_item(self, parent, text):
        """Create a pill/medication style list item."""
        row = tk.Frame(parent, bg=self.colors.get("card_bg"))
        row.pack(fill="x", pady=3)
        
        tk.Label(row, text="💊", font=("Segoe UI", 10), bg=self.colors.get("card_bg")).pack(side="left")
        tk.Label(row, text=text, font=("Segoe UI", 10), bg=self.colors.get("card_bg"),
                fg=self.colors.get("text_primary")).pack(side="left", padx=5)
    
    def _create_vital_display(self, parent, icon, label, value, color, col):
        """Create a vital sign display with icon."""
        box = tk.Frame(parent, bg=self.colors.get("card_bg"))
        box.grid(row=0, column=col, sticky="nsew", padx=10)
        parent.columnconfigure(col, weight=1)
        
        tk.Label(box, text=icon, font=("Segoe UI", 24), bg=self.colors.get("card_bg")).pack()
        tk.Label(box, text=label, font=("Segoe UI", 9), bg=self.colors.get("card_bg"), fg="gray").pack()
        tk.Label(box, text=value, font=("Segoe UI", 18, "bold"), bg=self.colors.get("card_bg"), fg=color).pack()
    
    def _create_note_entry(self, parent, date, content):
        """Create a note/journal entry display."""
        entry_frame = tk.Frame(parent, bg=self.colors.get("card_bg"))
        entry_frame.pack(fill="x", pady=8)
        
        tk.Label(entry_frame, text=date, font=("Segoe UI", 9, "bold"), 
                bg=self.colors.get("card_bg"), fg="#009688").pack(anchor="w")
        tk.Label(entry_frame, text=content if content else "No notes", font=("Segoe UI", 10),
                bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary"), wraplength=350, justify="left").pack(anchor="w")
    
    def _create_result_row(self, parent, text, date):
        """Create a result/lab result style row."""
        row = tk.Frame(parent, bg=self.colors.get("card_bg"))
        row.pack(fill="x", pady=4)
        
        tk.Label(row, text="📄", font=("Segoe UI", 10), bg=self.colors.get("card_bg")).pack(side="left")
        tk.Label(row, text=text, font=("Segoe UI", 10), bg=self.colors.get("card_bg"),
                fg=self.colors.get("text_primary")).pack(side="left", padx=5)
        tk.Label(row, text=date, font=("Segoe UI", 9), bg=self.colors.get("card_bg"), fg="gray").pack(side="right")
    
    def _create_dashboard_card(self, parent, title):
        """Create a styled card container with optional title."""
        card = tk.Frame(
            parent, bg=self.colors.get("card_bg"),
            highlightbackground=self.colors.get("card_border", "#E2E8F0"),
            highlightthickness=1
        )
        card.pack(fill="x", pady=(0, 15))
        
        if title:
            tk.Label(
                card, text=title, font=("Segoe UI", 14, "bold"),
                bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")
            ).pack(anchor="w", padx=20, pady=(15, 10))
        
        return card
    
    def _create_info_row(self, parent, label, value):
        """Create an info display row with label and value."""
        row = tk.Frame(parent, bg=self.colors.get("card_bg"))
        row.pack(fill="x", pady=5)
        
        tk.Label(
            row, text=label, font=("Segoe UI", 11), width=12, anchor="w",
            bg=self.colors.get("card_bg"), fg="gray"
        ).pack(side="left")
        
        tk.Label(
            row, text=value, font=("Segoe UI", 11),
            bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")
        ).pack(side="left", padx=10)
    
    def _create_stat_box(self, parent, label, value, color, row, col):
        """Create a stat display box with colored accent."""
        box = tk.Frame(parent, bg=self.colors.get("card_bg"))
        box.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        parent.columnconfigure(col, weight=1)
        
        # Value (large)
        tk.Label(
            box, text=value, font=("Segoe UI", 24, "bold"),
            bg=self.colors.get("card_bg"), fg=color
        ).pack(anchor="w")
        
        # Label (small)
        tk.Label(
            box, text=label, font=("Segoe UI", 10),
            bg=self.colors.get("card_bg"), fg="gray"
        ).pack(anchor="w")
    
    def _create_activity_row(self, parent, icon, text, timestamp):
        """Create an activity timeline row."""
        row = tk.Frame(parent, bg=self.colors.get("card_bg"))
        row.pack(fill="x", pady=3)
        
        tk.Label(
            row, text=icon, font=("Segoe UI", 12),
            bg=self.colors.get("card_bg")
        ).pack(side="left")
        
        tk.Label(
            row, text=text, font=("Segoe UI", 11),
            bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")
        ).pack(side="left", padx=(5, 10))
        
        # Format timestamp
        time_str = ""
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = timestamp
                diff = datetime.now() - dt.replace(tzinfo=None)
                if diff.days > 0:
                    time_str = f"{diff.days}d ago"
                elif diff.seconds > 3600:
                    time_str = f"{diff.seconds // 3600}h ago"
                else:
                    time_str = f"{diff.seconds // 60}m ago"
            except:
                time_str = str(timestamp)[:10] if timestamp else ""
        
        tk.Label(
            row, text=time_str, font=("Segoe UI", 9),
            bg=self.colors.get("card_bg"), fg="gray"
        ).pack(side="right")

    # ==========================
    # 1. MEDICAL VIEW
    # ==========================
    def _render_medical_view(self):
        # Card Container
        card = tk.Frame(
            self.view_container, 
            bg=self.colors.get("card_bg", "white"),
            highlightbackground=self.colors.get("card_border", "#E2E8F0"),
            highlightthickness=1
        )
        card.pack(fill="both", expand=True)
        
        # 2-Column Grid within Card
        content = tk.Frame(card, bg=self.colors.get("card_bg", "white"))
        content.pack(fill="both", expand=True, padx=40, pady=40)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        
        # --- LEFT COLUMN ---
        left_col = tk.Frame(content, bg=self.colors.get("card_bg"))
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        
        self._create_section_label(left_col, self.i18n.get("profile.section_general"))
        
        # Blood Type
        self._create_field_label(left_col, self.i18n.get("profile.blood_type"))
        blood_types = ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        self.blood_type_var = tk.StringVar()
        self.blood_combo = ttk.Combobox(left_col, textvariable=self.blood_type_var, values=blood_types, state="readonly", font=("Segoe UI", 11))
        self.blood_combo.pack(fill="x", pady=(0, 20))
        
        # Emergency Contact
        self._create_section_label(left_col, self.i18n.get("profile.section_contact"))
        
        self._create_field_label(left_col, self.i18n.get("profile.contact_name"))
        self.ec_name_var = tk.StringVar()
        self._create_entry(left_col, self.ec_name_var)
        
        self._create_field_label(left_col, self.i18n.get("profile.contact_phone"))
        self.ec_phone_var = tk.StringVar()
        self._create_entry(left_col, self.ec_phone_var)

        # --- RIGHT COLUMN ---
        right_col = tk.Frame(content, bg=self.colors.get("card_bg"))
        right_col.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        
        self._create_section_label(right_col, self.i18n.get("profile.section_details"))
        
        self._create_field_label(right_col, self.i18n.get("profile.allergies"))
        self.allergies_text = self._create_text_area(right_col)
        
        self._create_field_label(right_col, self.i18n.get("profile.medications"))
        self.medications_text = self._create_text_area(right_col)
        
        self._create_field_label(right_col, self.i18n.get("profile.conditions"))
        self.conditions_text = self._create_text_area(right_col)
        
        # --- PR #5: Surgeries & Therapy ---
        self._create_field_label(right_col, "Surgery History")
        self.surgeries_text = self._create_text_area(right_col)
        
        self._create_field_label(right_col, "Therapy History (Private 🔒)")
        self.therapy_text = self._create_text_area(right_col)

        # Issue #262: Ongoing Health Issues
        self._create_field_label(right_col, "Ongoing Health Issues")
        self.health_issues_text = self._create_text_area(right_col)

        # Footer Actions (Save Button)
        footer = tk.Frame(card, bg=self.colors.get("card_bg"), height=80)
        footer.pack(fill="x", side="bottom", padx=40, pady=30)
        
        tk.Label(footer, text=self.i18n.get("profile.privacy_note"), font=("Segoe UI", 9, "italic"), bg=self.colors.get("card_bg"), fg="gray").pack(side="left")
        
        save_btn = tk.Button(
            footer,
            text=self.i18n.get("profile.save"),
            command=self.save_medical_data,
            font=("Segoe UI", 12, "bold"),
            bg=self.colors.get("success", "#10B981"),
            fg="white",
            activebackground=self.colors.get("success_hover", "#059669"),
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            width=20, # Wider button
            pady=10
        )
        save_btn.pack(side="right")
        
        # Load Data
        self.load_medical_data()

    # ==========================
    # 2. PERSONAL HISTORY VIEW
    # ==========================
    def _render_history_view(self):
        # Responsive Split: Left (Form) | Right (Timeline)
        # Use simple Frame with grid instead of PanedWindow to allow proper vertical scrolling
        content_grid = tk.Frame(self.view_container, bg=self.colors.get("bg"))
        content_grid.pack(fill="x", expand=True, padx=0, pady=0)
        content_grid.columnconfigure(0, weight=1) # Form
        content_grid.columnconfigure(1, weight=1) # Timeline
        
        # --- LEFT COLUMN: Form ---
        left_col = tk.Frame(content_grid, bg=self.colors.get("bg"))
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        card = tk.Frame(left_col, bg=self.colors.get("card_bg"), highlightbackground=self.colors.get("card_border"), highlightthickness=1)
        card.pack(fill="both", expand=True)
        
        form_content = tk.Frame(card, bg=self.colors.get("card_bg"))
        form_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        self._create_section_label(form_content, "About You")
        
        self._create_field_label(form_content, "Occupation")
        self.occ_var = tk.StringVar()
        self._create_entry(form_content, self.occ_var)
        
        self._create_field_label(form_content, "Education")
        self.edu_var = tk.StringVar()
        self._create_entry(form_content, self.edu_var)
        
        self._create_field_label(form_content, "Marital Status")
        status_opts = ["Single", "Married", "Divorced", "Widowed", "Other"]
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(form_content, textvariable=self.status_var, values=status_opts, state="readonly", font=("Segoe UI", 11))
        self.status_combo.pack(fill="x", pady=5)
        
        self._create_field_label(form_content, "Bio")
        self.bio_text = self._create_text_area(form_content)
        
        # --- Phase 53: Contact Information Section ---
        self._create_section_label(form_content, "📞 Contact Information")
        
        # Email
        self._create_field_label(form_content, "Email")
        self.email_var = tk.StringVar()
        self._create_entry(form_content, self.email_var)
        
        # Phone
        self._create_field_label(form_content, "Phone")
        self.phone_var = tk.StringVar()
        self._create_entry(form_content, self.phone_var)
        
        # Date of Birth + Gender in a row
        dob_gender_frame = tk.Frame(form_content, bg=self.colors.get("card_bg"))
        dob_gender_frame.pack(fill="x", pady=(10, 0))
        
        dob_col = tk.Frame(dob_gender_frame, bg=self.colors.get("card_bg"))
        dob_col.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(dob_col, text="Date of Birth", font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
        self.dob_entry = DateEntry(
            dob_col, date_pattern="yyyy-mm-dd", font=("Segoe UI", 11),
            background=self.colors.get("primary"), foreground="white"
        )
        self.dob_entry.pack(fill="x", pady=5)
        
        gender_col = tk.Frame(dob_gender_frame, bg=self.colors.get("card_bg"))
        gender_col.pack(side="left", fill="x", expand=True, padx=(10, 0))
        tk.Label(gender_col, text="Gender", font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
        self.gender_var = tk.StringVar()
        gender_opts = ["Prefer not to say", "Male", "Female", "Non-binary", "Other"]
        self.gender_combo = ttk.Combobox(gender_col, textvariable=self.gender_var, values=gender_opts, state="readonly", font=("Segoe UI", 11))
        self.gender_combo.pack(fill="x", pady=5)
        
        # Address
        self._create_field_label(form_content, "Address")
        self.address_text = self._create_text_area(form_content)

        # --- PR #5: Society Contribution & Life POV ---
        self._create_section_label(form_content, "📝 Life Perspective")
        
        self._create_field_label(form_content, "Contribution to Society")
        self.society_text = self._create_text_area(form_content)

        self._create_field_label(form_content, "Perspective on Life")
        self.life_pov_text = self._create_text_area(form_content)

        # Issue #275: High-Pressure Events
        self._create_field_label(form_content, "Recent High-Pressure Events")
        self.high_pressure_text = self._create_text_area(form_content)
        
        # Save Button for Profile Details
        save_profile_btn = tk.Button(
            form_content, text="Save Details", command=self.save_personal_data,
            bg=self.colors.get("primary", "#3B82F6"), fg="white", 
            font=("Segoe UI", 10, "bold"), relief="flat", pady=8
        )
        save_profile_btn.pack(fill="x", pady=20)

        # --- RIGHT COLUMN: Timeline ---
        right_col = tk.Frame(content_grid, bg=self.colors.get("bg"))
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Timeline Component
        self.timeline = LifeTimeline(
            right_col,
            events=[], # Will load from DB
            on_add=lambda: self._open_event_dialog(),
            colors=self.colors
        )
        self.timeline.on_click = self._open_event_dialog # Bind click handler
        self.timeline.pack(fill="both", expand=True)
        
        self.load_personal_data()

    def _open_event_dialog(self, event_to_edit=None):
        # Dialog to Add or Edit life event
        is_edit = event_to_edit is not None
        title = "Edit Life Event" if is_edit else "Add Life Event"
        
        dialog = tk.Toplevel(self.window)
        dialog.title(title)
        dialog.geometry("400x500")
        dialog.configure(bg=self.colors.get("card_bg"))
        
        # Helper to create inputs
        def create_input(label, var=None):
            tk.Label(dialog, text=label, font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w", padx=20, pady=(10, 5))
            if var is None: var = tk.StringVar()
            entry = tk.Entry(dialog, textvariable=var, font=("Segoe UI", 11))
            entry.pack(fill="x", padx=20)
            return var

        # Date Field with DateEntry
        tk.Label(dialog, text="Date", font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w", padx=20, pady=(10, 5))
        date_entry = DateEntry(dialog, width=12, background='darkblue', foreground='white', borderwidth=2, font=("Segoe UI", 11), date_pattern='yyyy-mm-dd')
        date_entry.pack(fill="x", padx=20)
        
        if is_edit:
            try:
                 dt = datetime.strptime(event_to_edit['date'], "%Y-%m-%d")
                 date_entry.set_date(dt)
            except: pass

        # Title Field
        title_var = tk.StringVar(value=event_to_edit['title']) if is_edit else tk.StringVar()
        tk.Label(dialog, text="Event Title", font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w", padx=20, pady=(10, 5))
        tk.Entry(dialog, textvariable=title_var, font=("Segoe UI", 11)).pack(fill="x", padx=20)
        
        # Description Field
        tk.Label(dialog, text="Description", font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w", padx=20, pady=(10, 5))
        desc_text = tk.Text(dialog, height=5, font=("Segoe UI", 11))
        desc_text.pack(fill="x", padx=20)
        
        if is_edit:
            desc_text.insert("1.0", event_to_edit.get('description', ''))
            
        def save():
            date_str = date_entry.get_date().strftime("%Y-%m-%d")
            title = sanitize_text(title_var.get())
            desc = sanitize_text(desc_text.get("1.0", tk.END))
            
            # Validation
            valid_title, msg_title = validate_required(title, "Title")
            if not valid_title:
                messagebox.showwarning("Incomplete", msg_title)
                return
                
            valid_len, msg_len = validate_length(desc, MAX_TEXT_LENGTH, "Description")
            if not valid_len:
                messagebox.showwarning("Incomplete", msg_len)
                return
            
            new_data = {
                "date": date_str,
                "title": title,
                "description": desc
            }
            
            if is_edit:
                # Update existing
                # Use index to find and update because dicts are not unique by value safely
                # But here event_to_edit IS the object reference in list? 
                # Be safer: Find index of event_to_edit in self.current_events
                try:
                    idx = self.current_events.index(event_to_edit)
                    self.current_events[idx] = new_data
                except ValueError:
                    self.current_events.append(new_data) # Fallback
            else:
                 self.current_events.append(new_data)
                 
            self.save_life_events()
            self.timeline.refresh(self.current_events)
            dialog.destroy()
            
        def delete():
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this event?"):
                if event_to_edit in self.current_events:
                    self.current_events.remove(event_to_edit)
                    self.save_life_events()
                    self.timeline.refresh(self.current_events)
                    dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self.colors.get("card_bg"))
        btn_frame.pack(fill="x", padx=20, pady=20)

        if is_edit:
            tk.Button(btn_frame, text="🗑️ Delete", command=delete, bg="#EF4444", fg="white", font=("Segoe UI", 10, "bold"), pady=8).pack(side="left", expand=True, fill="x", padx=(0, 5))
            
        tk.Button(btn_frame, text="Save Event", command=save, bg=self.colors.get("success"), fg="white", font=("Segoe UI", 10, "bold"), pady=8).pack(side="left", expand=True, fill="x", padx=(5, 0))
    
    # --- DATA OPERATIONS ---
    
    def load_personal_data(self):
        try:
            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()
            self.current_events = []
            
            if user and user.personal_profile:
                profile = user.personal_profile
                self.occ_var.set(profile.occupation or "")
                self.edu_var.set(profile.education or "")
                self.status_var.set(profile.marital_status or "")
                self.bio_text.insert("1.0", profile.bio or "")

                # Phase 53: Load contact info
                self.email_var.set(profile.email or "")
                self.phone_var.set(profile.phone or "")
                if profile.date_of_birth:
                    try:
                        from datetime import datetime
                        dob = datetime.strptime(profile.date_of_birth, "%Y-%m-%d")
                        self.dob_entry.set_date(dob)
                    except:
                        pass
                self.gender_var.set(profile.gender or "Prefer not to say")
                self.address_text.insert("1.0", profile.address or "")

                # PR #5 Load
                self.society_text.insert("1.0", profile.society_contribution or "")
                self.life_pov_text.insert("1.0", profile.life_pov or "")
                self.high_pressure_text.insert("1.0", profile.high_pressure_events or "")
                
                # Load events
                if profile.life_events:
                    try:
                        self.current_events = json.loads(profile.life_events)
                    except json.JSONDecodeError:
                        self.current_events = []
            
            self.timeline.refresh(self.current_events)
            session.close()
        except Exception as e:
            logging.error(f"Error loading personal profile: {e}")

    def save_personal_data(self):
        try:
             session = get_session()
             user = session.query(User).filter_by(username=self.app.username).first()
             
             if not user.personal_profile:
                 profile = PersonalProfile(user_id=user.id)
                 user.personal_profile = profile
             else:
                 profile = user.personal_profile
                 
             # Sanitize
             occupation = sanitize_text(self.occ_var.get())
             education = sanitize_text(self.edu_var.get())
             bio = sanitize_text(self.bio_text.get("1.0", tk.END))
             email = sanitize_text(self.email_var.get())
             phone = sanitize_text(self.phone_var.get())
             dob_str = self.dob_entry.get_date().strftime("%Y-%m-%d")
             address = sanitize_text(self.address_text.get("1.0", tk.END))
             
             society = sanitize_text(self.society_text.get("1.0", tk.END))
             life_pov = sanitize_text(self.life_pov_text.get("1.0", tk.END))
             pressure = sanitize_text(self.high_pressure_text.get("1.0", tk.END))

             # Validation
             valid_email, msg_email = validate_email(email)
             if not valid_email:
                 messagebox.showwarning("Validation Error", msg_email)
                 return
                 
             valid_phone, msg_phone = validate_phone(phone)
             if not valid_phone:
                 messagebox.showwarning("Validation Error", msg_phone)
                 return

             valid_dob, msg_dob = validate_dob(dob_str)
             if not valid_dob:
                 messagebox.showwarning("Validation Error", msg_dob)
                 return
             
             # Max Lengths
             for label, txt in [("Bio", bio), ("Address", address), ("Perspective", life_pov), 
                               ("Society", society), ("Pressure Events", pressure)]:
                valid, msg = validate_length(txt, MAX_TEXT_LENGTH, label)
                if not valid:
                    messagebox.showwarning("Validation Error", msg)
                    return

             profile.occupation = occupation
             profile.education = education
             profile.marital_status = self.status_var.get()
             profile.bio = bio

             profile.email = email
             profile.phone = phone
             profile.date_of_birth = dob_str
             profile.gender = self.gender_var.get()
             profile.address = address

             # PR #5 Save
             profile.society_contribution = society
             profile.life_pov = life_pov
             profile.high_pressure_events = pressure
             
             session.commit()
             session.close()
             messagebox.showinfo("Success", "Personal details saved!")
        except Exception as e:
            logging.error(f"Error saving personal profile: {e}")
            messagebox.showerror("Error", "Failed to save details.")

    def save_life_events(self):
        try:
             session = get_session()
             user = session.query(User).filter_by(username=self.app.username).first()
             
             if not user.personal_profile:
                 profile = PersonalProfile(user_id=user.id)
                 user.personal_profile = profile
             else:
                 profile = user.personal_profile
            
             profile.life_events = json.dumps(self.current_events)
             
             session.commit()
             session.close()
        except Exception as e:
            logging.error(f"Error saving events: {e}")
            messagebox.showerror("Error", "Failed to save events.")

    def _render_settings_view(self, parent):
        """Render embedded settings view"""
        # Header
        self._create_section_label(parent, "Application Settings")
        
        # We can reuse logic from SettingsManager but render into 'parent'
        # Instead of full rewrite, let's instantiate SettingsManager and use its internal methods if possible,
        # OR just simpler: reimplement the sections here using the parent frame.
        # Reimplementing is safer for layout control.
        colors = self.colors
        
        # Theme Section
        self._create_field_label(parent, "Theme")
        theme_frame = tk.Frame(parent, bg=colors.get("card_bg", "white"))
        theme_frame.pack(fill="x", pady=5)
        
        current_theme = self.app.settings.get("theme", "light")
        self.theme_var = tk.StringVar(value=current_theme)
        
        def on_theme_change():
            new_theme = self.theme_var.get()
            self.app.settings["theme"] = new_theme
            self.app.apply_theme(new_theme)
            # View is reloaded by apply_theme, so we stop here.
            return

        tk.Radiobutton(
            theme_frame, 
            text="☀ Light", 
            variable=self.theme_var, 
            value="light", 
            command=on_theme_change, 
            bg=colors.get("card_bg", "white"), 
            fg=colors.get("text_primary"),
            selectcolor=colors.get("primary_light", "#DBEAFE"),
            activebackground=colors.get("card_bg", "white"), # Keep same as bg to avoid flash
            activeforeground=colors.get("primary", "blue")
        ).pack(side="left", padx=10)
        
        tk.Radiobutton(
            theme_frame, 
            text="🌙 Dark", 
            variable=self.theme_var, 
            value="dark", 
            command=on_theme_change, 
            bg=colors.get("card_bg", "white"), 
            fg=colors.get("text_primary"),
            selectcolor=colors.get("primary_light", "#DBEAFE"), # Use light color for indicator even in dark mode for contrast? 
            # OR better: use primary.
            # in dark mode: selectcolor="#3B82F6" (Primary Blue).
            activebackground=colors.get("card_bg", "white"),
            activeforeground=colors.get("primary", "blue")
        ).pack(side="left", padx=10)

        # Question Count Section
        self._create_field_label(parent, "Questions per Session")
        
        current_count = self.app.settings.get("question_count", 10)
        self.qcount_var = tk.IntVar(value=current_count)
        
        spinbox = tk.Spinbox(parent, from_=5, to=50, textvariable=self.qcount_var, width=10, font=("Segoe UI", 12))
        spinbox.pack(anchor="w", pady=5)
        
        # Save Button
        tk.Button(parent, text="Save Preferences",
                 command=self._save_settings,
                 bg=colors.get("primary"), fg="white", font=("Segoe UI", 12), pady=5).pack(pady=20, anchor="w")

        # Data Management Section
        self._create_section_label(parent, "Data Management")

        # Delete My Data Button
        delete_btn = tk.Button(parent, text="🗑️ Delete My Data",
                              command=self._delete_user_data,
                              bg="#DC2626", fg="white", font=("Segoe UI", 12, "bold"),
                              relief="flat", pady=10, padx=20)
        delete_btn.pack(pady=(10, 20), anchor="w")

        # Warning text
        warning_text = ("This action will permanently delete all your personal data, "
                       "including profiles, test results, journals, and settings. "
                       "This cannot be undone.")
        warning_label = tk.Label(parent, text=warning_text, font=("Segoe UI", 9),
                                bg=colors.get("card_bg"), fg="#DC2626", wraplength=400, justify="left")
        warning_label.pack(anchor="w", pady=(0, 20))

    def _save_settings(self):
        """Save settings to DB"""
        new_settings = {
            "theme": self.theme_var.get(),
            "question_count": self.qcount_var.get(),
            "sound_enabled": True # Default for now
        }
        
        self.app.settings.update(new_settings)
        
        # Save via DB helper if possible
        if hasattr(self.app, 'current_user_id') and self.app.current_user_id:
             try:
                from app.db import update_user_settings
                update_user_settings(self.app.current_user_id, **new_settings)
                tk.messagebox.showinfo("Success", "Settings saved!")
             except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to save: {e}")

    # --- UI Helpers ---
    def _create_section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 16, "bold"), bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")).pack(anchor="w", pady=(0, 15))
        
    def _create_field_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w", pady=(10, 5))
        
    def _create_entry(self, parent, variable, max_length=50):
        def validate(event):
            val = variable.get()
            if len(val) > max_length:
                variable.set(val[:max_length])
                
        entry = tk.Entry(
            parent, textvariable=variable, font=("Segoe UI", 11), relief="flat", 
            highlightthickness=1, highlightbackground=self.colors.get("card_border"),
            bg=self.colors.get("input_bg", "white"), fg=self.colors.get("input_fg", "black"),
            insertbackground=self.colors.get("input_fg", "black") # Caret color
        )
        entry.pack(fill="x", ipady=8) # Taller input
        entry.bind("<KeyRelease>", validate)
        return entry
        
    def _create_text_area(self, parent, max_length=1000):
        def validate(event):
            val = txt.get("1.0", "end-1c")
            if len(val) > max_length:
                # Keep current position
                # This is a basic truncator, for better UX we might want to block input
                # But blocking paste is harder, so truncation on release is safest fallback
                current_insert = txt.index(tk.INSERT)
                txt.delete("1.0", tk.END)
                txt.insert("1.0", val[:max_length])
                try:
                    txt.mark_set(tk.INSERT, current_insert)
                except:
                    pass
                    
        txt = tk.Text(
            parent, height=4, font=("Segoe UI", 11), relief="flat", 
            highlightthickness=1, highlightbackground=self.colors.get("card_border"),
            bg=self.colors.get("input_bg", "white"), fg=self.colors.get("input_fg", "black"),
            insertbackground=self.colors.get("input_fg", "black")
        )
        txt.pack(fill="x", pady=(0, 5))
        txt.bind("<KeyRelease>", validate)
        return txt

    # --- Data Logic ---
    def load_medical_data(self):
        try:
            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()
            if user and user.medical_profile:
                profile = user.medical_profile
                self.blood_type_var.set(profile.blood_type or "Unknown")
                self.ec_name_var.set(profile.emergency_contact_name or "")
                self.ec_phone_var.set(profile.emergency_contact_phone or "")
                
                self.allergies_text.insert("1.0", profile.allergies or "")
                self.medications_text.insert("1.0", profile.medications or "")
                self.medications_text.insert("1.0", profile.medications or "")
                self.conditions_text.insert("1.0", profile.medical_conditions or "")
                
                # PR #5 Load
                self.surgeries_text.insert("1.0", profile.surgeries or "")
                self.therapy_text.insert("1.0", profile.therapy_history or "")
                self.health_issues_text.insert("1.0", profile.ongoing_health_issues or "")
            else:
                self.blood_type_var.set("Unknown")
            
            session.close()
        except Exception as e:
            logging.error(f"Error loading medical profile: {e}")

    # ==========================
    # 2. MEDICAL VIEW
    # ==========================
    # ... (skipping render code) ...
    
    def save_medical_data(self):
        try:
            # --- VALIDATION ---
            contact_name = sanitize_text(self.ec_name_var.get())
            contact_phone = sanitize_text(self.ec_phone_var.get())
            
            # Validate Phone
            valid_phone, msg_phone = validate_phone(contact_phone)
            if not valid_phone:
                 messagebox.showwarning("Validation Error", msg_phone, parent=self.window)
                 return
            
            # Sanitize and Validate Text Areas
            allergies = sanitize_text(self.allergies_text.get("1.0", tk.END))
            medications = sanitize_text(self.medications_text.get("1.0", tk.END))
            conditions = sanitize_text(self.conditions_text.get("1.0", tk.END))
            # PR #5
            surgeries = sanitize_text(self.surgeries_text.get("1.0", tk.END))
            therapy = sanitize_text(self.therapy_text.get("1.0", tk.END))
            health_issues = sanitize_text(self.health_issues_text.get("1.0", tk.END))
            
            # Check Max Lengths
            for label, txt in [("Allergies", allergies), ("Medications", medications), 
                              ("Conditions", conditions), ("Surgeries", surgeries),
                              ("Therapy", therapy), ("Health Issues", health_issues)]:
                valid, msg = validate_length(txt, MAX_TEXT_LENGTH, label)
                if not valid:
                    messagebox.showwarning("Validation Error", msg, parent=self.window)
                    return

            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()
            
            if not user:
                session.close()
                return 
                
            if not user.medical_profile:
                profile = MedicalProfile(user_id=user.id)
                user.medical_profile = profile
            else:
                profile = user.medical_profile
                
            # Update fields
            profile.blood_type = self.blood_type_var.get()
            profile.emergency_contact_name = contact_name
            profile.emergency_contact_phone = contact_phone
            
            profile.allergies = allergies
            profile.medications = medications
            profile.medical_conditions = conditions
            
            # PR #5 Save
            profile.surgeries = surgeries
            profile.therapy_history = therapy
            profile.ongoing_health_issues = health_issues
            
            session.commit()
            session.close()
            
            messagebox.showinfo(self.i18n.get("profile.success_title"), self.i18n.get("profile.success_msg"), parent=self.window)
            
        except Exception as e:
            logging.error(f"Error saving medical profile: {e}")
            messagebox.showerror(self.i18n.get("profile.error_title"), self.i18n.get("profile.error_msg"), parent=self.window)

    # ==========================
    # 3. STRENGTHS VIEW
    # ==========================
    def _render_strengths_view(self):
        # Card Container (no fixed frame, use PanedWindow wrapper)
        # Using a vertical frame first to hold footer
        main_layout = tk.Frame(self.view_container, bg=self.colors.get("bg"))
        main_layout.pack(fill="both", expand=True)
        
        # Responsive PanedWindow
        paned = tk.PanedWindow(main_layout, orient=tk.HORIZONTAL, bg=self.colors.get("bg"), sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # --- LEFT COLUMN: Tags ---
        left_wrapper = tk.Frame(paned, bg=self.colors.get("bg"))
        paned.add(left_wrapper, minsize=350, sticky="nsew", padx=5) # Tuple padding (0,5) causes TclError
        
        left_card = tk.Frame(left_wrapper, bg=self.colors.get("card_bg"), highlightbackground=self.colors.get("card_border"), highlightthickness=1)
        left_card.pack(fill="both", expand=True) # Removed inner spacing here, relying on wrapper padx
        
        left_col = tk.Frame(left_card, bg=self.colors.get("card_bg"))
        left_col.pack(fill="both", expand=True, padx=20, pady=20)
        
        self._create_section_label(left_col, "Self-Perception")
        
        # Top Strengths
        self._create_field_label(left_col, "Top Strengths")
        tk.Label(left_col, text="(Type & Enter)", font=("Segoe UI", 9), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w")
        suggested_strengths = ["Empathy", "Creativity", "Problem Solving", "Resilience", "Leadership", "Coding"]
        self.strengths_input = TagInput(left_col, max_tags=5, colors=self.colors, suggestion_list=suggested_strengths)
        self.strengths_input.pack(fill="x", pady=(5, 20))
        
        # Improvements
        self._create_field_label(left_col, "Areas for Improvement")
        suggested_improvements = ["Public Speaking", "Time Management", "Delegation", "Patience", "Networking"]
        self.improvements_input = TagInput(left_col, max_tags=5, colors=self.colors, suggestion_list=suggested_improvements)
        self.improvements_input.pack(fill="x", pady=(0, 20))
        
        # Goals
        self._create_section_label(left_col, "Aspirations")
        self._create_field_label(left_col, "Current Goals")
        self.goals_text = self._create_text_area(left_col)
        
        # --- RIGHT COLUMN: Preferences ---
        right_wrapper = tk.Frame(paned, bg=self.colors.get("bg"))
        paned.add(right_wrapper, minsize=350, sticky="nsew", padx=5) # Tuple padding causes error
        
        right_card = tk.Frame(right_wrapper, bg=self.colors.get("card_bg"), highlightbackground=self.colors.get("card_border"), highlightthickness=1)
        right_card.pack(fill="both", expand=True)

        right_col = tk.Frame(right_card, bg=self.colors.get("card_bg"))
        right_col.pack(fill="both", expand=True, padx=20, pady=20)
        
        self._create_section_label(right_col, "Learning & Style")
        
        # Learning Style
        self._create_field_label(right_col, "Learning Style")
        
        # Suggestion Helper (Future: AI based)
        ls_frame = tk.Frame(right_col, bg=self.colors.get("card_bg"))
        ls_frame.pack(fill="x")
        
        learn_styles = ["Visual (Images)", "Auditory (Listening)", "Kinesthetic (Doing)", "Reading/Writing"]
        self.learn_style_var = tk.StringVar()
        self.learn_style_combo = ttk.Combobox(ls_frame, textvariable=self.learn_style_var, values=learn_styles, state="readonly", font=("Segoe UI", 12))
        self.learn_style_combo.pack(side="left", fill="x", expand=True, pady=(0, 20))
        
        # Suggestion Button
        def show_ls_hint():
            messagebox.showinfo("Suggestion", "Based on your general profile, 'Visual' or 'Kinesthetic' might fit best.\n(Full AI analysis coming soon!)")
            
        tk.Button(ls_frame, text="💡 Suggest", command=show_ls_hint, bg="#F59E0B", fg="white", font=("Segoe UI", 8), relief="flat", padx=10).pack(side="right", padx=(10, 0), pady=(0, 20))
        
        # Communication
        self._create_field_label(right_col, "Preferred Communication Tone")
        comm_styles = ["Direct & Concise", "Supportive & Gentle", "Data-Driven", "Storytelling"]
        self.comm_style_var = tk.StringVar()
        self.comm_style_combo = ttk.Combobox(right_col, textvariable=self.comm_style_var, values=comm_styles, state="readonly", font=("Segoe UI", 12))
        self.comm_style_combo = ttk.Combobox(right_col, textvariable=self.comm_style_var, values=comm_styles, state="readonly", font=("Segoe UI", 12))
        self.comm_style_combo.pack(fill="x", pady=(0, 20))

        # --- PR #5: Detailed Comm Style ---
        self._create_field_label(right_col, "Detailed Communication Style")
        self.comm_style_text = self._create_text_area(right_col)
        
        # Boundaries
        self._create_section_label(right_col, "Privacy Boundaries")
        self._create_field_label(right_col, "Topics to Avoid")
        suggested_boundaries = ["Politics", "Religion", "Finances", "Family Matters", "Past Trauma"]
        self.boundaries_input = TagInput(right_col, max_tags=5, colors=self.colors, suggestion_list=suggested_boundaries)
        self.boundaries_input.pack(fill="x", pady=(0, 20))

        # Footer Actions (Overlay or Bottom of Main Layout)
        footer = tk.Frame(main_layout, bg=self.colors.get("bg"), height=60)
        footer.pack(fill="x", side="bottom", padx=0, pady=10)
        
        save_btn = tk.Button(
            footer, text="Save Preferences", command=self.save_strengths_data,
            font=("Segoe UI", 12, "bold"), bg=self.colors.get("success", "#10B981"), fg="white",
            relief="flat", cursor="hand2", width=20, pady=10
        )
        save_btn.pack(side="right", padx=20)
        
        self.load_strengths_data()

    def load_strengths_data(self):
        try:
            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()
            
            if user and user.strengths:
                s = user.strengths
                
                # Load JSONs safely
                try: self.strengths_input.tags = json.loads(s.top_strengths)
                except: self.strengths_input.tags = []
                self.strengths_input._render_tags()
                
                try: self.improvements_input.tags = json.loads(s.areas_for_improvement)
                except: self.improvements_input.tags = []
                self.improvements_input._render_tags()
                
                try: self.boundaries_input.tags = json.loads(s.sharing_boundaries)
                except: self.boundaries_input.tags = []
                self.boundaries_input._render_tags()
                
                self.learn_style_var.set(s.learning_style or "")
                self.comm_style_var.set(s.communication_preference or "")
                self.goals_text.insert("1.0", s.goals or "")

                # PR #5 Load
                self.comm_style_text.insert("1.0", s.comm_style or "")
                
            session.close()
        except Exception as e:
            logging.error(f"Error loading strengths: {e}")

    def save_strengths_data(self):
        try:
            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()

            if not user.strengths:
                strengths = UserStrengths(user_id=user.id)
                user.strengths = strengths
            else:
                strengths = user.strengths

            # Update fields
            strengths.top_strengths = json.dumps(self.strengths_input.get_tags())
            strengths.areas_for_improvement = json.dumps(self.improvements_input.get_tags())
            strengths.sharing_boundaries = json.dumps(self.boundaries_input.get_tags())

            strengths.learning_style = self.learn_style_var.get()
            strengths.communication_preference = self.comm_style_var.get()
            strengths.learning_style = self.learn_style_var.get()
            strengths.communication_preference = self.comm_style_var.get()
            strengths.goals = self.goals_text.get("1.0", tk.END).strip()

            # PR #5 Save
            strengths.comm_style = self.comm_style_text.get("1.0", tk.END).strip()

            session.commit()
            session.close()
            messagebox.showinfo("Success", "Preferences saved successfully!")
        except Exception as e:
            logging.error(f"Error saving strengths: {e}")
            messagebox.showerror("Error", "Failed to save preferences.")

    def _delete_user_data(self):
        """Handle the delete user data action with confirmation."""
        # First confirmation dialog
        confirm1 = messagebox.askyesno(
            "Delete My Data",
            "Are you sure you want to delete all your personal data?\n\n"
            "This includes:\n"
            "• Profile information\n"
            "• Test results and scores\n"
            "• Journal entries\n"
            "• Medical information\n"
            "• Settings and preferences\n\n"
            "This action cannot be undone.",
            icon="warning",
            parent=self.window
        )

        if not confirm1:
            return

        # Second confirmation dialog for extra safety
        confirm2 = messagebox.askyesno(
            "Final Confirmation",
            f"Please confirm by typing your username: {self.app.username}\n\n"
            "Type 'YES' below to permanently delete all data:",
            icon="warning",
            parent=self.window
        )

        if not confirm2:
            return

        # Get user ID
        try:
            from app.db import get_session
            session = get_session()
            user = session.query(User).filter_by(username=self.app.username).first()
            session.close()

            if not user:
                messagebox.showerror("Error", "User not found.", parent=self.window)
                return

            user_id = user.id

        except Exception as e:
            logging.error(f"Error getting user ID: {e}")
            messagebox.showerror("Error", "Failed to identify user.", parent=self.window)
            return

        # Perform deletion
        try:
            from app.db import delete_user_data
            success = delete_user_data(user_id)

            if success:
                messagebox.showinfo(
                    "Data Deleted",
                    "All your personal data has been permanently deleted.\n\n"
                    "You will now be logged out.",
                    parent=self.window
                )

                # Log out the user by switching to login view
                # Assuming the app has a switch_view method and "login" view
                if hasattr(self.app, 'switch_view'):
                    self.app.switch_view("login")
                else:
                    # Fallback: destroy current window and restart app
                    self.window.quit()

            else:
                messagebox.showerror(
                    "Deletion Failed",
                    "Failed to delete your data. Please try again or contact support.",
                    parent=self.window
                )

        except Exception as e:
            logging.error(f"Error during data deletion: {e}")
            messagebox.showerror(
                "Error",
                "An error occurred while deleting your data. Please contact support.",
                parent=self.window
            )
