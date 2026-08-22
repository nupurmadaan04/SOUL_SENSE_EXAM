"""
Internationalization (i18n) Manager for SoulSense Application

This module provides localization support for multiple languages.
It manages language switching and string translation throughout the app.
"""

import json
import os
from typing import Dict, Any, Optional
from app.config import BASE_DIR


class I18nManager:
    """Manages internationalization and localization for the application"""
    
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'hi': 'हिंदी (Hindi)',
        'es': 'Español (Spanish)'
    }
    
    def __init__(self, default_language: str = 'en'):
        """
        Initialize the i18n manager
        
        Args:
            default_language: Default language code (default: 'en')
        """
        self.current_language = default_language
        self.translations: Dict[str, Any] = {}
        self.locales_dir = os.path.join(BASE_DIR, 'app', 'locales')
        
        # Load the default language
        self.load_language(default_language)
        
        # Load or create settings
        self.settings_file = os.path.join(BASE_DIR, 'app', 'language_settings.json')
        self.load_settings()
    
    def load_language(self, language_code: str) -> bool:
        """
        Load translations for a specific language
        
        Args:
            language_code: Language code (e.g., 'en', 'hi', 'es')
            
        Returns:
            True if language loaded successfully, False otherwise
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            print(f"Warning: Language '{language_code}' not supported. Using English.")
            language_code = 'en'
        
        locale_file = os.path.join(self.locales_dir, f'{language_code}.json')
        
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_language = language_code
            return True
        except FileNotFoundError:
            print(f"Error: Translation file not found: {locale_file}")
            if language_code != 'en':
                # Fallback to English
                return self.load_language('en')
            return False
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in translation file: {e}")
            return False
    
    def switch_language(self, language_code: str) -> bool:
        """
        Switch to a different language
        
        Args:
            language_code: Language code to switch to
            
        Returns:
            True if switch was successful
        """
        if self.load_language(language_code):
            self.save_settings()
            return True
        return False
    
    def get(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Get a translated string by key
        
        Args:
            key: Translation key
            default: Optional default value if key not found
            **kwargs: Format parameters
        """
        # Support dot notation for nested keys
        keys = key.split('.')
        value = self.translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None:
            # Return default if provided, else key
            return default if default is not None else key
        
        # If it's a string, format it with kwargs
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return str(value)
    
    def get_question(self, index: int) -> str:
        """
        Get a specific question by index
        
        Args:
            index: Question index (0-based)
            
        Returns:
            Translated question text
        """
        questions = self.translations.get('questions', [])
        if 0 <= index < len(questions):
            return questions[index]
        return f"Question {index + 1}"
    
    def get_all_questions(self) -> list:
        """
        Get all questions in current language
        
        Returns:
            List of question texts
        """
        return self.translations.get('questions', [])
    
    def get_language_name(self, language_code: Optional[str] = None) -> str:
        """
        Get the display name of a language
        
        Args:
            language_code: Language code (if None, returns current language name)
            
        Returns:
            Language display name
        """
        if language_code is None:
            language_code = self.current_language
        return self.SUPPORTED_LANGUAGES.get(language_code, language_code)
    
    def load_settings(self):
        """Load language settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_language = settings.get('language', 'en')
                    if saved_language != self.current_language:
                        self.load_language(saved_language)
        except Exception as e:
            print(f"Warning: Could not load language settings: {e}")
    
    def save_settings(self):
        """Save current language settings to file"""
        try:
            settings = {'language': self.current_language}
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save language settings: {e}")


# Global i18n instance
_i18n_instance = None


def get_i18n() -> I18nManager:
    """
    Get the global i18n manager instance
    
    Returns:
        Global I18nManager instance
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18nManager()
    return _i18n_instance


def set_language(language_code: str) -> bool:
    """
    Set the global language
    
    Args:
        language_code: Language code to set
        
    Returns:
        True if successful
    """
    return get_i18n().switch_language(language_code)


def translate(key: str, **kwargs) -> str:
    """
    Translate a key (convenience function)
    
    Args:
        key: Translation key
        **kwargs: Format parameters
        
    Returns:
        Translated string
    """
    return get_i18n().get(key, **kwargs)


# Alias for shorter syntax
t = translate
