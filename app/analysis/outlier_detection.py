"""Outlier Detection - Statistical methods to identify extreme or inconsistent scores."""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from app.models import Score, User
from sqlalchemy import func

logger = logging.getLogger(__name__)


class OutlierDetector:
    """Outlier detection using multiple statistical methods."""
    
    def __init__(self, threshold: float = 2.5):
        """Initialize with Z-score threshold (default: 2.5)."""
        self.threshold = threshold
        self.outlier_report = {}
    
    # Z-Score: |Z| > threshold
    def detect_outliers_zscore(self, scores: List[float], threshold: Optional[float] = None) -> Dict:
        """Z-score based outlier detection."""
        if threshold is None:
            threshold = self.threshold
            
        if len(scores) < 2:
            return {"outliers": [], "indices": [], "z_scores": [], "method": "zscore"}
        
        scores_array = np.array(scores, dtype=float)
        mean = np.mean(scores_array)
        std_dev = np.std(scores_array)
        
        if std_dev == 0:
            return {"outliers": [], "indices": [], "z_scores": [], "method": "zscore"}
        
        z_scores = np.abs((scores_array - mean) / std_dev)
        # print(f"DEBUG: scores={scores_array}, mean={mean}, std={std_dev}, z_scores={z_scores}, threshold={threshold}")
        outlier_mask = z_scores > threshold
        
        return {
            "outliers": scores_array[outlier_mask].tolist(),
            "indices": np.where(outlier_mask)[0].tolist(),
            "z_scores": z_scores.tolist(),
            "threshold": threshold,
            "mean": float(mean),
            "std_dev": float(std_dev),
            "method": "zscore"
        }
    
    # IQR: Bounds = Q1 ± 1.5*IQR
    def detect_outliers_iqr(self, scores: List[float], iqr_multiplier: float = 1.5) -> Dict:
        """IQR-based outlier detection."""
        if len(scores) < 4:
            return {"outliers": [], "indices": [], "method": "iqr"}
        
        scores_array = np.array(scores, dtype=float)
        q1 = np.percentile(scores_array, 25)
        q3 = np.percentile(scores_array, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr
        
        outlier_mask = (scores_array < lower_bound) | (scores_array > upper_bound)
        
        return {
            "outliers": scores_array[outlier_mask].tolist(),
            "indices": np.where(outlier_mask)[0].tolist(),
            "q1": float(q1),
            "q3": float(q3),
            "iqr": float(iqr),
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "method": "iqr"
        }
    
    # Modified Z-Score: Uses median/MAD for robustness
    def detect_outliers_modified_zscore(self, scores: List[float], threshold: float = 3.5) -> Dict:
        """Modified Z-score detection (robust to skewed data)."""
        if len(scores) < 2:
            return {"outliers": [], "indices": [], "method": "modified-zscore"}
        
        scores_array = np.array(scores, dtype=float)
        median = np.median(scores_array)
        mad = np.median(np.abs(scores_array - median))
        
        if mad == 0:
            return {"outliers": [], "indices": [], "method": "modified-zscore"}
        
        modified_z_scores = 0.6745 * np.abs((scores_array - median) / mad)
        outlier_mask = modified_z_scores > threshold
        
        return {
            "outliers": scores_array[outlier_mask].tolist(),
            "indices": np.where(outlier_mask)[0].tolist(),
            "modified_z_scores": modified_z_scores.tolist(),
            "threshold": threshold,
            "median": float(median),
            "mad": float(mad),
            "method": "modified-zscore"
        }
    
    # MAD: |x - median| > threshold * MAD
    def detect_outliers_mad(self, scores: List[float], threshold: float = 2.5) -> Dict:
        """MAD-based outlier detection."""
        if len(scores) < 2:
            return {"outliers": [], "indices": [], "method": "mad"}
        
        scores_array = np.array(scores, dtype=float)
        median = np.median(scores_array)
        mad = np.median(np.abs(scores_array - median))
        
        if mad == 0:
            return {"outliers": [], "indices": [], "method": "mad"}
        
        deviations = np.abs(scores_array - median)
        outlier_mask = deviations > threshold * mad
        
        return {
            "outliers": scores_array[outlier_mask].tolist(),
            "indices": np.where(outlier_mask)[0].tolist(),
            "deviations": deviations.tolist(),
            "median": float(median),
            "mad": float(mad),
            "threshold": threshold,
            "method": "mad"
        }
    
    # Ensemble: Consensus voting from all methods
    def detect_outliers_ensemble(self, scores: List[float], 
                                consensus_threshold: float = 0.5) -> Dict:
        """Consensus-based outlier detection."""
        if len(scores) < 2:
            return {"outliers": [], "indices": [], "methods_used": [], "method": "ensemble"}
        
        results = {
            "zscore": self.detect_outliers_zscore(scores),
            "iqr": self.detect_outliers_iqr(scores),
            "modified_zscore": self.detect_outliers_modified_zscore(scores),
            "mad": self.detect_outliers_mad(scores)
        }
        
        # Create voting matrix
        num_scores = len(scores)
        votes = np.zeros(num_scores)
        
        for method_name, method_result in results.items():
            for idx in method_result.get("indices", []):
                votes[idx] += 1
        
        # Find consensus outliers
        num_methods = len(results)
        consensus_votes_needed = int(np.ceil(num_methods * consensus_threshold))
        consensus_mask = votes >= consensus_votes_needed
        
        scores_array = np.array(scores, dtype=float)
        
        return {
            "outliers": scores_array[consensus_mask].tolist(),
            "indices": np.where(consensus_mask)[0].tolist(),
            "votes": votes.tolist(),
            "consensus_threshold": consensus_threshold,
            "methods_used": list(results.keys()),
            "individual_results": results,
            "method": "ensemble"
        }
    
    # Database methods
    def detect_outliers_for_user(self, session: Session, username: str, 
                                 method: str = "ensemble") -> Dict:
        """User-level outlier detection."""
        try:
            scores_query = session.query(Score).filter(
                Score.username == username
            ).order_by(Score.timestamp).all()
            
            if not scores_query:
                logger.warning(f"No scores found for user: {username}")
                return {"error": f"No scores found for user: {username}"}
            
            scores = [score.total_score for score in scores_query]
            score_ids = [score.id for score in scores_query]
            
            # Detect outliers using specified method
            if method == "zscore":
                result = self.detect_outliers_zscore(scores)
            elif method == "iqr":
                result = self.detect_outliers_iqr(scores)
            elif method == "modified_zscore":
                result = self.detect_outliers_modified_zscore(scores)
            elif method == "mad":
                result = self.detect_outliers_mad(scores)
            elif method == "ensemble":
                result = self.detect_outliers_ensemble(scores)
            else:
                result = self.detect_outliers_ensemble(scores)
            
            # Map indices to score IDs and timestamps
            outlier_indices = result.get("indices", [])
            outlier_details = []
            
            for idx in outlier_indices:
                score_obj = scores_query[idx]
                outlier_details.append({
                    "score_id": score_obj.id,
                    "score_value": score_obj.total_score,
                    "age": score_obj.age,
                    "age_group": score_obj.detailed_age_group,
                    "timestamp": score_obj.timestamp
                })
            
            return {
                "username": username,
                "total_scores": len(scores),
                "outlier_count": len(outlier_indices),
                "detection_method": method,
                "outlier_details": outlier_details,
                **result
            }
            
        except Exception as e:
            logger.error(f"Error detecting outliers for user {username}: {e}")
            return {"error": str(e)}
    
    def detect_outliers_by_age_group(self, session: Session, age_group: str,
                                    method: str = "ensemble") -> Dict:
        """Age group-level outlier detection."""
        try:
            scores_query = session.query(Score).filter(
                Score.detailed_age_group == age_group
            ).order_by(Score.timestamp).all()
            
            if not scores_query:
                logger.warning(f"No scores found for age group: {age_group}")
                return {"error": f"No scores found for age group: {age_group}"}
            
            scores = [score.total_score for score in scores_query]
            
            # Detect outliers
            if method == "zscore":
                result = self.detect_outliers_zscore(scores)
            elif method == "iqr":
                result = self.detect_outliers_iqr(scores)
            elif method == "modified_zscore":
                result = self.detect_outliers_modified_zscore(scores)
            elif method == "mad":
                result = self.detect_outliers_mad(scores)
            else:
                result = self.detect_outliers_ensemble(scores)
            
            # Map indices to score objects
            outlier_indices = result.get("indices", [])
            outlier_details = []
            
            for idx in outlier_indices:
                score_obj = scores_query[idx]
                outlier_details.append({
                    "score_id": score_obj.id,
                    "username": score_obj.username,
                    "score_value": score_obj.total_score,
                    "age": score_obj.age,
                    "timestamp": score_obj.timestamp
                })
            
            return {
                "age_group": age_group,
                "total_scores": len(scores),
                "outlier_count": len(outlier_indices),
                "detection_method": method,
                "outlier_details": outlier_details,
                "statistics": {
                    "mean_score": float(np.mean(scores)),
                    "median_score": float(np.median(scores)),
                    "std_dev": float(np.std(scores)),
                    "min_score": float(np.min(scores)),
                    "max_score": float(np.max(scores))
                },
                **result
            }
            
        except Exception as e:
            logger.error(f"Error detecting outliers for age group {age_group}: {e}")
            return {"error": str(e)}
    
    def detect_outliers_global(self, session: Session, method: str = "ensemble") -> Dict:
        """System-wide outlier detection."""
        try:
            scores_query = session.query(Score).order_by(Score.timestamp).all()
            
            if not scores_query:
                logger.warning("No scores found in database")
                return {"error": "No scores found in database"}
            
            scores = [score.total_score for score in scores_query]
            
            # Detect outliers
            if method == "zscore":
                result = self.detect_outliers_zscore(scores)
            elif method == "iqr":
                result = self.detect_outliers_iqr(scores)
            elif method == "modified_zscore":
                result = self.detect_outliers_modified_zscore(scores)
            elif method == "mad":
                result = self.detect_outliers_mad(scores)
            else:
                result = self.detect_outliers_ensemble(scores)
            
            # Map indices to score objects
            outlier_indices = result.get("indices", [])
            outlier_details = []
            
            for idx in outlier_indices:
                score_obj = scores_query[idx]
                outlier_details.append({
                    "score_id": score_obj.id,
                    "username": score_obj.username,
                    "score_value": score_obj.total_score,
                    "age": score_obj.age,
                    "age_group": score_obj.detailed_age_group,
                    "timestamp": score_obj.timestamp
                })
            
            return {
                "scope": "global",
                "total_scores": len(scores),
                "outlier_count": len(outlier_indices),
                "detection_method": method,
                "outlier_details": outlier_details,
                "statistics": {
                    "mean_score": float(np.mean(scores)),
                    "median_score": float(np.median(scores)),
                    "std_dev": float(np.std(scores)),
                    "min_score": float(np.min(scores)),
                    "max_score": float(np.max(scores))
                },
                **result
            }
            
        except Exception as e:
            logger.error(f"Error detecting global outliers: {e}")
            return {"error": str(e)}
    
    def detect_inconsistency_patterns(self, session: Session, username: str,
                                     time_window_days: int = 30) -> Dict:
        """Detect scoring inconsistency over time window."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            scores_query = session.query(Score).filter(
                Score.username == username,
                Score.timestamp >= cutoff_date.isoformat()
            ).order_by(Score.timestamp).all()
            
            if len(scores_query) < 2:
                return {
                    "username": username,
                    "error": f"Insufficient scores in the last {time_window_days} days"
                }
            
            scores = [score.total_score for score in scores_query]
            
            # Calculate score differences (variability)
            score_diffs = np.diff(scores)
            mean_diff = np.mean(np.abs(score_diffs))
            std_diff = np.std(np.abs(score_diffs))
            
            # Identify inconsistent changes
            inconsistent_indices = []
            for i, diff in enumerate(score_diffs):
                if np.abs(diff) > mean_diff + 2 * std_diff:
                    inconsistent_indices.append(i)
            
            # Calculate coefficient of variation
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            cv = (std_score / mean_score * 100) if mean_score != 0 else 0
            
            inconsistency_details = []
            for idx in inconsistent_indices:
                inconsistency_details.append({
                    "between_scores": [scores[idx], scores[idx + 1]],
                    "change": scores[idx + 1] - scores[idx],
                    "timestamp_1": scores_query[idx].timestamp,
                    "timestamp_2": scores_query[idx + 1].timestamp
                })
            
            return {
                "username": username,
                "time_window_days": time_window_days,
                "total_scores_in_window": len(scores),
                "inconsistent_transitions": len(inconsistent_indices),
                "mean_change": float(mean_diff),
                "std_change": float(std_diff),
                "coefficient_of_variation": float(cv),
                "inconsistency_details": inconsistency_details,
                "is_highly_inconsistent": cv > 30  # CV > 30% indicates high variability
            }
            
        except Exception as e:
            logger.error(f"Error analyzing inconsistency patterns for {username}: {e}")
            return {"error": str(e)}
    
    def get_statistical_summary(self, session: Session, age_group: Optional[str] = None) -> Dict:
        """Get statistical summary."""
        try:
            if age_group:
                query = session.query(Score).filter(Score.detailed_age_group == age_group)
            else:
                query = session.query(Score)
            
            scores = [score.total_score for score in query.all()]
            
            if not scores:
                return {"error": "No scores found"}
            
            return {
                "scope": f"age_group_{age_group}" if age_group else "global",
                "count": len(scores),
                "mean": float(np.mean(scores)),
                "median": float(np.median(scores)),
                "std_dev": float(np.std(scores)),
                "min": float(np.min(scores)),
                "max": float(np.max(scores)),
                "q1": float(np.percentile(scores, 25)),
                "q3": float(np.percentile(scores, 75)),
                "iqr": float(np.percentile(scores, 75) - np.percentile(scores, 25))
            }
            
        except Exception as e:
            logger.error(f"Error getting statistical summary: {e}")
            return {"error": str(e)}


# Create singleton instance
outlier_detector = OutlierDetector()
