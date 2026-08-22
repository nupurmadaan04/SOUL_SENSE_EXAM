import http.client
import json

def check_backend():
    print("Checking backend at 127.0.0.1:8000...")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=10)
        conn.request("GET", "/api/v1/health")
        resp = conn.getresponse()
        data = resp.read().decode()
        print(f"Status: {resp.status}")
        print(f"Response: {data}")
        conn.close()
    except Exception as e:
        print(f"Error connecting to 127.0.0.1:8000: {e}")

    print("\nChecking CAPTCHA endpoint...")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=10)
        conn.request("GET", "/api/v1/auth/captcha")
        resp = conn.getresponse()
        data = resp.read().decode()
        print(f"Status: {resp.status}")
        print(f"Response: {data}")
        conn.close()
    except Exception as e:
        print(f"Error connecting to CAPTCHA endpoint: {e}")

if __name__ == "__main__":
    check_backend()
