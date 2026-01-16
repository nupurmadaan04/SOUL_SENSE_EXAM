import tkinter as tk
from app.i18n_manager import t # your i18n manager


class ReflectionScreen(tk.Frame):
    """Premium reflection screen UI"""

    def __init__(self, master, app, on_submit):
        """
        Args:
            master: Tk root or parent frame
            app: main app instance
            on_submit: callback function called with reflection text
        """
        super().__init__(master, bg=app.colors["bg"])
        self.app = app
        self.on_submit = on_submit
        self.pack(fill="both", expand=True, padx=40, pady=20)

        self._build_ui()

    def _build_ui(self):
        colors = self.app.colors

        # Header
        header_frame = tk.Frame(self, bg=colors.get("secondary", "#8B5CF6"), height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        tk.Label(
            header_frame,
            text=t("quiz.warning"),  # optional i18n header or change text
            font=("Segoe UI", 28, "bold"),
            bg=colors.get("secondary", "#8B5CF6"),
            fg=colors.get("text_inverse", "#FFFFFF")
        ).pack(pady=30)

        # Instruction card
        instruction_card = tk.Frame(
            self, bg=colors.get("surface", "#FFFFFF"),
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightthickness=1
        )
        instruction_card.pack(fill="x", pady=10, padx=25)
        tk.Label(
            instruction_card,
            text=t("journal.daily_reflection"),  # localized instruction
            font=("Segoe UI", 13),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            wraplength=500,
            justify="center"
        ).pack(pady=20)

        # Text area
        self.reflection_entry = tk.Text(
            self, height=8, font=("Segoe UI", 12),
            bg=colors.get("surface", "#FFFFFF"),
            fg=colors.get("text_primary", "#0F172A"),
            insertbackground=colors.get("text_primary", "#0F172A"),
            relief="flat", highlightthickness=2,
            highlightbackground=colors.get("border", "#E2E8F0"),
            highlightcolor=colors.get("primary", "#3B82F6"),
            padx=15, pady=15
        )
        self.reflection_entry.pack(fill="both", expand=True, pady=10)

        # Submit button
        submit_btn = tk.Button(
            self,
            text=t("quiz.finish"),  # localized submit text
            command=self._submit,
            font=("Segoe UI", 14, "bold"),
            bg=colors.get("success", "#10B981"),
            fg=colors.get("text_inverse", "#FFFFFF"),
            relief="flat",
            cursor="hand2",
            width=22, pady=12,
        )
        submit_btn.pack(pady=15)

        # Skip link
        skip_label = tk.Label(
            self, text=t("quiz.warning"),  # optional localized skip
            font=("Segoe UI", 10, "underline"),
            bg=self.app.colors["bg"],
            fg=colors.get("text_tertiary", "#94A3B8"),
            cursor="hand2"
        )
        skip_label.pack()
        skip_label.bind("<Button-1>", lambda e: self._skip())

    def _submit(self):
        text = self.reflection_entry.get("1.0", tk.END).strip()
        self.on_submit(text)

    def _skip(self):
        self.on_submit("")  # empty string means skip
