import os
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)
import numpy as np

from .dataset import load_training_data
from .features import build_vectorizer

# Correct paths relative to project root (assuming script run from root)
DB_PATH = "data/soulsense.db"
MODEL_PATH = "data/experiments/emotion_classification/model.pkl"


def train():
    texts, labels = load_training_data(DB_PATH)

    vectorizer = build_vectorizer()
    X = vectorizer.fit_transform(texts)

    X_train, X_test, y_train, y_test = train_test_split(
        X, labels, test_size=0.2, random_state=42
    )

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    
    # Calculate Metrics
    train_acc = accuracy_score(y_test, preds)
    precision = precision_score(y_test, preds, average='weighted', zero_division=0)
    recall = recall_score(y_test, preds, average='weighted', zero_division=0)
    f1 = f1_score(y_test, preds, average='weighted', zero_division=0)

    print("\n Model Evaluation Results:")
    print(f"   Accuracy:  {train_acc:.4f} ({train_acc*100:.2f}%)")
    print(f"   Precision (weighted): {precision:.4f}")
    print(f"   Recall (weighted):    {recall:.4f}")
    print(f"   F1 Score (weighted):  {f1:.4f}")

    print("\n Confusion Matrix:")
    cm = confusion_matrix(y_test, preds)
    print(cm)
    
    print("\n Detailed Classification Report:")
    print(classification_report(y_test, preds))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    joblib.dump(
        {"model": model, "vectorizer": vectorizer},
        MODEL_PATH
    )

    print(" Emotion classification model saved:", MODEL_PATH)        


if __name__ == "__main__":
    train()
