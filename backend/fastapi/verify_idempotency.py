import asyncio
import uuid
import httpx
import time
from datetime import datetime

async def test_idempotency():
    base_url = "http://localhost:8000/api/v1"
    idempotency_key = str(uuid.uuid4())
    headers = {
        "X-Idempotency-Key": idempotency_key,
        "Content-Type": "application/json"
    }
    
    # Note: This test assumes the server is running and we have a valid token if RBAC is enabled.
    # For a unit-style test WITHOUT a running server, we would mock the dependencies.
    # Since I cannot start a long-running server easily here, I will provide the script
    # to the user to run, or try to run it if they have a dev server up.
    
    print(f"Testing with Idempotency Key: {idempotency_key}")
    
    async with httpx.AsyncClient() as client:
        # Mocking a request (replace with real endpoint if testing on live dev)
        # 1. First request
        print("\n--- Request 1 ---")
        try:
            # We use a POST request as they are the primary target for idempotency
            # Using a non-existent endpoint to verify the middleware intercept logic 
            # (though middleware runs for all 404s too if registered globally, 
            # but usually we want to see a 200 cached).
            
            # Let's try to hit an endpoint that might exist or just check headers.
            response1 = await client.post(f"{base_url}/auth/login", json={"username": "test", "password": "password"}, headers=headers)
            print(f"Status: {response1.status_code}")
            print(f"Cache Header: {response1.headers.get('X-Idempotency-Cache')}")
            
            # 2. Second request with SAME key
            print("\n--- Request 2 (Duplicate) ---")
            response2 = await client.post(f"{base_url}/auth/login", json={"username": "test", "password": "password"}, headers=headers)
            print(f"Status: {response2.status_code}")
            print(f"Cache Header: {response2.headers.get('X-Idempotency-Cache')}")
            
            if response2.headers.get('X-Idempotency-Cache') == "HIT":
                print("\nSUCCESS: Idempotency middleware correctly cached and returned the response!")
            else:
                print("\nFAILURE: Second request did not result in a cache HIT.")
                
        except Exception as e:
            print(f"Error during test: {e}")
            print("Note: Ensure the backend server is running on http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(test_idempotency())
