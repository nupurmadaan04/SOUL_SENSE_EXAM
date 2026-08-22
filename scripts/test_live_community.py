import httpx
import time

def main():
    time.sleep(1)
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=10.0)

    print("--- 1. HEALTH CHECK ---")
    health = client.get("/api/v1/health").json()
    print("Health:", health.get("status"))

    print("\n--- 2. REPOSITORY & PR STATS ---")
    stats = client.get("/api/v1/community/stats").json()
    repo = stats.get("repository", {})
    prs = stats.get("pull_requests", {})
    print(f"Stars: {repo.get('stars')}, Forks: {repo.get('forks')}, Open Issues: {repo.get('open_issues')}")
    print(f"Total PRs: {prs.get('total')}, Open PRs: {prs.get('open')}, Closed/Merged PRs: {prs.get('merged')}")

    print("\n--- 3. TOP REAL CONTRIBUTORS ---")
    contribs = client.get("/api/v1/community/contributors?limit=8").json()
    for c in contribs:
        print(f"Rank #{c.get('rank')}: {c.get('login')} - Commits: {c.get('contributions')} - Badges: {c.get('badges')}")

    print("\n--- 4. CONTRIBUTION MIX ---")
    mix = client.get("/api/v1/community/mix").json()
    for m in mix:
        print(f" - {m.get('name')}: {m.get('value')}% ({m.get('count')} {m.get('unit')})")

    print("\n--- 5. COMMUNITY GRAPH & REVIEWS ---")
    graph = client.get("/api/v1/community/graph").json()
    print(f"Graph nodes: {len(graph.get('nodes', []))}, links: {len(graph.get('links', []))}")
    reviews = client.get("/api/v1/community/reviews").json()
    print(f"Top reviewers: {[r.get('name') for r in reviews.get('top_reviewers', [])]}")

    print("\n--- 6. AUTH CAPTCHA & REGISTER CHECK ---")
    cap = client.get("/api/v1/auth/captcha").json()
    print(f"Captcha Code: {cap.get('captcha_code')}, Session ID: {cap.get('session_id')}")

    user_check = client.get("/api/v1/auth/check-username?username=realtestuser999").json()
    print(f"Username Availability: {user_check}")

if __name__ == "__main__":
    main()
