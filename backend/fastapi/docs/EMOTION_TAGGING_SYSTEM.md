# Emotion Tagging System (Issue #1334)

## Overview

The Emotion Tagging System provides granular emotion categorization for journal entries, allowing users to tag their entries with predefined emotion categories and custom tags. This enables better emotional tracking and more effective filtering of journal entries.

## Features

### 1. Emotion Categories

Emotions are organized into three categories:

#### **Positive Emotions** 😊
- happy, excited, grateful, peaceful, proud, hopeful, energized

#### **Challenging Emotions** 😢  
- sad, angry, frustrated, anxious, disappointed, overwhelmed, exhausted

#### **Neutral Emotions** 😌
- calm, focused, curious, neutral, thoughtful, contemplative

### 2. General Categories

Non-emotion tags for content organization:
- work, family, health, relationships, personal, goals, achievement, learning

### 3. Custom Tags

Users can add custom tags beyond the preset options for personalized organization.

## API Usage

### Creating a Journal Entry with Tags

**POST `/api/journal/`**

```json
{
  "content": "Today was great! I felt energized and accomplished my goals.",
  "tags": ["happy", "energized", "goals", "achievement"],
  "sleep_hours": 8,
  "energy_level": 9,
  "stress_level": 2
}
```

### Updating Entry Tags

**PUT `/api/journal/{entry_id}`**

```json
{
  "tags": ["happy", "grateful", "work"]
}
```

### Filtering by Emotion Tags

**GET `/api/journal/filtered`**

```json
{
  "tags": ["happy", "energized"],
  "emotion_types": ["positive"],
  "skip": 0,
  "limit": 20
}
```

## Tag Validation Rules

- **Minimum Length**: 2 characters
- **Maximum Length**: 20 characters
- **Maximum Tags per Entry**: 10
- **Valid Characters**: Alphanumeric, hyphens, underscores
- **Case Handling**: All tags are normalized to lowercase

## Frontend Implementation

### Tag Selector Component

The `TagSelector` component in `/frontend-web/src/components/journal/tag-selector.tsx` provides:

1. **Organized Display**: Tags grouped by emotion category
2. **Visual Indicators**: Emojis for better UX (😊, 😢, 😌, etc.)
3. **Easy Selection**: Click to add preset tags
4. **Custom Tags**: Input field for adding custom tags
5. **Tag Management**: Quick removal with X button
6. **Tag Counter**: Shows current/max tags usage

### Usage in Components

```tsx
import { TagSelector } from '@/components/journal/tag-selector';
import { EMOTION_EMOJIS, EMOTION_CATEGORIES } from '@/types/journal';

function JournalEditor() {
  const [tags, setTags] = useState<string[]>([]);

  return (
    <TagSelector
      selected={tags}
      onChange={setTags}
      maxTags={10}
      showEmojis={true}
    />
  );
}
```

## Backend Implementation

### Emotion Tags Utility

Located in `/backend/fastapi/api/utils/emotion_tags.py`

**Key Functions:**

- `validate_tag(tag)` - Validate individual tag format
- `validate_tags(tags)` - Validate list of tags
- `categorize_tag(tag)` - Get tag category (positive, negative, neutral, general, custom)
- `get_tag_emoji(tag)` - Get emoji for tag
- `get_emotion_tags(tags)` - Filter to emotion tags only
- `get_category_tags(tags)` - Filter to category tags only

### Schema Validation

`JournalCreate` and `JournalUpdate` schemas include field validators that:

1. Normalize tags to lowercase
2. Validate tag format and length
3. Enforce maximum tag count (10 tags)
4. Remove duplicates
5. Return helpful error messages

## Database Schema

### Indexes

- `idx_journal_tags` - Index on tags column for efficient tag-based filtering

### Storage Format

Tags are stored as JSON array in the `tags` column of `journal_entries` table.

Example:
```json
["happy", "grateful", "work", "achievement"]
```

## Filtering Capabilities

The emotion tagging system supports multiple filtering approaches:

### 1. Tag-Based Filtering
```
Filter by specific tags: ["happy", "energized"]
OR logic: Returns entries with ANY of these tags
```

### 2. Emotion Type Filtering
```
Filter by emotion category: ["positive", "negative"]
Returns entries containing emotions from specified categories
```

### 3. Combined Filtering
```
Use multiple filters simultaneously:
- Tags: ["work", "learning"]
- Emotion Types: ["positive"]  
- Sentiment Range: 65-100
- Date Range: Last 7 days
```

## Usage Statistics & Insights

Users can gain insights about their emotional patterns:

- **Most Used Emotions**: Frequency count of emotion tags
- **Emotional Trends**: How emotions change over time
- **Emotion-Context Mapping**: Which contexts (work, family, health) associate with which emotions
- **Tag Co-occurrence**: Which emotions frequently appear together

## Frontend Type Definitions

Located in `/frontend-web/src/types/journal.ts`:

```typescript
// Emotion categories
export const EMOTION_CATEGORIES = {
  positive: ['happy', 'excited', ...],
  negative: ['sad', 'angry', ...],
  neutral: ['calm', 'focused', ...]
};

// Emoji mappings
export const EMOTION_EMOJIS: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  // ...
};

// All preset tags
export const PRESET_TAGS = [
  'happy', 'excited', 'grateful', // ... emotion tags
  'work', 'family', 'health', // ... category tags
];
```

## Constants

### Constants File

Located in `/frontend-web/src/lib/constants/journal.ts`:

```typescript
// Re-exports from types
export const PRESET_TAGS = TAG_LIST;
export const EMOTION_TAG_CATEGORIES = EMOTION_CATEGORIES;
export const TAG_EMOJIS = EMOTION_EMOJIS;
export const CATEGORY_TAGS = GENERAL_TAGS;
```

## Error Handling

### Validation Errors

The system provides clear error messages:

- "Tags must be a list"
- "Maximum 10 tags allowed per entry"
- "Tag 'xyz' must be 2-20 characters"
- "Tag 'abc' contains invalid characters"

### HTTP Status Codes

- `400 Bad Request` - Invalid tag format/validation failure
- `422 Unprocessable Entity` - Pydantic validation error
- `200 OK` - Successful tag creation/update

## Best Practices

1. **Use Emotion Tags**: Always tag emotions to build emotional awareness patterns
2. **Be Specific**: Use 2-5 tags per entry for meaningful filtering
3. **Mix Emotions and Categories**: Combine emotion and situational tags
4. **Review Patterns**: Use filters to identify emotional trends
5. **Custom Tags**: Add custom tags for recurring situations

## Testing

The emotion tagging system includes:

- Tag validation tests
- Tag filtering tests
- Emoji mapping tests
- Category classification tests
- Database migration tests

Run tests with:
```bash
pytest tests/test_emotion_tagging.py -v
```

## Migration Notes

### Initial Setup

Run migration `1334_add_emotion_tags_support` to:
- Add index on tags column for efficient filtering

### Data Migration

Existing entries without tags:
- No action required
- Tags field is nullable
- New entries will begin using emotion tags

## Performance Considerations

1. **Tag Index**: `idx_journal_tags` provides O(log n) lookup for tag filtering
2. **JSON Storage**: Tags stored as JSON for flexibility and querying
3. **Caching**: Consider caching tag frequency statistics
4. **Batch Operations**: Efficient bulk tag updates supported

## Future Enhancements

- Machine learning-based emotion suggestion
- Emotion pattern analysis and reporting
- Tag analytics dashboard
- Sentiment-emotion correlation analysis
- Automated tag suggestions based on entry content

## Related Issues

- #1325 - Advanced Emotion Filtering (dependency)
- #1326 - Weekly Emotional Summary (uses emotion tags)

## Support

For issues or questions about the Emotion Tagging System:
1. Check existing documentation
2. Review API examples
3. Examine test cases for implementation patterns
4. Contact development team
