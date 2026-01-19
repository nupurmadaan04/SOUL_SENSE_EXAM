import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock tkinter to avoid display errors during headless testing
# We only need it to allow imports, the tests use MagicMock for widgets.
sys.modules['tkinter'] = MagicMock()

# Now import the module under test
import app.ui.validation_ui as v_ui

class TestValidationUI(unittest.TestCase):
    
    def test_setup_entry_limit_configuration(self):
        """Verify setup_entry_limit configures the entry widget correctly."""
        mock_entry = MagicMock()
        limit = 10
        
        v_ui.setup_entry_limit(mock_entry, limit)
        
        # Check that a validation command was registered
        mock_entry.register.assert_called_once()
        
        # Check that configure was called with validate='key'
        mock_entry.configure.assert_called_with(
            validate='key',
            validatecommand=ANY # The tuple (vcmd, '%P')
        )
        
    def test_entry_limit_logic(self):
        """Verify the validation function enforces the limit."""
        mock_entry = MagicMock()
        limit = 5
        
        v_ui.setup_entry_limit(mock_entry, limit)
        
        # Extract the validation function passed to register
        validate_func = mock_entry.register.call_args[0][0]
        
        # 1. Input within limit
        self.assertTrue(validate_func("hello")) # 5 chars
        mock_entry.bell.assert_not_called()
        
        # 2. Input below limit
        self.assertTrue(validate_func("hi"))
        
        # 3. Input exceeds limit
        self.assertFalse(validate_func("hello!")) # 6 chars
        mock_entry.bell.assert_called_once()
        
    def test_setup_text_limit_configuration(self):
        """Verify setup_text_limit binds correct events."""
        mock_text = MagicMock()
        limit = 100
        
        v_ui.setup_text_limit(mock_text, limit)
        
        # Check bindings
        mock_text.bind.assert_any_call('<KeyPress>', ANY)
        mock_text.bind.assert_any_call('<KeyRelease>', ANY)
        
    def test_text_keypress_logic(self):
        """Verify KeyPress blocks input when limit reached."""
        mock_text = MagicMock()
        # Explicitly mock empty selection (default MagicMock is truthy)
        mock_text.tag_ranges.return_value = []
        limit = 5
        v_ui.setup_text_limit(mock_text, limit)
        
        # Extract the KeyPress handler
        # Note: bind is called twice, need to find the one for KeyPress
        calls = mock_text.bind.call_args_list
        keypress_handler = None
        for args, _ in calls:
            if args[0] == '<KeyPress>':
                keypress_handler = args[1]
                break
                
        self.assertIsNotNone(keypress_handler)
        
        # Mock Event
        mock_event = MagicMock()
        mock_event.keysym = "a"
        mock_event.state = 0
        
        # Case 1: Under limit
        mock_text.get.return_value = "hi" # Length 2
        result = keypress_handler(mock_event)
        self.assertIsNone(result) # None means "continue" (allow)
        
        # Case 2: At limit
        mock_text.get.return_value = "hello" # Length 5
        result = keypress_handler(mock_event)
        self.assertEqual(result, "break") # Block input
        mock_text.bell.assert_called()
        
        # Case 3: At limit but BackSpace
        mock_event.keysym = "BackSpace"
        result = keypress_handler(mock_event)
        self.assertIsNone(result) # Allow deletion
        
    def test_text_keyrelease_logic(self):
        """Verify KeyRelease trims content (Paste protection)."""
        mock_text = MagicMock()
        limit = 5
        v_ui.setup_text_limit(mock_text, limit)
        
        # Extract handler
        calls = mock_text.bind.call_args_list
        keyrelease_handler = None
        for args, _ in calls:
            if args[0] == '<KeyRelease>':
                keyrelease_handler = args[1]
                break
                
        # Mock content exceeding limit (e.g. after paste)
        mock_text.get.return_value = "hello world" # 11 chars
        
        keyrelease_handler(MagicMock())
        
        # Verify delete was called to trim
        mock_text.delete.assert_called_with(f"1.0 + {limit} chars", "end")
        mock_text.bell.assert_called()

    def test_text_keypress_with_selection(self):
        """Verify KeyPress allows typing if text is selected (replacement), even at limit."""
        mock_text = MagicMock()
        limit = 5
        v_ui.setup_text_limit(mock_text, limit)

        # Extract handler
        keypress_handler = None
        for args, _ in mock_text.bind.call_args_list:
            if args[0] == '<KeyPress>':
                keypress_handler = args[1]
                break

        mock_event = MagicMock()
        mock_event.keysym = "a"
        mock_event.state = 0

        # Setup: Text is full "hello"
        mock_text.get.return_value = "hello"
        
        # Scenario: User selects "hel" (indices "1.0", "1.3") and types 'a'
        # The result should be "alo" (3 chars) -> Valid.
        # But current logic blocks if len >= limit.
        
        # Mock selection exists
        mock_text.tag_ranges.return_value = ["1.0", "1.3"]
        
        # Test
        result = keypress_handler(mock_event)
        
        # Should allow (return None), currently might fail (return "break")
        # We Assert what SHOULD happen:
        self.assertIsNone(result, "Should allow typing if selection is being replaced")
        
        # Verify tag_ranges was checked
        mock_text.tag_ranges.assert_called_with("sel")

if __name__ == "__main__":
    unittest.main()
