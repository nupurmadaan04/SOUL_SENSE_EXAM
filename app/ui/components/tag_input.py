"""Tag input component for strengths and skills"""
import tkinter as tk
from typing import List, Dict, Optional

class TagInput:
    def __init__(self, parent, max_tags: int = 5, max_char: int = 30, colors: Dict = None, suggestion_list: List[str] = None):
        self.parent = parent
        self.max_tags = max_tags
        self.max_char = max_char
        self.colors = colors or {}
        self.suggestions = suggestion_list or []
        self.tags = []
        
        self.frame = tk.Frame(parent, bg=self.colors.get("card_bg", "white"))
        self._setup_ui()
        
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def _setup_ui(self):
        # Entry field
        self.entry = tk.Entry(
            self.frame, font=("Segoe UI", 11),
            bg=self.colors.get("input_bg", "white"),
            fg=self.colors.get("input_fg", "black")
        )
        self.entry.pack(fill="x", pady=(0, 10))
        self.entry.bind("<Return>", self._add_tag)
        
        # Tags display area
        self.tags_frame = tk.Frame(self.frame, bg=self.colors.get("card_bg", "white"))
        self.tags_frame.pack(fill="x")
        
        # Suggestions
        if self.suggestions:
            self._create_suggestions()
    
    def _create_suggestions(self):
        sugg_frame = tk.Frame(self.frame, bg=self.colors.get("card_bg", "white"))
        sugg_frame.pack(fill="x", pady=(5, 0))
        
        tk.Label(
            sugg_frame, text="Suggestions:", 
            font=("Segoe UI", 9), bg=self.colors.get("card_bg", "white"), fg="gray"
        ).pack(anchor="w")
        
        for suggestion in self.suggestions[:6]:  # Show max 6 suggestions
            btn = tk.Button(
                sugg_frame, text=suggestion, 
                command=lambda s=suggestion: self._add_suggestion(s),
                font=("Segoe UI", 8), bg="#E5E7EB", fg="black",
                relief="flat", padx=8, pady=2
            )
            btn.pack(side="left", padx=2, pady=2)
    
    def _add_suggestion(self, suggestion: str):
        if suggestion not in self.tags and len(self.tags) < self.max_tags:
            self.tags.append(suggestion)
            self._render_tags()
    
    def _add_tag(self, event=None):
        text = self.entry.get().strip()
        if text and text not in self.tags and len(self.tags) < self.max_tags:
            if len(text) <= self.max_char:
                self.tags.append(text)
                self.entry.delete(0, tk.END)
                self._render_tags()
    
    def _render_tags(self):
        # Clear existing tags
        for widget in self.tags_frame.winfo_children():
            widget.destroy()
        
        # Render current tags
        for i, tag in enumerate(self.tags):
            tag_frame = tk.Frame(self.tags_frame, bg="#3B82F6", relief="flat")
            tag_frame.pack(side="left", padx=2, pady=2)
            
            tk.Label(
                tag_frame, text=tag, 
                font=("Segoe UI", 9), bg="#3B82F6", fg="white", padx=8, pady=4
            ).pack(side="left")
            
            tk.Button(
                tag_frame, text="×", 
                command=lambda idx=i: self._remove_tag(idx),
                font=("Segoe UI", 8, "bold"), bg="#3B82F6", fg="white",
                relief="flat", padx=4, pady=2, bd=0
            ).pack(side="left")
    
    def _remove_tag(self, index: int):
        if 0 <= index < len(self.tags):
            self.tags.pop(index)
            self._render_tags()
    
    def get_tags(self) -> List[str]:
        return self.tags.copy()