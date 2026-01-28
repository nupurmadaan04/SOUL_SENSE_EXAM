import os
import joblib
import logging
from typing import Optional, Dict, Any, List
import numpy as np

from app.ml.risk_predictor import RiskPredictor

logger = logging.getLogger(__name__)

class SoulSenseMLPredictor:
    """
    Advanced ML Predictor for SoulSense with versioning and scaling support.
    Wraps the RiskPredictor with additional ML pipeline features.
    """

    def __init__(self, use_versioning: bool = True, models_dir: str = "models"):
        """Initialize the ML predictor.

        Args:
            use_versioning (bool, optional): Whether to use model versioning. Defaults to True.
            models_dir (str, optional): Directory containing trained models. Defaults to "models".
        """
        self.use_versioning = use_versioning
        self.models_dir = models_dir

        # Initialize components
        self.risk_predictor = RiskPredictor(models_dir=models_dir)
        self.model = None
        self.scaler = None
        self.feature_names = [
            "emotional_recognition",      # Q1
            "emotional_understanding",    # Q2
            "emotional_regulation",       # Q3
            "emotional_reflection",       # Q4
            "social_awareness",           # Q5
            "total_score",
            "age",
            "average_score",
            "sentiment_score",
        ]
        self.class_names = ["Low Risk", "Moderate Risk", "High Risk"]

        # Load latest model if available
        self._load_model()

    def _load_model(self) -> bool:
        """Load the latest trained model and scaler.

        Returns:
            bool: True if model loaded successfully, False otherwise.
        """
        try:
            # Try to load from versioning system first
            if self.use_versioning:
                try:
                    from model_versioning import ModelVersioningManager
                    versioning_manager = ModelVersioningManager()
                    model_data, metadata = versioning_manager.registry.load_model("soulsense_predictor")
                    self.model = model_data.get("model")
                    self.scaler = model_data.get("scaler")
                    logger.info(f"Loaded model version {metadata.version} from versioning system")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load from versioning system: {e}")

            # Fallback: load from models directory
            model_files = [f for f in os.listdir(self.models_dir)
                          if f.startswith("soulsense_predictor") and f.endswith(".pkl")]

            if model_files:
                # Sort by modification time to get latest
                model_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.models_dir, x)),
                               reverse=True)
                latest_model = os.path.join(self.models_dir, model_files[0])

                model_data = joblib.load(latest_model)
                self.model = model_data.get("model")
                self.scaler = model_data.get("scaler")
                logger.info(f"Loaded model from {latest_model}")
                return True

        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}")

        # If no model loaded, use fallback risk predictor
        logger.info("Using fallback rule-based prediction")
        return False

    def predict(self, total_score: float, sentiment_score: float, age: int) -> str:
        """Predict risk level using the trained model or fallback.

        Args:
            total_score (float): Total EQ assessment score.
            sentiment_score (float): Sentiment analysis score.
            age (int): User's age.

        Returns:
            str: Risk level string ("Low Risk", "Moderate Risk", or "High Risk").
        """
        if self.model is not None and self.scaler is not None:
            try:
                # Prepare features
                features = np.array([[total_score, sentiment_score, age]])

                # Scale features
                features_scaled = self.scaler.transform(features)

                # Make prediction
                prediction_idx = self.model.predict(features_scaled)[0]
                return self.class_names[prediction_idx]

            except Exception as e:
                logger.error(f"Model prediction failed: {e}")

        # Fallback to rule-based prediction
        return self.risk_predictor.predict(total_score, sentiment_score, age)

    def predict_with_explanation(self, responses: List[Dict], age: int, total_score: float,
                               sentiment_score: float = 0.0) -> Dict[str, Any]:
        """Predict with detailed explanation.

        Args:
            responses (List[Dict]): List of question responses.
            age (int): User's age.
            total_score (float): Total assessment score.
            sentiment_score (float, optional): Sentiment score. Defaults to 0.0.

        Returns:
            Dict[str, Any]: Dictionary with prediction details including prediction code,
                           label, score, sentiment, and confidence.
        """
        # Get basic prediction
        label = self.predict(total_score, sentiment_score, age)

        # Calculate confidence if model available
        confidence = 0.8  # Default for rule-based
        if self.model is not None and self.scaler is not None:
            try:
                features = np.array([[total_score, sentiment_score, age]])
                features_scaled = self.scaler.transform(features)
                probas = self.model.predict_proba(features_scaled)[0]
                confidence = float(max(probas))
            except Exception as e:
                logger.warning(f"Could not calculate confidence: {e}")

        # Map to UI codes (0=Low, 1=Moderate, 2=High)
        if "High Risk" in label:
            code = 2
        elif "Moderate Risk" in label:
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

    def is_model_loaded(self) -> bool:
        """Check if a trained model is loaded.

        Returns:
            bool: True if a model is loaded, False otherwise.
        """
        return self.model is not None
