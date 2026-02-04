import requests
import time

BASE_URL = "http://localhost:8000/api/v1/auth"
USERNAME = "2fa_test_user_" + str(int(time.time()))
PASSWORD = "Password123!"
EMAIL = f"test_{int(time.time())}@example.com"

def test_flow():
    print(f"--- Starting 2FA Flow Test for {USERNAME} ---")
    
    # 1. Register
    print("\n1. Registering User...")
    resp = requests.post(f"{BASE_URL}/register", json={
        "username": USERNAME,
        "password": PASSWORD,
        "email": EMAIL,
        "first_name": "Test",
        "last_name": "User"
    })
    if resp.status_code != 200:
        print(f"Registration failed: {resp.text}")
        return
    print("OK: Registered.")

    # 2. Login (Should happen immediately, but let's test login endpoint)
    print("\n2. Logging in (2FA Disabled)...")
    resp = requests.post(f"{BASE_URL}/login", data={
        "username": USERNAME,
        "password": PASSWORD
    })
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    data = resp.json()
    token = data["access_token"]
    print("OK: Login Success via Token.")
    
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Enable 2FA Setup
    print("\n3. Initiating 2FA Setup...")
    resp = requests.post(f"{BASE_URL}/2fa/setup/initiate", headers=headers)
    if resp.status_code != 200:
        print(f"Setup Init failed: {resp.text}")
        return
    print("OK: OTP Sent.")

    # 4. Read OTP from debug file (since we use Mock Email)
    print("\n4. Reading OTP from debug file...")
    # Wait a moment for file write
    time.sleep(5)
    otp = None
    
    # Server runs in backend/fastapi/ so file might be there
    otp_paths = ["otp_debug.txt", "backend/fastapi/otp_debug.txt"]
    
    found_file = False
    for path in otp_paths:
        try:
            with open(path, "r") as f:
                lines = f.readlines()
                found_file = True
                print(f"Read OTP file at: {path} ({len(lines)} lines)")
                # Get last line matching our email
                for line in reversed(lines):
                     if EMAIL in line:
                         print(f"Found line for {EMAIL}: {line.strip()}")
                         # Parse: "... | Code: 123456 | ..."
                         parts = line.strip().split("|")
                         for part in parts:
                             if "Code:" in part:
                                 otp = part.split("Code:")[1].strip()
                                 print(f"Extracted OTP: {otp}")
                                 break
                         if otp: break
                if otp: break
        except FileNotFoundError:
            continue
            
    if not found_file:
        print("FAIL: otp_debug.txt not found in expected paths.")
        return

    if not otp:
        print(f"FAIL: Could not find OTP for {EMAIL} in debug file.")
        return
    print(f"OK: Found OTP: {otp}")

    # 5. Enable 2FA
    print("\n5. Confirming 2FA Enable...")
    resp = requests.post(f"{BASE_URL}/2fa/enable", headers=headers, json={"code": otp})
    if resp.status_code != 200:
        print(f"Enable failed: {resp.text}")
        return
    print("OK: 2FA Enabled.")

    # 6. Login again (Should require 2FA)
    print("\n6. Logging in (2FA Enabled)...")
    resp = requests.post(f"{BASE_URL}/login", data={
        "username": USERNAME,
        "password": PASSWORD
    })
    
    if resp.status_code == 202:
        print("OK: Correctly received 202 Accepted.")
        data = resp.json()
        if data.get("require_2fa") and "pre_auth_token" in data:
            pre_auth_token = data["pre_auth_token"]
            print("OK: Received pre_auth_token.")
        else:
            print(f"FAIL: Unexpected response body: {data}")
            return
    else:
        print(f"FAIL: Expected 202, got {resp.status_code}: {resp.text}")
        return

    # 7. Verify 2FA Login
    # We need a NEW OTP. 
    print("\n7. Getting Login OTP...")
    time.sleep(5) # Wait for new OTP write
    login_otp = None
    
    for path in otp_paths:
        try:
             with open(path, "r") as f:
                lines = f.readlines()
                # Get last line
                for line in reversed(lines):
                     if EMAIL in line:
                         # Read the code
                         parts = line.strip().split("|")
                         code_in_line = None
                         for part in parts:
                             if "Code:" in part:
                                 code_in_line = part.split("Code:")[1].strip()
                                 break
                         
                         if code_in_line and code_in_line != otp:
                             print(f"Found NEW OTP: {code_in_line}")
                             login_otp = code_in_line
                             break
                         elif code_in_line == otp:
                             print(f"Found OLD OTP: {code_in_line}. Searching previous...")
                             # Continue searching reversed? No, assume sequential. 
                             # If we found OLD OTP at the END, it means NEW OTP wasn't written.
                             pass
                if login_otp: break
        except: pass
        
    if not login_otp:
        print("WARN: Could not distinguish new OTP, trying previous one (assuming cooldown active).")
        login_otp = otp

    print(f"Using OTP: {login_otp}")

    print("\n8. Verifying 2FA Login...")
    resp = requests.post(f"{BASE_URL}/login/2fa", json={
        "pre_auth_token": pre_auth_token,
        "code": login_otp
    })
    
    if resp.status_code == 200:
        token_data = resp.json()
        if "access_token" in token_data:
            print("OK: 2FA Login Success! Access Token received.")
        else:
            print(f"FAIL: Missing token in response: {token_data}")
    else:
        print(f"FAIL: 2FA Login Failed: {resp.text}")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_flow()
