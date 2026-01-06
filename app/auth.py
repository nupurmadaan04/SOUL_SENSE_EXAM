import hashlib
import sqlite3
from datetime import datetime
from app.db import get_connection

class AuthManager:
    def __init__(self):
        self.ensure_users_table()
    
    def ensure_users_table(self):
        """Create users table if it doesn't exist"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, password):
        """Register new user"""
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, "Username already exists"
            
            password_hash = self.hash_password(password)
            created_at = datetime.now().isoformat()
            
            cursor.execute("""
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """, (username, password_hash, created_at))
            
            conn.commit()
            return True, "Registration successful"
        
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        """Authenticate user login"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Invalid username or password"
            
            stored_hash = result[0]
            password_hash = self.hash_password(password)
            
            if stored_hash == password_hash:
                return True, "Login successful"
            else:
                return False, "Invalid username or password"
        
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        finally:
            conn.close()