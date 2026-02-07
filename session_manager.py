"""
Session Management CLI Utility
-------------------------------
Command-line tool for managing user sessions.

Usage:
    python session_manager.py list [username]       - List active sessions
    python session_manager.py validate <session_id> - Validate a session
    python session_manager.py cleanup [hours]       - Cleanup old sessions
    python session_manager.py invalidate <username> - Invalidate all sessions for a user
    python session_manager.py stats                 - Show session statistics
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, UTC
from tabulate import tabulate

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.auth import AuthManager
from app.db import get_session
from app.models import Session, User
from sqlalchemy import func


class SessionManager:
    """CLI Session Manager"""
    
    def __init__(self):
        self.auth = AuthManager()
    
    def list_sessions(self, username=None):
        """List active sessions"""
        sessions = self.auth.get_active_sessions(username)
        
        if not sessions:
            print("No active sessions found.")
            return
        
        # Prepare table data
        headers = ["Session ID", "Username", "Created At", "Last Accessed", "IP Address"]
        data = []
        
        for s in sessions:
            data.append([
                s['session_id'],
                s['username'],
                s['created_at'][:19] if s['created_at'] else 'N/A',
                s['last_accessed'][:19] if s['last_accessed'] else 'N/A',
                s['ip_address'] or 'N/A'
            ])
        
        print(f"\nActive Sessions{f' for {username}' if username else ''}:")
        print(tabulate(data, headers=headers, tablefmt="grid"))
        print(f"\nTotal: {len(sessions)} active session(s)")
    
    def validate_session(self, session_id):
        """Validate a session ID"""
        print(f"\nValidating session: {session_id[:16]}...")
        
        is_valid, username = self.auth.validate_session(session_id)
        
        if is_valid:
            print(f"✓ Valid session for user: {username}")
            
            # Get more details
            session = get_session()
            try:
                db_session = session.query(Session).filter_by(session_id=session_id).first()
                
                print("\nSession Details:")
                print(f"  User ID: {db_session.user_id}")
                print(f"  Created: {db_session.created_at}")
                print(f"  Last Accessed: {db_session.last_accessed}")
                
                # Calculate session age
                created = datetime.fromisoformat(db_session.created_at)
                age = datetime.now(UTC) - created
                print(f"  Age: {age.total_seconds() / 3600:.1f} hours")
            finally:
                session.close()
        else:
            print("✗ Invalid or expired session")
    
    def cleanup_sessions(self, hours=24):
        """Cleanup old sessions"""
        print(f"\nCleaning up sessions older than {hours} hours...")
        
        count = self.auth.cleanup_old_sessions(hours=hours)
        
        if count > 0:
            print(f"✓ Cleaned up {count} old session(s)")
        else:
            print("No old sessions to clean up")
    
    def invalidate_user_sessions(self, username):
        """Invalidate all sessions for a user"""
        print(f"\nInvalidating all sessions for user: {username}...")
        
        count = self.auth.invalidate_user_sessions(username)
        
        if count > 0:
            print(f"✓ Invalidated {count} session(s) for {username}")
        else:
            print(f"No active sessions found for {username}")
    
    def show_statistics(self):
        """Show session statistics"""
        session = get_session()
        try:
            # Total sessions
            total_sessions = session.query(func.count(Session.id)).scalar()
            
            # Active sessions
            active_sessions = session.query(func.count(Session.id))\
                .filter(Session.is_active == True).scalar()
            
            # Inactive sessions
            inactive_sessions = total_sessions - active_sessions
            
            # Sessions created today
            today = datetime.now(UTC).date().isoformat()
            today_sessions = session.query(func.count(Session.id))\
                .filter(Session.created_at >= today).scalar()
            
            # Unique users with sessions
            unique_users = session.query(func.count(func.distinct(Session.user_id)))\
                .filter(Session.is_active == True).scalar()
            
            # Most active user
            most_active = session.query(
                Session.username, 
                func.count(Session.id).label('count')
            ).filter(Session.is_active == True)\
             .group_by(Session.username)\
             .order_by(func.count(Session.id).desc())\
             .first()
            
            print("\n" + "="*60)
            print("SESSION STATISTICS")
            print("="*60)
            print(f"\nTotal Sessions (All Time):     {total_sessions}")
            print(f"Active Sessions:               {active_sessions}")
            print(f"Inactive Sessions:             {inactive_sessions}")
            print(f"Sessions Created Today:        {today_sessions}")
            print(f"Unique Users Online:           {unique_users}")
            
            if most_active:
                print(f"\nMost Active User:              {most_active[0]} ({most_active[1]} sessions)")
            
            # Recent sessions
            recent = session.query(Session)\
                .filter(Session.is_active == True)\
                .order_by(Session.created_at.desc())\
                .limit(5).all()
            
            if recent:
                print("\n" + "-"*60)
                print("Recent Active Sessions:")
                print("-"*60)
                
                for s in recent:
                    created = datetime.fromisoformat(s.created_at)
                    age = datetime.now(UTC) - created
                    print(f"\n  {s.username}")
                    print(f"    Session: {s.session_id[:24]}...")
                    print(f"    Age: {age.total_seconds() / 3600:.1f} hours")
            
        finally:
            session.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Session Management CLI Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python session_manager.py list                    # List all active sessions
  python session_manager.py list john_doe           # List sessions for john_doe
  python session_manager.py validate <session_id>   # Validate a session
  python session_manager.py cleanup                 # Cleanup sessions > 24 hours
  python session_manager.py cleanup 48              # Cleanup sessions > 48 hours
  python session_manager.py invalidate john_doe     # Invalidate all sessions for john_doe
  python session_manager.py stats                   # Show session statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List active sessions')
    list_parser.add_argument('username', nargs='?', help='Filter by username')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a session')
    validate_parser.add_argument('session_id', help='Session ID to validate')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old sessions')
    cleanup_parser.add_argument('hours', nargs='?', type=int, default=24,
                              help='Age threshold in hours (default: 24)')
    
    # Invalidate command
    invalidate_parser = subparsers.add_parser('invalidate', 
                                             help='Invalidate all sessions for a user')
    invalidate_parser.add_argument('username', help='Username')
    
    # Stats command
    subparsers.add_parser('stats', help='Show session statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    manager = SessionManager()
    
    try:
        if args.command == 'list':
            manager.list_sessions(args.username)
        elif args.command == 'validate':
            manager.validate_session(args.session_id)
        elif args.command == 'cleanup':
            manager.cleanup_sessions(args.hours)
        elif args.command == 'invalidate':
            manager.invalidate_user_sessions(args.username)
        elif args.command == 'stats':
            manager.show_statistics()
        else:
            parser.print_help()
            return 1
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
