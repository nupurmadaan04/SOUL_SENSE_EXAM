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
        self.buttons = {}
        self.active_id = None
        
        # Prevent auto-shrinking
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        self._render_header()
        self._render_items()
        
    def _render_header(self):
        # User Profile Summary Area
        header = tk.Frame(self, bg=self.app.colors.get("sidebar_bg"), height=100)
        header.pack(fill="x", padx=20, pady=30)
        
        # Avatar Placeholder (Circle)
        self.avatar_canvas = tk.Canvas(header, width=60, height=60, bg=self.app.colors.get("sidebar_bg"), highlightthickness=0, cursor="hand2")
        self.avatar_canvas.pack(side="left")
        
        # Load existing avatar if available
        self._load_avatar()
        
        self.avatar_canvas.bind("<Button-1>", self._upload_avatar)
        
        # Name Info
        info_frame = tk.Frame(header, bg=self.app.colors.get("sidebar_bg"))
        info_frame.pack(side="left", padx=15, fill="both", expand=True)
        
        self.name_label = tk.Label(
            info_frame, 
            text=self.app.username or "Guest",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=self.app.colors.get("sidebar_bg"),
            fg="white",
            anchor="w"
        )
        self.name_label.pack(fill="x", pady=(10, 0))
        
        self.edit_label = tk.Label(
            info_frame, 
            text="View Profile", 
            font=self.app.ui_styles.get_font("xs"),
            bg=self.app.colors.get("sidebar_bg"),
            fg=self.app.colors.get("sidebar_divider"),
            anchor="w",
            cursor="hand2"
        )
        self.edit_label.pack(fill="x")
        
        # Bind Name/Info to Open Profile Tab
        for widget in [info_frame, self.name_label, self.edit_label]:
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

    def update_user_info(self):
        """Update username display and avatar after login"""
        if hasattr(self, 'name_label'):
            self.name_label.configure(text=self.app.username or "Guest")
        
        # Reload avatar
        self._load_avatar()
