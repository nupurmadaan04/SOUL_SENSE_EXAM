"""
Emotion Tag Categorization and Utilities (Issue #1334)

Provides support for granular emotion tagging with categories and validation.
"""

# Emotion categories for tag-based filtering (Issue #1334)
EMOTION_CATEGORIES = {
    "positive": [
        "happy",
        "excited",
        "grateful",
        "peaceful",
        "proud",
        "hopeful",
        "energized"
    ],
    "negative": [
        "sad",
        "angry",
        "frustrated",
        "anxious",
        "disappointed",
        "overwhelmed",
        "exhausted"
    ],
    "neutral": [
        "calm",
        "focused",
        "curious",
        "neutral",
        "thoughtful",
        "contemplative"
    ]
}

# General category tags (non-emotion)
GENERAL_TAGS = [
    "work",
    "family",
    "health",
    "relationships",
    "personal",
    "goals",
    "achievement",
    "learning"
]

# All valid tags
ALL_TAGS = (
    list(EMOTION_CATEGORIES["positive"]) + 
    list(EMOTION_CATEGORIES["negative"]) + 
    list(EMOTION_CATEGORIES["neutral"]) + 
    GENERAL_TAGS
)

# Emoji mappings for emotion tags
EMOTION_EMOJIS = {
    # Positive emotions
    "happy": "😊",
    "excited": "🤩",
    "grateful": "🙏",
    "peaceful": "😌",
    "proud": "🎉",
    "hopeful": "🌟",
    "energized": "⚡",
    # Negative emotions
    "sad": "😢",
    "angry": "😠",
    "frustrated": "😤",
    "anxious": "😰",
    "disappointed": "😞",
    "overwhelmed": "😵",
    "exhausted": "😫",
    # Neutral emotions
    "calm": "🧘",
    "focused": "🎯",
    "curious": "🤔",
    "neutral": "😐",
    "thoughtful": "💭",
    "contemplative": "🤐",
    # General tags
    "work": "💼",
    "family": "👨‍👩‍👧‍👦",
    "health": "🏥",
    "relationships": "❤️",
    "personal": "🔑",
    "goals": "🎯",
    "achievement": "🏆",
    "learning": "📚"
}

# Maximum tags per entry
MAX_TAGS_PER_ENTRY = 10

# Tag length constraints
MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 20


def validate_tag(tag: str) -> bool:
    """
    Validate if a tag meets format requirements.
    
    Args:
        tag: The tag to validate
        
    Returns:
        bool: True if tag is valid, False otherwise
    """
    if not tag or not isinstance(tag, str):
        return False
    
    tag = tag.strip().lower()
    
    if len(tag) < MIN_TAG_LENGTH or len(tag) > MAX_TAG_LENGTH:
        return False
    
    # Allow alphanumeric and hyphens
    return tag.replace("-", "").replace("_", "").isalnum()


def categorize_tag(tag: str) -> str:
    """
    Get the category of a tag.
    
    Args:
        tag: The tag to categorize
        
    Returns:
        str: Category name ('positive', 'negative', 'neutral', 'general', or 'custom')
    """
    tag_lower = tag.lower().strip()
    
    if tag_lower in EMOTION_CATEGORIES["positive"]:
        return "positive"
    elif tag_lower in EMOTION_CATEGORIES["negative"]:
        return "negative"
    elif tag_lower in EMOTION_CATEGORIES["neutral"]:
        return "neutral"
    elif tag_lower in GENERAL_TAGS:
        return "general"
    else:
        return "custom"


def get_tag_emoji(tag: str) -> str:
    """
    Get the emoji for a tag.
    
    Args:
        tag: The tag
        
    Returns:
        str: Emoji for the tag, or default tag emoji
    """
    return EMOTION_EMOJIS.get(tag.lower().strip(), "🏷️")


def validate_tags(tags: list, max_tags: int = MAX_TAGS_PER_ENTRY) -> tuple[bool, str]:
    """
    Validate a list of tags.
    
    Args:
        tags: List of tags to validate
        max_tags: Maximum allowed tags
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not tags:
        return True, ""
    
    if not isinstance(tags, list):
        return False, "Tags must be a list"
    
    if len(tags) > max_tags:
        return False, f"Too many tags. Maximum allowed: {max_tags}"
    
    for tag in tags:
        if not validate_tag(tag):
            return False, f"Invalid tag format: '{tag}'. Must be {MIN_TAG_LENGTH}-{MAX_TAG_LENGTH} alphanumeric characters"
    
    return True, ""


def get_emotion_tags(tags: list) -> list:
    """
    Extract emotion tags from a list of tags.
    
    Args:
        tags: List of all tags
        
    Returns:
        list: Tags that are emotion-related
    """
    emotion_tags = []
    for tag in tags:
        category = categorize_tag(tag)
        if category in ["positive", "negative", "neutral"]:
            emotion_tags.append(tag.lower().strip())
    return emotion_tags


def get_category_tags(tags: list) -> list:
    """
    Extract general category tags from a list of tags.
    
    Args:
        tags: List of all tags
        
    Returns:
        list: Tags that are general categories
    """
    category_tags = []
    for tag in tags:
        if categorize_tag(tag) == "general":
            category_tags.append(tag.lower().strip())
    return category_tags
