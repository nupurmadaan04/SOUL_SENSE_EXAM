# Achievement Badge System (#1336)

## Overview
Milestone-based gamification system that rewards users for consistent engagement and progress.

## Badge Categories

### Journal Badges
- **first_journal** 📝: Write your first journal entry
- **journal_streak_7** 🔥: Maintain a 7-day journaling streak
- **journal_streak_30** 🏆: Maintain a 30-day journaling streak
- **journal_100** 💯: Write 100 journal entries

### EQ Test Badges
- **first_eq_test** 🎯: Complete your first EQ assessment
- **eq_master** 👑: Score 90+ on an EQ assessment
- **eq_improvement** 📈: Improve your EQ score by 20 points

### Engagement Badges
- **consistent_user** ⭐: Use the app for 14 consecutive days

## API Endpoints

### GET /api/v1/badges
Get all badges for the current user with progress.

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
  }
]
```

### POST /api/v1/badges/check
Manually trigger badge unlock check.

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

## Badge Rules Engine

Badges are automatically checked and unlocked based on:
- **count**: Total number of actions (journal entries, assessments)
- **streak**: Consecutive days of activity
- **score**: Maximum score achieved
- **improvement**: Score increase over time

## Frontend Integration

```tsx
import { BadgeDisplay } from '@/components/profile/BadgeDisplay';

<BadgeDisplay />
```

## Acceptance Criteria
- ✅ Badges unlock at correct milestones
- ✅ Progress tracking updates in real-time
- ✅ Profile displays earned badges
- ✅ Filter badges by status (all/unlocked/locked)
