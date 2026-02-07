# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- **Session Tracking System**: Complete session management with unique session IDs
  - Secure session ID generation using 256-bit cryptographic tokens
  - Session storage in database with user ID, timestamps, and activity tracking
  - Session validation with automatic 24-hour expiration
  - Session invalidation on logout with logged-out timestamp recording
  - Support for multiple concurrent user sessions
  - Session cleanup utilities for removing old/expired sessions
  - Bulk session invalidation for specific users
  - CLI utility for session management (`session_manager.py`)
  - Comprehensive test suite with 10 test cases covering all features
  - Database migration script for existing installations
  - Detailed documentation in `SESSION_TRACKING.md`
- Initial project setup
- Core exam/test flow
- Result generation logic

### Changed

- Updated `AuthManager` with session management methods
- Migrated from deprecated `datetime.utcnow()` to `datetime.now(UTC)` (Python 3.13+)
- Enhanced `User` model with sessions relationship
- UI improvements and styling updates

### Fixed

- Minor bug fixes and validation improvements

---

## [0.1.0] - Initial Release

### Added

- Basic exam platform structure
- Question rendering and submission
- Score calculation
