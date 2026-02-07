import requests
import json
import time

def test_registration():
    url = "http://localhost:8000/api/v1/auth/register"
    ts = int(time.time())
    payload = {
        "username": f"tester_{ts}",
        "password": "SecurePassword123!",
        "email": f"test_{ts}@gmail.com",
        "first_name": "Test",
        "last_name": "User",
        "age": 25,
        "gender": "Male"
    }
    
    print(f"Testing registration at {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Raw Response: {response.text}")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_registration()
