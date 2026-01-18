import sqlite3
import pandas as pd
import joblib
import os
import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import logging
import sys

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add parent dir for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DB_PATH, MODELS_DIR

# Constants
MIN_RECORDS_REQUIRED = 100

def get_db_connection():
    """Create a database connection."""
    if not os.path.exists(DB_PATH):
        logging.error(f"Database not found at {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def fetch_data(conn):
    """Fetch scores and journal entries, merging them on user_id."""
    query = """
    SELECT 
        s.user_id, 
        s.total_score, 
        s.age,
        j.sentiment_score
    FROM scores s
    JOIN journal_entries j ON s.user_id = j.user_id
    -- We assume the latest journal entry correlates with the score for simplicity in this MVP
    -- In a real scenario, we'd match by date proximity. 
    -- Here we take a simplified approach: aggregation or direct join if 1:1.
    -- Better approach for this MVP: Cross join on user_id where dates are close? 
    -- Let's stick to a simpler join: users who have BOTH a score and a journal.
    GROUP BY s.user_id 
    """
    # Note: The above query is a bit simplistic. It groups by user_id but doesn't aggregate.
    # SQLite will pick an arbitrary row. For an MVP to prove the concept, this is "okay",
    # but let's make it slightly better by averaging sentiment if multiple exist.
    
    query = """
    SELECT 
        s.user_id,
        s.total_score,
        s.age,
        AVG(j.sentiment_score) as avg_sentiment
    FROM scores s
    INNER JOIN journal_entries j ON s.user_id = j.user_id
    GROUP BY s.user_id, s.total_score, s.age
    """
    
    df = pd.read_sql_query(query, conn)
    return df

def label_risk(row):
    """
    Risk Labeling Rules:
    - High Risk: Score < 25 AND Sentiment < -0.3
    - Low Risk: Score > 35 AND Sentiment > 0.3
    - Medium Risk: Everything else
    """
    score = row['total_score']
    sentiment = row['avg_sentiment']
    
    if score < 25 and sentiment < -0.3:
        return "High Risk"
    elif score > 35 and sentiment > 0.3:
        return "Low Risk"
    else:
        return "Medium Risk"

def train_model():
    """Main training pipeline."""
    conn = get_db_connection()
    
    logging.info("Fetching data from real user records...")
    df = fetch_data(conn)
    conn.close()
    
    record_count = len(df)
    logging.info(f"Found {record_count} valid user records (Score + Journal).")
    
    if record_count < MIN_RECORDS_REQUIRED:
        logging.warning(f"Not enough data to train. Required: {MIN_RECORDS_REQUIRED}, Found: {record_count}.")
        logging.warning("Aborting training. Please collect more real user data.")
        return False

    # Labeling
    logging.info("Labeling data based on risk thresholds...")
    df['risk_label'] = df.apply(label_risk, axis=1)
    
    # Feature Selection
    X = df[['total_score', 'avg_sentiment', 'age']]
    y = df['risk_label']
    
    # Splitting
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Training
    logging.info(f"Training RandomForestClassifier on {len(X_train)} samples...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluation
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Model Accuracy: {accuracy:.2f}")
    logging.info("\n" + classification_report(y_test, y_pred))
    
    # Saving (Versioning)
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    model_filename = f"risk_model_v{timestamp}.pkl"
    model_path = os.path.join(MODELS_DIR, model_filename)
    
    joblib.dump(clf, model_path)
    logging.info(f"Model saved to {model_path}")
    
    # Clean up old models? (Optional: Keep last 5)
    return True

if __name__ == "__main__":
    train_model()
