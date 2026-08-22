"""
Loading Overlay Component

Provides visual feedback during long-running operations like ML inference
or data exports. Shows an animated spinner with customizable message.

Usage:
    from app.ui.components.loading_overlay import show_loading, hide_loading
    
    # Show loading overlay
    overlay = show_loading(parent_window, "Processing...")
    
    # Do long operation...
    
    # Hide loading overlay
    hide_loading(overlay)
"""

import tkinter as tk
from typing import Optional


class LoadingOverlay(tk.Toplevel):
    """
    A modal loading overlay that displays an animated spinner and message.
    
    Covers the parent window with a semi-transparent overlay to prevent
    user interaction during long-running operations.
    """
    
    # Spinner animation frames (braille pattern)
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    def __init__(
        self, 
        parent: tk.Tk | tk.Toplevel, 
        message: str = "Loading...",
        bg_color: str = "#0F172A",
        fg_color: str = "#F8FAFC",
        accent_color: str = "#3B82F6"
    ):
        """
        Create a loading overlay.
        
        Args:
            parent: Parent window to overlay
            message: Loading message to display
            bg_color: Background color of the overlay
            fg_color: Text color
            accent_color: Spinner color
        """
        super().__init__(parent)
        
        self.parent = parent
        self.message = message
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.accent_color = accent_color
        
        self._frame_index = 0
        self._animation_id: Optional[str] = None
        self._is_destroyed = False
        
        self._setup_window()
        self._create_widgets()
        self._start_animation()
    
    def _setup_window(self) -> None:
        """Configure the overlay window."""
        # Remove window decorations
        self.overrideredirect(True)
        
        # Semi-transparent background
        self.configure(bg=self.bg_color)
        self.attributes("-alpha", 0.95)
        
        # Position and size to match parent
        self._update_geometry()
        
        # Keep on top
        self.attributes("-topmost", True)
        self.lift()
        
        # Capture all input
        self.grab_set()
        self.focus_set()
        
        # Bind to parent resize
        self.parent.bind("<Configure>", self._on_parent_configure, add="+")
    
    def _update_geometry(self) -> None:
        """Update overlay position and size to match parent."""
        try:
            if self._is_destroyed:
                return
            
            self.parent.update_idletasks()
            
            x = self.parent.winfo_rootx()
            y = self.parent.winfo_rooty()
            width = self.parent.winfo_width()
            height = self.parent.winfo_height()
            
            # Ensure minimum size
            width = max(width, 300)
            height = max(height, 200)
            
            self.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            pass  # Parent may have been destroyed
    
    def _on_parent_configure(self, event: tk.Event) -> None:
        """Handle parent window resize/move."""
        self._update_geometry()
    
    def _create_widgets(self) -> None:
        """Create the loading indicator widgets."""
        # Center container
        container = tk.Frame(self, bg=self.bg_color)
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Spinner label
        self.spinner_label = tk.Label(
            container,
            text=self.SPINNER_FRAMES[0],
            font=("Segoe UI", 48),
            bg=self.bg_color,
            fg=self.accent_color
        )
        self.spinner_label.pack(pady=(0, 20))
        
        # Message label
        self.message_label = tk.Label(
            container,
            text=self.message,
            font=("Segoe UI", 14),
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.message_label.pack()
        
        # Subtle hint
        tk.Label(
            container,
            text="Please wait...",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg="#64748B"
        ).pack(pady=(10, 0))
    
    def _start_animation(self) -> None:
        """Start the spinner animation."""
        self._animate()
    
    def _animate(self) -> None:
        """Animate the spinner."""
        if self._is_destroyed:
            return
        
        try:
            self.spinner_label.configure(text=self.SPINNER_FRAMES[self._frame_index])
            self._frame_index = (self._frame_index + 1) % len(self.SPINNER_FRAMES)
            self._animation_id = self.after(80, self._animate)
        except tk.TclError:
            pass  # Widget may have been destroyed
    
    def update_message(self, message: str) -> None:
        """Update the loading message."""
        if not self._is_destroyed:
            try:
                self.message_label.configure(text=message)
            except tk.TclError:
                pass
    
    def destroy(self) -> None:
        """Clean up and destroy the overlay."""
        if self._is_destroyed:
            return
        
        self._is_destroyed = True
        
        # Cancel animation
        if self._animation_id:
            try:
                self.after_cancel(self._animation_id)
            except tk.TclError:
                pass
        
        # Unbind from parent
        try:
            self.parent.unbind("<Configure>")
        except tk.TclError:
            pass
        
        # Release grab
        try:
            self.grab_release()
        except tk.TclError:
            pass
        
        # Destroy window
        try:
            super().destroy()
        except tk.TclError:
            pass


def show_loading(
    parent: tk.Tk | tk.Toplevel, 
    message: str = "Loading..."
) -> LoadingOverlay:
    """
    Show a loading overlay on the parent window.
    
    Args:
        parent: Parent window to overlay
        message: Loading message to display
        
    Returns:
        LoadingOverlay instance (call destroy() or use hide_loading() to remove)
    """
    overlay = LoadingOverlay(parent, message=message)
    overlay.update()  # Force immediate display
    return overlay


def hide_loading(overlay: Optional[LoadingOverlay]) -> None:
    """
    Safely hide and destroy a loading overlay.
    
    Args:
        overlay: LoadingOverlay instance to destroy, or None
    """
    if overlay is not None:
        try:
            overlay.destroy()
        except Exception:
            pass  # Already destroyed or error
