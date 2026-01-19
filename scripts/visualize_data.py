import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Add parent dir to path to import app modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DB_PATH

OUTPUT_DIR = os.path.join("docs", "images")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "training_data_distribution.png")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"Database found at {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def label_risk(row):
    """
    Same logic as training script.
    """
    score = row['total_score']
    sentiment = row['avg_sentiment']
    
    if score < 25 and sentiment < -0.3:
        return "High Risk"
    elif score > 35 and sentiment > 0.3:
        return "Low Risk"
    else:
        return "Medium Risk"

def generate_viz():
    conn = get_db_connection()
    
    query = """
    SELECT 
        s.user_id,
        s.total_score,
        AVG(j.sentiment_score) as avg_sentiment
    FROM scores s
    INNER JOIN journal_entries j ON s.user_id = j.user_id
    GROUP BY s.user_id, s.total_score
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Error reading database: {e}")
        return

    conn.close()
    
    if df.empty:
        print("No data found to visualize.")
        return

    # Apply labeling
    df['Risk Label'] = df.apply(label_risk, axis=1)
    
    # Prepare Plot
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    plt.figure(figsize=(10, 5))
    
    # Subplot 1: Risk Distribution (Bar)
    plt.subplot(1, 2, 1)
    counts = df['Risk Label'].value_counts()
    colors = ['#F59E0B', '#22C55E', '#EF4444'] # Yellow, Green, Red-ish approximation
    # Map colors to labels if possible, but simple valid colors is fine for now
    
    # Assign specific colors
    color_map = {'High Risk': '#EF4444', 'Medium Risk': '#F59E0B', 'Low Risk': '#22C55E'}
    bar_colors = [color_map.get(lbl, 'gray') for lbl in counts.index]
    
    counts.plot(kind='bar', color=bar_colors)
    plt.title('Distribution of Risk Labels')
    plt.xlabel('Risk Category')
    plt.ylabel('Number of Users')
    plt.xticks(rotation=45)
    
    # Subplot 2: Score Histogram
    plt.subplot(1, 2, 2)
    plt.hist(df['total_score'], bins=10, color='#3B82F6', edgecolor='black')
    plt.title('Distribution of EQ Scores')
    plt.xlabel('Total Score')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_FILE)
    print(f"Visualization saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_viz()
