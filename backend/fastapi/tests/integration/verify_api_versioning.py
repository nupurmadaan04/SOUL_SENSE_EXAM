import requests
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, expected_status, check_header=False):
    print(f"Testing {name} ({method} {url})...", end=" ")
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url)
            
        if response.status_code == expected_status:
            print("pLACEHOLDER_M_PASSED")
            if check_header:
                if "X-API-Version" in response.headers:
                    print(f"  -> X-API-Version: {response.headers['X-API-Version']}")
                else:
                    print("  -> FAILED: Missing X-API-Version header")
                    return False
            return True
        else:
            print(f"FAILED (Expected {expected_status}, got {response.status_code})")
            return False
    except Exception as e:
        print(f"FAILED (Exception: {e})")
        return False

success = True

# 1. Version Discovery
success &= test_endpoint("Discovery", "GET", f"{BASE_URL}/", 200)

# 2. Health Check (v1)
success &= test_endpoint("Health V1", "GET", f"{BASE_URL}/api/v1/health", 200, check_header=True)

# 3. Auth Login (v1) - Expect 422 because of missing form data, but 422 implies it reached the endpoint
success &= test_endpoint("Auth V1", "POST", f"{BASE_URL}/api/v1/auth/login", 422, check_header=True)

# 4. Old Auth Login (Legacy) - Expect 404
success &= test_endpoint("Old Auth", "POST", f"{BASE_URL}/auth/login", 404)

# 5. Old Users Endpoint (Legacy) - Expect 404
success &= test_endpoint("Old Users", "GET", f"{BASE_URL}/api/users/me", 404)

if success:
    print("\n✅ API Versioning Verification PASSED")
    sys.exit(0)
else:
    print("\n❌ API Versioning Verification FAILED")
    sys.exit(1)
