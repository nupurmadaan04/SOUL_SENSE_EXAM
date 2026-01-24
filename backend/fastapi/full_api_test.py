
import urllib.request
import urllib.parse
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
RESULTS = []

def log_result(endpoint, method, status, response, success):
    RESULTS.append({
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "response": response,
        "success": success,
        "timestamp": datetime.now().isoformat()
    })

def make_request(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    body = None
    if data:
        if method == "POST" and "/auth/login" in path:
            # Auth/login uses form data
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            try:
                res_json = json.loads(res_body)
            except:
                res_json = res_body
            return response.status, res_json
    except urllib.error.HTTPError as e:
        try:
            res_body = e.read().decode("utf-8")
            res_json = json.loads(res_body)
        except:
            res_json = res_body
        return e.code, res_json
    except Exception as e:
        return 500, str(e)

def run_tests():
    print("🚀 Starting Comprehensive API Verification...\n")
    
    # 1. Health
    status, res = make_request("/api/v1/health")
    log_result("/api/v1/health", "GET", status, res, status == 200)
    
    # 2. Auth - Register
    user_data = {"username": f"testuser_{int(time.time())}", "password": "password123"}
    status, res = make_request("/api/v1/auth/register", "POST", user_data)
    log_result("/api/v1/auth/register", "POST", status, res, status in [200, 201])
    
    # 3. Auth - Login
    status, login_res = make_request("/api/v1/auth/login", "POST", user_data)
    log_result("/api/v1/auth/login", "POST", status, login_res, status == 200)
    
    token = login_res.get("access_token") if isinstance(login_res, dict) else None
    if not token:
        print("❌ Login failed, skipping authenticated tests.")
        return
    
    # 4. Users
    status, res = make_request("/api/v1/users/me", "GET", token=token)
    log_result("/api/v1/users/me", "GET", status, res, status == 200)
    
    # 5. Profiles
    profile_endpoints = [
        "/api/v1/profiles/settings",
        "/api/v1/profiles/medical",
        "/api/v1/profiles/personal",
        "/api/v1/profiles/strengths",
        "/api/v1/profiles/emotional"
    ]
    for ep in profile_endpoints:
        status, res = make_request(ep, "GET", token=token)
        log_result(ep, "GET", status, res, status in [200, 404]) # 404 is ok if not created yet
    
    # 6. Questions
    status, res = make_request("/api/v1/questions/?limit=5", "GET")
    log_result("/api/v1/questions/", "GET", status, res, status == 200)
    
    status, res = make_request("/api/v1/questions/categories", "GET")
    log_result("/api/v1/questions/categories", "GET", status, res, status == 200)
    
    # 7. Assessments
    status, res = make_request("/api/v1/assessments/?limit=5", "GET", token=token)
    log_result("/api/v1/assessments/", "GET", status, res, status == 200)
    
    status, res = make_request("/api/v1/assessments/stats", "GET", token=token)
    log_result("/api/v1/assessments/stats", "GET", status, res, status == 200)
    
    # 8. Analytics
    status, res = make_request("/api/v1/analytics/summary", "GET", token=token)
    log_result("/api/v1/analytics/summary", "GET", status, res, status == 200)
    
    # 9. Journal
    status, res = make_request("/api/v1/journal/prompts", "GET", token=token)
    log_result("/api/v1/journal/prompts", "GET", status, res, status == 200)
    
    journal_data = {"content": "Comprehensive test of the journal API. This should be exactly sixteen words for testing.", "tags": ["test", "verification"]}
    status, create_res = make_request("/api/v1/journal/", "POST", journal_data, token=token)
    log_result("/api/v1/journal/", "POST", status, create_res, status == 201)
    
    journal_id = create_res.get("id") if isinstance(create_res, dict) else None
    if journal_id:
        status, res = make_request(f"/api/v1/journal/{journal_id}", "GET", token=token)
        log_result(f"/api/v1/journal/{journal_id}", "GET", status, res, status == 200)
        
        status, res = make_request(f"/api/v1/journal/{journal_id}", "PUT", {"content": "Updated content for comprehensive test. Check word count again."}, token=token)
        log_result(f"/api/v1/journal/{journal_id}", "PUT", status, res, status == 200)
        
        status, res = make_request("/api/v1/journal/analytics", "GET", token=token)
        log_result("/api/v1/journal/analytics", "GET", status, res, status == 200)
        
        status, res = make_request("/api/v1/journal/search?query=comprehensive", "GET", token=token)
        log_result("/api/v1/journal/search", "GET", status, res, status == 200)
        
        status, res = make_request(f"/api/v1/journal/{journal_id}", "DELETE", token=token)
        log_result(f"/api/v1/journal/{journal_id}", "DELETE", status, res, status == 204)
    
    # Save results
    with open("full_api_test_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    
    print("\n✅ Tests completed. Generating report...")

if __name__ == "__main__":
    run_tests()
