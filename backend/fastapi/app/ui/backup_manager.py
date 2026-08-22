"""
Backup Manager UI Component (Issue #345)
Provides a modal dialog for creating and restoring database backups.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import threading
import logging
from typing import Optional, List, Callable

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backup/restore operations with premium UI."""
    
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.backup_win: Optional[tk.Toplevel] = None
        self.selected_backup: Optional[str] = None
        self.backup_listbox: Optional[tk.Listbox] = None
        self.backups: List = []
        
    def show_backup_dialog(self) -> None:
        """Show the backup management dialog."""
        colors = self.app.colors
        
        # Create modal window
        self.backup_win = tk.Toplevel(self.root)
        self.backup_win.title("Data Backup & Restore")
        
        # Responsive sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(550, int(screen_width * 0.4))
        window_height = min(700, int(screen_height * 0.7))
        
        self.backup_win.geometry(f"{window_width}x{window_height}")
        self.backup_win.minsize(450, 500)
        self.backup_win.resizable(True, True)
        self.backup_win.configure(bg=colors["bg"])
        
        # Center window on parent
        self.backup_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - window_width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - window_height) // 2
        self.backup_win.geometry(f"+{x}+{y}")
        
        # Make modal
        self.backup_win.transient(self.root)
        self.backup_win.grab_set()
        
        # Header
        self._create_header(colors)
        
        # Content
        content_frame = tk.Frame(self.backup_win, bg=colors["bg"])
        content_frame.pack(fill="both", expand=True, padx=25, pady=20)
        
        # Sections
        self._create_backup_section(content_frame, colors)
        self._create_restore_section(content_frame, colors)
        
        # Close button
        self._create_close_button(content_frame, colors)
        
        # Load existing backups
        self._refresh_backup_list()
    
    def _create_header(self, colors: dict) -> None:
        """Create the header with title and icon."""
        header_frame = tk.Frame(
            self.backup_win,
            bg=colors.get("primary", "#3B82F6"),
            height=70
        )
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(
            header_frame,
            text="💾 Data Backup & Restore",
            font=self.app.ui_styles.get_font("xl", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        )
        header_label.pack(pady=20)
    
    def _create_backup_section(self, parent: tk.Frame, colors: dict) -> None:
        """Create the backup creation section."""
        section = tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        section.pack(fill="x", pady=8)
        
        inner = tk.Frame(section, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="x", padx=15, pady=12)
        
        # Title
        label = tk.Label(
            inner,
            text="Create Backup",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        label.pack(anchor="w")
        
        desc = tk.Label(
            inner,
            text="Create a snapshot of your current data",
            font=self.app.ui_styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc.pack(anchor="w", pady=(2, 8))
        
        # Description input
        input_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        input_frame.pack(fill="x", pady=(0, 8))
        
        desc_label = tk.Label(
            input_frame,
            text="Description (optional):",
            font=self.app.ui_styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc_label.pack(anchor="w")
        
        self.desc_var = tk.StringVar()
        desc_entry = tk.Entry(
            input_frame,
            textvariable=self.desc_var,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("entry_bg", "#FFFFFF"),
            fg=colors.get("entry_fg", "#0F172A"),
            relief="flat",
            highlightthickness=1,
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightcolor=colors.get("primary", "#3B82F6")
        )
        desc_entry.pack(fill="x", pady=4)
        
        # Create backup button
        btn_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        btn_frame.pack(anchor="w")
        
        create_btn = tk.Button(
            btn_frame,
            text="📦 Create Backup",
            command=self._create_backup,
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("success", "#10B981"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("success_hover", "#059669"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            padx=15,
            pady=8,
            borderwidth=0
        )
        create_btn.pack(side="left")
        create_btn.bind("<Enter>", lambda e: create_btn.configure(bg=colors.get("success_hover", "#059669")))
        create_btn.bind("<Leave>", lambda e: create_btn.configure(bg=colors.get("success", "#10B981")))
    
    def _create_restore_section(self, parent: tk.Frame, colors: dict) -> None:
        """Create the restore section with backup list."""
        section = tk.Frame(
            parent,
            bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        section.pack(fill="both", expand=True, pady=8)
        
        inner = tk.Frame(section, bg=colors.get("surface", "#FFFFFF"))
        inner.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Title
        label = tk.Label(
            inner,
            text="Available Backups",
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A")
        )
        label.pack(anchor="w")
        
        desc = tk.Label(
            inner,
            text="Select a backup to restore or delete",
            font=self.app.ui_styles.get_font("xs"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569")
        )
        desc.pack(anchor="w", pady=(2, 8))
        
        # Backup list with scrollbar
        list_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        list_frame.pack(fill="both", expand=True, pady=(0, 8))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.backup_listbox = tk.Listbox(
            list_frame,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("entry_bg", "#FFFFFF"),
            fg=colors.get("entry_fg", "#0F172A"),
            selectbackground=colors.get("primary", "#3B82F6"),
            selectforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            highlightthickness=1,
            highlightbackground=colors.get("border", "#E2E8F0"),
            yscrollcommand=scrollbar.set,
            height=8
        )
        self.backup_listbox.pack(fill="both", expand=True)
        self.backup_listbox.bind("<<ListboxSelect>>", self._on_backup_selected)
        scrollbar.config(command=self.backup_listbox.yview)
        
        # Action buttons
        btn_frame = tk.Frame(inner, bg=colors.get("surface", "#FFFFFF"))
        btn_frame.pack(anchor="w")
        
        # Restore button
        self.restore_btn = tk.Button(
            btn_frame,
            text="🔄 Restore",
            command=self._restore_backup,
            font=self.app.ui_styles.get_font("sm", "bold"),
            bg=colors.get("primary", "#3B82F6"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("primary_hover", "#2563EB"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            borderwidth=0,
            state="disabled"
        )
        self.restore_btn.pack(side="left", padx=(0, 8))
        
        # Delete button
        self.delete_btn = tk.Button(
            btn_frame,
            text="🗑 Delete",
            command=self._delete_backup,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("error", "#EF4444"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            activebackground=colors.get("error_hover", "#DC2626"),
            activeforeground=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            borderwidth=0,
            state="disabled"
        )
        self.delete_btn.pack(side="left", padx=(0, 8))
        
        # Refresh button
        refresh_btn = tk.Button(
            btn_frame,
            text="🔃 Refresh",
            command=self._refresh_backup_list,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface_hover", "#F8FAFC"),
            fg=colors.get("text_secondary", "#475569"),
            activebackground=colors.get("border", "#E2E8F0"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        refresh_btn.pack(side="left")
    
    def _create_close_button(self, parent: tk.Frame, colors: dict) -> None:
        """Create the close button."""
        btn_frame = tk.Frame(parent, bg=colors["bg"])
        btn_frame.pack(fill="x", pady=(10, 0))
        
        close_btn = tk.Button(
            btn_frame,
            text="Close",
            command=self.backup_win.destroy,
            font=self.app.ui_styles.get_font("sm"),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_secondary", "#475569"),
            activebackground=colors.get("surface_hover", "#F8FAFC"),
            activeforeground=colors.get("text_primary", "#0F172A"),
            relief="flat",
            cursor="hand2",
            width=12,
            pady=8,
            borderwidth=1,
            highlightbackground=colors.get("border", "#E2E8F0")
        )
        close_btn.pack(side="right")
    
    def _refresh_backup_list(self) -> None:
        """Refresh the list of available backups."""
        from app.db_backup import list_backups
        
        if not self.backup_listbox:
            return
        
        self.backup_listbox.delete(0, tk.END)
        self.backups = list_backups()
        
        if not self.backups:
            self.backup_listbox.insert(tk.END, "(No backups found)")
        else:
            for backup in self.backups:
                display_text = f"{backup.timestamp_display} - {backup.size_display}"
                if backup.description:
                    display_text += f" ({backup.description[:20]}...)" if len(backup.description) > 20 else f" ({backup.description})"
                self.backup_listbox.insert(tk.END, display_text)
        
        # Reset selection state
        self.selected_backup = None
        self.restore_btn.config(state="disabled")
        self.delete_btn.config(state="disabled")
    
    def _on_backup_selected(self, event) -> None:
        """Handle backup selection."""
        selection = self.backup_listbox.curselection()
        if selection and self.backups:
            index = selection[0]
            if index < len(self.backups):
                self.selected_backup = self.backups[index].path
                self.restore_btn.config(state="normal")
                self.delete_btn.config(state="normal")
            else:
                self.selected_backup = None
                self.restore_btn.config(state="disabled")
                self.delete_btn.config(state="disabled")
    
    def _create_backup(self) -> None:
        """Create a new backup."""
        from app.db_backup import create_backup
        
        description = self.desc_var.get().strip()
        
        try:
            backup_info = create_backup(description)
            messagebox.showinfo(
                "Backup Created",
                f"Backup created successfully!\n\n"
                f"File: {backup_info.filename}\n"
                f"Size: {backup_info.size_display}",
                parent=self.backup_win
            )
            self.desc_var.set("")  # Clear description
            self._refresh_backup_list()
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            messagebox.showerror(
                "Backup Failed",
                f"Failed to create backup:\n{str(e)}",
                parent=self.backup_win
            )
    
    def _restore_backup(self) -> None:
        """Restore from the selected backup."""
        from app.db_backup import restore_backup
        
        if not self.selected_backup:
            return
        
        # Get selected backup info
        selection = self.backup_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index >= len(self.backups):
            return
        
        backup_info = self.backups[index]
        
        # Confirm with user
        result = messagebox.askyesno(
            "Confirm Restore",
            f"Are you sure you want to restore from this backup?\n\n"
            f"Date: {backup_info.timestamp_display}\n"
            f"Size: {backup_info.size_display}\n\n"
            f"⚠️ This will replace your current data with the backup.\n"
            f"A safety copy will be created before restoration.",
            icon="warning",
            parent=self.backup_win
        )
        
        if not result:
            return
        
        try:
            restore_backup(self.selected_backup)
            messagebox.showinfo(
                "Restore Complete",
                "Database restored successfully!\n\n"
                "Please restart the application for changes to take effect.",
                parent=self.backup_win
            )
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            messagebox.showerror(
                "Restore Failed",
                f"Failed to restore backup:\n{str(e)}",
                parent=self.backup_win
            )
    
    def _delete_backup(self) -> None:
        """Delete the selected backup."""
        from app.db_backup import delete_backup
        
        if not self.selected_backup:
            return
        
        # Get selected backup info
        selection = self.backup_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index >= len(self.backups):
            return
        
        backup_info = self.backups[index]
        
        # Confirm with user
        result = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this backup?\n\n"
            f"Date: {backup_info.timestamp_display}\n"
            f"Size: {backup_info.size_display}\n\n"
            f"⚠️ This action cannot be undone.",
            icon="warning",
            parent=self.backup_win
        )
        
        if not result:
            return
        
        try:
            delete_backup(self.selected_backup)
            messagebox.showinfo(
                "Backup Deleted",
                "Backup deleted successfully!",
                parent=self.backup_win
            )
            self._refresh_backup_list()
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            messagebox.showerror(
                "Delete Failed",
                f"Failed to delete backup:\n{str(e)}",
                parent=self.backup_win
            )
