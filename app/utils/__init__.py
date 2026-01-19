
import json
import os
import logging
from typing import Dict, Any, Optional, Union
from app.config import DATA_DIR

SETTINGS_FILE: str = os.path.join(DATA_DIR, "settings.json")
DEFAULT_SETTINGS: Dict[str, Any] = {
    "question_count": 10,
    "theme": "light",
    "sound_effects": True
}

def load_settings() -> Dict[str, Any]:
    """Load user settings from file or use defaults"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Ensure all default keys exist
                for key in DEFAULT_SETTINGS:
                    if key not in settings:
                        settings[key] = DEFAULT_SETTINGS[key]
                return settings
        except Exception:
            logging.error("Failed to load settings", exc_info=True)
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: Dict[str, Any]) -> bool:
    """Save user settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        logging.error("Failed to save settings", exc_info=True)
        return False

def compute_age_group(age: Optional[Union[int, str]]) -> str:
    """
    Compute age group category based on age.
    
    This function maintains backward compatibility with existing categories
    (child, adult, senior, unknown) used by legacy code and tests.
    
    Args:
        age: Integer age or None
        
    Returns:
        str: Age group category - 'child', 'adult', 'senior', or 'unknown'
    """
    if age is None:
        return "unknown"
    try:
        age_int = int(age)
    except Exception:
        return "unknown"

    if age_int < 18:
        return "child"
    if age_int < 65:
        return "adult"
    return "senior"


def compute_detailed_age_group(age: Optional[Union[int, str]]) -> str:
    """
    Compute detailed age group for enhanced analytics and EDA.
    
    This function provides granular age groupings suitable for
    demographic analysis and trend identification across age cohorts.
    
    Age Groupings:
        - '13-17': Adolescents (13-17 years)
        - '18-24': Young Adults (18-24 years)
        - '25-34': Adults (25-34 years)
        - '35-44': Middle Age (35-44 years)
        - '45-54': Mature Adults (45-54 years)
        - '55-64': Pre-Senior (55-64 years)
        - '65+': Seniors (65+ years)
        - '<13': Children (under 13 years)
        - 'unknown': Invalid or missing age data
    
    Args:
        age: Integer age or None
        
    Returns:
        str: Detailed age group category
        
    Examples:
        >>> compute_detailed_age_group(16)
        '13-17'
        >>> compute_detailed_age_group(30)
        '25-34'
        >>> compute_detailed_age_group(70)
        '65+'
    """
    if age is None:
        return "unknown"
    
    try:
        age_int = int(age)
    except (ValueError, TypeError):
        return "unknown"
    
    # Validate age range
    if age_int < 0 or age_int > 120:
        return "unknown"
    
    # Detailed age groupings for analytics
    if age_int < 13:
        return "<13"
    elif age_int <= 17:
        return "13-17"
    elif age_int <= 24:
        return "18-24"
    elif age_int <= 34:
        return "25-34"
    elif age_int <= 44:
        return "35-44"
    elif age_int <= 54:
        return "45-54"
    elif age_int <= 64:
        return "55-64"
    else:  # 65+
        return "65+"
