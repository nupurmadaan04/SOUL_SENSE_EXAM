# Database Session Management Refactor TODO

## Phase 1: Remove Redundancies
- [x] Remove redundant `get_session()` from `app/models.py`

## Phase 2: Replace Manual Session Management with Context Manager
- [x] Update `app/auth.py` - replace manual session.close() with safe_db_context()
- [x] Update `app/auth/app_auth.py` - replace manual session.close() with safe_db_context()
- [x] Update `app/main.py` - replace manual session.close() with safe_db_context()
- [x] Update `app/ui/app_initializer.py` - replace manual session.close() with safe_db_context()
- [x] Update `app/ui/correlation.py` - replace manual session.close() with safe_db_context()
- [ ] Update `app/ui/journal.py` - replace manual session.close() with safe_db_context()
- [ ] Update `app/ui/profile.py` - replace manual session.close() with safe_db_context()
- [ ] Update `app/ui/results.py` - replace manual session.close() with safe_db_context()
- [ ] Update `app/ui/satisfaction.py` - replace manual session.close() with safe_db_context()
- [ ] Update `app/ui/view_manager.py` - replace manual session.close() with safe_db_context()
- [ ] Update `app/ml/score_analyzer.py` - replace manual session.close() with safe_db_context()

## Phase 3: Replace Direct SQLite Usage with SQLAlchemy
- [ ] Update `app/db.py` - replace create_tables_directly() with SQLAlchemy
- [ ] Update `app/db_backup.py` - replace direct SQLite with SQLAlchemy
- [ ] Update `app/ml/bias_checker.py` - replace direct SQLite with SQLAlchemy
- [ ] Update `app/ml/xai_explainer.py` - replace direct SQLite with SQLAlchemy

## Phase 4: Add Session Leak Detection
- [ ] Add session leak detection to test suite
- [ ] Update test fixtures to detect leaks

## Phase 5: Verification
- [ ] Run tests to ensure no regressions
- [ ] Verify all database operations use consistent session management
