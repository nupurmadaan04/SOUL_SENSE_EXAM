import tkinter as tk
from tkinter import ttk

class TagInput(tk.Frame):
    def __init__(self, parent, tags=None, on_change=None, max_tags=10, max_char=25, colors=None, suggestion_list=None):
        """
        A component for adding/removing text tags (chips).
        
        Args:
            parent: Parent widget
            tags: Initial list of strings e.g. ["Python", "AI"]
            on_change: Callback function(tags_list) called on add/remove
            max_tags: Maximum number of tags allowed (default 10)
            max_char: Maximum characters per tag (default 25)
            colors: Dict of app colors
            suggestion_list: Optional list of strings for suggestions (future impl)
        """
        self.colors = colors or {}
        bg_color = self.colors.get("card_bg", "white")
        
        super().__init__(parent, bg=bg_color)
        
        self.tags = tags or []
        self.on_change = on_change
        self.max_tags = max_tags
        self.max_char = max_char
        
        # --- Entry Area ---
        self.entry_var = tk.StringVar()
        entry_bg = self.colors.get("bg_secondary", "#F8FAFC")
        entry_fg = self.colors.get("text_primary", "#1E293B")
        
        self.entry = tk.Entry(
            self, 
            textvariable=self.entry_var, 
            font=("Segoe UI", 12), # Increased size
            bg=entry_bg,
            fg=entry_fg, # Explicit text color
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors.get("border", "#E2E8F0")
        )
        self.entry.pack(fill="x", pady=(0, 10), ipady=5)
        self.entry.bind("<Return>", self._add_tag)
        
        # --- Tag Container (Flow Layout) ---
        # We use a Frame that wraps its children
        self.tag_container = tk.Frame(self, bg=bg_color)
        self.tag_container.pack(fill="both", expand=True)
        
        self.suggestion_list = suggestion_list or []
        
        # --- Suggestion Container ---
        self.suggestion_frame = tk.Frame(self, bg=bg_color)
        self.suggestion_frame.pack(fill="x", pady=(5, 0))
        
        self._render_tags()
        self._render_suggestions()

    def _add_tag(self, event=None, tag_to_add=None):
        text = tag_to_add if tag_to_add else self.entry_var.get().strip()
        
        # Validation checks (Edge Case implemented)
        if not text:
            return
        
        if len(self.tags) >= self.max_tags:
            # Shake animation or visual cue could go here
            self.entry.config(highlightbackground="red")
            self.after(500, lambda: self.entry.config(highlightbackground=self.colors.get("border", "#E2E8F0")))
            return
            
        if len(text) > self.max_char:
            # Truncate or warn? Truncate for now.
             text = text[:self.max_char]
             
        # Deduplication (Case-insensitive)
        if any(t.lower() == text.lower() for t in self.tags):
            self.entry_var.set("") # Clear input
            return

        self.tags.append(text)
        if not tag_to_add: self.entry_var.set("")
        
        self._render_tags()
        self._render_suggestions()
        
        if self.on_change:
            self.on_change(self.tags)

    def _remove_tag(self, tag_text):
        if tag_text in self.tags:
            self.tags.remove(tag_text)
            self._render_tags()
            self._render_suggestions()
            if self.on_change:
                self.on_change(self.tags)

    def _render_tags(self):
        # Clear existing
        for w in self.tag_container.winfo_children():
            w.destroy()
            
        # Basic flow layout simulation with grid
        # Note: A real flow layout in Tkinter is complex. 
        # For simplicity, we'll use a wrapper frame that packs left, 
        # and if it overflows, we rely on the parent to handle it (or basic wrapping logic).
        # Improving loop for basic wrapping:
        
        row = 0
        col = 0
        max_cols = 3 # Approximate columns before wrapping
        
        for tag in self.tags:
            chip = self._create_chip(tag)
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="w")
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _render_suggestions(self):
        if not self.suggestion_list:
            return
            
        for w in self.suggestion_frame.winfo_children():
            w.destroy()
            
        # Filter available suggestions
        available = [s for s in self.suggestion_list if not any(t.lower() == s.lower() for t in self.tags)]
        
        if not available:
            return
            
        tk.Label(self.suggestion_frame, text="Suggested:", font=("Segoe UI", 9, "italic"), bg=self.colors.get("card_bg"), fg="gray").pack(side="left", padx=(0, 5))
        
        # Limit visible suggestions
        for s in available[:4]:
            lbl = tk.Label(
                self.suggestion_frame, 
                text=f"+ {s}", 
                font=("Segoe UI", 9), 
                bg=self.colors.get("bg_secondary", "#F1F5F9"), 
                fg=self.colors.get("primary", "blue"),
                cursor="hand2",
                padx=6, pady=2
            )
            lbl.pack(side="left", padx=2)
            lbl.bind("<Button-1>", lambda e, t=s: self._add_tag(tag_to_add=t))
            
            # Hover effect
            def on_enter(e, widget=lbl): widget.config(fg=self.colors.get("primary_hover", "darkblue"), font=("Segoe UI", 9, "bold"))
            def on_leave(e, widget=lbl): widget.config(fg=self.colors.get("primary", "blue"), font=("Segoe UI", 9))
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)

    def _create_chip(self, text):
        # Chip Container
        chip_bg = self.colors.get("primary", "#3B82F6")
        chip_fg = "white"
        
        frame = tk.Frame(self.tag_container, bg=chip_bg, padx=8, pady=4)
        
        # Label
        lbl = tk.Label(frame, text=text, bg=chip_bg, fg=chip_fg, font=("Segoe UI", 9, "bold"))
        lbl.pack(side="left")
        
        # Close Button (x)
        # Using a label as a button for tighter control
        btn = tk.Label(frame, text="×", bg=chip_bg, fg=chip_fg, font=("Arial", 11, "bold"), cursor="hand2")
        btn.pack(side="left", padx=(6, 0))
        btn.bind("<Button-1>", lambda e, t=text: self._remove_tag(t))
        
        # Hover effect for close button
        def on_enter(e): btn.config(fg="#EF4444") # Red on hover
        def on_leave(e): btn.config(fg=chip_fg)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return frame

    def get_tags(self):
        return self.tags
