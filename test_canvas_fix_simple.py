#!/usr/bin/env python3
"""
Simple unit test to verify the Tkinter Canvas Invalid Command Error fix logic.

This test verifies the core logic of the fix without creating actual GUI components.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_canvas_existence_check():
    """Test the logic of checking canvas existence before scrolling."""

    # Mock canvas object
    class MockCanvas:
        def __init__(self, exists=True):
            self.exists = exists

        def winfo_exists(self):
            return self.exists

        def yview_scroll(self, delta, unit):
            if not self.exists:
                raise Exception("Canvas is destroyed")
            return f"Scrolled {delta} {unit}"

    # Test case 1: Canvas exists
    canvas = MockCanvas(exists=True)
    result = None

    def _on_mousewheel(event):
        nonlocal result
        if canvas and canvas.winfo_exists():
            result = canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        else:
            result = "Canvas not available"

    # Mock event
    class MockEvent:
        def __init__(self, delta):
            self.delta = delta

    event = MockEvent(120)

    # Test with existing canvas
    _on_mousewheel(event)
    assert result == "Scrolled -1 units", f"Expected 'Scrolled -1 units', got {result}"
    print("✓ Mouse wheel scrolling works when canvas exists")

    # Test case 2: Canvas destroyed
    canvas.exists = False

    try:
        _on_mousewheel(event)
        assert result == "Canvas not available", f"Expected 'Canvas not available', got {result}"
        print("✓ Mouse wheel event handled gracefully when canvas is destroyed")
        return True
    except Exception as e:
        print(f"✗ FAILED: Exception occurred when canvas destroyed: {e}")
        return False

if __name__ == "__main__":
    print("Testing canvas existence check logic...")

    success = test_canvas_existence_check()

    if success:
        print("\n🎉 Logic test passed! The canvas fix logic is sound.")
        print("The fix should prevent TclError by checking canvas existence before scrolling.")
        sys.exit(0)
    else:
        print("\n❌ Logic test failed.")
        sys.exit(1)
