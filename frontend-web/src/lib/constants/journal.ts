import { PRESET_TAGS as TAG_LIST, EMOTION_CATEGORIES, EMOTION_EMOJIS, GENERAL_TAGS } from '@/types/journal';

export const PRESET_TAGS = TAG_LIST;

/**
 * Emotion tag categories for granular emotion tracking (Issue #1334)
 * - Positive emotions: happy, excited, grateful, etc.
 * - Challenging emotions: sad, angry, frustrated, etc.
 * - Neutral emotions: calm, focused, curious, etc.
 */
export const EMOTION_TAG_CATEGORIES = EMOTION_CATEGORIES;

/**
 * Emoji mappings for visual representation of emotion tags (Issue #1334)
 */
export const TAG_EMOJIS = EMOTION_EMOJIS;

/**
 * General category tags (non-emotion)
 */
export const CATEGORY_TAGS = GENERAL_TAGS;
