import tkinter as tk
from tkinter import messagebox
import time
from app.logger import get_logger
from app.security_config import INACTIVITY_TIMEOUT_SECONDS, INACTIVITY_WARNING_SECONDS

class IdleWatcher:
    """
    Monitors user activity (mouse/keyboard) and triggers a logout callback
    after a specified period of inactivity.
    
    Issue #999: Session timeout handling
    """
    def __init__(self, root, logout_callback, timeout_seconds=None):
        """
        Args:
            root: The Tkinter root window
            logout_callback: Function to call when timeout is reached
            timeout_seconds: Seconds of inactivity before logout (default from config)
        """
        self.root = root
        self.logout_callback = logout_callback
        # Use configured timeout or fallback to 15 minutes
        self.timeout_seconds = timeout_seconds or INACTIVITY_TIMEOUT_SECONDS
        # Use configured warning threshold
        self.warning_threshold = INACTIVITY_WARNING_SECONDS
        
        self.last_activity = time.time()
        self.warning_shown = False
        self.warning_dialog = None
        self.logger = get_logger(__name__)
        
        # Throttling for motion events
        self.last_motion_process = 0
        
        self.is_running = False
        self.check_job = None
        self.logger.info(f"IdleWatcher initialized with timeout={timeout_seconds}s")

    def start(self):
        """Start monitoring for inactivity"""
        if self.is_running:
            return
            
        self.is_running = True
        self.last_activity = time.time()
        self._bind_events()
        self._schedule_check()
        self.logger.info("IdleWatcher monitoring started")

    def stop(self):
        """Stop monitoring"""
        if not self.is_running:
            return
            
        self.is_running = False
        self._unbind_events()
        if self.check_job:
            self.root.after_cancel(self.check_job)
            self.check_job = None
            
        if self.warning_dialog:
            try:
                self.warning_dialog.destroy()
            except: pass
            self.warning_dialog = None
            self.warning_shown = False
            
        self.logger.info("IdleWatcher monitoring stopped")

    def _bind_events(self):
        """Bind global events to reset timer"""
        # Bind to 'all' allows catching events even if widgets have focus
        self.root.bind_all("<Key>", self._reset_timer)
        self.root.bind_all("<Button>", self._reset_timer)
        self.root.bind_all("<Motion>", self._on_motion)

    def _on_motion(self, event=None):
        """Throttle motion events to avoid excessive processing"""
        now = time.time()
        if now - self.last_motion_process > 1.0: # Process max once per sec
            self.last_motion_process = now
            self._reset_timer(event)

    def _reset_timer(self, event=None):
        """Reset the inactivity timer"""
        if not self.is_running:
            return
            
        self.last_activity = time.time()
        
        # If warning is showing, close it since user came back
        if self.warning_shown and self.warning_dialog:
            try:
                self.warning_dialog.destroy()
                self.warning_dialog = None
            except:
                pass # Already destroyed
            self.warning_shown = False
            self.logger.info("User activity detected. Idle warning dismissed.")

    def _schedule_check(self):
        """Schedule the next check"""
        if self.is_running:
            # check every 1 second
            self.check_job = self.root.after(1000, self._check_idle)

    def _check_idle(self):
        """Check if we passed the timeout"""
        try:
            now = time.time()
            elapsed = now - self.last_activity
            remaining = self.timeout_seconds - elapsed
            
            # Case 1: Timeout Reached
            if remaining <= 0:
                self.logger.warning("Idle timeout reached. Triggering logout.")
                self.stop() # Ensure clean stop
                self.logout_callback()
                return # Stop checking
                
            # Case 2: Warning Threshold Reached
            elif remaining <= self.warning_threshold and not self.warning_shown:
                self._show_warning()
                
        except Exception as e:
            self.logger.error(f"Error in idle check: {e}")
            
        # Reschedule
        self._schedule_check()
        
    def _show_warning(self):
        """Show a non-blocking top-level warning window"""
        self.warning_shown = True
        self.logger.info("Showing idle warning")
        
        try:
            wd = tk.Toplevel(self.root)
            wd.title("Idle Warning")
            
            # Position logic
            w_w, w_h = 300, 150
            x = self.root.winfo_x() + (self.root.winfo_width()//2) - (w_w//2)
            y = self.root.winfo_y() + (self.root.winfo_height()//2) - (w_h//2)
            wd.geometry(f"{w_w}x{w_h}+{x}+{y}")
            
            wd.transient(self.root)
            wd.grab_set()
            wd.attributes("-topmost", True)
            
            tk.Label(wd, text="Are you still there?", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
            tk.Label(wd, text="You will be logged out in 30 seconds\ndue to inactivity.", 
                    font=("Segoe UI", 10)).pack(pady=(0, 20))
            
            # Button just closes dialog (which triggers _reset_timer ideally via click, 
            # but button command explicitly resetting is safer)
            def on_continue():
                self._reset_timer()
                
            tk.Button(wd, text="I'm still here", command=on_continue, 
                     bg="#3B82F6", fg="white", font=("Segoe UI", 10, "bold"), padx=20).pack()
            
            # Handle X button
            wd.protocol("WM_DELETE_WINDOW", on_continue)
            
            self.warning_dialog = wd
            
        except Exception as e:
            self.logger.error(f"Failed to show warning dialog: {e}")

    def _unbind_events(self):
        try:
            self.root.unbind_all("<Key>")
            self.root.unbind_all("<Button>")
            self.root.unbind_all("<Motion>")
        except:
            pass
