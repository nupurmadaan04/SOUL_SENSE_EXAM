"""
UI Validation Utilities

This module deals with Tkinter-specific validation logic, such as blocking input
when character limits are reached. It complements the logic-only rules in `app/validation.py`.
"""

import tkinter as tk
from typing import Optional

def setup_entry_limit(entry: tk.Entry, limit: int, callback: Optional[callable] = None) -> None:
    """
    Configure a tk.Entry to reject input if it exceeds the limit.
    
    Args:
        entry: The tk.Entry widget
        limit: Max character count
        callback: Optional function to call on change (e.g. to update a char counter)
    """
    def validate(new_text: str) -> bool:
        if len(new_text) > limit:
            entry.bell() # Audio feedback
            return False
        if callback:
            callback(len(new_text))
        return True

    # Register the validation wrapper
    vcmd = (entry.register(validate), '%P')
    # validate='key' checks on every keystroke
    entry.configure(validate='key', validatecommand=vcmd)


def setup_text_limit(text_widget: tk.Text, limit: int, counter_label: Optional[tk.Label] = None) -> None:
    """
    Configure a tk.Text to block input if it exceeds the limit.
    Also handles trimming on paste.
    
    Args:
        text_widget: The tk.Text widget
        limit: Max character count
        counter_label: Optional label to update with "X/Limit"
    """
    
    def update_counter(current_len: int):
        if counter_label:
            counter_label.configure(text=f"{current_len}/{limit}")
            if current_len >= limit:
                counter_label.configure(fg="red")
            else:
                # Need to know default color? usually 'black' or theme dependent
                # We'll just leave it or set to gray/black if we knew the theme.
                # Just toggling red on limit is enough.
                pass

    def on_key_press(event):
        # Allow navigation and deletion keys regardless of limit
        # This list isn't exhaustive but covers common editing keys
        if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down', 'Home', 'End'):
            return

        # Check Copy/Paste shortcuts to allow them (paste handled by release)
        # Windows/Linux: Control-c, Control-v. Mac: Command usually handled by OS but Tkinter mapping varies.
        # Simplest: if Control is down, allow it?
        if event.state & 4: # Control key mask (typically 4)
             return

        # Check for selection replacement (always allow if selecting text)
        try:
            if text_widget.tag_ranges("sel"):
                return
        except Exception:
            pass

        # Get current content length
        # "end-1c" because Tk adds a newline at the end
        content = text_widget.get("1.0", "end-1c")
        if len(content) >= limit:
            text_widget.bell()
            return "break" # Stop event propagation (prevents insertion)

    def on_key_release(event):
        # Handle Paste overflow or other modifications
        content = text_widget.get("1.0", "end-1c")
        if len(content) > limit:
            # Truncate
            text_widget.delete(f"1.0 + {limit} chars", "end")
            text_widget.bell()
            content = text_widget.get("1.0", "end-1c") # Re-read truncated
        
        update_counter(len(content))

    # Bind events
    text_widget.bind('<KeyPress>', on_key_press)
    text_widget.bind('<KeyRelease>', on_key_release)
    
    # Initial counter update
    update_counter(len(text_widget.get("1.0", "end-1c")))
