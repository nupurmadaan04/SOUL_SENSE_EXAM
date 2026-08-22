"""
Form State Management

This module provides utilities for preserving form state and managing validation
errors in Tkinter forms. It ensures that user input is never lost due to validation
errors and provides clear visual feedback about what needs to be corrected.
"""

import tkinter as tk
from typing import Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field


@dataclass
class FormFieldState:
    """Represents the state of a single form field."""
    name: str
    value: str = ""
    error: str = ""
    is_valid: bool = True
    touched: bool = False
    widget: Optional[tk.Widget] = None
    error_label: Optional[tk.Label] = None


@dataclass
class FormState:
    """Represents the complete state of a form."""
    fields: Dict[str, FormFieldState] = field(default_factory=dict)
    is_submitting: bool = False
    general_error: str = ""
    
    def add_field(self, name: str, widget: Optional[tk.Widget] = None, 
                  error_label: Optional[tk.Label] = None) -> FormFieldState:
        """Add a field to the form state."""
        field_state = FormFieldState(name=name, widget=widget, error_label=error_label)
        self.fields[name] = field_state
        return field_state
    
    def get_field(self, name: str) -> Optional[FormFieldState]:
        """Get a field's state."""
        return self.fields.get(name)
    
    def set_field_value(self, name: str, value: str) -> None:
        """Set a field's value."""
        if name in self.fields:
            self.fields[name].value = value
    
    def set_field_error(self, name: str, error: str) -> None:
        """Set a field's error message."""
        if name in self.fields:
            field_state = self.fields[name]
            field_state.error = error
            field_state.is_valid = not error
            
            # Update the error label if it exists
            if field_state.error_label:
                field_state.error_label.config(text=error)
                if error:
                    field_state.error_label.pack(anchor="w", pady=(0, 2))
                else:
                    field_state.error_label.pack_forget()
            
            # Update the widget's visual state
            if field_state.widget:
                if error:
                    field_state.widget.config(highlightbackground="#EF4444", highlightcolor="#EF4444")
                else:
                    field_state.widget.config(highlightbackground="#10B981", highlightcolor="#10B981")
    
    def clear_field_error(self, name: str) -> None:
        """Clear a field's error message."""
        self.set_field_error(name, "")
    
    def clear_all_errors(self) -> None:
        """Clear all field errors."""
        for field_state in self.fields.values():
            self.set_field_error(field_state.name, "")
    
    def has_errors(self) -> bool:
        """Check if the form has any validation errors."""
        return any(not field.is_valid for field in self.fields.values())
    
    def get_all_values(self) -> Dict[str, str]:
        """Get all field values as a dictionary."""
        return {name: field.value for name, field in self.fields.items()}
    
    def get_all_errors(self) -> Dict[str, str]:
        """Get all field errors as a dictionary."""
        return {name: field.error for name, field in self.fields.items() if field.error}


class FormStateManager:
    """
    Manages form state preservation and validation for Tkinter forms.
    
    This class handles:
    - Preserving user input values
    - Managing validation errors
    - Updating UI elements with error states
    - Preventing data loss on validation failures
    """
    
    def __init__(self):
        self.form_states: Dict[str, FormState] = {}
    
    def create_form(self, form_name: str) -> FormState:
        """Create a new form state tracker."""
        if form_name not in self.form_states:
            self.form_states[form_name] = FormState()
        return self.form_states[form_name]
    
    def get_form(self, form_name: str) -> Optional[FormState]:
        """Get a form's state."""
        return self.form_states.get(form_name)
    
    def register_field(self, form_name: str, field_name: str, 
                      widget: Optional[tk.Widget] = None,
                      error_label: Optional[tk.Label] = None) -> FormFieldState:
        """Register a field in a form."""
        form_state = self.create_form(form_name)
        return form_state.add_field(field_name, widget, error_label)
    
    def update_field_value(self, form_name: str, field_name: str, value: str) -> None:
        """Update a field's value."""
        form_state = self.get_form(form_name)
        if form_state:
            form_state.set_field_value(field_name, value)
    
    def set_field_error(self, form_name: str, field_name: str, error: str) -> None:
        """Set a field's error message."""
        form_state = self.get_form(form_name)
        if form_state:
            form_state.set_field_error(field_name, error)
    
    def clear_field_error(self, form_name: str, field_name: str) -> None:
        """Clear a field's error."""
        form_state = self.get_form(form_name)
        if form_state:
            form_state.clear_field_error(field_name)
    
    def clear_all_errors(self, form_name: str) -> None:
        """Clear all errors in a form."""
        form_state = self.get_form(form_name)
        if form_state:
            form_state.clear_all_errors()
    
    def validate_required(self, form_name: str, field_name: str, 
                         value: str, message: str = "This field is required") -> bool:
        """Validate that a field is not empty."""
        if not value or not value.strip():
            self.set_field_error(form_name, field_name, message)
            return False
        else:
            self.clear_field_error(form_name, field_name)
            return True
    
    def validate_custom(self, form_name: str, field_name: str, 
                       validator: Callable[[str], Tuple[bool, str]]) -> bool:
        """
        Validate a field using a custom validator function.
        
        The validator should return a tuple of (is_valid, error_message).
        """
        form_state = self.get_form(form_name)
        if not form_state:
            return False
        
        field_state = form_state.get_field(field_name)
        if not field_state:
            return False
        
        is_valid, error_message = validator(field_state.value)
        if not is_valid:
            self.set_field_error(form_name, field_name, error_message)
            return False
        else:
            self.clear_field_error(form_name, field_name)
            return True
    
    def validate_matching_fields(self, form_name: str, field1: str, field2: str,
                                 error_message: str = "Fields do not match") -> bool:
        """Validate that two fields have matching values."""
        form_state = self.get_form(form_name)
        if not form_state:
            return False
        
        field1_state = form_state.get_field(field1)
        field2_state = form_state.get_field(field2)
        
        if not field1_state or not field2_state:
            return False
        
        if field1_state.value == field2_state.value:
            self.clear_field_error(form_name, field2)
            return True
        else:
            self.set_field_error(form_name, field2, error_message)
            return False
    
    def get_form_values(self, form_name: str) -> Dict[str, str]:
        """Get all values from a form."""
        form_state = self.get_form(form_name)
        if form_state:
            return form_state.get_all_values()
        return {}
    
    def has_errors(self, form_name: str) -> bool:
        """Check if a form has any errors."""
        form_state = self.get_form(form_name)
        if form_state:
            return form_state.has_errors()
        return False


# Global instance for use throughout the app
_form_state_manager = FormStateManager()


def get_form_state_manager() -> FormStateManager:
    """Get the global form state manager instance."""
    return _form_state_manager
