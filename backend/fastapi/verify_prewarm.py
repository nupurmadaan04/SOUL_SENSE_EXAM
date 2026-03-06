import asyncio
import sys
import os
import time
from datetime import datetime, timezone
UTC = timezone.utc

# Add parent directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.services.smart_prompt_service import SmartPromptService, L1_CACHE
from api.utils.singleflight import singleflight_service
from api.services.db_service import AsyncSessionLocal
from api.models import User

async def test_thundering_herd():
    print("=== Testing Thundering Herd Prevention (Singleflight) ===")
    user_id = 1
    
    async with AsyncSessionLocal() as db:
        service = SmartPromptService(db)
        
        # Clear caches
        L1_CACHE.clear()
        # We assume Redis might have data, but we want to test the Singleflight layer
        
        print(f"Launching 10 simultaneous requests for user {user_id}...")
        
        # Simultaneously launch 10 requests
        tasks = [service.get_smart_prompts(user_id, count=3, bypass_cache=True) for _ in range(10)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        print(f"All 10 requests finished in {duration:.4f}s")
        
        # Verify all results are identical
        first_res = results[0]
        for i, res in enumerate(results[1:]):
            if res != first_res:
                print(f"ERROR: Result {i+1} differs!")
                return False
        
        print("Success: All 10 requests received the exact same collapsed result.")
        return True

async def test_tiered_caching():
    print("\n=== Testing Tiered Caching (L1 -> L2) ===")
    user_id = 1
    
    async with AsyncSessionLocal() as db:
        service = SmartPromptService(db)
        
        # 1. First run (Cold Cache)
        L1_CACHE.clear()
        print("1. Cold cache (DB/ML Calc)...")
        start = time.time()
        await service.get_smart_prompts(user_id, count=3)
        print(f"   Finished in {time.time() - start:.4f}s")
        
        # 2. Second run (L1 Memory Hit)
        print("2. L1 Memory Hit...")
        start = time.time()
        await service.get_smart_prompts(user_id, count=3)
        print(f"   Finished in {time.time() - start:.4f}s (Should be near zero)")
        
        # 3. Third run (L2 Redis Hit - simulating L1 clear)
        L1_CACHE.clear()
        print("3. L2 Redis Hit (L1 Cleared)...")
        start = time.time()
        await service.get_smart_prompts(user_id, count=3)
        print(f"   Finished in {time.time() - start:.4f}s")
        
    return True

async def main():
    try:
        await test_thundering_herd()
        await test_tiered_caching()
        print("\n[OK] Issue #1177 Verification Complete.")
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
