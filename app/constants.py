# Based on EQ test norms (simulated data for demonstration)
BENCHMARK_DATA = {
    "age_groups": {
        "Under 18": {"avg_score": 28, "std_dev": 6, "sample_size": 1200},
        "18-25": {"avg_score": 32, "std_dev": 7, "sample_size": 2500},
        "26-35": {"avg_score": 34, "std_dev": 6, "sample_size": 3200},
        "36-50": {"avg_score": 36, "std_dev": 5, "sample_size": 2800},
        "51-65": {"avg_score": 38, "std_dev": 4, "sample_size": 1800},
        "65+": {"avg_score": 35, "std_dev": 6, "sample_size": 900}
    },
    "global": {
        "avg_score": 34,
        "std_dev": 6,
        "sample_size": 12500,
        "percentiles": {
            10: 24,
            25: 29,
            50: 34,
            75: 39,
            90: 42
        }
    },
    "professions": {
        "Student": {"avg_score": 31, "std_dev": 7},
        "Professional": {"avg_score": 36, "std_dev": 5},
        "Manager": {"avg_score": 38, "std_dev": 4},
        "Healthcare": {"avg_score": 39, "std_dev": 3},
        "Education": {"avg_score": 37, "std_dev": 4},
        "Technology": {"avg_score": 33, "std_dev": 6},
        "Creative": {"avg_score": 35, "std_dev": 5}
    }
}

# --- Typography ---
FONT_FAMILY_PRIMARY = "Segoe UI"
FONT_FAMILY_SECONDARY = "Georgia"
FONT_FAMILY_FALLBACK = "Arial"

# Font Sizes
FONT_SIZE_XS = 10
FONT_SIZE_SM = 12
FONT_SIZE_MD = 14
FONT_SIZE_LG = 18
FONT_SIZE_XL = 24
FONT_SIZE_XXL = 32
FONT_SIZE_HERO = 48

# --- Layout Metrics ---
DEFAULT_PADDING = 20
PADDING_XS = 5
PADDING_SM = 10
PADDING_MD = 20
PADDING_LG = 30
PADDING_XL = 40
PADDING_XXL = 60

# Icons
ICON_SIZE_SM = 16
ICON_SIZE_MD = 24
ICON_SIZE_LG = 32
ICON_SIZE_XL = 48

# --- UI Defaults ---
DEFAULT_WINDOW_SIZE = "1200x800"
DIALOG_SIZE_MD = "600x400"
DIALOG_SIZE_LG = "800x600"
AVATAR_SIZE_LG = 110
AVATAR_SIZE_SM = 40

# --- Validation Limits ---
MAX_USERNAME_LENGTH = 30
MIN_USERNAME_LENGTH = 3
MAX_PASSWORD_LENGTH = 64
MIN_PASSWORD_LENGTH = 8
MAX_AGE_LENGTH = 3

# Age Limits
AGE_MIN = 10
AGE_MAX = 120

# Text Area Limits
MAX_BIO_LENGTH = 500
MAX_MANIFESTO_LENGTH = 700
MAX_NOTE_LENGTH = 1000
MAX_ENTRY_LENGTH = 50  # Single line inputs
MAX_TEXT_LENGTH = 1000 # General text blocks

# --- Timeout / Durations ---
TOOLTIP_DELAY_MS = 500
TOOLTIP_DURATION_MS = 3000
ANIM_FAST_MS = 150
ANIM_NORMAL_MS = 300
ANIM_SLOW_MS = 500
