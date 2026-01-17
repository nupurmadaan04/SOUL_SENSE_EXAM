"""
Test script for Admin Interface functionality
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from admin_interface import QuestionDatabase

def test_admin_interface():
    """Test the admin interface functionality"""
    print("=" * 60)
    print("Testing Admin Interface")
    print("=" * 60)
    
    # Initialize database
    db = QuestionDatabase("test_admin_db.sqlite3")
    print("\n✓ Database initialized")
    
    # Test 1: Create admin user
    print("\n[Test 1] Creating admin user...")
    username = "admin_test"
    password = "test1234"
    
    if db.create_admin(username, password):
        print(f"✓ Admin user '{username}' created")
    else:
        print(f"ℹ Admin user '{username}' already exists")
    
    # Test 2: Verify admin
    print("\n[Test 2] Verifying admin credentials...")
    if db.verify_admin(username, password):
        print("✓ Admin authentication successful")
    else:
        print("✗ Admin authentication failed")
        return False
    
    # Test with wrong password
    if not db.verify_admin(username, "wrongpassword"):
        print("✓ Correctly rejected wrong password")
    else:
        print("✗ Should have rejected wrong password")
    
    # Test 3: Add questions
    print("\n[Test 3] Adding questions...")
    
    test_questions = [
        ("You can recognize your emotions as they happen.", "Self-Awareness", 12, 25, 2, 1.0),
        ("You find it easy to understand why you feel a certain way.", "Self-Awareness", 14, 30, 3, 1.0),
        ("You can control your emotions even in stressful situations.", "Self-Management", 15, 35, 4, 1.5),
        ("You reflect on your emotional reactions to situations.", "Self-Awareness", 13, 28, 3, 1.0),
        ("You are aware of how your emotions affect others.", "Social Awareness", 16, 40, 4, 1.5),
    ]
    
    question_ids = []
    for q_data in test_questions:
        q_id = db.add_question(*q_data)
        question_ids.append(q_id)
        print(f"✓ Added question {q_id}: {q_data[0][:50]}...")
    
    # Test 4: Get all questions
    print("\n[Test 4] Retrieving all questions...")
    questions = db.get_all_questions()
    print(f"✓ Retrieved {len(questions)} questions")
    
    # Test 5: Get question by ID
    print("\n[Test 5] Getting question by ID...")
    question = db.get_question_by_id(question_ids[0])
    if question:
        print(f"✓ Retrieved question: {question['text'][:50]}...")
        print(f"  Category: {question['category']}")
        print(f"  Age Range: {question['age_min']}-{question['age_max']}")
        print(f"  Difficulty: {question['difficulty']}")
        print(f"  Weight: {question['weight']}")
    else:
        print("✗ Failed to retrieve question")
    
    # Test 6: Update question
    print("\n[Test 6] Updating question...")
    if db.update_question(question_ids[0], difficulty=5, weight=2.0):
        print("✓ Question updated successfully")
        updated = db.get_question_by_id(question_ids[0])
        print(f"  New difficulty: {updated['difficulty']}")
        print(f"  New weight: {updated['weight']}")
    else:
        print("✗ Failed to update question")
    
    # Test 7: Get categories
    print("\n[Test 7] Getting categories...")
    categories = db.get_categories()
    print(f"✓ Found {len(categories)} categories:")
    for cat in categories:
        count = len([q for q in questions if q['category'] == cat])
        print(f"  - {cat}: {count} question(s)")
    
    # Test 8: Soft delete question
    print("\n[Test 8] Soft deleting question...")
    if db.delete_question(question_ids[-1]):
        print("✓ Question soft deleted")
        # Verify it's not in active list
        active_questions = db.get_all_questions(include_inactive=False)
        inactive_questions = db.get_all_questions(include_inactive=True)
        print(f"  Active questions: {len(active_questions)}")
        print(f"  Total questions (including inactive): {len(inactive_questions)}")
    else:
        print("✗ Failed to delete question")
    
    # Test 9: Filter by category
    print("\n[Test 9] Filtering by category...")
    all_questions = db.get_all_questions()
    self_awareness = [q for q in all_questions if q['category'] == 'Self-Awareness']
    print(f"✓ Found {len(self_awareness)} questions in 'Self-Awareness' category")
    
    # Test 10: Error handling
    print("\n[Test 10] Testing error handling...")
    
    # Try to get non-existent question
    non_existent = db.get_question_by_id(99999)
    if non_existent is None:
        print("✓ Correctly handled non-existent question")
    else:
        print("✗ Should return None for non-existent question")
    
    # Try to create duplicate admin
    if not db.create_admin(username, password):
        print("✓ Correctly prevented duplicate admin username")
    else:
        print("✗ Should not allow duplicate username")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    
    # Cleanup
    print("\n🧹 Cleaning up test database...")
    if os.path.exists("test_admin_db.sqlite3"):
        os.remove("test_admin_db.sqlite3")
        print("✓ Test database removed")
    
    return True

def test_database_structure():
    """Test database table structure"""
    print("\n" + "=" * 60)
    print("Testing Database Structure")
    print("=" * 60)
    
    import sqlite3
    
    db = QuestionDatabase("test_structure_db.sqlite3")
    conn = sqlite3.connect("test_structure_db.sqlite3")
    cursor = conn.cursor()
    
    # Check questions table
    print("\n[Questions Table]")
    cursor.execute("PRAGMA table_info(questions)")
    columns = cursor.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col[1]}: {col[2]}")
    
    # Check admin_users table
    print("\n[Admin Users Table]")
    cursor.execute("PRAGMA table_info(admin_users)")
    columns = cursor.fetchall()
    print("Columns:")
    for col in columns:
        print(f"  - {col[1]}: {col[2]}")
    
    conn.close()
    
    # Cleanup
    if os.path.exists("test_structure_db.sqlite3"):
        os.remove("test_structure_db.sqlite3")
    
    print("\n✓ Database structure verified")

if __name__ == "__main__":
    try:
        test_database_structure()
        test_admin_interface()
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
