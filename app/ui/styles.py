"""
Soul Sense UI Styles Module
Premium design system with modern aesthetics
"""

import tkinter as tk
from tkinter import ttk


class DesignTokens:
    """Centralized design tokens for consistent styling"""
    
    # Typography
    FONT_FAMILY = "Segoe UI"
    FONT_FAMILY_FALLBACK = "Arial"
    
    FONT_SIZE_XS = 10
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 18
    FONT_SIZE_XL = 24
    FONT_SIZE_XXL = 32
    FONT_SIZE_HERO = 48
    
    # Spacing
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    SPACING_XXL = 48
    
    # Border Radius (for canvas-based rounded elements)
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    
    # Shadows (as color overlays for depth effect)
    SHADOW_COLOR = "#00000020"
    
    # Animation durations (ms)
    ANIM_FAST = 150
    ANIM_NORMAL = 300
    ANIM_SLOW = 500


class ColorSchemes:
    """Premium color palettes"""
    
    LIGHT = {
        # Background colors
        "bg": "#F8FAFC",
        "bg_secondary": "#F1F5F9",
        "bg_tertiary": "#E2E8F0",
        
        # Surface colors (cards, panels)
        "surface": "#FFFFFF",
        "surface_hover": "#F8FAFC",
        "surface_active": "#F1F5F9",
        
        # Text colors
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_tertiary": "#94A3B8",
        "text_inverse": "#FFFFFF",
        
        # Primary accent (Blue)
        "primary": "#3B82F6",
        "primary_hover": "#2563EB",
        "primary_active": "#1D4ED8",
        "primary_light": "#DBEAFE",
        
        # Secondary accent (Purple)
        "secondary": "#8B5CF6",
        "secondary_hover": "#7C3AED",
        "secondary_active": "#6D28D9",
        "secondary_light": "#EDE9FE",
        
        # Success (Green)
        "success": "#10B981",
        "success_hover": "#059669",
        "success_light": "#D1FAE5",
        
        # Warning (Amber)
        "warning": "#F59E0B",
        "warning_hover": "#D97706",
        "warning_light": "#FEF3C7",
        
        # Error (Red)
        "error": "#EF4444",
        "error_hover": "#DC2626",
        "error_light": "#FEE2E2",
        
        # Border colors
        "border": "#E2E8F0",
        "border_focus": "#3B82F6",
        
        # Special
        "overlay": "#0F172A80",
        "tooltip_bg": "#1E293B",
        "tooltip_text": "#F8FAFC",
        
        # Legacy compatibility mappings
        "fg": "#0F172A",
        "button_bg": "#3B82F6",
        "button_fg": "#FFFFFF",
        "entry_bg": "#FFFFFF",
        "entry_fg": "#0F172A",
        "label_bg": "#F8FAFC",
        "label_fg": "#0F172A",
        "radiobutton_bg": "#F8FAFC",
        "radiobutton_fg": "#0F172A",
        "frame_bg": "#F8FAFC",
        
        # Modern Layout Tokens
        "sidebar_bg": "#3B82F6", # Brand Blue
        "sidebar_fg": "#FFFFFF",
        "sidebar_hover": "#2563EB", # Darker Blue
        "sidebar_active": "#1D4ED8", # Even Darker
        "sidebar_divider": "#60A5FA",
        
        "card_bg": "#FFFFFF",
        "card_border": "#E2E8F0",
        "card_shadow": "#94A3B833", # Semi-transparent slate
    }
    
    DARK = {
        # Background colors
        "bg": "#0F172A",
        "bg_secondary": "#1E293B",
        "bg_tertiary": "#334155",
        
        # Surface colors (cards, panels)
        "surface": "#1E293B",
        "surface_hover": "#334155",
        "surface_active": "#475569",
        
        # Text colors
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "text_tertiary": "#94A3B8",
        "text_inverse": "#0F172A",
        
        # Primary accent (Blue)
        "primary": "#60A5FA",
        "primary_hover": "#3B82F6",
        "primary_active": "#2563EB",
        "primary_light": "#1E3A5F",
        
        # Secondary accent (Purple)
        "secondary": "#A78BFA",
        "secondary_hover": "#8B5CF6",
        "secondary_active": "#7C3AED",
        "secondary_light": "#2E1065",
        
        # Success (Green)
        "success": "#34D399",
        "success_hover": "#10B981",
        "success_light": "#064E3B",
        
        # Warning (Amber)
        "warning": "#FBBF24",
        "warning_hover": "#F59E0B",
        "warning_light": "#78350F",
        
        # Error (Red)
        "error": "#F87171",
        "error_hover": "#EF4444",
        "error_light": "#7F1D1D",
        
        # Border colors
        "border": "#334155",
        "border_focus": "#60A5FA",
        
        # Special
        "overlay": "#00000080",
        "tooltip_bg": "#F8FAFC",
        "tooltip_text": "#0F172A",
        
        # Legacy compatibility mappings
        "fg": "#F8FAFC",
        "button_bg": "#60A5FA",
        "button_fg": "#0F172A",
        "entry_bg": "#1E293B",
        "entry_fg": "#F8FAFC",
        "label_bg": "#0F172A",
        "label_fg": "#F8FAFC",
        "radiobutton_bg": "#0F172A",
        "radiobutton_fg": "#F8FAFC",
        "frame_bg": "#0F172A",
        
        # Modern Layout Tokens
        "sidebar_bg": "#1E293B", # Dark Slate
        "sidebar_fg": "#F8FAFC",
        "sidebar_hover": "#334155",
        "sidebar_active": "#475569",
        "sidebar_divider": "#334155",
        
        "card_bg": "#1E293B",
        "card_border": "#334155",
        "card_shadow": "#00000066",
    }


class UIStyles:
    """Enhanced UI styling manager with premium aesthetics"""
    
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.tokens = DesignTokens()
        
    def get_font(self, size="md", weight="normal"):
        """Get font tuple with fallback"""
        sizes = {
            "xs": self.tokens.FONT_SIZE_XS,
            "sm": self.tokens.FONT_SIZE_SM,
            "md": self.tokens.FONT_SIZE_MD,
            "lg": self.tokens.FONT_SIZE_LG,
            "xl": self.tokens.FONT_SIZE_XL,
            "xxl": self.tokens.FONT_SIZE_XXL,
            "hero": self.tokens.FONT_SIZE_HERO,
        }
        font_size = sizes.get(size, self.tokens.FONT_SIZE_MD)
        font_weight = "bold" if weight == "bold" else ""
        return (self.tokens.FONT_FAMILY, font_size, font_weight) if font_weight else (self.tokens.FONT_FAMILY, font_size)

    def apply_theme(self, theme_name):
        """Apply the selected theme to the application"""
        self.app.current_theme = theme_name
        
        # Get appropriate color scheme
        if theme_name == "dark":
            self.app.colors = ColorSchemes.DARK.copy()
        else:
            self.app.colors = ColorSchemes.LIGHT.copy()
        
        # Configure root window
        self.root.configure(bg=self.app.colors["bg"])
        
        # Configure default widget styles
        self.root.option_add("*Background", self.app.colors["bg"])
        self.root.option_add("*Foreground", self.app.colors["fg"])
        self.root.option_add("*Button.Background", self.app.colors["button_bg"])
        self.root.option_add("*Button.Foreground", self.app.colors["button_fg"])
        self.root.option_add("*Entry.Background", self.app.colors["entry_bg"])
        self.root.option_add("*Entry.Foreground", self.app.colors["entry_fg"])
        self.root.option_add("*Label.Background", self.app.colors["label_bg"])
        self.root.option_add("*Label.Foreground", self.app.colors["label_fg"])
        self.root.option_add("*Radiobutton.Background", self.app.colors["radiobutton_bg"])
        self.root.option_add("*Radiobutton.Foreground", self.app.colors["radiobutton_fg"])
        self.root.option_add("*Radiobutton.selectColor", self.app.colors["bg"])
        self.root.option_add("*Frame.Background", self.app.colors["frame_bg"])
        
        # Configure ttk styles for modern widgets
        self._configure_ttk_styles()

    def _configure_ttk_styles(self):
        """Configure ttk styles for modern look"""
        style = ttk.Style()
        
        # PROACTIVE FIX: Force 'clam' theme to respect custom background colors
        # Standard Windows themes (vista/xpnative) often ignore custom fieldbackgrounds.
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass # Fallback if clam unavailable
        
        # General background fix for clam
        style.configure(".", background=self.app.colors["bg"], foreground=self.app.colors["fg"])

        # Progress bar style
        style.configure(
            "Premium.Horizontal.TProgressbar",
            troughcolor=self.app.colors["bg_secondary"],
            background=self.app.colors["primary"],
            thickness=8,
            borderwidth=0
        )
        
        # Notebook (Tab) style
        style.configure(
            "Premium.TNotebook",
            background=self.app.colors["bg"],
            borderwidth=0,
            tabmargins=[0, 0, 0, 0]
        )
        style.configure(
            "Premium.TNotebook.Tab",
            background=self.app.colors["surface"],
            foreground=self.app.colors["text_secondary"],
            padding=[16, 8],
            font=self.get_font("md"),
            borderwidth=0
        )
        style.map(
            "Premium.TNotebook.Tab",
            background=[("selected", self.app.colors["primary"])],
            foreground=[("selected", self.app.colors["text_inverse"])]
        )
        
        # Combobox Style
        # Clam theme uses fieldbackground for the input area
        style.configure(
            "TCombobox",
            fieldbackground=self.app.colors["entry_bg"],
            background=self.app.colors["bg_secondary"], # Arrow area
            foreground=self.app.colors["text_primary"],
            arrowcolor=self.app.colors["text_primary"],
            selectbackground=self.app.colors["primary"],
            selectforeground=self.app.colors["text_inverse"],
            borderwidth=1,
            relief="flat"
        )
        
        # We need to being very specific for Clam
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.app.colors["entry_bg"]), ("disabled", self.app.colors["bg_tertiary"])],
            selectbackground=[("readonly", self.app.colors["entry_bg"]), ("!focus", self.app.colors["entry_bg"])],
            selectforeground=[("readonly", self.app.colors["text_primary"]), ("!focus", self.app.colors["text_primary"])],
            foreground=[("readonly", self.app.colors["text_primary"]), ("disabled", self.app.colors["text_secondary"])]
        )

    def create_widget(self, widget_type, *args, **kwargs):
        """Create a widget with current theme colors"""
        # Override colors if not specified
        if widget_type == tk.Label:
            kwargs.setdefault("bg", self.app.colors["label_bg"])
            kwargs.setdefault("fg", self.app.colors["label_fg"])
        elif widget_type == tk.Button:
            kwargs.setdefault("bg", self.app.colors["button_bg"])
            kwargs.setdefault("fg", self.app.colors["button_fg"])
            kwargs.setdefault("activebackground", self.app.colors.get("primary_hover", self.darken_color(self.app.colors["button_bg"])))
            kwargs.setdefault("activeforeground", self.app.colors["button_fg"])
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("cursor", "hand2")
            kwargs.setdefault("borderwidth", 0)
        elif widget_type == tk.Entry:
            kwargs.setdefault("bg", self.app.colors["entry_bg"])
            kwargs.setdefault("fg", self.app.colors["entry_fg"])
            kwargs.setdefault("insertbackground", self.app.colors["fg"])
            kwargs.setdefault("relief", "flat")
            kwargs.setdefault("highlightthickness", 1)
            kwargs.setdefault("highlightbackground", self.app.colors["border"])
            kwargs.setdefault("highlightcolor", self.app.colors["border_focus"])
        elif widget_type == tk.Radiobutton:
            kwargs.setdefault("bg", self.app.colors["radiobutton_bg"])
            kwargs.setdefault("fg", self.app.colors["radiobutton_fg"])
            kwargs.setdefault("selectcolor", self.app.colors["primary"])
            kwargs.setdefault("activebackground", self.app.colors["radiobutton_bg"])
            kwargs.setdefault("activeforeground", self.app.colors["radiobutton_fg"])
        elif widget_type == tk.Frame:
            kwargs.setdefault("bg", self.app.colors["frame_bg"])
        
        return widget_type(*args, **kwargs)

    def create_card(self, parent, **kwargs):
        """Create a card-style container with elevated appearance"""
        card = tk.Frame(
            parent,
            bg=self.app.colors["surface"],
            highlightbackground=self.app.colors["border"],
            highlightthickness=1,
            **kwargs
        )
        return card

    def create_primary_button(self, parent, text, command, **kwargs):
        """Create a primary action button with hover effects"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.app.colors["primary"],
            fg=self.app.colors["text_inverse"],
            activebackground=self.app.colors["primary_hover"],
            activeforeground=self.app.colors["text_inverse"],
            font=self.get_font("md", "bold"),
            relief="flat",
            cursor="hand2",
            borderwidth=0,
            padx=self.tokens.SPACING_LG,
            pady=self.tokens.SPACING_MD,
            **kwargs
        )
        
        # Hover effects
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.app.colors["primary_hover"]))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.app.colors["primary"]))
        
        return btn

    def create_secondary_button(self, parent, text, command, **kwargs):
        """Create a secondary action button"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.app.colors["surface"],
            fg=self.app.colors["text_primary"],
            activebackground=self.app.colors["surface_hover"],
            activeforeground=self.app.colors["text_primary"],
            font=self.get_font("md"),
            relief="flat",
            cursor="hand2",
            borderwidth=1,
            highlightbackground=self.app.colors["border"],
            padx=self.tokens.SPACING_LG,
            pady=self.tokens.SPACING_MD,
            **kwargs
        )
        
        # Hover effects
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.app.colors["surface_hover"]))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.app.colors["surface"]))
        
        return btn

    def create_success_button(self, parent, text, command, **kwargs):
        """Create a success/confirm button"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.app.colors["success"],
            fg=self.app.colors["text_inverse"],
            activebackground=self.app.colors["success_hover"],
            activeforeground=self.app.colors["text_inverse"],
            font=self.get_font("md", "bold"),
            relief="flat",
            cursor="hand2",
            borderwidth=0,
            padx=self.tokens.SPACING_LG,
            pady=self.tokens.SPACING_MD,
            **kwargs
        )
        
        # Hover effects
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.app.colors["success_hover"]))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.app.colors["success"]))
        
        return btn

    def darken_color(self, color):
        """Darken a color for active button state"""
        if color.startswith("#") and len(color) >= 7:
            try:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                r = max(0, r - 30)
                g = max(0, g - 30)
                b = max(0, b - 30)
                return f"#{r:02x}{g:02x}{b:02x}"
            except ValueError:
                return color
        return color

    def lighten_color(self, color, amount=30):
        """Lighten a color for hover state"""
        if color.startswith("#") and len(color) >= 7:
            try:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                r = min(255, r + amount)
                g = min(255, g + amount)
                b = min(255, b + amount)
                return f"#{r:02x}{g:02x}{b:02x}"
            except ValueError:
                return color
        return color

    def toggle_tooltip(self, event, text):
        """Toggle tooltip visibility on click/enter"""
        if hasattr(self.app, 'tooltip_win') and self.app.tooltip_win:
            self.app.tooltip_win.destroy()
            self.app.tooltip_win = None
            return

        x, y, _, _ = event.widget.bbox("insert") if hasattr(event.widget, 'bbox') else (0, 0, 0, 0)
        x += event.widget.winfo_rootx() + 25
        y += event.widget.winfo_rooty() + 25

        self.app.tooltip_win = tk.Toplevel(self.root)
        self.app.tooltip_win.wm_overrideredirect(True)
        self.app.tooltip_win.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.app.tooltip_win,
            text=text,
            justify='left',
            background=self.app.colors.get("tooltip_bg", "#1E293B"),
            foreground=self.app.colors.get("tooltip_text", "#F8FAFC"),
            relief='flat',
            borderwidth=0,
            font=self.get_font("sm"),
            padx=self.tokens.SPACING_MD,
            pady=self.tokens.SPACING_SM
        )
        label.pack()
        
        # Auto-hide after 3 seconds
        self.root.after(3000, lambda: self.app.tooltip_win.destroy() if hasattr(self.app, 'tooltip_win') and self.app.tooltip_win else None)
