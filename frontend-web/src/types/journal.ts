/**
 * Journal Entry Types
 * ====================
 * Type definitions for journal entries, filters and payloads.
 */

export type MoodLevel = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

/**
 * Emotion tag categories for granular emotion tracking (Issue #1334)
 */
export const EMOTION_CATEGORIES = {
    positive: ['happy', 'excited', 'grateful', 'peaceful', 'proud', 'hopeful', 'energized'],
    negative: ['sad', 'angry', 'frustrated', 'anxious', 'disappointed', 'overwhelmed', 'exhausted'],
    neutral: ['calm', 'focused', 'curious', 'neutral', 'thoughtful', 'contemplative'],
} as const;

/**
 * Emoji mappings for emotion tags (Issue #1334)
 */
export const EMOTION_EMOJIS: Record<string, string> = {
    // Positive emotions
    happy: '😊',
    excited: '🤩',
    grateful: '🙏',
    peaceful: '😌',
    proud: '🎉',
    hopeful: '🌟',
    energized: '⚡',
    // Negative emotions
    sad: '😢',
    angry: '😠',
    frustrated: '😤',
    anxious: '😰',
    disappointed: '😞',
    overwhelmed: '😵',
    exhausted: '😫',
    // Neutral emotions
    calm: '🧘',
    focused: '🎯',
    curious: '🤔',
    neutral: '😐',
    thoughtful: '💭',
    contemplative: '🤐',
};

/**
 * General tags for journal categorization
 */
export const GENERAL_TAGS = [
    "work",
    "family",
    "health",
    "relationships",
    "personal",
    "goals",
    "achievement",
    "learning",
] as const;

/**
 * All available preset tags combining emotions and general categories (Issue #1334)
 */
export const PRESET_TAGS = [
    // Positive emotions
    "happy",
    "excited",
    "grateful",
    "peaceful",
    "proud",
    "hopeful",
    "energized",
    // Negative emotions
    "sad",
    "angry",
    "frustrated",
    "anxious",
    "disappointed",
    "overwhelmed",
    "exhausted",
    // Neutral emotions
    "calm",
    "focused",
    "curious",
    "neutral",
    "thoughtful",
    "contemplative",
    // General categories
    "work",
    "family",
    "health",
    "relationships",
    "personal",
    "goals",
    "achievement",
    "learning",
] as const;

export type PresetTag = (typeof PRESET_TAGS)[number];

export interface JournalEntry {
    id: number;
    content: string;
    mood_rating: number; // 1-10
    energy_level?: number; // 1-10
    stress_level?: number; // 1-10
    tags: string[];
    sentiment_score?: number; // -1 to 1
    patterns?: string[]; // detected emotional patterns
    created_at: string;
    updated_at: string;
}

export interface JournalEntryCreate {
    content: string;
    mood_rating: number;
    energy_level?: number;
    stress_level?: number;
    tags?: string[];
}

export interface JournalEntryUpdate extends Partial<JournalEntryCreate> { }

export interface JournalFilters {
    startDate?: string;
    endDate?: string;
    moodMin?: number;
    moodMax?: number;
    tags?: string[];
    search?: string;
}

export type TimeRange = '7d' | '14d' | '30d';
