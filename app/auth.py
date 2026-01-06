from app.db import get_connection
from app.models import hash_password, verify_password

def create_user(username, password, conn=None):
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        return True, "User created successfully"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def authenticate_user(username, password, conn=None):
    if conn is None:
        conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result and verify_password(password, result[0]):
            return True, "Login successful"
        return False, "Invalid username or password"
    except Exception as e:
        return False, f"Authentication error: {str(e)}"