# Bug Fix: Tkinter Canvas Invalid Command Error in Satisfaction UI

## Problem
When scrolling with the mouse wheel in the satisfaction survey UI, a TclError occurs because the canvas widget is no longer valid (destroyed or out of scope), causing the application to crash.

## Root Cause
The canvas was defined as a local variable in the `show()` method, and the `_on_mousewheel` function was bound globally. When the window was closed, the canvas was destroyed, but the event handler still tried to access it.

## Solution
1. Make the canvas an instance variable (`self.canvas`) so it persists as long as the survey object exists.
2. Add a check in `_on_mousewheel` to verify the canvas still exists using `winfo_exists()` before calling `yview_scroll`.
3. Ensure all references to the canvas use `self.canvas`.

## Changes Made
- [x] Modified `app/ui/satisfaction.py` to store canvas as `self.canvas`
- [x] Added existence check in `_on_mousewheel` function
- [x] Fixed pack layout to use `self.canvas.pack()`

## Testing
- The fix prevents the TclError by checking if the canvas widget is still valid before attempting to scroll.
- Mouse wheel scrolling will now work smoothly without crashes.
- The canvas remains functional throughout the UI interaction.

## Status
✅ Bug fixed and implemented.
