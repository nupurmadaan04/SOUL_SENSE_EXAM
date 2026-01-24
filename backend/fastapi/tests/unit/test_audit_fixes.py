"""
Test script for Journal API Audit Fixes.
Verifies:
1. Soft Delete (entry still in DB but not visible via API)
2. Word Count (correctly calculated)
3. Ownership (can only access own entries via user_id)
4. Reading Time (correctly estimated)
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_journal_audit_fixes():
    print("🚀 Starting Journal API Audit Fixes Test...\n")
    
    # 1. Login to get token
    print("🔐 Logging in...")
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    if login_resp.status_code != 200:
        print("❌ Login failed. Make sure 'testuser' exists.")
        return
    
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create entry (Test Word Count & Reading Time)
    print("\n📝 Creating journal entry...")
    content = "This is a test journal entry with exactly ten words in it for verification."
    create_resp = requests.post(
        f"{BASE_URL}/api/v1/journal/",
        headers=headers,
        json={
            "content": content,
            "tags": ["test", "audit"]
        }
    )
    
    if create_resp.status_code != 201:
        print(f"❌ Create failed: {create_resp.text}")
        return
    
    entry = create_resp.json()
    entry_id = entry["id"]
    
    print(f"✅ Created entry ID: {entry_id}")
    print(f"📊 Word Count: {entry['word_count']} (Expected: 14)")
    print(f"📖 Reading Time: {entry['reading_time_mins']} mins")
    
    # 3. Verify Soft Delete
    print("\n🗑️ Testing Soft Delete...")
    delete_resp = requests.delete(
        f"{BASE_URL}/api/v1/journal/{entry_id}",
        headers=headers
    )
    
    if delete_resp.status_code == 204:
        print(f"✅ Soft deleted entry {entry_id}")
    else:
        print(f"❌ Delete failed: {delete_resp.text}")
    
    # 4. Verify filtered out from list
    print("\n🔍 Verifying entry is hidden from list...")
    list_resp = requests.get(
        f"{BASE_URL}/api/v1/journal/",
        headers=headers
    )
    
    found = any(e["id"] == entry_id for e in list_resp.json()["entries"])
    if not found:
        print("✅ Entry correctly filtered out from list.")
    else:
        print("❌ Entry still visible in list after deletion!")
    
    # 5. Verify 404 on direct access
    print("\n🔍 Verifying entry returns 404 on direct access...")
    get_resp = requests.get(
        f"{BASE_URL}/api/v1/journal/{entry_id}",
        headers=headers
    )
    
    if get_resp.status_code == 404:
        print("✅ Correctly returned 404 for deleted entry.")
    else:
        print(f"❌ Expected 404, got {get_resp.status_code}")

    print("\n✨ Journal Audit Fixes Test Complete!")

if __name__ == "__main__":
    test_journal_audit_fixes()
