import os
import joblib
import pandas as pd
import glob
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)

class RiskPredictor:
    """Predicts emotional risk levels using ML models or rule-based fallback."""

    def __init__(self, models_dir="models"):
        """Initialize the risk predictor.

        Args:
            models_dir (str, optional): Directory containing trained models. Defaults to "models".
        """
        self.models_dir = models_dir
        self.model = None
        self._model_loaded = False
        
    def load_latest_model(self):
        """Finds and loads the most recent model file."""
        try:
            # List all .pkl files in models dir
            pattern = os.path.join(self.models_dir, "risk_model_v*.pkl")
            files = glob.glob(pattern)
            
            if not files:
                logging.warning("No ML models found in %s. Using fallback logic.", self.models_dir)
                self.model = None
                return

            # Sort by name (timestamp is in name)
            latest_file = max(files, key=os.path.getctime)
            logging.info(f"Loading ML Model: {latest_file}")
            
            self.model = joblib.load(latest_file)
            
        except Exception as e:
            logging.error(f"Failed to load ML model: {e}")
            self.model = None

    def predict(self, total_score, sentiment_score, age):
        """Predicts risk level.

        Args:
            total_score: Total assessment score.
            sentiment_score: Sentiment analysis score.
            age: User's age.

        Returns:
            str: Risk level ('High Risk', 'Medium Risk', 'Low Risk', or 'Unknown').
        """
        # Lazy load model if not already loaded
        if not self._model_loaded:
            self.load_latest_model()
            self._model_loaded = True

        # Fallback if no model
        if self.model is None:
            logging.info("ML Model not loaded. Using Rule-Based Fallback.")
            return self._rule_based_fallback(total_score, sentiment_score)
            
        try:
            # Prepare feature vector (must match training columns: score, sentiment, age)
            features = pd.DataFrame([[total_score, sentiment_score, age]], 
                                  columns=['total_score', 'avg_sentiment', 'age'])
            
            prediction = self.model.predict(features)[0]
            return prediction
            
        except Exception as e:
            logging.error(f"Prediction error: {e}")
            return self._rule_based_fallback(total_score, sentiment_score)

    def predict_with_explanation(self, responses, age, total_score, sentiment_score=0.0):
        """Interface for UI. Returns dict with 'prediction' (int) and 'prediction_label' (str).

        Args:
            responses: List of question responses.
            age: User's age.
            total_score: Total assessment score.
            sentiment_score: Sentiment score. Defaults to 0.0.

        Returns:
            dict: Dictionary with prediction details including prediction code, label, score, sentiment, and confidence.
        """
        # Get raw prediction (String)
        label = self.predict(total_score, sentiment_score, age)
        
        # Calculate confidence if model supports it
        confidence = 0.8 # Default for rule-based or fallback
        if self.model:
            try:
                features = pd.DataFrame([[total_score, sentiment_score, age]], 
                                      columns=['total_score', 'avg_sentiment', 'age'])
                # Get max probability
                probs = self.model.predict_proba(features)[0]
                confidence = max(probs)
            except Exception as e:
                logging.warning(f"Could not calculate confidence: {e}")

        # Map to UI codes
        # 2 = High Risk (Red), 1 = Medium Risk (Yellow), 0 = Low Risk (Green)
        if "High Risk" in label:
            code = 2
        elif "Medium Risk" in label:
            code = 1
        else:
            code = 0
            
        return {
            "prediction": code,
            "prediction_label": label,
            "score": total_score,
            "sentiment": sentiment_score,
            "confidence": confidence
        }

    def _rule_based_fallback(self, score, sentiment):
        """Simple rules if ML is broken/missing.

        Args:
            score: Total assessment score.
            sentiment: Sentiment score.

        Returns:
            str: Risk level based on simple rules.
        """
        if score < 25:
            return "High Risk (Rule)"
        elif score > 35:
            return "Low Risk (Rule)"
        else:
            return "Medium Risk (Rule)"
