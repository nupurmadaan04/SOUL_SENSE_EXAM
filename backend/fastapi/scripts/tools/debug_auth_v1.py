import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def debug_auth():
    print("🚀 Debugging Auth V1 Flow...\n")
    
    # 1. Register
    username = f"debug_user_{int(time.time())}"
    password = "password123"
    register_url = f"{BASE_URL}/api/v1/auth/register"
    
    print(f"1. Registering user '{username}' at {register_url}...")
    try:
        reg_res = requests.post(register_url, json={"username": username, "password": password})
        print(f"   Status: {reg_res.status_code}")
        print(f"   Response: {reg_res.text}")
        
        if reg_res.status_code not in [200, 201]:
            print("❌ Registration Failed")
            return
    except Exception as e:
        print(f"❌ Registration Exception: {e}")
        return

    # 2. Login
    login_url = f"{BASE_URL}/api/v1/auth/login"
    print(f"\n2. Logging in at {login_url}...")
    try:
        # Note: OAuth2PasswordRequestForm expects form data, not JSON!
        login_data = {"username": username, "password": password}
        login_res = requests.post(login_url, data=login_data)
        
        print(f"   Status: {login_res.status_code}")
        print(f"   Response: {login_res.text}")
        
        if login_res.status_code == 200:
            token = login_res.json().get("access_token")
            print(f"✅ Login Successful! Token: {token[:10]}...")
        else:
            print("❌ Login Failed")
            
    except Exception as e:
        print(f"❌ Login Exception: {e}")

if __name__ == "__main__":
    debug_auth()
