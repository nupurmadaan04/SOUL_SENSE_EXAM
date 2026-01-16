import bcrypt
from datetime import datetime
from app.db import get_session
from app.models import User
import logging

class AuthManager:
    def __init__(self):
        self.current_user = None
    
    def hash_password(self, password):
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def verify_password(self, password, password_hash):
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception as e:
            logging.error(f"Password verification failed: {e}")
            return False
    
    def register_user(self, username, password):
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(password) < 4:
            return False, "Password must be at least 4 characters"
        
        session = get_session()
        try:
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                return False, "Username already exists"
            
            password_hash = self.hash_password(password)
            new_user = User(
                username=username,
                password_hash=password_hash,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)  # ensures ID is set
            return True, "Registration successful"
        
        except Exception as e:
            session.rollback()
            logging.error(f"Registration failed: {e}")
            return False, "Registration failed"
        finally:
            session.close()
    
    def login_user(self, username, password):
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            
            if user and self.verify_password(password, user.password_hash):
                user.last_login = datetime.utcnow().isoformat()
                session.commit()
                self.current_user = user  # store user object
                return True, "Login successful"
            else:
                return False, "Invalid username or password"
        
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False, "Login failed"
        finally:
            session.close()
    
    def logout_user(self):
        self.current_user = None
    
    def is_logged_in(self):
        return self.current_user is not None
