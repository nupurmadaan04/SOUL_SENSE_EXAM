def analyze_sentiment(text):
    """
    Analyze sentiment of input text.

    Returns:
        float between -1.0 and 1.0 (rough sentiment score)
        or None if input is empty
    """
    if not text or not isinstance(text, str):
        return None

    text = text.lower()

    positive_words = [
        "good", "happy", "calm", "positive", "confident",
        "hope", "grateful", "better", "improving"
    ]

    negative_words = [
        "bad", "sad", "angry", "stress", "anxious",
        "tired", "overwhelmed", "frustrated", "worried"
    ]

    score = 0

    for word in positive_words:
        if word in text:
            score += 1

    for word in negative_words:
        if word in text:
            score -= 1

    # Normalize score
    if score > 0:
        return min(score / 5, 1.0)
    if score < 0:
        return max(score / 5, -1.0)

    return 0.0
