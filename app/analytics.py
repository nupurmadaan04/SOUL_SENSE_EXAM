from textblob import TextBlob

def analyze_sentiment_trends(report_data):
    """
    Analyzes the emotional tone of user stressors.
    """
    total_sentiment = 0
    count = len(report_data)
    
    for entry in report_data:
        analysis = TextBlob(entry['text'])
        total_sentiment += analysis.sentiment.polarity
    
    avg_sentiment = total_sentiment / count if count > 0 else 0
    
    # Determine status based on polarity
    if avg_sentiment > 0.1:
        status = "Positive/Coping Well"
    elif avg_sentiment < -0.1:
        status = "High Stress/Overwhelmed"
    else:
        status = "Neutral/Stable"
        
    return {
        "avg_sentiment": round(avg_sentiment, 2),
        "status": status,
        "count": count
    }