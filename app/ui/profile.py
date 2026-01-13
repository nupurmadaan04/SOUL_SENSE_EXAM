import tkinter as tk
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

class UserProfileView:
    def __init__(self, parent_root, app_instance):
        self.parent_root = parent_root
        self.app = app_instance
        self.i18n = app_instance.i18n
        self.colors = app_instance.colors
        
        # Window Setup
        self.window = tk.Toplevel(parent_root)
        self.window.title(self.i18n.get("profile.title"))
        self.window.geometry("1100x750") # Wider for sidebar
        self.window.configure(bg=self.colors.get("bg_secondary", "#F1F5F9"))
        
        # Center the window
        self.center_window()
        
        # Main Layout Container
        self.main_container = tk.Frame(self.window, bg=self.colors.get("bg_secondary"))
        self.main_container.pack(fill="both", expand=True)
        
        # --- LEFT SIDEBAR ---
        self.sidebar = SidebarNav(
            self.main_container, 
            self.app,
            items=[
                {"id": "medical", "icon": "🏥", "label": self.i18n.get("profile.tab_medical")},
                {"id": "history", "icon": "📜", "label": "Personal History"},
                {"id": "strengths", "icon": "💪", "label": "Strengths & Goals"}, # New Tab
                {"id": "settings", "icon": "⚙️", "label": "Settings"},
            ],
            on_change=self.on_nav_change
        )
        self.sidebar.pack(side="left", fill="y")
        
        # --- RIGHT CONTENT AREA ---
        self.content_area = tk.Frame(self.main_container, bg=self.colors.get("bg_secondary"))
        self.content_area.pack(side="left", fill="both", expand=True, padx=30, pady=30)
        
        # Header (Top of Content Area)
        self.header_label = tk.Label(
            self.content_area,
            text="Profile",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors.get("bg_secondary"),
            fg=self.colors.get("text_primary")
        )
        self.header_label.pack(anchor="w", pady=(0, 20))
        
        # Content Dynamic Frame with Scrollbar
        container_frame = tk.Frame(self.content_area, bg=self.colors.get("bg_secondary"))
        container_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container_frame, bg=self.colors.get("bg_secondary"), highlightthickness=0)
        
        # User requested hidden scrollbars but functional scrolling
        self.scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=self.canvas.yview)
        # self.scrollbar.pack(side="right", fill="y") # HIDDEN as requested
        
        self.view_container = tk.Frame(self.canvas, bg=self.colors.get("bg_secondary"))
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.view_container, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Ensure inner frame expands to fill width AND minimal height
        def _on_canvas_configure(event):
            current_width = event.width
            # Force height to be at least the canvas height (fill screen)
            # effectively mimicking expand=True behavior for the inner frame
            min_height = max(event.height, self.view_container.winfo_reqheight())
            self.canvas.itemconfig(self.canvas_window, width=current_width, height=min_height)
            
        self.canvas.bind("<Configure>", _on_canvas_configure)
        
        # Also update height when content changes
        self.view_container.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, height=max(self.canvas.winfo_height(), e.height)) or self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Smart Scroll: Bind only when hovering
        def _on_mousewheel(event):
             if self.canvas.winfo_exists():
                # Check if we should scroll (if content is larger than viewport)
                if self.canvas.bbox("all")[3] > self.canvas.winfo_height():
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_mouse(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_mouse(event):
            try: self.canvas.unbind_all("<MouseWheel>")
            except: pass

        self.canvas.bind("<Enter>", _bind_mouse)
        self.canvas.bind("<Leave>", _unbind_mouse)
        
        # Views Cache
        self.views = {}
        
        # Initialize default view
        self.sidebar.select_item("medical")

    def center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def on_nav_change(self, view_id):
        # Clear current view
        for widget in self.view_container.winfo_children():
            widget.destroy()
            
        # FORCE SCROLL RESET: Reset to top
        self.canvas.yview_moveto(0)
            
        if view_id == "medical":
            self.header_label.configure(text=self.i18n.get("profile.header", name=self.app.username))
            self._render_medical_view()
        elif view_id == "history":
            self.header_label.configure(text="Personal History")
            self._render_history_view()
        elif view_id == "strengths":
            self.header_label.configure(text="Strengths & Goals")
            self._render_strengths_view()
        elif view_id == "settings":
            self.header_label.configure(text="Account Settings")
            self._render_settings_view()

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
        paned = tk.PanedWindow(self.view_container, orient=tk.HORIZONTAL, bg=self.colors.get("bg_secondary"), sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True)
        
        # --- LEFT COLUMN: Form ---
        left_col = tk.Frame(paned, bg=self.colors.get("bg_secondary"))
        # Add to pane
        paned.add(left_col, width=350, minsize=250, sticky="nsew", padx=0) # padx tuple not supported in PanedWindow add
        
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
        
        # Save Button for Profile Details
        save_profile_btn = tk.Button(
            form_content, text="Save Details", command=self.save_personal_data,
            bg=self.colors.get("primary", "#3B82F6"), fg="white", 
            font=("Segoe UI", 10, "bold"), relief="flat", pady=8
        )
        save_profile_btn.pack(fill="x", pady=20)

        # --- RIGHT COLUMN: Timeline ---
        right_col = tk.Frame(paned, bg=self.colors.get("bg_secondary"))
        paned.add(right_col, minsize=400, sticky="nsew", padx=0)
        
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
            title = title_var.get().strip()
            desc = desc_text.get("1.0", tk.END).strip()
            
            if not title:
                messagebox.showwarning("Incomplete", "Title is required.")
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
                 
             profile.occupation = self.occ_var.get()
             profile.education = self.edu_var.get()
             profile.marital_status = self.status_var.get()
             profile.bio = self.bio_text.get("1.0", tk.END).strip()
             
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

    def _render_settings_view(self):
        # Placeholder for settings
        tk.Label(self.view_container, text="Settings coming soon...", font=("Segoe UI", 14), bg=self.colors.get("bg_secondary"), fg="gray").pack(pady=50)

    # --- UI Helpers ---
    def _create_section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 16, "bold"), bg=self.colors.get("card_bg"), fg=self.colors.get("sidebar_bg")).pack(anchor="w", pady=(0, 15))
        
    def _create_field_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"), bg=self.colors.get("card_bg"), fg="gray").pack(anchor="w", pady=(10, 5))
        
    def _create_entry(self, parent, variable):
        entry = tk.Entry(parent, textvariable=variable, font=("Segoe UI", 11), relief="flat", highlightthickness=1, highlightbackground=self.colors.get("card_border"))
        entry.pack(fill="x", ipady=8) # Taller input
        
    def _create_text_area(self, parent):
        txt = tk.Text(parent, height=4, font=("Segoe UI", 11), relief="flat", highlightthickness=1, highlightbackground=self.colors.get("card_border"))
        txt.pack(fill="x", pady=(0, 5))
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
                self.conditions_text.insert("1.0", profile.medical_conditions or "")
            else:
                self.blood_type_var.set("Unknown")
            
            session.close()
        except Exception as e:
            logging.error(f"Error loading medical profile: {e}")

    def save_medical_data(self):
        try:
            # --- VALIDATION ---
            contact_phone = self.ec_phone_var.get().strip()
            if contact_phone:
                if not any(char.isdigit() for char in contact_phone):
                     messagebox.showwarning("Validation Error", self.i18n.get("profile.validation_phone"), parent=self.window)
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
            profile.emergency_contact_name = self.ec_name_var.get()
            profile.emergency_contact_phone = contact_phone
            
            profile.allergies = self.allergies_text.get("1.0", tk.END).strip()
            profile.medications = self.medications_text.get("1.0", tk.END).strip()
            profile.medical_conditions = self.conditions_text.get("1.0", tk.END).strip()
            
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
        main_layout = tk.Frame(self.view_container, bg=self.colors.get("bg_secondary"))
        main_layout.pack(fill="both", expand=True)
        
        # Responsive PanedWindow
        paned = tk.PanedWindow(main_layout, orient=tk.HORIZONTAL, bg=self.colors.get("bg_secondary"), sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # --- LEFT COLUMN: Tags ---
        left_wrapper = tk.Frame(paned, bg=self.colors.get("bg_secondary"))
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
        right_wrapper = tk.Frame(paned, bg=self.colors.get("bg_secondary"))
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
        self.comm_style_combo.pack(fill="x", pady=(0, 20))
        
        # Boundaries
        self._create_section_label(right_col, "Privacy Boundaries")
        self._create_field_label(right_col, "Topics to Avoid")
        suggested_boundaries = ["Politics", "Religion", "Finances", "Family Matters", "Past Trauma"]
        self.boundaries_input = TagInput(right_col, max_tags=5, colors=self.colors, suggestion_list=suggested_boundaries)
        self.boundaries_input.pack(fill="x", pady=(0, 20))

        # Footer Actions (Overlay or Bottom of Main Layout)
        footer = tk.Frame(main_layout, bg=self.colors.get("bg_secondary"), height=60)
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
            strengths.goals = self.goals_text.get("1.0", tk.END).strip()
            
            session.commit()
            session.close()
            messagebox.showinfo("Success", "Preferences saved successfully!")
        except Exception as e:
            logging.error(f"Error saving strengths: {e}")
            messagebox.showerror("Error", "Failed to save preferences.")
