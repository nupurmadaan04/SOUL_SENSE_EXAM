import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading
import logging
from typing import Dict, Any

# Try importing tkcalendar, fallback if missing
try:
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

from app.services.export_service import ExportService
from app.ui.components.loading_overlay import show_loading, hide_loading
from app.utils.file_validation import validate_file_path, sanitize_filename, ValidationError
from app.utils.atomic import atomic_write
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

class ExportWizard(tk.Toplevel):
    def __init__(self, parent, app, user_id=None):
        super().__init__(parent)
        self.app = app
        self.user_id = user_id or getattr(app, 'current_user_id', None)
        
        # If user_id is still None, try to get it from profile service using username
        if not self.user_id:
            try:
                user = ProfileService.get_user_profile(app.username)
                if user:
                    self.user_id = user.id
            except:
                pass
                
        self.title("Data Export Wizard")
        self.geometry("600x650") 
        self.resizable(False, False)
        
        # Theme colors
        self.colors = app.colors
        self.configure(bg=self.colors.get("bg", "#F0F2F5"))
        
        # Thread handling
        self.loading_overlay = None
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self._init_ui()
        self._center_window()
        
    def _init_ui(self):
        # 1. Header (Top)
        header_frame = tk.Frame(self, bg=self.colors.get("card_bg", "white"))
        header_frame.pack(fill="x", pady=(0, 0), side="top")
        
        tk.Label(
            header_frame, 
            text="📤 Export Your Data", 
            font=("Segoe UI", 16, "bold"),
            bg=self.colors.get("card_bg"),
            fg=self.colors.get("text_primary")
        ).pack(anchor="w", padx=20, pady=20)

        # 2. Buttons (Bottom) - Pack FIRST to ensure visibility
        btn_frame = tk.Frame(self, bg=self.colors.get("bg"))
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        tk.Button(
            btn_frame, text="Cancel", command=self.destroy,
            font=("Segoe UI", 10), bg="#E2E8F0", fg="black", relief="flat", padx=20, pady=10
        ).pack(side="right", padx=10)
        
        tk.Button(
            btn_frame, 
            text="⬇ Export Data", 
            command=self._start_export,
            font=("Segoe UI", 10, "bold"), 
            bg=self.colors.get("primary", "#3B82F6"), 
            fg="white", 
            relief="flat", 
            padx=20, pady=10
        ).pack(side="right")
        
        # 3. Content (Middle) - Fills remaining space
        content = tk.Frame(self, bg=self.colors.get("bg"))
        content.pack(fill="both", expand=True, padx=2, pady=0)
        
        # Scrollable canvas for content (in case screens are small)
        canvas = tk.Canvas(content, bg=self.colors.get("bg"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors.get("bg"))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # --- Section 1: Data Filters ---
        self._create_section_label(scrollable_frame, "1. What data to include?")
        
        filter_frame = tk.Frame(scrollable_frame, bg=self.colors.get("card_bg"), padx=15, pady=10)
        filter_frame.pack(fill="x", pady=(0, 15), padx=20)
        
        self.var_profile = tk.BooleanVar(value=True)
        self.var_journal = tk.BooleanVar(value=True)
        self.var_medical = tk.BooleanVar(value=True) # Bundled with profile usually
        self.var_assessments = tk.BooleanVar(value=True)
        
        self._create_check(filter_frame, "Profile & Medical Info", self.var_profile)
        self._create_check(filter_frame, "Journal Entries & Notes", self.var_journal)
        self._create_check(filter_frame, "Assessment Results (EQ, etc.)", self.var_assessments)
        
        # --- Section 2: Date Range ---
        self._create_section_label(scrollable_frame, "2. Date Range (Optional)")
        
        date_frame = tk.Frame(scrollable_frame, bg=self.colors.get("card_bg"), padx=15, pady=15)
        date_frame.pack(fill="x", pady=(0, 15), padx=20)
        
        if HAS_CALENDAR:
            tk.Label(date_frame, text="Start:", bg=self.colors.get("card_bg")).pack(side="left")
            self.start_date = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
            self.start_date.pack(side="left", padx=(5, 15))
            
            tk.Label(date_frame, text="End:", bg=self.colors.get("card_bg")).pack(side="left")
            self.end_date = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
            self.end_date.pack(side="left", padx=5)
        else:
             tk.Label(date_frame, text="Date picker not available (install tkcalendar)", bg=self.colors.get("card_bg")).pack()

        # --- Section 3: Export Format ---
        self._create_section_label(scrollable_frame, "3. Export Format")
        
        format_frame = tk.Frame(scrollable_frame, bg=self.colors.get("card_bg"), padx=15, pady=10)
        format_frame.pack(fill="x", pady=(0, 15), padx=20)
        
        self.format_var = tk.StringVar(value="json")
        
        self._create_radio(format_frame, "JSON (Raw Data) - Best for backups", "json")
        self._create_radio(format_frame, "CSV (Spreadsheet) - Best for Excel/Analysis", "csv")
        self._create_radio(format_frame, "PDF (Report) - Best for reading/printing", "pdf")
        
        # --- Section 4: Privacy Consent ---
        self._create_section_label(scrollable_frame, "4. Privacy Consent")
        
        privacy_frame = tk.Frame(scrollable_frame, bg=self.colors.get("card_bg"), padx=15, pady=10)
        privacy_frame.pack(fill="x", pady=(0, 20), padx=20)
        
        self.consent_var = tk.BooleanVar(value=False)
        
        warn_msg = ("I understand that this file contains sensitive, unencrypted personal "
                    "and medical data. I agree to store it securely.")
        
        consent_chk = tk.Checkbutton(
            privacy_frame, 
            text=warn_msg,
            variable=self.consent_var,
            font=("Segoe UI", 9, "bold"),
            bg=self.colors.get("card_bg"),
            fg="#DC2626", # Red warning color
            wraplength=500,
            justify="left",
            activebackground=self.colors.get("card_bg")
        )
        consent_chk.pack(anchor="w")

    def _create_section_label(self, parent, text):
        tk.Label(
            parent, text=text, 
            font=("Segoe UI", 11, "bold"), 
            bg=self.colors.get("bg"), 
            fg=self.colors.get("text_secondary", "gray")
        ).pack(anchor="w", pady=(0, 5), padx=20)
        
    def _create_check(self, parent, text, variable):
        tk.Checkbutton(
            parent, text=text, variable=variable, font=("Segoe UI", 10),
            bg=self.colors.get("card_bg"), activebackground=self.colors.get("card_bg")
        ).pack(anchor="w", pady=2)
        
    def _create_radio(self, parent, text, value):
        tk.Radiobutton(
            parent, text=text, variable=self.format_var, value=value,
            font=("Segoe UI", 10), bg=self.colors.get("card_bg"),
            activebackground=self.colors.get("card_bg"), selectcolor=self.colors.get("card_bg")
        ).pack(anchor="w", pady=2)

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _start_export(self):
        # 1. Validation
        if not self.consent_var.get():
            messagebox.showwarning("Consent Required", "Please acknowledge the privacy warning to proceed.", parent=self)
            return

        fmt = self.format_var.get()
        
        # 2. Ask for Save Location
        ext = f".{fmt}"
        if fmt == "csv": ext = ".zip" # CSV is zipped
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = sanitize_filename(self.app.username)
        default_file = f"SoulSense_Export_{safe_name}_{timestamp}{ext}"
        
        file_types = []
        if fmt == "json": file_types = [("JSON Data", "*.json")]
        elif fmt == "csv": file_types = [("CSV Archive", "*.zip")]
        elif fmt == "pdf": file_types = [("PDF Document", "*.pdf")]
        
        filename = filedialog.asksaveasfilename(
            title="Save Export As",
            initialfile=default_file,
            defaultextension=ext,
            filetypes=file_types,
            parent=self
        )
        
        if not filename:
            return

        # 3. Prepare Options
        options = {
            "include_profile": self.var_profile.get(),
            "include_journal": self.var_journal.get(),
            "include_assessments": self.var_assessments.get()
        }
        
        if HAS_CALENDAR:
            # Logic: If user didn't change them, they might be today?
            # We pass them as strings if valid
            try:
                # Convert date object to string YYYY-MM-DD
                options["start_date"] = self.start_date.get_date().strftime("%Y-%m-%d")
                options["end_date"] = self.end_date.get_date().strftime("%Y-%m-%d")
            except:
                pass # Ignore date errors
        
        # 4. Start Background Thread
        self.loading_overlay = show_loading(self, f"Generating {fmt.upper()} export...")
        
        thread = threading.Thread(
            target=self._run_export_thread,
            args=(self.user_id, fmt, options, filename)
        )
        thread.daemon = True # Kill if app closes
        thread.start()

    def _run_export_thread(self, user_id, fmt, options, filename):
        try:
            # Generate Data (CPU Intensive)
            file_bytes = ExportService.export_data(user_id, fmt, options)
            
            # Write to Disk (IO)
            # Use atomic write for safety
            with atomic_write(filename, 'wb') as f:
                f.write(file_bytes)
            
            # Success Callback
            self.after(0, lambda: self._on_export_success(filename))
            
        except Exception as e:
            logger.error(f"Export thread failed: {e}")
            self.after(0, lambda err=str(e): self._on_export_error(err))

    def _on_export_success(self, filename):
        hide_loading(self.loading_overlay)
        messagebox.showinfo(
            "Export Complete", 
            f"Your data has been successfully exported to:\n{filename}",
            parent=self
        )
        self.destroy()

    def _on_export_error(self, error_msg):
        hide_loading(self.loading_overlay)
        messagebox.showerror(
            "Export Failed", 
            f"An error occurred during export:\n{error_msg}",
            parent=self
        )
