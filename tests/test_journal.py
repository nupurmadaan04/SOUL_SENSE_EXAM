import logging
from datetime import datetime
from app.models import JournalEntry

def test_journal_insert(temp_db):
    """
    Test journal entry insertion using the isolated temp_db fixture.
    This avoids locking issues with the running dev server.
    """
    print("Testing Journal Entry Insertion...")
    session = temp_db
    
    try:
        entry = JournalEntry(
            username="test_user",
            entry_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            content="This is a test entry from the debug script.",
            sentiment_score=50.0,
            emotional_patterns="Test pattern"
        )
        session.add(entry)
        session.commit()
        print("✅ Successfully inserted journal entry.")
        
        # Verify
        saved_entry = session.query(JournalEntry).filter_by(username="test_user").order_by(JournalEntry.id.desc()).first()
        assert saved_entry is not None
        assert saved_entry.content == "This is a test entry from the debug script."
        print(f"✅ Verified read back: {saved_entry.content}")
        
    except Exception as e:
        print(f"❌ Failed to insert journal entry: {e}")
        session.rollback()
        raise e
