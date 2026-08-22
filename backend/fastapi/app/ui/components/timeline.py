import tkinter as tk
from tkinter import ttk
import logging
from datetime import datetime

class LifeTimeline(tk.Frame):
    def __init__(self, parent, events=None, on_add=None, colors=None):
        """
        Interactive Timeline Component
        
        Args:
            parent: Parent widget
            events: List of dicts [{date, title, description, impact}]
            on_add: Callback when 'Add Event' is clicked
            colors: Dict of app colors
        """
        self.colors = colors or {}
        bg_color = self.colors.get("card_bg", "white")
        
        super().__init__(parent, bg=bg_color)
        
        self.events = events or []
        self.on_add = on_add
        self.on_click = None # Helper for edit/delete
        
        # Sort events by date (Safety Measure)
        self._sort_events()
        
        self._create_header()
        
        # Scrollable Canvas for Timeline
        self.canvas_frame = tk.Frame(self, bg=bg_color)
        self.canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg_color)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=500) # Fixed width base
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        # self.scrollbar.pack(side="right", fill="y") # HIDDEN as requested
        
        # Smart Scroll: Bind only when hovering
        def _on_mousewheel_local(event):
            try:
                if self.canvas.winfo_exists():
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except Exception: pass

        def _bind_mouse(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel_local)
            
        def _unbind_mouse(event):
            try: self.canvas.unbind_all("<MouseWheel>")
            except: pass

        self.canvas.bind("<Enter>", _bind_mouse)
        self.canvas.bind("<Leave>", _unbind_mouse)
        
        self._render_events()

    def _sort_events(self):
        try:
            # Audit: Sort by date safely
            self.events.sort(key=lambda x: x.get('date', '9999-12-31') or '9999-12-31', reverse=True)
        except Exception as e:
            logging.error(f"Error sorting events: {e}")

    def _create_header(self):
        header = tk.Frame(self, bg=self.colors.get("card_bg"))
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(
            header,
            text="Life Journey",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors.get("card_bg"),
            fg=self.colors.get("text_primary", "black")
        ).pack(side="left")
        
        if self.on_add:
            tk.Button(
                header,
                text="+ Add Event",
                command=self.on_add,
                bg=self.colors.get("primary", "blue"),
                fg="white",
                relief="flat",
                font=("Segoe UI", 10, "bold"),
                padx=10
            ).pack(side="right")

    def _render_events(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        if not self.events:
            tk.Label(
                self.scrollable_frame,
                text="No life events added yet.\nStart your timeline above!",
                font=("Segoe UI", 10, "italic"),
                bg=self.colors.get("card_bg"),
                fg="gray",
                pady=40
            ).pack(fill="x")
            return

        # Render Nodes
        for i, event in enumerate(self.events):
            self._create_event_node(event, is_last=(i == len(self.events) - 1))

    def _create_event_node(self, event, is_last=False):
        row = tk.Frame(self.scrollable_frame, bg=self.colors.get("card_bg"), cursor="hand2")
        row.pack(fill="x")
        
        # 1. Date Column
        date_str = event.get('date', 'Unknown')
        tk.Label(
            row, text=date_str, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.colors.get("card_bg"), 
            fg="gray", 
            width=12, anchor="e"
        ).pack(side="left", padx=(0, 10), anchor="n", pady=5)
        
        # 2. Line & Dot Column
        line_col = tk.Frame(row, bg=self.colors.get("card_bg"), width=20)
        line_col.pack(side="left", fill="y")
        
        # Canvas for drawing
        canvas = tk.Canvas(line_col, width=20, height=80, bg=self.colors.get("card_bg"), highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # Draw Line
        line_color = self.colors.get("border", "#E2E8F0")
        if not is_last:
            canvas.create_line(10, 15, 10, 100, fill=line_color, width=2)
            
        # Draw Dot
        canvas.create_oval(4, 9, 16, 21, fill=self.colors.get("secondary", "purple"), outline="")
        
        # 3. Content Column
        content = tk.Frame(row, bg=self.colors.get("card_bg"))
        content.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=(0, 20))
        
        lbl_title = tk.Label(
            content, text=event.get('title', 'Untitled'),
            font=("Segoe UI", 12, "bold"),
            bg=self.colors.get("card_bg"), fg=self.colors.get("text_primary")
        )
        lbl_title.pack(anchor="w")
        
        desc = event.get('description', '')
        if len(desc) > 200:
             desc = desc[:200] + "..." # Audit: Truncate long text
             
        lbl_desc = tk.Label(
            content, text=desc,
            font=("Segoe UI", 10),
            bg=self.colors.get("card_bg"), fg=self.colors.get("text_secondary"),
            wraplength=400, justify="left"
        )
        lbl_desc.pack(anchor="w")
        
        # Bind Click Events
        # We bind to all major visible widgets in the row
        if self.on_click:
            for widget in [row, content, lbl_title, lbl_desc]:
                widget.bind("<Button-1>", lambda e, ev=event: self.on_click(ev))
                widget.configure(cursor="hand2")

    def refresh(self, events):
        self.events = events
        self._sort_events()
        self._render_events()
