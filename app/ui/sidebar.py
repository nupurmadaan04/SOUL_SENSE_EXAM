import tkinter as tk
from tkinter import ttk

class SidebarNav(tk.Frame):
    def __init__(self, parent, app, items, on_change=None):
        """
        Sidebar Navigation Component
        
        Args:
            parent: Parent widget
            app: App instance (for colors/styles)
            items: List of dicts {'id': str, 'icon': str, 'label': str}
            on_change: Callback function(item_id) when selection changes
        """
        super().__init__(parent, bg=app.colors.get("sidebar_bg"), width=250)
        self.app = app
        self.items = items
        self.on_change = on_change
        self.is_collapsed = False
        self.expanded_width = 250
        self.collapsed_width = 70
        self.buttons = {}
        self.active_id = None
        
        # Prevent auto-shrinking
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        self._render_header()
        self._render_items()
        self._render_footer()
        
    def _render_header(self):
        # User Profile Summary Area
        self.header_frame = tk.Frame(self, bg=self.app.colors.get("sidebar_bg"), height=100)
        self.header_frame.pack(fill="x", padx=10, pady=(20, 10))
        
        # Toggle Button (Top Right)
        self.toggle_btn = tk.Label(
            self.header_frame, 
            text="❮", 
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=self.app.colors.get("sidebar_divider", "#4A5568"),
            fg="white",
            padx=8,
            pady=2,
            cursor="hand2",
            relief="flat"
        )
        self.toggle_btn.pack(side="top", anchor="e", padx=5, pady=(0, 5))
        self.toggle_btn.bind("<Button-1>", lambda e: self.toggle_collapse())
        
        # Hover effect for toggle
        self.toggle_btn.bind("<Enter>", lambda e: self.toggle_btn.configure(bg=self.app.colors.get("sidebar_active", "#4C51BF")))
        self.toggle_btn.bind("<Leave>", lambda e: self.toggle_btn.configure(bg=self.app.colors.get("sidebar_divider", "#4A5568")))

        # Main Header Content (Avatar + Name)
        self.header_content = tk.Frame(self.header_frame, bg=self.app.colors.get("sidebar_bg"))
        self.header_content.pack(fill="both", expand=True)

        # Avatar Placeholder (Circle)
        self.avatar_canvas = tk.Canvas(self.header_content, width=60, height=60, bg=self.app.colors.get("sidebar_bg"), highlightthickness=0, cursor="hand2")
        self.avatar_canvas.pack(side="left")
        
        # Load existing avatar if available
        self._load_avatar()
        
        self.avatar_canvas.bind("<Button-1>", self._upload_avatar)
        
        # Name Info
        self.info_frame = tk.Frame(self.header_content, bg=self.app.colors.get("sidebar_bg"))
        self.info_frame.pack(side="left", padx=15, fill="both", expand=True)
        
        self.name_label = tk.Label(
            self.info_frame, 
            text=self.app.username or "Guest",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=self.app.colors.get("sidebar_bg"),
            fg="white",
            anchor="w"
        )
        self.name_label.pack(fill="x", pady=(10, 0))
        
        self.edit_label = tk.Label(
            self.info_frame, 
            text="View Profile", 
            font=self.app.ui_styles.get_font("xs"),
            bg=self.app.colors.get("sidebar_bg"),
            fg=self.app.colors.get("sidebar_divider"),
            anchor="w",
            cursor="hand2"
        )
        self.edit_label.pack(fill="x")
        
        # Bind Name/Info to Open Profile Tab
        for widget in [self.info_frame, self.name_label, self.edit_label]:
            widget.bind("<Button-1>", lambda e: self.select_item("profile"))
            widget.configure(cursor="hand2")
        
    def _load_avatar(self):
        import os
        from PIL import Image, ImageTk, ImageDraw
        
        avatar_path = os.path.join("app_data", "avatars", f"{self.app.username}_avatar.png")
        
        self.avatar_canvas.delete("all")
        
        if os.path.exists(avatar_path):
            try:
                # Load and Resize for display (60x60)
                img = Image.open(avatar_path)
                img = img.resize((56, 56), Image.Resampling.LANCZOS)
                
                # Circular Mask (Safety check)
                # Ensure the saved image is proper, but for display we can just blit it inside a circle?
                # Actually, ImageCropper saves a transparent circular PNG.
                # Just displaying it is enough.
                
                self.tk_avatar = ImageTk.PhotoImage(img) # Keep ref
                
                # Draw white border circle
                self.avatar_canvas.create_oval(2, 2, 58, 58, fill="white", outline=self.app.colors.get("sidebar_divider"))
                # Place image center
                self.avatar_canvas.create_image(30, 30, image=self.tk_avatar, anchor="center")
                
            except Exception as e:
                print(f"Error loading avatar: {e}")
                self._draw_initials_avatar()
        else:
            self._draw_initials_avatar()

    def _draw_initials_avatar(self):
        self.avatar_canvas.delete("all")
        self.avatar_canvas.create_oval(5, 5, 55, 55, fill="white", outline=self.app.colors.get("sidebar_divider"))
        initial = self.app.username[0].upper() if self.app.username else "?"
        self.avatar_canvas.create_text(30, 30, text=initial, font=self.app.ui_styles.get_font("h2", "bold"), fill=self.app.colors.get("sidebar_bg"))

    def _upload_avatar(self, event=None):
        from tkinter import filedialog, messagebox
        import os
        from app.ui.components.image_cropper import AvatarCropper
        
        file_path = filedialog.askopenfilename(
            title="Select Profile Picture",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
        )
        
        if file_path:
            # Audit Check: File Size < 5MB
            if os.path.getsize(file_path) > 5 * 1024 * 1024:
                messagebox.showwarning("File too large", "Please select an image smaller than 5MB.")
                return
            
            try:
                # Create app_data/avatars directory
                avatar_dir = os.path.join("app_data", "avatars")
                os.makedirs(avatar_dir, exist_ok=True)
                dest_path = os.path.join(avatar_dir, f"{self.app.username}_avatar.png") 
                
                # Open Cropper Dialog
                AvatarCropper(self, file_path, dest_path, on_complete=self._on_crop_complete)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open cropper: {e}")

    def _on_crop_complete(self):
        # Refresh the avatar immediately
        self._load_avatar()

    def _render_items(self):
        self.nav_frame = tk.Frame(self, bg=self.app.colors.get("sidebar_bg"))
        self.nav_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for item in self.items:
            self._create_nav_item(item)
            
    def _create_nav_item(self, item):
        item_id = item["id"]
        
        btn_frame = tk.Frame(self.nav_frame, bg=self.app.colors.get("sidebar_bg"), cursor="hand2", height=50)
        btn_frame.pack(fill="x", pady=2)
        btn_frame.pack_propagate(False)
        
        # Active Indicator (Left Bar) - Hidden by default
        indicator = tk.Frame(btn_frame, bg=self.app.colors.get("sidebar_bg"), width=4)
        indicator.pack(side="left", fill="y", pady=8, padx=(0, 8))
        
        # Icon
        lbl_icon = tk.Label(
            btn_frame, 
            text=item.get("icon", "•"), 
            font=self.app.ui_styles.get_font("md"),
            bg=self.app.colors.get("sidebar_bg"),
            fg=self.app.colors.get("sidebar_fg")
        )
        lbl_icon.pack(side="left", padx=5)
        
        # Label
        lbl_text = tk.Label(
            btn_frame, 
            text=item.get("label", item_id.title()), 
            font=self.app.ui_styles.get_font("sm"),
            bg=self.app.colors.get("sidebar_bg"),
            fg=self.app.colors.get("sidebar_fg")
        )
        lbl_text.pack(side="left", padx=10)
        
        # Store references
        self.buttons[item_id] = {
            "frame": btn_frame,
            "indicator": indicator,
            "icon": lbl_icon,
            "text": lbl_text
        }
        
        # Bind events
        for widget in [btn_frame, lbl_icon, lbl_text, indicator]:
            widget.bind("<Button-1>", lambda e, i=item_id: self.select_item(i))
            widget.bind("<Enter>", lambda e, i=item_id: self._on_hover(i, True))
            widget.bind("<Leave>", lambda e, i=item_id: self._on_hover(i, False))
            
    def _on_hover(self, item_id, is_hovering):
        if item_id == self.active_id:
            return
            
        widgets = self.buttons[item_id]
        bg_color = self.app.colors.get("sidebar_hover") if is_hovering else self.app.colors.get("sidebar_bg")
        
        widgets["frame"].configure(bg=bg_color)
        widgets["icon"].configure(bg=bg_color)
        widgets["text"].configure(bg=bg_color)
        widgets["indicator"].configure(bg=bg_color)

    def select_item(self, item_id, trigger_callback=True):
        # Allow re-clicking to refresh view (User Requested)
        # if self.active_id == item_id:
        #     return
            
        # Reset old active
        if self.active_id:
            self._update_item_style(self.active_id, False)
            
        # Set new active
        self.active_id = item_id
        self._update_item_style(item_id, True)
        
        if self.on_change and trigger_callback:
            self.on_change(item_id)
            
    def _render_footer(self):
        """Render Logout button at the bottom"""
        self.footer_frame = tk.Frame(self, bg=self.app.colors.get("sidebar_bg"), height=60)
        self.footer_frame.pack(side="bottom", fill="x", padx=10, pady=20)
        self.footer_frame.pack_propagate(False)

        # Divider
        divider = tk.Frame(self.footer_frame, bg=self.app.colors.get("sidebar_divider"), height=1)
        divider.pack(fill="x", side="top", pady=(0, 10))

        # Logout Button
        logout_btn = tk.Frame(self.footer_frame, bg=self.app.colors.get("sidebar_bg"), cursor="hand2", height=40)
        logout_btn.pack(fill="x")
        logout_btn.pack_propagate(False)

        # Icon
        self.logout_icon = tk.Label(
            logout_btn, 
            text="🚪", 
            font=self.app.ui_styles.get_font("md"),
            bg=self.app.colors.get("sidebar_bg"),
            fg=self.app.colors.get("sidebar_fg")
        )
        self.logout_icon.pack(side="left", padx=5)

        # Label
        self.logout_text = tk.Label(
            logout_btn, 
            text="Logout", 
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=self.app.colors.get("sidebar_bg"),
            fg=self.app.colors.get("sidebar_fg")
        )
        self.logout_text.pack(side="left", padx=10)

        # Bindings
        for widget in [logout_btn, self.logout_icon, self.logout_text]:
            widget.bind("<Button-1>", lambda e: self.app.logout())
            widget.bind("<Enter>", lambda e: self._on_logout_hover(True))
            widget.bind("<Leave>", lambda e: self._on_logout_hover(False))

        self.logout_btn_frame = logout_btn

    def _on_logout_hover(self, is_hovering):
        bg_color = self.app.colors.get("sidebar_hover") if is_hovering else self.app.colors.get("sidebar_bg")
        self.logout_btn_frame.configure(bg=bg_color)
        self.logout_icon.configure(bg=bg_color)
        self.logout_text.configure(bg=bg_color)

    def toggle_collapse(self):
        """Toggle between mini and full sidebar with animation"""
        if self.app.is_animating: return # Debounce
        
        self.app.is_animating = True
        self.is_collapsed = not self.is_collapsed
        target_width = self.collapsed_width if self.is_collapsed else self.expanded_width
        
        # Update Icon immediately
        self.toggle_btn.configure(text="❯" if self.is_collapsed else "❮")
        
        if self.is_collapsed:
            # Preparing for collapse: hide text early to avoid layout glitch
            self.info_frame.pack_forget()
            self.header_frame.configure(padx=0)
            self.avatar_canvas.pack(side="top", pady=10)
            
            for item_id, widgets in self.buttons.items():
                widgets["text"].pack_forget()
                widgets["indicator"].pack_forget()
                widgets["icon"].pack(side="top", pady=10, fill="none", expand=True)
                
            if hasattr(self, 'footer_frame'):
                self.logout_text.pack_forget()
                self.logout_icon.pack(side="top", pady=10, fill="none", expand=True)

        self._animate_sidebar(target_width)

    def _animate_sidebar(self, target_width):
        """Step-based width animation"""
        current_width = self.winfo_width()
        # Balanced speed: 30px step @ 20ms delay ~ 1.5px/ms
        step = 30
        
        if abs(current_width - target_width) <= step:
            self.configure(width=target_width)
            self._finalize_toggle_state()
            return

        next_width = current_width + (step if target_width > current_width else -step)
        self.configure(width=next_width)
        # Increase delay to 20ms (50fps) to reduce main thread load during complex layout resizing
        self.after(20, lambda: self._animate_sidebar(target_width))

    def _finalize_toggle_state(self):
        """Finalize UI elements after animation finish"""
        self.app.is_animating = False
        
        if not self.is_collapsed:
            # Restoration for Expanded Mode
            self.avatar_canvas.pack_forget()
            self.avatar_canvas.pack(side="left", pady=0)
            self.info_frame.pack(side="left", padx=15, fill="both", expand=True)
            self.header_frame.configure(padx=10)
            
            for item_id, widgets in self.buttons.items():
                # Clear and Repack to ensure order
                widgets["indicator"].pack_forget()
                widgets["icon"].pack_forget()
                widgets["text"].pack_forget()
                
                widgets["indicator"].pack(side="left", fill="y", pady=8, padx=(0, 8))
                widgets["icon"].pack(side="left", padx=5)
                widgets["text"].pack(side="left", padx=10)
                widgets["frame"].configure(padx=0)

            if hasattr(self, 'footer_frame'):
                self.logout_icon.pack_forget()
                self.logout_text.pack_forget()
                self.logout_icon.pack(side="left", padx=5)
                self.logout_text.pack(side="left", padx=10)

    def _update_item_style(self, item_id, is_active):
        if item_id not in self.buttons:
            return

        widgets = self.buttons[item_id]
        
        # Colors
        if is_active:
            bg_color = self.app.colors.get("sidebar_active")
            fg_color = "white"
            indicator_color = "white"
        else:
            bg_color = self.app.colors.get("sidebar_bg")
            fg_color = self.app.colors.get("sidebar_fg")
            indicator_color = bg_color # Hide by matching bg
            
        widgets["frame"].configure(bg=bg_color)
        widgets["icon"].configure(bg=bg_color, fg=fg_color)
        widgets["text"].configure(bg=bg_color, fg=fg_color)
        widgets["indicator"].configure(bg=indicator_color)

    def update_theme(self):
        """Update colors for all sidebar elements"""
        # Main background
        self.configure(bg=self.app.colors.get("sidebar_bg"))
        self.nav_frame.configure(bg=self.app.colors.get("sidebar_bg"))
        
        # Update Header
        if hasattr(self, 'name_label'):
             self.name_label.configure(bg=self.app.colors.get("sidebar_bg"), fg="white")
        if hasattr(self, 'edit_label'):
             self.edit_label.configure(bg=self.app.colors.get("sidebar_bg"), fg=self.app.colors.get("sidebar_divider"))
        
        # Recursive update for all children to ensure nested frames (like info_frame) get updated
        def update_recursive(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.Canvas)):
                     widget.configure(bg=self.app.colors.get("sidebar_bg"))
                elif isinstance(widget, tk.Label):
                     # Be careful not to overwrite custom fgs, but bg should match sidebar
                     # Unless it's a specific button label. 
                     # For header labels, we handled them above or they match sidebar_bg
                     if widget not in self.buttons.values(): # Don't touch nav buttons here
                        widget.configure(bg=self.app.colors.get("sidebar_bg"))
                
                for child in widget.winfo_children():
                    update_recursive(child)
            except:
                pass

        # Update non-nav items (Header)
        for widget in self.winfo_children():
            if widget != self.nav_frame:
                update_recursive(widget)

        # Update Buttons
        for item_id, widgets in self.buttons.items():
            is_active = (item_id == self.active_id)
            self._update_item_style(item_id, is_active)

        # Update Footer
        if hasattr(self, 'footer_frame'):
            self.footer_frame.configure(bg=self.app.colors.get("sidebar_bg"))
            self.logout_btn_frame.configure(bg=self.app.colors.get("sidebar_bg"))
            self.logout_icon.configure(bg=self.app.colors.get("sidebar_bg"), fg=self.app.colors.get("sidebar_fg"))
            self.logout_text.configure(bg=self.app.colors.get("sidebar_bg"), fg=self.app.colors.get("sidebar_fg"))

    def update_user_info(self):
        """Update username display and avatar after login"""
        if hasattr(self, 'name_label'):
            self.name_label.configure(text=self.app.username or "Guest")
        
        # Reload avatar
        self._load_avatar()
