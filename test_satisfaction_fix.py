#!/usr/bin/env python3
"""
Test script to verify the Tkinter Canvas Invalid Command Error fix in Satisfaction UI.

This test creates a SatisfactionSurvey instance and simulates mouse wheel events
to ensure the canvas remains valid and no TclError occurs.
"""

import os
import sys
import tkinter as tk
from unittest.mock import MagicMock, patch

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_satisfaction_canvas_fix():
    """Test that the canvas fix prevents TclError on mouse wheel events."""

    # Create a mock root window
    root = tk.Tk()
    root.withdraw()  # Hide the window for headless testing

    try:
        # Import the SatisfactionSurvey
        from app.ui.satisfaction import SatisfactionSurvey

        # Mock the database and other dependencies
        with patch('app.db.get_session') as mock_session, \
             patch('app.questions.SATISFACTION_QUESTIONS', {'satisfaction_level': {'en': 'Test question'}}), \
             patch('app.questions.SATISFACTION_OPTIONS', {'context_options': {'en': ['Test']}}):

            # Create a mock session
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            # Create the satisfaction survey
            survey = SatisfactionSurvey(root, "testuser", user_id=1)

            # Show the survey (this creates the canvas)
            survey.show()

            # Verify canvas was created as instance variable
            assert hasattr(survey, 'canvas'), "Canvas should be an instance variable"
            assert survey.canvas is not None, "Canvas should not be None"

            # Simulate mouse wheel event by triggering the bound event
            # Create a mock event with delta (Windows mouse wheel)
            mock_event = MagicMock()
            mock_event.delta = 120  # Standard mouse wheel delta

            # The mouse wheel event is bound globally to "<MouseWheel>"
            # We need to simulate the event being triggered
            # Since the handler checks if canvas exists, we can test by generating the event

            # First, verify canvas exists
            assert survey.canvas.winfo_exists(), "Canvas should exist initially"

            # Generate a mouse wheel event on the canvas
            try:
                # Simulate mouse wheel event - this will trigger the bound handler
                survey.canvas.event_generate("<MouseWheel>", delta=120)
                print("✓ Mouse wheel event generated successfully while canvas exists")
            except tk.TclError as e:
                print(f"✗ FAILED: TclError during mouse wheel event: {e}")
                return False

            # Test closing the survey
            survey.on_close()

            # After closing, canvas should be destroyed
            assert not survey.canvas.winfo_exists(), "Canvas should be destroyed after closing"

            # Try to generate mouse wheel event after destruction
            # This should not crash due to the winfo_exists() check in the handler
            try:
                survey.canvas.event_generate("<MouseWheel>", delta=120)
                print("✓ Mouse wheel event after canvas destruction handled gracefully")
            except tk.TclError as e:
                if "invalid command name" in str(e):
                    print("✗ FAILED: TclError still occurs after canvas destruction")
                    return False
                else:
                    # Re-raise if it's a different error
                    raise

            print("✓ Canvas fix verified: No TclError on mouse wheel after canvas destruction")
            return True

    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            root.destroy()
        except:
            pass

if __name__ == "__main__":
    print("Testing Tkinter Canvas Invalid Command Error fix...")

    success = test_satisfaction_canvas_fix()

    if success:
        print("\n🎉 All tests passed! The canvas fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. The fix needs more work.")
        sys.exit(1)
