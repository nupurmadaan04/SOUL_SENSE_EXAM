import pytest
from backend.fastapi.api.services.badge_service import BadgeService
from backend.fastapi.api.models import User, Badge, UserBadge, JournalEntry, Score

@pytest.mark.asyncio
async def test_first_journal_badge(async_db_session, test_user):
    """Test first journal badge unlocks after first entry."""
    entry = JournalEntry(user_id=test_user.id, content="Test entry")
    async_db_session.add(entry)
    await async_db_session.commit()
    
    unlocked = await BadgeService.check_and_unlock_badges(test_user.id, async_db_session)
    assert len(unlocked) == 1
    assert unlocked[0].name == "first_journal"

@pytest.mark.asyncio
async def test_badge_progress_tracking(async_db_session, test_user):
    """Test badge progress updates correctly."""
    for i in range(5):
        entry = JournalEntry(user_id=test_user.id, content=f"Entry {i}")
        async_db_session.add(entry)
    await async_db_session.commit()
    
    badges = await BadgeService.get_user_badges(test_user.id, async_db_session)
    journal_100 = next(b for b in badges if b["name"] == "journal_100")
    assert journal_100["progress"] == 5
    assert journal_100["milestone"] == 100
    assert not journal_100["unlocked"]

@pytest.mark.asyncio
async def test_eq_master_badge(async_db_session, test_user):
    """Test EQ master badge unlocks at 90+ score."""
    score = Score(user_id=test_user.id, username=test_user.username, total_score=95)
    async_db_session.add(score)
    await async_db_session.commit()
    
    unlocked = await BadgeService.check_and_unlock_badges(test_user.id, async_db_session)
    assert any(b.name == "eq_master" for b in unlocked)
