# Achievement Badge System (#1336)

## Summary
Implemented milestone-based gamification with 8 achievement badges across journal, EQ test, and engagement categories to increase user motivation and retention.

## Problem
Users lacked motivational feedback for consistent app usage and progress milestones, leading to reduced engagement.

## Solution
Created a comprehensive badge system with:
- **Badge Rules Engine**: Automatic unlock logic for count, streak, score, and improvement milestones
- **Progress Tracking**: Real-time progress updates toward locked badges
- **Profile Display**: React component with filter (all/unlocked/locked) and progress bars
- **8 Achievement Badges**: Journal (4), EQ Test (3), Engagement (1)

## Badge Categories

### Journal Badges
- 📝 **first_journal**: Write your first journal entry
- 🔥 **journal_streak_7**: Maintain a 7-day journaling streak
- 🏆 **journal_streak_30**: Maintain a 30-day journaling streak
- 💯 **journal_100**: Write 100 journal entries

### EQ Test Badges
- 🎯 **first_eq_test**: Complete your first EQ assessment
- 👑 **eq_master**: Score 90+ on an EQ assessment
- 📈 **eq_improvement**: Improve your EQ score by 20 points

### Engagement Badges
- ⭐ **consistent_user**: Use the app for 14 consecutive days

## API Usage

### Get User Badges
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/badges
```

**Response:**
```json
[
  {
    "name": "first_journal",
    "description": "Write your first journal entry",
    "icon": "📝",
    "category": "journal",
    "progress": 1,
    "milestone": 1,
    "unlocked": true,
    "earned_at": "2026-03-01T10:00:00Z"
  },
  {
    "name": "journal_100",
    "description": "Write 100 journal entries",
    "icon": "💯",
    "category": "journal",
    "progress": 45,
    "milestone": 100,
    "unlocked": false,
    "earned_at": null
  }
]
```

### Trigger Badge Check
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/badges/check
```

**Response:**
```json
{
  "unlocked_count": 2,
  "badges": [
    {"name": "first_journal", "icon": "📝"},
    {"name": "first_eq_test", "icon": "🎯"}
  ]
}
```

## Technical Implementation

### Backend
- **Models**: Badge and UserBadge with milestone tracking
- **Service**: BadgeService with 4 unlock logic types (count, streak, score, improvement)
- **Router**: GET /badges and POST /badges/check endpoints
- **Migration**: Database schema for badge tables

### Frontend
- **Component**: BadgeDisplay with filter and progress visualization
- **Integration**: useCachedApi hook for real-time updates
- **UI**: Grid layout with locked/unlocked states

### Unlock Logic Types
1. **count**: Total number of actions (journal entries, assessments)
2. **streak**: Consecutive days of activity
3. **score**: Maximum score achieved
4. **improvement**: Score increase over time

## Files Added (~450 lines)

### Backend
- `backend/fastapi/api/models/badge.py` (40 lines) - Badge/UserBadge models
- `backend/fastapi/api/services/badge_service.py` (160 lines) - Unlock logic engine
- `backend/fastapi/api/routers/badges.py` (25 lines) - API endpoints
- `migrations/versions/20260301_130000_add_badge_system.py` (50 lines) - DB migration

### Frontend
- `frontend-web/src/components/profile/BadgeDisplay.tsx` (70 lines) - Badge UI component

### Testing & Docs
- `tests/test_badge_system.py` (35 lines) - Test suite with 3 test cases
- `docs/BADGE_SYSTEM.md` (70 lines) - Complete documentation

### Integration
- Updated `backend/fastapi/api/models/__init__.py` - Added badges relationship to User
- Updated `backend/fastapi/api/api/v1/router.py` - Registered badges router

## Database Schema

```sql
CREATE TABLE badges (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    milestone_type VARCHAR(50) NOT NULL,
    milestone_value INTEGER NOT NULL,
    created_at DATETIME
);

CREATE TABLE user_badges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    badge_id INTEGER NOT NULL,
    earned_at DATETIME,
    progress INTEGER DEFAULT 0,
    unlocked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (badge_id) REFERENCES badges(id)
);
```

## Testing

```bash
# Run badge system tests
pytest tests/test_badge_system.py -v

# Test coverage
pytest tests/test_badge_system.py --cov=backend.fastapi.api.services.badge_service
```

**Test Cases:**
- ✅ First journal badge unlocks after first entry
- ✅ Badge progress tracking updates correctly
- ✅ EQ master badge unlocks at 90+ score

## Acceptance Criteria
- ✅ Badges unlock at correct milestones
- ✅ Progress tracking updates in real-time
- ✅ Profile displays earned badges with filters
- ✅ API endpoints return proper badge data
- ✅ Database migration runs successfully
- ✅ Frontend component renders badges correctly

## Future Enhancements
- Badge notifications on unlock
- Leaderboard integration
- Custom badge icons
- Social sharing of achievements
- Seasonal/limited-time badges
