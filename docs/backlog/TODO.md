# Safe Application Shutdown Handling

## Tasks
- [x] Add graceful shutdown handler to main.py for tkinter window close
- [x] Add signal handlers for SIGINT/SIGTERM in main.py
- [x] Ensure database commits and connections are properly closed
- [x] Add shutdown logging
- [x] Test shutdown behavior to prevent data loss
- [x] Fix database session handling bug: Use scoped_session for thread-local sessions to ensure all pending changes are committed on shutdown
