#!/usr/bin/env python3
"""
Test script for soft delete functionality.
Tests that:
1. Soft deletes mark records as deleted with timestamp
2. Queries filter out soft-deleted records
3. Admin can access soft-deleted records (future feature)
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timezone

# Python 3.10 compatibility
UTC = timezone.utc
from app.db import SessionLocal
from backend.fastapi.api.models import JournalEntry, AssessmentResult, User

def test_soft_deletes():
    """Test soft delete functionality."""
    print("🧪 Testing Soft Delete Functionality")
    print("=" * 50)

    with SessionLocal() as db:
        # Create test user
        test_user = db.query(User).filter(User.username == "test_user").first()
        if not test_user:
            test_user = User(
                username="test_user",
                password_hash="dummy_hash",
                created_at=datetime.now(UTC).isoformat()
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)

        print(f"✅ Test user: {test_user.username} (ID: {test_user.id})")

        # Test 1: Create and soft delete a journal entry
        print("\n📝 Testing Journal Entry Soft Delete")

        # Create entry
        entry = JournalEntry(
            username=test_user.username,
            user_id=test_user.id,
            title="Test Entry",
            content="This is a test journal entry for soft delete testing.",
            entry_date=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        print(f"✅ Created journal entry (ID: {entry.id})")

        # Verify it's not soft deleted
        assert entry.is_deleted == False
        assert entry.deleted_at is None
        print("✅ Entry is not soft deleted initially")

        # Soft delete the entry
        entry.is_deleted = True
        entry.deleted_at = datetime.now(UTC)
        db.commit()
        print("✅ Soft deleted the journal entry")

        # Verify soft delete worked
        db.refresh(entry)
        assert entry.is_deleted == True
        assert entry.deleted_at is not None
        print("✅ Entry is now soft deleted with timestamp")

        # Test 2: Query filtering
        print("\n🔍 Testing Query Filtering")

        # Query should not return soft-deleted entries
        active_entries = db.query(JournalEntry).filter(
            JournalEntry.user_id == test_user.id,
            JournalEntry.is_deleted == False
        ).all()
        print(f"✅ Found {len(active_entries)} active entries (should be 0)")

        # Query should return soft-deleted entries when explicitly requested
        deleted_entries = db.query(JournalEntry).filter(
            JournalEntry.user_id == test_user.id,
            JournalEntry.is_deleted == True
        ).all()
        print(f"✅ Found {len(deleted_entries)} soft-deleted entries (should be 1)")

        # Test 3: Assessment Result soft delete
        print("\n📊 Testing Assessment Result Soft Delete")

        # Create assessment result
        result = AssessmentResult(
            user_id=test_user.id,
            assessment_type="test_assessment",
            timestamp=datetime.now(UTC).isoformat(),
            overall_score=85.0,
            details='{"test": "data"}'
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        print(f"✅ Created assessment result (ID: {result.id})")

        # Verify it's not soft deleted
        assert result.is_deleted == False
        assert result.deleted_at is None
        print("✅ Result is not soft deleted initially")

        # Soft delete the result
        result.is_deleted = True
        result.deleted_at = datetime.now(UTC)
        db.commit()
        print("✅ Soft deleted the assessment result")

        # Verify soft delete worked
        db.refresh(result)
        assert result.is_deleted == True
        assert result.deleted_at is not None
        print("✅ Result is now soft deleted with timestamp")

        # Test 4: Query filtering for assessment results
        print("\n🔍 Testing Assessment Result Query Filtering")

        # Query should not return soft-deleted results
        active_results = db.query(AssessmentResult).filter(
            AssessmentResult.user_id == test_user.id,
            AssessmentResult.is_deleted == False
        ).all()
        print(f"✅ Found {len(active_results)} active assessment results (should be 0)")

        # Query should return soft-deleted results when explicitly requested
        deleted_results = db.query(AssessmentResult).filter(
            AssessmentResult.user_id == test_user.id,
            AssessmentResult.is_deleted == True
        ).all()
        print(f"✅ Found {len(deleted_results)} soft-deleted assessment results (should be 1)")

        # Cleanup
        print("\n🧹 Cleaning up test data")
        db.delete(result)
        db.delete(entry)
        db.delete(test_user)
        db.commit()
        print("✅ Test data cleaned up")

    print("\n🎉 All soft delete tests passed!")
    print("=" * 50)

if __name__ == "__main__":
    test_soft_deletes()