"""
Test Journal Entry Deletion (Issue #1331)

Tests the soft deletion feature for journal entries with confirmation.
"""

import pytest
import logging
from datetime import datetime, UTC
from app.models import JournalEntry, User, Base
from app.services.journal_service import JournalService
from app.db import engine, safe_db_context

logger = logging.getLogger(__name__)


class TestJournalEntryDeletion:
    """Test suite for journal entry deletion functionality"""
    
    @pytest.fixture(scope="function", autouse=True)
    def setup_teardown(self):
        """Create and clean up test database"""
        Base.metadata.create_all(engine)
        yield
        Base.metadata.drop_all(engine)
    
    def test_delete_entry_soft_delete(self):
        """Test that delete_entry performs soft delete"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="test_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create entry
            entry = JournalEntry(
                user_id=user.id,
                username=user.username,
                content="Test entry",
                sentiment_score=0.5,
                emotional_patterns="[]",
                is_deleted=False
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id
        
        # Delete entry
        success = JournalService.delete_entry(entry_id)
        assert success, "Delete should succeed"
        
        # Verify soft delete
        with safe_db_context() as session:
            deleted_entry = session.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
            assert deleted_entry is not None, "Entry should still exist (soft delete)"
            assert deleted_entry.is_deleted == True, "is_deleted flag should be True"
            assert deleted_entry.deleted_at is not None, "deleted_at should be set"
    
    def test_delete_nonexistent_entry(self):
        """Test delete_entry with invalid entry ID"""
        success = JournalService.delete_entry(99999)
        assert not success, "Delete should fail for nonexistent entry"
    
    def test_get_entries_excludes_deleted(self):
        """Test that get_entries excludes soft-deleted entries"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="test_user2", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create two entries
            entry1 = JournalEntry(
                user_id=user.id,
                username=user.username,
                content="Active entry",
                sentiment_score=0.5,
                emotional_patterns="[]"
            )
            entry2 = JournalEntry(
                user_id=user.id,
                username=user.username,
                content="Deleted entry",
                sentiment_score=-0.3,
                emotional_patterns="[]",
                is_deleted=True,
                deleted_at=datetime.now(UTC)
            )
            session.add_all([entry1, entry2])
            session.commit()
        
        # Get entries
        entries = JournalService.get_entries("test_user2")
        
        assert len(entries) == 1, "Should only return active entries"
        assert entries[0].content == "Active entry", "Should return non-deleted entry"
    
    def test_delete_and_retrieve(self):
        """Test that deleted entries don't appear in retrieval"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="test_user3", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create entry
            entry = JournalEntry(
                user_id=user.id,
                username=user.username,
                content="To be deleted",
                sentiment_score=0.5,
                emotional_patterns="[]"
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id
        
        # Retrieve before delete
        entries_before = JournalService.get_entries("test_user3")
        assert len(entries_before) == 1, "Should have 1 entry before delete"
        
        # Delete
        JournalService.delete_entry(entry_id)
        
        # Retrieve after delete
        entries_after = JournalService.get_entries("test_user3")
        assert len(entries_after) == 0, "Should have 0 entries after soft delete"
    
    def test_multiple_deletion(self):
        """Test deleting multiple entries"""
        with safe_db_context() as session:
            user = User(username="test_user4", password_hash="hash")
            session.add(user)
            session.commit()
            
            entry_ids = []
            for i in range(3):
                entry = JournalEntry(
                    user_id=user.id,
                    username=user.username,
                    content=f"Entry {i}",
                    sentiment_score=0.5,
                    emotional_patterns="[]"
                )
                session.add(entry)
                session.commit()
                entry_ids.append(entry.id)
        
        # Delete two entries
        assert JournalService.delete_entry(entry_ids[0])
        assert JournalService.delete_entry(entry_ids[1])
        
        # Verify only one remains
        entries = JournalService.get_entries("test_user4")
        assert len(entries) == 1, "Should have 1 active entry"
        assert entries[0].content == "Entry 2", "Remaining entry should be Entry 2"
    
    def test_get_recent_entries_excludes_deleted(self):
        """Test that get_recent_entries excludes soft-deleted entries"""
        with safe_db_context() as session:
            user = User(username="test_user5", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create recent entry
            entry1 = JournalEntry(
                user_id=user.id,
                username=user.username,
                content="Recent active",
                sentiment_score=0.5,
                emotional_patterns="[]",
                entry_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            # Create and soft-delete entry
            entry2 = JournalEntry(
                user_id=user.id,
                username=user.username,
                content="Recent deleted",
                sentiment_score=-0.3,
                emotional_patterns="[]",
                entry_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                is_deleted=True,
                deleted_at=datetime.now(UTC)
            )
            session.add_all([entry1, entry2])
            session.commit()
        
        # Get recent
        recent = JournalService.get_recent_entries("test_user5", days=7)
        
        assert len(recent) == 1, "Should only return active recent entries"
        assert recent[0].content == "Recent active", "Should return non-deleted entry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
