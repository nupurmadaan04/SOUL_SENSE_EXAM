"""Timeline component for life events"""
import tkinter as tk
from typing import List, Dict, Callable, Optional

class LifeTimeline:
    def __init__(self, parent, events: List[Dict] = None, on_add: Callable = None, colors: Dict = None):
        self.parent = parent
        self.events = events or []
        self.on_add = on_add
        self.colors = colors or {}
        self.on_click = None
        
        self.frame = tk.Frame(parent, bg=self.colors.get("card_bg", "white"))
        
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
        self._render()
    
    def refresh(self, events: List[Dict]):
        self.events = events
        self._render()
    
    def _render(self):
        # Clear existing widgets
        for widget in self.frame.winfo_children():
            widget.destroy()
        
        # Header
        header = tk.Frame(self.frame, bg=self.colors.get("card_bg", "white"))
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        tk.Label(
            header, text="📅 Life Timeline", 
            font=("Segoe UI", 14, "bold"),
            bg=self.colors.get("card_bg", "white"), 
            fg=self.colors.get("text_primary", "black")
        ).pack(side="left")
        
        if self.on_add:
            tk.Button(
                header, text="+ Add Event", command=self.on_add,
                font=("Segoe UI", 10), bg=self.colors.get("primary", "blue"), 
                fg="white", relief="flat", padx=10, pady=5
            ).pack(side="right")
        
        # Events list
        content = tk.Frame(self.frame, bg=self.colors.get("card_bg", "white"))
        content.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        if not self.events:
            tk.Label(
                content, text="No life events added yet.\nClick 'Add Event' to get started!",
                font=("Segoe UI", 11), bg=self.colors.get("card_bg", "white"), 
                fg="gray", justify="center"
            ).pack(pady=20)
        else:
            # Sort events by date
            sorted_events = sorted(self.events, key=lambda x: x.get("date", ""), reverse=True)
            
            for event in sorted_events:
                self._create_event_item(content, event)
    
    def _create_event_item(self, parent, event: Dict):
        item = tk.Frame(parent, bg=self.colors.get("card_bg", "white"))
        item.pack(fill="x", pady=5)
        
        # Date
        tk.Label(
            item, text=event.get("date", ""), 
            font=("Segoe UI", 10, "bold"),
            bg=self.colors.get("card_bg", "white"), 
            fg=self.colors.get("primary", "blue")
        ).pack(anchor="w")
        
        # Title
        tk.Label(
            item, text=event.get("title", ""), 
            font=("Segoe UI", 12, "bold"),
            bg=self.colors.get("card_bg", "white"), 
            fg=self.colors.get("text_primary", "black")
        ).pack(anchor="w")
        
        # Description (truncated)
        desc = event.get("description", "")
        if len(desc) > 100:
            desc = desc[:100] + "..."
        
        tk.Label(
            item, text=desc, 
            font=("Segoe UI", 10),
            bg=self.colors.get("card_bg", "white"), 
            fg="gray",
            wraplength=300, justify="left"
        ).pack(anchor="w", pady=(0, 5))
        
        # Make clickable
        if self.on_click:
            item.bind("<Button-1>", lambda e: self.on_click(event))
            item.configure(cursor="hand2")