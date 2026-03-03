# Emotion Comparison Tool (#1337)

## Summary

Side-by-side comparison tool for analyzing emotional patterns across different time periods.

## Features

- **Dual Date Picker**: Select two custom date ranges for comparison
- **Quick Compare**: Predefined periods (this week vs last week, etc.)
- **Comparative Analytics**: Sentiment, mood, stress, EQ scores
- **Visual Indicators**: Trend arrows and percentage changes
- **Detailed Metrics**: Entry counts and averages for each period

## API Endpoints

### POST `/api/v1/emotion-comparison/compare`

Compare two custom date ranges.

**Request:**
```json
{
  "period1_start": "2024-01-01T00:00:00",
  "period1_end": "2024-01-07T23:59:59",
  "period2_start": "2024-01-08T00:00:00",
  "period2_end": "2024-01-14T23:59:59"
}
```

**Response:**
```json
{
  "period1": {
    "start": "2024-01-01T00:00:00",
    "end": "2024-01-07T23:59:59",
    "metrics": {
      "avg_sentiment": 0.65,
      "avg_mood": 7.2,
      "avg_stress": 4.1,
      "journal_entries": 12,
      "avg_eq_score": 78.5
    }
  },
  "period2": {
    "start": "2024-01-08T00:00:00",
    "end": "2024-01-14T23:59:59",
    "metrics": {
      "avg_sentiment": 0.72,
      "avg_mood": 7.8,
      "avg_stress": 3.5,
      "journal_entries": 15,
      "avg_eq_score": 82.0
    }
  },
  "comparison": {
    "sentiment": {
      "change": 0.07,
      "percentage": 10.77,
      "direction": "up"
    },
    "mood": {
      "change": 0.6,
      "percentage": 8.33,
      "direction": "up"
    },
    "stress": {
      "change": -0.6,
      "percentage": -14.63,
      "direction": "down"
    }
  }
}
```

### GET `/api/v1/emotion-comparison/quick-compare`

Compare using predefined periods.

**Parameters:**
- `period1`: `this_week`, `last_week`, `this_month`, `last_month`, `this_quarter`, `last_quarter`
- `period2`: Same options as period1

**Example:**
```
GET /api/v1/emotion-comparison/quick-compare?period1=last_week&period2=this_week
```

## Frontend Usage

```tsx
import EmotionComparisonTool from '@/components/dashboard/EmotionComparisonTool';

export default function AnalyticsPage() {
  return <EmotionComparisonTool />;
}
```

## Files Created

- `backend/fastapi/api/services/emotion_comparison_service.py` (150 lines)
- `backend/fastapi/api/routers/emotion_comparison.py` (120 lines)
- `frontend-web/src/components/dashboard/EmotionComparisonTool.tsx` (200 lines)
- `tests/test_emotion_comparison.py` (60 lines)
- `docs/EMOTION_COMPARISON.md` (this file)

**Total:** ~530 lines

## Acceptance Criteria Met

- [x] Dual date picker UI implemented
- [x] Comparative analytics visualization
- [x] Accurate comparison metrics displayed
- [x] Side-by-side period comparison
- [x] Percentage changes calculated
- [x] Trend indicators (up/down/neutral)

**Closes #1337**
