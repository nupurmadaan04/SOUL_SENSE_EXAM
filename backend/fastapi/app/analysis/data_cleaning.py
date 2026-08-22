"""
Data cleaning utilities for SoulSense EQ assessment data.

This module provides comprehensive data validation and cleaning functions
to ensure data quality for ML models and analysis. It handles common data
issues like missing values, invalid formats, and outliers while maintaining
data integrity and logging problematic cases.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DataCleaner:
    """
    Pipeline for cleaning and validating SoulSense data.
    
    This class provides static methods to:
    - Validate and sanitize individual data points (age, scores)
    - Clean complete input sets for ML predictions
    - Process pandas DataFrames for training data preparation
    
    All methods include logging for data quality monitoring and handle
    edge cases gracefully with appropriate defaults or None returns.
    """
    
    @staticmethod
    def clean_age(age):
        """
        Validate and clip age to realistic bounds (5-120).
        Returns None if invalid/missing and cannot be fixed.
        """
        # Handle missing or empty age inputs
        if age is None or str(age).strip() == "":
            logger.warning("Age input is missing or empty")
            return None
        
        # Convert to integer, handling float strings like "25.0"
        try:
            age = int(float(age)) # Handle "25.0" string
        except (ValueError, TypeError):
            logger.warning(f"Invalid age format: {age}")
            return None
            
        # Clip unrealistic age values to reasonable bounds
        if age < 5:
            logger.warning(f"Age {age} too low, clipping to 5")
            return 5
        if age > 120:
            logger.warning(f"Age {age} too high, clipping to 120")
            return 120
            
        return age

    @staticmethod
    def clean_score(score, max_possible=None):
        """
        Ensure score is non-negative and optionally within max bounds.
        """
        # Handle missing scores by defaulting to 0
        if score is None:
            return 0
            
        # Convert to integer, handling various numeric formats
        try:
            score = int(float(score))
        except (ValueError, TypeError):
            logger.warning(f"Invalid score format: {score}")
            return 0
            
        # Ensure non-negative scores (negative scores don't make sense)
        if score < 0:
            logger.warning(f"Negative score {score} detected, setting to 0")
            return 0
            
        # Clip scores that exceed maximum possible value if specified
        if max_possible and score > max_possible:
            logger.warning(f"Score {score} exceeds max {max_possible}, clipping")
            return max_possible
            
        return score

    @staticmethod
    def clean_inputs(q_scores, age, total_score):
        """
        Clean a full set of inputs for prediction.
        Returns cleaned (q_scores, age, total_score)
        """
        # Clean age with fallback to reasonable default if invalid
        clean_age = DataCleaner.clean_age(age)
        if clean_age is None:
            clean_age = 25 # Default fallback for missing/invalid age
            
        # Clean total score with maximum bound (25 questions * 5 max per question = 125)
        clean_total = DataCleaner.clean_score(total_score, max_possible=125) # 25 questions * 5
        
        # Clean individual question scores, ensuring each is within 1-5 range
        clean_q_scores = []
        if q_scores:
            clean_q_scores = [DataCleaner.clean_score(s, 5) for s in q_scores]
        
        return clean_q_scores, clean_age, clean_total

    @staticmethod
    def clean_dataframe(df):
        """
        Apply cleaning rules to a pandas DataFrame (e.g. for ML training).
        """
        if df is None or df.empty:
            logger.warning("Empty dataframe provided for cleaning")
            return df
            
        # 1. Drop duplicates
        initial_len = len(df)
        df = df.drop_duplicates()
        if len(df) < initial_len:
            logger.info(f"Dropped {initial_len - len(df)} duplicate rows")

        # 2. Clean Age
        if 'age' in df.columns:
            # Convert age column to numeric, coercing invalid values to NaN
            df['age'] = pd.to_numeric(df['age'], errors='coerce')
            
            # Impute missing ages with median value (robust to outliers)
            median_age = df['age'].median()
            if pd.isna(median_age):
                median_age = 30 # Fallback median if all ages are missing
                
            df['age'] = df['age'].fillna(median_age)
            
            # Clip age values to realistic bounds (5-120 years)
            df['age'] = df['age'].clip(lower=5, upper=120)

        # 3. Clean Scores
        if 'total_score' in df.columns:
            # Convert to numeric, handling invalid formats
            df['total_score'] = pd.to_numeric(df['total_score'], errors='coerce')
            # Fill missing scores with 0 and ensure non-negative values
            df['total_score'] = df['total_score'].fillna(0).clip(lower=0)
            
        logger.info("Dataframe cleaning complete")
        return df

if __name__ == "__main__":
    # Self-test section to validate cleaning functions with edge cases
    print("Testing DataCleaner...")
    print(f"Clean Age (150): {DataCleaner.clean_age(150)}")
    print(f"Clean Age (-5): {DataCleaner.clean_age(-5)}")
    print(f"Clean Age ('abc'): {DataCleaner.clean_age('abc')}")
    print(f"Clean Score (10, 5): {DataCleaner.clean_score(10, 5)}")
