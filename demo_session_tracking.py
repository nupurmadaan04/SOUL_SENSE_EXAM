"""
Session Tracking Demonstration
-------------------------------
This script demonstrates the session tracking functionality with unique session IDs.

Features demonstrated:
- Unique session ID generation on login
- Session storage in database
- Session validation
- Session invalidation on logout
- Multiple concurrent sessions
- Session cleanup
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.auth import AuthManager
from app.db import get_session, check_db_state
from app.models import Session, User
import time


def print_separator(title=""):
    """Print a visual separator"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print("-" * 60)


def demo_basic_session_flow():
    """Demonstrate basic session creation and invalidation"""
    print_separator("1. Basic Session Flow")
    
    auth = AuthManager()
    
    # Register a user
    print("Registering user 'demo_user'...")
    success, msg = auth.register_user("demo_user", "password123")
    print(f"  Result: {msg}")
    
    # Login
    print("\nLogging in 'demo_user'...")
    success, msg = auth.login_user("demo_user", "password123")
    print(f"  Result: {msg}")
    
    if success:
        print(f"  Session ID: {auth.current_session_id[:16]}...")
        print(f"  Current User: {auth.current_user}")
        
        # Show session in database
        session = get_session()
        try:
            db_session = session.query(Session).filter_by(
                session_id=auth.current_session_id
            ).first()
            
            print(f"\n  Session Details from Database:")
            print(f"    - User ID: {db_session.user_id}")
            print(f"    - Username: {db_session.username}")
            print(f"    - Created At: {db_session.created_at}")
            print(f"    - Is Active: {db_session.is_active}")
        finally:
            session.close()
        
        # Logout
        print("\nLogging out...")
        success, msg = auth.logout_user()
        print(f"  Result: {msg}")
        print(f"  Session ID after logout: {auth.current_session_id}")
        print(f"  Current User after logout: {auth.current_user}")


def demo_multiple_sessions():
    """Demonstrate multiple concurrent sessions"""
    print_separator("2. Multiple Concurrent Sessions")
    
    # Create multiple auth managers (simulating different devices/browsers)
    auth1 = AuthManager()
    auth2 = AuthManager()
    auth3 = AuthManager()
    
    # Login from different "devices"
    print("Logging in from Device 1...")
    auth1.login_user("demo_user", "password123")
    print(f"  Session ID: {auth1.current_session_id[:16]}...")
    
    print("\nLogging in from Device 2...")
    auth2.login_user("demo_user", "password123")
    print(f"  Session ID: {auth2.current_session_id[:16]}...")
    
    print("\nLogging in from Device 3...")
    auth3.login_user("demo_user", "password123")
    print(f"  Session ID: {auth3.current_session_id[:16]}...")
    
    # Verify all sessions are unique
    print("\nVerifying session uniqueness...")
    print(f"  Device 1 == Device 2: {auth1.current_session_id == auth2.current_session_id}")
    print(f"  Device 2 == Device 3: {auth2.current_session_id == auth3.current_session_id}")
    print(f"  Device 1 == Device 3: {auth1.current_session_id == auth3.current_session_id}")
    
    # Show all active sessions
    print("\nActive sessions for 'demo_user':")
    active_sessions = auth1.get_active_sessions("demo_user")
    for i, sess in enumerate(active_sessions, 1):
        print(f"  {i}. Session: {sess['session_id']}")
        print(f"     Created: {sess['created_at']}")
    
    # Logout from one device
    print("\nLogging out from Device 2...")
    auth2.logout_user()
    
    print("\nActive sessions after Device 2 logout:")
    active_sessions = auth1.get_active_sessions("demo_user")
    print(f"  Total active sessions: {len(active_sessions)}")


def demo_session_validation():
    """Demonstrate session validation"""
    print_separator("3. Session Validation")
    
    auth = AuthManager()
    
    # Login
    print("Logging in 'demo_user'...")
    auth.login_user("demo_user", "password123")
    session_id = auth.current_session_id
    
    # Validate active session
    print(f"\nValidating active session {session_id[:16]}...")
    is_valid, username = auth.validate_session(session_id)
    print(f"  Is Valid: {is_valid}")
    print(f"  Username: {username}")
    
    # Logout
    print("\nLogging out...")
    auth.logout_user()
    
    # Try to validate logged out session
    print(f"\nValidating logged out session {session_id[:16]}...")
    is_valid, username = auth.validate_session(session_id)
    print(f"  Is Valid: {is_valid}")
    print(f"  Username: {username}")
    
    # Try to validate fake session
    print("\nValidating fake session...")
    is_valid, username = auth.validate_session("fake_session_id_xyz")
    print(f"  Is Valid: {is_valid}")
    print(f"  Username: {username}")


def demo_session_cleanup():
    """Demonstrate session cleanup"""
    print_separator("4. Session Cleanup")
    
    auth = AuthManager()
    
    # Create some sessions
    print("Creating test sessions...")
    for i in range(3):
        temp_auth = AuthManager()
        temp_auth.login_user("demo_user", "password123")
    
    # Show active sessions before cleanup
    active_before = auth.get_active_sessions("demo_user")
    print(f"\nActive sessions before cleanup: {len(active_before)}")
    
    # Run cleanup (this will clean sessions older than 24 hours)
    print("\nRunning session cleanup (24 hour threshold)...")
    count = auth.cleanup_old_sessions(hours=24)
    print(f"  Cleaned up {count} old sessions")
    
    # Show active sessions after cleanup
    active_after = auth.get_active_sessions("demo_user")
    print(f"\nActive sessions after cleanup: {len(active_after)}")


def demo_invalidate_all_sessions():
    """Demonstrate invalidating all user sessions"""
    print_separator("5. Invalidate All User Sessions")
    
    auth = AuthManager()
    
    # Create multiple sessions
    print("Creating 5 sessions for 'demo_user'...")
    for i in range(5):
        temp_auth = AuthManager()
        temp_auth.login_user("demo_user", "password123")
    
    # Show active sessions
    active = auth.get_active_sessions("demo_user")
    print(f"\nActive sessions: {len(active)}")
    
    # Invalidate all
    print("\nInvalidating all sessions for 'demo_user'...")
    count = auth.invalidate_user_sessions("demo_user")
    print(f"  Invalidated {count} sessions")
    
    # Show active sessions after invalidation
    active = auth.get_active_sessions("demo_user")
    print(f"\nActive sessions after invalidation: {len(active)}")


def demo_session_details():
    """Show detailed session information"""
    print_separator("6. Detailed Session Information")
    
    auth = AuthManager()
    
    print("Logging in 'demo_user'...")
    auth.login_user("demo_user", "password123")
    
    # Get session from database
    session = get_session()
    try:
        db_session = session.query(Session).filter_by(
            session_id=auth.current_session_id
        ).first()
        
        print("\nComplete Session Details:")
        print(f"  Session ID: {db_session.session_id}")
        print(f"  User ID: {db_session.user_id}")
        print(f"  Username: {db_session.username}")
        print(f"  Created At: {db_session.created_at}")
        print(f"  Last Accessed: {db_session.last_accessed}")
        print(f"  Is Active: {db_session.is_active}")
        print(f"  IP Address: {db_session.ip_address}")
        print(f"  User Agent: {db_session.user_agent}")
        print(f"  Logged Out At: {db_session.logged_out_at}")
        
        # Get user details
        user = session.query(User).filter_by(id=db_session.user_id).first()
        print(f"\n  Associated User:")
        print(f"    - Username: {user.username}")
        print(f"    - Created At: {user.created_at}")
        print(f"    - Last Login: {user.last_login}")
        print(f"    - Total Sessions: {len(user.sessions)}")
        
    finally:
        session.close()


def main():
    """Run all demonstrations"""
    print("\n" + "="*60)
    print("  SESSION TRACKING DEMONSTRATION")
    print("  SoulSense EQ Assessment")
    print("="*60)
    
    # Initialize database
    print("\nInitializing database...")
    check_db_state()
    
    try:
        # Run all demos
        demo_basic_session_flow()
        demo_multiple_sessions()
        demo_session_validation()
        demo_session_cleanup()
        demo_invalidate_all_sessions()
        demo_session_details()
        
        print_separator("Demonstration Complete")
        print("✓ All session tracking features demonstrated successfully!")
        print("\nKey Takeaways:")
        print("  1. Every login generates a unique session ID")
        print("  2. Sessions are stored with user and timestamp")
        print("  3. Session IDs can be used to identify active users")
        print("  4. Sessions are invalidated on logout")
        print("  5. Multiple concurrent sessions are supported")
        print("  6. Old sessions can be automatically cleaned up")
        print("  7. All user sessions can be invalidated at once")
        
    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
