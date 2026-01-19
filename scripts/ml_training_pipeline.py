#!/usr/bin/env python3
"""
ML Training Pipeline for SoulSense
==================================
A reproducible pipeline to train, validate, and save ML models.

This script provides:
- Data loading and preprocessing
- Model training with hyperparameter tuning
- Cross-validation and evaluation
- Model versioning and artifact saving
- Experiment tracking and comparison

Usage:
    python scripts/ml_training_pipeline.py --help
    python scripts/ml_training_pipeline.py train --model-type rf
    python scripts/ml_training_pipeline.py evaluate --model-version 1.0.0
    python scripts/ml_training_pipeline.py compare --versions 1.0.0 1.1.0

Author: SoulSense Team
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_versioning import ModelVersioningManager, create_versioning_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/ml_training.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


class MLTrainingPipeline:
    """
    Reproducible ML Training Pipeline for SoulSense depression risk prediction.
    
    This pipeline supports:
    - Multiple model types (Random Forest, Gradient Boosting, Logistic Regression, SVM)
    - Hyperparameter tuning via GridSearchCV
    - Cross-validation for robust evaluation
    - Model versioning and experiment tracking
    - Artifact saving (models, metrics, plots)
    """
    
    MODEL_NAME = "soulsense_predictor"
    
    FEATURE_NAMES = [
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
    
    CLASS_NAMES = ["Low Risk", "Moderate Risk", "High Risk"]
    
    # Default hyperparameter grids for each model type
    PARAM_GRIDS = {
        "rf": {
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 5, 10, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "class_weight": ["balanced", None],
        },
        "gb": {
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.01, 0.1, 0.2],
            "min_samples_split": [2, 5],
            "min_samples_leaf": [1, 2],
        },
        "lr": {
            "C": [0.01, 0.1, 1, 10],
            "penalty": ["l1", "l2"],
            "solver": ["liblinear", "saga"],
            "class_weight": ["balanced", None],
            "max_iter": [1000],
        },
        "svm": {
            "C": [0.1, 1, 10],
            "kernel": ["rbf", "linear"],
            "gamma": ["scale", "auto"],
            "class_weight": ["balanced", None],
        },
    }
    
    # Quick hyperparameter grids for faster training
    QUICK_PARAM_GRIDS = {
        "rf": {
            "n_estimators": [100],
            "max_depth": [5],
            "min_samples_split": [2],
            "class_weight": ["balanced"],
        },
        "gb": {
            "n_estimators": [100],
            "max_depth": [5],
            "learning_rate": [0.1],
        },
        "lr": {
            "C": [1],
            "penalty": ["l2"],
            "solver": ["lbfgs"],
            "max_iter": [1000],
        },
        "svm": {
            "C": [1],
            "kernel": ["rbf"],
            "gamma": ["scale"],
        },
    }
    
    def __init__(
        self,
        output_dir: str = "models/pipeline_output",
        use_versioning: bool = True,
        random_state: int = 42,
    ):
        """
        Initialize the ML Training Pipeline.
        
        Args:
            output_dir: Directory to save outputs
            use_versioning: Whether to use model versioning
            random_state: Random seed for reproducibility
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_versioning = use_versioning
        self.random_state = random_state
        
        self.scaler = StandardScaler()
        self.model = None
        self.best_params = None
        self.metrics = {}
        
        if use_versioning:
            self.versioning_manager = create_versioning_manager()
        else:
            self.versioning_manager = None
        
        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)
        
        logger.info(f"Initialized MLTrainingPipeline with output_dir={output_dir}")
    
    def generate_synthetic_data(
        self,
        n_samples: int = 1000,
        noise_level: float = 0.1,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data for the depression risk model.
        
        Args:
            n_samples: Number of samples to generate
            noise_level: Amount of noise to add (0-1)
            
        Returns:
            Tuple of (features, labels)
        """
        logger.info(f"Generating {n_samples} synthetic samples...")
        
        np.random.seed(self.random_state)
        
        X = np.zeros((n_samples, len(self.FEATURE_NAMES)))
        
        for i in range(n_samples):
            # Generate individual question scores (1-5)
            q_scores = np.random.randint(1, 6, 5)
            
            # Calculate derived features
            total_score = q_scores.sum()
            age = np.random.randint(12, 65)
            avg_score = total_score / 5
            
            # Generate sentiment correlated with EQ score + noise
            base_sentiment = (total_score / 25.0) * 100
            sentiment_noise = np.random.normal(0, 30 * (1 + noise_level))
            sentiment_score = np.clip((base_sentiment - 50) * 2 + sentiment_noise, -100, 100)
            
            # Create feature vector
            X[i] = [
                q_scores[0], q_scores[1], q_scores[2], q_scores[3], q_scores[4],
                total_score, age, avg_score, sentiment_score
            ]
        
        # Generate labels based on rules with some noise
        y = []
        for i in range(n_samples):
            total_score = X[i, 5]
            sentiment_score = X[i, 8]
            
            # Add noise to thresholds
            noise = np.random.normal(0, noise_level * 3)
            
            # Risk classification rules
            if total_score <= (10 + noise) or (total_score <= (15 + noise) and sentiment_score < -50):
                y.append(2)  # High risk
            elif total_score <= (15 + noise) or (total_score <= (20 + noise) and sentiment_score < -20):
                y.append(1)  # Moderate risk
            else:
                y.append(0)  # Low risk
        
        y = np.array(y)
        
        # Log class distribution
        unique, counts = np.unique(y, return_counts=True)
        dist = dict(zip(unique, counts))
        logger.info(f"Class distribution: {dist}")
        
        return X, y
    
    def load_data_from_db(self, db_path: str = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load training data from the database.
        
        Args:
            db_path: Path to the SQLite database (uses config default if None)
            
        Returns:
            Tuple of (features, labels) or None if insufficient data
        """
        import sqlite3
        from app.config import DB_PATH as DEFAULT_DB_PATH
        
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        
        logger.info(f"Loading data from {db_path}...")
        
        if not Path(db_path).exists():
            logger.warning(f"Database not found at {db_path}")
            return None, None
        
        try:
            conn = sqlite3.connect(db_path)
            
            # Try to load from scores table
            query = """
                SELECT total_score, age, timestamp
                FROM scores
                WHERE total_score IS NOT NULL AND age IS NOT NULL
            """
            df = pd.read_sql_query(query, conn)
            
            if len(df) < 100:
                logger.warning(f"Insufficient data ({len(df)} rows). Need at least 100 samples.")
                conn.close()
                return None, None
            
            logger.info(f"Loaded {len(df)} samples from database")
            conn.close()
            
            # Process data (simplified for demonstration)
            # In production, you'd want more sophisticated feature engineering
            return None, None  # Return None to use synthetic data for now
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return None, None
    
    def preprocess_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2,
        val_size: float = 0.1,
    ) -> Dict[str, np.ndarray]:
        """
        Preprocess and split data into train/val/test sets.
        
        Args:
            X: Feature matrix
            y: Labels
            test_size: Proportion for test set
            val_size: Proportion for validation set
            
        Returns:
            Dictionary with train/val/test splits
        """
        logger.info("Preprocessing data...")
        
        # First split: separate test set
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )
        
        # Second split: separate validation set
        val_ratio = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_ratio, random_state=self.random_state, stratify=y_temp
        )
        
        # Fit scaler on training data only
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Validate distribution
        logger.info("-" * 40)
        logger.info(f"DATA SPLIT REPORT")
        logger.info(f"Total Samples: {len(y)}")
        logger.info(f"Training Set:   {len(y_train)} ({len(y_train)/len(y):.1%})")
        logger.info(f"Validation Set: {len(y_val)} ({len(y_val)/len(y):.1%})")
        logger.info(f"Test Set:       {len(y_test)} ({len(y_test)/len(y):.1%})")
        
        # Log class distribution for verification
        unique, counts = np.unique(y_test, return_counts=True)
        test_dist = dict(zip(unique, counts))
        logger.info(f"Test Class Dist: {test_dist} (Stratification Verification)")
        logger.info("-" * 40)
        
        return {
            "X_train": X_train_scaled,
            "X_val": X_val_scaled,
            "X_test": X_test_scaled,
            "y_train": y_train,
            "y_val": y_val,
            "y_test": y_test,
            "X_train_raw": X_train,
            "X_val_raw": X_val,
            "X_test_raw": X_test,
        }
    
    def get_model(self, model_type: str) -> Any:
        """
        Get a model instance based on type.
        
        Args:
            model_type: One of 'rf', 'gb', 'lr', 'svm'
            
        Returns:
            Sklearn model instance
        """
        models = {
            "rf": RandomForestClassifier(random_state=self.random_state),
            "gb": GradientBoostingClassifier(random_state=self.random_state),
            "lr": LogisticRegression(random_state=self.random_state),
            "svm": SVC(probability=True, random_state=self.random_state),
        }
        
        if model_type not in models:
            raise ValueError(f"Unknown model type: {model_type}. Choose from {list(models.keys())}")
        
        return models[model_type]
    
    def train(
        self,
        model_type: str = "rf",
        data: Optional[Dict[str, np.ndarray]] = None,
        hyperparameter_tuning: bool = True,
        quick_mode: bool = False,
        cv_folds: int = 5,
        experiment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Train a model with optional hyperparameter tuning.
        
        Args:
            model_type: Type of model to train
            data: Preprocessed data dict (if None, generates synthetic data)
            hyperparameter_tuning: Whether to perform grid search
            quick_mode: Use reduced parameter grid for faster training
            cv_folds: Number of cross-validation folds
            experiment_name: Name for experiment tracking
            
        Returns:
            Dictionary with training results
        """
        logger.info(f"Starting training with model_type={model_type}, tuning={hyperparameter_tuning}")
        
        # Generate data if not provided
        if data is None:
            X, y = self.generate_synthetic_data()
            data = self.preprocess_data(X, y)
        
        X_train = data["X_train"]
        y_train = data["y_train"]
        X_val = data["X_val"]
        y_val = data["y_val"]
        
        # Start experiment tracking
        exp_name = experiment_name or f"{model_type}_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.versioning_manager:
            param_grid = self.QUICK_PARAM_GRIDS[model_type] if quick_mode else self.PARAM_GRIDS[model_type]
            self.versioning_manager.start_run(
                name=exp_name,
                description=f"Training {model_type.upper()} model for depression risk prediction",
                hyperparameters={"model_type": model_type, "param_grid": param_grid},
                dataset_info={
                    "n_train": len(y_train),
                    "n_val": len(y_val),
                    "n_features": X_train.shape[1],
                    "n_classes": len(self.CLASS_NAMES),
                },
                tags=["soulsense", "depression_risk", model_type],
            )
        
        try:
            # Get base model
            base_model = self.get_model(model_type)
            
            if hyperparameter_tuning:
                # Perform grid search
                param_grid = self.QUICK_PARAM_GRIDS[model_type] if quick_mode else self.PARAM_GRIDS[model_type]
                
                logger.info(f"Performing GridSearchCV with {cv_folds} folds...")
                
                grid_search = GridSearchCV(
                    base_model,
                    param_grid,
                    cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state),
                    scoring="f1_weighted",
                    n_jobs=-1,
                    verbose=1,
                )
                
                grid_search.fit(X_train, y_train)
                
                self.model = grid_search.best_estimator_
                self.best_params = grid_search.best_params_
                
                logger.info(f"Best parameters: {self.best_params}")
                logger.info(f"Best CV score: {grid_search.best_score_:.4f}")
            else:
                # Train with default parameters
                self.model = base_model
                self.model.fit(X_train, y_train)
                self.best_params = {}
            
            # Evaluate on validation set
            y_val_pred = self.model.predict(X_val)
            y_val_proba = self.model.predict_proba(X_val)
            
            val_metrics = self._calculate_metrics(y_val, y_val_pred, y_val_proba)
            
            logger.info(f"Validation metrics: {val_metrics}")
            
            # Log metrics
            if self.versioning_manager:
                self.versioning_manager.log_metrics({f"val_{k}": v for k, v in val_metrics.items()})
            
            self.metrics = {
                "model_type": model_type,
                "best_params": self.best_params,
                "validation": val_metrics,
            }
            
            return {
                "model": self.model,
                "scaler": self.scaler,
                "metrics": self.metrics,
                "best_params": self.best_params,
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            if self.versioning_manager:
                self.versioning_manager.fail_run(str(e))
            raise
    
    def evaluate(
        self,
        data: Dict[str, np.ndarray],
        save_artifacts: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate the trained model on test data.
        
        Args:
            data: Preprocessed data dict
            save_artifacts: Whether to save evaluation artifacts
            
        Returns:
            Dictionary with evaluation results
        """
        if self.model is None:
            raise ValueError("No model trained. Call train() first.")
        
        logger.info("Evaluating model on test set...")
        
        X_test = data["X_test"]
        y_test = data["y_test"]
        
        # Make predictions
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)
        
        # Calculate metrics
        test_metrics = self._calculate_metrics(y_test, y_pred, y_proba)
        
        logger.info(f"Test metrics: {test_metrics}")
        
        # Generate classification report
        report = classification_report(y_test, y_pred, target_names=self.CLASS_NAMES)
        logger.info(f"\nClassification Report:\n{report}")
        
        # Generate confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        if save_artifacts:
            self._save_evaluation_artifacts(y_test, y_pred, report, cm)
        
        # Log to versioning system if an experiment is active
        if self.versioning_manager:
            has_run = getattr(self.versioning_manager, 'has_active_run', None)
            active = has_run() if callable(has_run) else bool(getattr(self.versioning_manager, '_current_experiment', None))
            if active:
                self.versioning_manager.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})
                try:
                    self.versioning_manager.log_artifact("classification_report", report)
                except Exception:
                    # Non-fatal if artifact logging fails
                    logger.warning("Failed to log classification report artifact")
        
        self.metrics["test"] = test_metrics
        
        return {
            "metrics": test_metrics,
            "classification_report": report,
            "confusion_matrix": cm,
            "predictions": y_pred,
            "probabilities": y_proba,
        }
    
    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: np.ndarray,
    ) -> Dict[str, float]:
        """Calculate evaluation metrics."""
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "f1_weighted": f1_score(y_true, y_pred, average="weighted"),
            "f1_macro": f1_score(y_true, y_pred, average="macro"),
            "precision_weighted": precision_score(y_true, y_pred, average="weighted"),
            "recall_weighted": recall_score(y_true, y_pred, average="weighted"),
        }
        
        # Calculate ROC AUC if possible
        try:
            if len(np.unique(y_true)) > 2:
                metrics["roc_auc"] = roc_auc_score(y_true, y_proba, multi_class="ovr")
            else:
                metrics["roc_auc"] = roc_auc_score(y_true, y_proba[:, 1])
        except Exception:
            pass
        
        return {k: round(v, 4) for k, v in metrics.items()}
    
    def _save_evaluation_artifacts(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        report: str,
        cm: np.ndarray,
    ):
        """Save evaluation artifacts to disk."""
        artifacts_dir = self.output_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save metrics text
        metrics_file = artifacts_dir / f"metrics_{timestamp}.txt"
        with open(metrics_file, "w", encoding="utf-8") as f:
            f.write("SoulSense ML Model Evaluation\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Timestamp: {timestamp}\n\n")
            f.write("Classification Report:\n")
            f.write(report)
            f.write("\n\nConfusion Matrix:\n")
            f.write(str(cm))
        
        logger.info(f"Saved metrics to {metrics_file}")
        
        # Save confusion matrix plot
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            plt.figure(figsize=(10, 8))
            sns.heatmap(
                cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=self.CLASS_NAMES,
                yticklabels=self.CLASS_NAMES,
            )
            plt.title("Confusion Matrix - Depression Risk Prediction")
            plt.ylabel("True Label")
            plt.xlabel("Predicted Label")
            plt.tight_layout()
            
            plot_file = artifacts_dir / f"confusion_matrix_{timestamp}.png"
            plt.savefig(plot_file, dpi=150)
            plt.close()
            
            logger.info(f"Saved confusion matrix plot to {plot_file}")
        except ImportError:
            logger.warning("matplotlib/seaborn not available, skipping plot")
    
    def save_model(
        self,
        description: str = "",
        bump_type: str = "patch",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Save the trained model with versioning.
        
        Args:
            description: Model description
            bump_type: Version bump type ('major', 'minor', 'patch')
            tags: Additional tags
            
        Returns:
            Model version string
        """
        if self.model is None:
            raise ValueError("No model trained. Call train() first.")
        
        logger.info("Saving model...")
        
        # Save with versioning system
        if self.versioning_manager:
            metadata = self.versioning_manager.registry.register_model(
                model=self.model,
                name=self.MODEL_NAME,
                description=description or f"SoulSense predictor trained with {self.metrics.get('model_type', 'unknown')}",
                model_type="classifier",
                framework="sklearn",
                metrics=self.metrics.get("test", self.metrics.get("validation", {})),
                parameters=self.best_params,
                feature_names=self.FEATURE_NAMES,
                class_names=self.CLASS_NAMES,
                tags=tags or ["soulsense", "depression_risk"],
                bump_type=bump_type,
                scaler=self.scaler,
            )
            
            version = metadata.version
            logger.info(f"Model saved with version {version}")
            
            # End the experiment run
            self.versioning_manager.end_run()
            
            return version
        
        # Fallback: save without versioning
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.FEATURE_NAMES,
            "class_names": self.CLASS_NAMES,
            "metrics": self.metrics,
            "best_params": self.best_params,
            "timestamp": datetime.now().isoformat(),
        }
        
        model_file = self.output_dir / "model.pkl"
        joblib.dump(model_data, model_file)
        logger.info(f"Model saved to {model_file}")
        
        return "1.0.0"
    
    def load_model(self, version: Optional[str] = None) -> bool:
        """
        Load a saved model.
        
        Args:
            version: Specific version to load (None for latest)
            
        Returns:
            True if successful
        """
        if self.versioning_manager:
            try:
                model_data, metadata = self.versioning_manager.registry.load_model(
                    self.MODEL_NAME, version
                )
                
                self.model = model_data["model"]
                self.scaler = model_data.get("scaler", StandardScaler())
                
                logger.info(f"Loaded model version {metadata.version}")
                return True
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False
        
        # Fallback
        model_file = self.output_dir / "model.pkl"
        if model_file.exists():
            model_data = joblib.load(model_file)
            self.model = model_data["model"]
            self.scaler = model_data.get("scaler", StandardScaler())
            logger.info(f"Loaded model from {model_file}")
            return True
        
        return False
    
    def cross_validate(
        self,
        model_type: str = "rf",
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        cv_folds: int = 5,
    ) -> Dict[str, Any]:
        """
        Perform cross-validation to get robust performance estimates.
        
        Args:
            model_type: Type of model
            X: Features (if None, generates synthetic data)
            y: Labels
            cv_folds: Number of folds
            
        Returns:
            Dictionary with CV results
        """
        logger.info(f"Performing {cv_folds}-fold cross-validation...")
        
        if X is None or y is None:
            X, y = self.generate_synthetic_data()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Get model
        model = self.get_model(model_type)
        
        # Perform CV
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        
        scoring_metrics = ["accuracy", "f1_weighted", "precision_weighted", "recall_weighted"]
        
        results = {}
        for metric in scoring_metrics:
            scores = cross_val_score(model, X_scaled, y, cv=cv, scoring=metric, n_jobs=-1)
            results[metric] = {
                "mean": round(scores.mean(), 4),
                "std": round(scores.std(), 4),
                "scores": scores.tolist(),
            }
            logger.info(f"{metric}: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
        
        return results
    
    def compare_models(
        self,
        model_types: Optional[List[str]] = None,
        quick_mode: bool = True,
    ) -> pd.DataFrame:
        """
        Compare multiple model types on the same data.
        
        Args:
            model_types: List of model types to compare
            quick_mode: Use quick training mode
            
        Returns:
            DataFrame with comparison results
        """
        if model_types is None:
            model_types = ["rf", "gb", "lr", "svm"]
        
        logger.info(f"Comparing models: {model_types}")
        
        # Generate shared data
        X, y = self.generate_synthetic_data()
        data = self.preprocess_data(X, y)
        
        results = []
        
        for model_type in model_types:
            logger.info(f"\n{'='*50}\nTraining {model_type.upper()}...\n{'='*50}")
            
            try:
                # Create fresh pipeline for each model
                pipeline = MLTrainingPipeline(
                    output_dir=self.output_dir,
                    use_versioning=False,
                    random_state=self.random_state,
                )
                pipeline.scaler = self.scaler
                
                # Train
                train_result = pipeline.train(
                    model_type=model_type,
                    data=data,
                    hyperparameter_tuning=True,
                    quick_mode=quick_mode,
                )
                
                # Evaluate
                eval_result = pipeline.evaluate(data, save_artifacts=False)
                
                results.append({
                    "model_type": model_type,
                    **eval_result["metrics"],
                    "best_params": str(train_result["best_params"]),
                })
                
            except Exception as e:
                logger.error(f"Failed to train {model_type}: {e}")
                results.append({
                    "model_type": model_type,
                    "error": str(e),
                })
        
        # Create comparison DataFrame
        df = pd.DataFrame(results)
        
        # Save comparison
        comparison_file = self.output_dir / "model_comparison.csv"
        df.to_csv(comparison_file, index=False)
        logger.info(f"Saved comparison to {comparison_file}")
        
        print("\n" + "=" * 80)
        print("MODEL COMPARISON RESULTS")
        print("=" * 80)
        print(df.to_string(index=False))
        print("=" * 80)
        
        return df


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="ML Training Pipeline for SoulSense",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Train a Random Forest model:
    python scripts/ml_training_pipeline.py train --model-type rf
    
  Train with full hyperparameter tuning:
    python scripts/ml_training_pipeline.py train --model-type rf --full-search
    
  Compare all model types:
    python scripts/ml_training_pipeline.py compare
    
  Cross-validate a model:
    python scripts/ml_training_pipeline.py cv --model-type gb --folds 10
        """,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Train a model")
    train_parser.add_argument(
        "--model-type", "-m",
        choices=["rf", "gb", "lr", "svm"],
        default="rf",
        help="Model type to train (default: rf)",
    )
    train_parser.add_argument(
        "--full-search",
        action="store_true",
        help="Perform full hyperparameter search (slower)",
    )
    train_parser.add_argument(
        "--no-tuning",
        action="store_true",
        help="Skip hyperparameter tuning",
    )
    train_parser.add_argument(
        "--samples", "-n",
        type=int,
        default=1000,
        help="Number of synthetic samples to generate",
    )
    train_parser.add_argument(
        "--output-dir", "-o",
        default="models/pipeline_output",
        help="Output directory",
    )
    train_parser.add_argument(
        "--bump-type",
        choices=["major", "minor", "patch"],
        default="patch",
        help="Version bump type",
    )
    train_parser.add_argument(
        "--experiment-name",
        help="Name for experiment tracking",
    )
    
    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a saved model")
    eval_parser.add_argument(
        "--model-version", "-v",
        help="Model version to evaluate (default: latest)",
    )
    eval_parser.add_argument(
        "--output-dir", "-o",
        default="models/pipeline_output",
        help="Output directory",
    )
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare multiple models")
    compare_parser.add_argument(
        "--models", "-m",
        nargs="+",
        choices=["rf", "gb", "lr", "svm"],
        help="Models to compare (default: all)",
    )
    compare_parser.add_argument(
        "--full-search",
        action="store_true",
        help="Perform full hyperparameter search",
    )
    compare_parser.add_argument(
        "--output-dir", "-o",
        default="models/pipeline_output",
        help="Output directory",
    )
    
    # Cross-validation command
    cv_parser = subparsers.add_parser("cv", help="Cross-validate a model")
    cv_parser.add_argument(
        "--model-type", "-m",
        choices=["rf", "gb", "lr", "svm"],
        default="rf",
        help="Model type",
    )
    cv_parser.add_argument(
        "--folds", "-k",
        type=int,
        default=5,
        help="Number of CV folds",
    )
    cv_parser.add_argument(
        "--output-dir", "-o",
        default="models/pipeline_output",
        help="Output directory",
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Execute command
    if args.command == "train":
        pipeline = MLTrainingPipeline(output_dir=args.output_dir)
        
        # Generate data
        X, y = pipeline.generate_synthetic_data(n_samples=args.samples)
        data = pipeline.preprocess_data(X, y)
        
        # Train
        pipeline.train(
            model_type=args.model_type,
            data=data,
            hyperparameter_tuning=not args.no_tuning,
            quick_mode=not args.full_search,
            experiment_name=args.experiment_name,
        )
        
        # Evaluate
        pipeline.evaluate(data)
        
        # Save
        version = pipeline.save_model(bump_type=args.bump_type)
        
        print(f"\n✅ Model trained and saved as version {version}")
        
    elif args.command == "evaluate":
        pipeline = MLTrainingPipeline(output_dir=args.output_dir)
        
        if not pipeline.load_model(args.model_version):
            print("❌ Failed to load model")
            return
        
        # Generate test data
        X, y = pipeline.generate_synthetic_data()
        data = pipeline.preprocess_data(X, y)
        
        # Evaluate
        results = pipeline.evaluate(data)
        
        print("\n✅ Evaluation complete")
        print(f"Test Accuracy: {results['metrics']['accuracy']:.4f}")
        print(f"Test F1 Score: {results['metrics']['f1_weighted']:.4f}")
        
    elif args.command == "compare":
        pipeline = MLTrainingPipeline(output_dir=args.output_dir, use_versioning=False)
        
        df = pipeline.compare_models(
            model_types=args.models,
            quick_mode=not args.full_search,
        )
        
        # Find best model
        if "accuracy" in df.columns:
            best_idx = df["accuracy"].idxmax()
            best_model = df.loc[best_idx]
            print(f"\n🏆 Best model: {best_model['model_type'].upper()} (Accuracy: {best_model['accuracy']:.4f})")
        
    elif args.command == "cv":
        pipeline = MLTrainingPipeline(output_dir=args.output_dir, use_versioning=False)
        
        results = pipeline.cross_validate(
            model_type=args.model_type,
            cv_folds=args.folds,
        )
        
        print(f"\n✅ {args.folds}-fold CV complete for {args.model_type.upper()}")
        for metric, values in results.items():
            print(f"  {metric}: {values['mean']:.4f} (+/- {values['std']*2:.4f})")


if __name__ == "__main__":
    main()
