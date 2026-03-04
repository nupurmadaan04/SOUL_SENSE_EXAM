"""
Crisis Alert Modal Component (Issue #1332)

Displays an intervention modal when extreme distress patterns are detected.
Provides crisis support resources, hotlines, and guidance options.
Allows user to acknowledge the alert and access help.

Usage:
    from app.ui.components.crisis_alert_modal import show_crisis_alert
    
    crisis_alert = show_crisis_alert(
        parent_window, 
        user_id=123,
        alert_id=456,
        severity="high",
        resources=resources_dict
    )
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import webbrowser
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class CrisisAlertModal(tk.Toplevel):
    """
    A modal dialog for displaying crisis alerts.
    
    Shows support resources, hotlines, and guidance when a user's
    emotional distress patterns reach crisis threshold.
    Designed to be helpful without being alarming.
    """
    
    def __init__(
        self,
        parent: tk.Tk,
        user_id: int,
        alert_id: int,
        severity: str = "high",
        resources: Optional[dict] = None,
        on_close: Optional[Callable] = None,
        colors: Optional[dict] = None
    ):
        """
        Create a crisis alert modal.
        
        Args:
            parent: Parent window
            user_id: User ID for this alert
            alert_id: Crisis alert ID
            severity: Alert severity (low, medium, high, critical)
            resources: Support resources dictionary
            on_close: Callback when modal is closed
            colors: Color scheme dictionary
        """
        super().__init__(parent)
        
        self.user_id = user_id
        self.alert_id = alert_id
        self.severity = severity
        self.resources = resources or self._default_resources()
        self.on_close = on_close
        self.colors = colors or self._default_colors()
        
        self.title("Support Available")
        self.geometry("600x700")
        self.resizable(False, False)
        
        # Configure modal appearance
        self.configure(bg=self.colors["bg"])
        
        # Make modal stay on top but not fully blocking
        self.transient(parent)
        self.grab_set()
        
        # Initialize UI
        self._setup_ui()
        
        # Center on parent
        self._center_on_parent(parent)
    
    def _setup_ui(self):
        """Setup the modal UI components."""
        # Main frame
        main_frame = tk.Frame(self, bg=self.colors["bg"])
        main_frame.pack(fill="both", expand=True)
        
        # Header with severity indicator
        self._setup_header(main_frame)
        
        # Content area
        content_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Message
        self._setup_message(content_frame)
        
        # Resources section
        self._setup_resources(content_frame)
        
        # Hotlines section
        self._setup_hotlines(content_frame)
        
        # Action buttons
        self._setup_buttons(main_frame)
    
    def _setup_header(self, parent: tk.Frame):
        """Setup header with title and severity indicator."""
        header_frame = tk.Frame(parent, bg=self._severity_color())
        header_frame.pack(fill="x", padx=0, pady=0)
        
        content = tk.Frame(header_frame, bg=self._severity_color())
        content.pack(fill="x", padx=20, pady=15)
        
        # Title
        title = tk.Label(
            content,
            text="We're Here to Help",
            font=("Segoe UI", 18, "bold"),
            bg=self._severity_color(),
            fg="white"
        )
        title.pack(anchor="w")
        
        # Subtitle based on severity
        subtitle_text = self._get_subtitle()
        subtitle = tk.Label(
            content,
            text=subtitle_text,
            font=("Segoe UI", 11),
            bg=self._severity_color(),
            fg="rgba(255, 255, 255, 0.9)"
        )
        subtitle.pack(anchor="w", pady=(5, 0))
    
    def _setup_message(self, parent: tk.Frame):
        """Setup the main message."""
        message_text = (
            "We've noticed a pattern of increased emotional distress in your recent entries. "
            "Your wellbeing matters to us. Please know that support is available, and you don't "
            "have to face this alone.\n\n"
            "Below are some resources that may help:"
        )
        
        message = tk.Label(
            parent,
            text=message_text,
            font=("Segoe UI", 10),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"],
            wraplength=540,
            justify="left"
        )
        message.pack(pady=(0, 20), anchor="w")
    
    def _setup_hotlines(self, parent: tk.Frame):
        """Setup crisis hotlines section."""
        section_label = tk.Label(
            parent,
            text="🚨 Crisis Hotlines (24/7 Free & Confidential)",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"]
        )
        section_label.pack(anchor="w", pady=(15, 10))
        
        # Hotlines
        for hotline in self.resources.get("crisis_hotlines", []):
            self._create_hotline_item(parent, hotline)
    
    def _create_hotline_item(self, parent: tk.Frame, hotline: dict):
        """Create a hotline display item."""
        frame = tk.Frame(parent, bg=self.colors["surface"], relief="flat", padx=12, pady=10)
        frame.pack(fill="x", pady=5)
        
        # Hotline name
        name = tk.Label(
            frame,
            text=hotline["name"],
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["surface"],
            fg=self.colors["text_primary"]
        )
        name.pack(anchor="w")
        
        # Number/Contact
        number = tk.Label(
            frame,
            text=hotline["number"],
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["surface"],
            fg="#3B82F6"
        )
        number.pack(anchor="w", pady=(3, 5))
        
        # Description
        desc = tk.Label(
            frame,
            text=hotline["description"],
            font=("Segoe UI", 9),
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"]
        )
        desc.pack(anchor="w")
        
        # Copy button for contact info
        copy_btn = tk.Button(
            frame,
            text="Copy",
            font=("Segoe UI", 9),
            bg=self.colors["primary"],
            fg="white",
            relief="flat",
            padx=10,
            pady=2,
            command=lambda: self._copy_to_clipboard(hotline["number"])
        )
        copy_btn.pack(anchor="w", pady=(8, 0))
    
    def _setup_resources(self, parent: tk.Frame):
        """Setup additional resources section."""
        section_label = tk.Label(
            parent,
            text="💡 Immediate Coping Strategies",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"]
        )
        section_label.pack(anchor="w", pady=(15, 10))
        
        # Coping strategies
        for i, strategy in enumerate(self.resources.get("guidance", []), 1):
            strategy_text = f"• {strategy}"
            strategy_label = tk.Label(
                parent,
                text=strategy_text,
                font=("Segoe UI", 9),
                bg=self.colors["bg"],
                fg=self.colors["text_secondary"],
                wraplength=520,
                justify="left"
            )
            strategy_label.pack(anchor="w", pady=3)
        
        # Additional resources
        if self.resources.get("resources"):
            section_label = tk.Label(
                parent,
                text="📚 Additional Resources",
                font=("Segoe UI", 11, "bold"),
                bg=self.colors["bg"],
                fg=self.colors["text_primary"]
            )
            section_label.pack(anchor="w", pady=(15, 10))
            
            for resource in self.resources.get("resources", []):
                self._create_resource_link(parent, resource)
    
    def _create_resource_link(self, parent: tk.Frame, resource: dict):
        """Create a clickable resource link."""
        link_btn = tk.Button(
            parent,
            text=f"🔗 {resource['name']}",
            font=("Segoe UI", 9),
            bg=self.colors["surface"],
            fg="#3B82F6",
            relief="flat",
            anchor="w",
            padx=10,
            pady=6,
            command=lambda: webbrowser.open(resource.get("url", ""))
        )
        link_btn.pack(fill="x", pady=3)
        
        # Hover effect
        def on_enter(event):
            link_btn.config(bg="#E0E7FF")
        
        def on_leave(event):
            link_btn.config(bg=self.colors["surface"])
        
        link_btn.bind("<Enter>", on_enter)
        link_btn.bind("<Leave>", on_leave)
    
    def _setup_buttons(self, parent: tk.Frame):
        """Setup action buttons."""
        button_frame = tk.Frame(parent, bg=self.colors["bg"])
        button_frame.pack(fill="x", padx=20, pady=20)
        
        # Talk to someone button
        talk_btn = tk.Button(
            button_frame,
            text="Talk to Someone",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["primary"],
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            command=self._on_talk_to_someone
        )
        talk_btn.pack(side="left", padx=(0, 10))
        
        # I'm safe button
        safe_btn = tk.Button(
            button_frame,
            text="I'm Safe, Close This",
            font=("Segoe UI", 10),
            bg=self.colors["surface"],
            fg=self.colors["text_primary"],
            relief="flat",
            padx=20,
            pady=10,
            command=self._on_acknowledge
        )
        safe_btn.pack(side="left")
    
    def _on_talk_to_someone(self):
        """Handle 'Talk to Someone' button click."""
        messagebox.showinfo(
            "Talk to Someone",
            "You can reach out to:\n\n"
            "• 988 Suicide & Crisis Lifeline\n"
            "• Crisis Text Line (Text HOME to 741741)\n\n"
            "Or speak with a trusted friend, family member, or mental health professional."
        )
    
    def _on_acknowledge(self):
        """Handle acknowledgment - close the modal."""
        if self.on_close:
            self.on_close(self.alert_id)
        self.destroy()
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # Required to keep clipboard available after window close
            messagebox.showinfo("Copied", f"Copied to clipboard: {text}")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            messagebox.showerror("Error", "Failed to copy to clipboard")
    
    def _severity_color(self) -> str:
        """Get color based on severity level."""
        severity_colors = {
            "critical": "#DC2626",  # Red
            "high": "#EA580C",      # Orange
            "medium": "#EAB308",    # Yellow
            "low": "#3B82F6"        # Blue
        }
        return severity_colors.get(self.severity, "#3B82F6")
    
    def _get_subtitle(self) -> str:
        """Get subtitle based on severity."""
        subtitles = {
            "critical": "Your wellbeing is important. Critical support is available now.",
            "high": "We care about you. Support is available right now.",
            "medium": "Let's talk. Resources are available to help.",
            "low": "We're here if you need support."
        }
        return subtitles.get(self.severity, "We're here to help.")
    
    def _center_on_parent(self, parent: tk.Tk):
        """Center modal on parent window."""
        self.update_idletasks()
        
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        
        self.geometry(f"+{x}+{y}")
    
    def _default_resources(self) -> dict:
        """Default support resources."""
        return {
            "crisis_hotlines": [
                {
                    "name": "National Crisis Hotline",
                    "number": "988",
                    "description": "Free, confidential support 24/7",
                    "available_24_7": True
                },
                {
                    "name": "Crisis Text Line",
                    "number": "Text HOME to 741741",
                    "description": "Text-based crisis support",
                    "available_24_7": True
                }
            ],
            "guidance": [
                "Reach out to a trusted friend or family member",
                "Contact a mental health professional",
                "Use grounding techniques (5-4-3-2-1 method)",
                "Practice deep breathing exercises"
            ]
        }
    
    def _default_colors(self) -> dict:
        """Default color scheme."""
        return {
            "bg": "#F8FAFC",
            "surface": "#E2E8F0",
            "primary": "#3B82F6",
            "text_primary": "#1E293B",
            "text_secondary": "#64748B"
        }


def show_crisis_alert(
    parent: tk.Tk,
    user_id: int,
    alert_id: int,
    severity: str = "high",
    resources: Optional[dict] = None,
    on_close: Optional[Callable] = None,
    colors: Optional[dict] = None
) -> CrisisAlertModal:
    """
    Display a crisis alert modal.
    
    Args:
        parent: Parent window
        user_id: User ID for this alert
        alert_id: Crisis alert database ID
        severity: Alert severity level
        resources: Support resources dictionary
        on_close: Callback when modal is closed
        colors: Color scheme
        
    Returns:
        CrisisAlertModal instance
    """
    modal = CrisisAlertModal(parent, user_id, alert_id, severity, resources, on_close, colors)
    return modal
