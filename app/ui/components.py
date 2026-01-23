"""Common UI components to reduce code duplication"""
import tkinter as tk
from typing import Callable, Optional, Dict, Any

class UIComponents:
    @staticmethod
    def create_button(parent, text: str, command: Callable, 
                     style: Dict[str, Any] = None) -> tk.Button:
        """Create standardized button"""
        default_style = {
            "font": ("Segoe UI", 12),
            "relief": "flat",
            "cursor": "hand2",
            "pady": 8,
            "padx": 16
        }
        if style:
            default_style.update(style)
        
        return tk.Button(parent, text=text, command=command, **default_style)
    
    @staticmethod
    def create_entry(parent, placeholder: str = "", 
                    style: Dict[str, Any] = None) -> tk.Entry:
        """Create standardized entry field"""
        default_style = {
            "font": ("Segoe UI", 11),
            "relief": "flat",
            "highlightthickness": 1
        }
        if style:
            default_style.update(style)
        
        entry = tk.Entry(parent, **default_style)
        if placeholder:
            entry.insert(0, placeholder)
            entry.bind("<FocusIn>", lambda e: entry.delete(0, tk.END) if entry.get() == placeholder else None)
        
        return entry
    
    @staticmethod
    def create_label(parent, text: str, 
                    style: Dict[str, Any] = None) -> tk.Label:
        """Create standardized label"""
        default_style = {
            "font": ("Segoe UI", 11),
            "anchor": "w"
        }
        if style:
            default_style.update(style)
        
        return tk.Label(parent, text=text, **default_style)
    
    @staticmethod
    def create_card(parent, colors: Dict[str, str]) -> tk.Frame:
        """Create card-style frame"""
        return tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1,
            padx=20,
            pady=15
        )