"""Integration example: Using outlier detection in the main application."""

import logging
from typing import Dict, List, Optional
from app.db import get_session
from app.models import Score, User
from app.analysis.outlier_detection import OutlierDetector

logger = logging.getLogger(__name__)


class ScoreAnalyzer:
    """Integrates outlier detection with score analysis."""
    
    def __init__(self):
        """Initialize the score analyzer with outlier detector."""
    
    def validate_user_score(self, username: str, score_value: int, 
                           age: int, age_group: str) -> Dict:
        """Validate new score against user history.

        Args:
            username (str): Username to validate score for.
            score_value (int): New score value to validate.
            age (int): User's age.
            age_group (str): User's age group.

        Returns:
            Dict: Validation result with validity, warnings, and details.
        """
        session = get_session()
        try:
            # Get user's historical scores
            historical_scores = session.query(Score).filter(
                Score.username == username
            ).all()
            
            if not historical_scores:
                return {
                    "valid": True,
                    "warnings": [],
                    "message": "First score - no historical comparison available"
                }
            
            historical_values = [s.total_score for s in historical_scores]
            
            warnings = []
            
            # Check if new score would be statistical outlier
            all_scores = historical_values + [score_value]
            result = self.detector.detect_outliers_zscore(all_scores)
            
            if score_value in result["outliers"]:
                warnings.append({
                    "type": "statistical_outlier",
                    "severity": "medium",
                    "message": f"Score {score_value} is statistically unusual compared to user's history"
                })
            
            # Check for extreme change from last score
            last_score = historical_values[-1]
            change = abs(score_value - last_score)
            avg_change = self._calculate_average_change(historical_values)
            
            if change > 3 * avg_change:
                warnings.append({
                    "type": "extreme_change",
                    "severity": "high",
                    "message": f"Score change of {change} is much higher than usual ({avg_change:.1f})"
                })
            
            return {
                "valid": len(warnings) == 0 or all(w["severity"] != "critical" for w in warnings),
                "warnings": warnings,
                "validation_details": {
                    "user_history_count": len(historical_values),
                    "historical_mean": sum(historical_values) / len(historical_values),
                    "historical_std": self._calculate_std(historical_values),
                    "change_from_last": score_value - last_score
                }
            }
        
        finally:
            session.close()
    
    def get_score_analytics(self, username: str) -> Dict:
        """Get comprehensive score analytics with outlier analysis.

        Args:
            username (str): Username to get analytics for.

        Returns:
            Dict: Analytics including score statistics, outliers, and quality assessment.
        """
        session = get_session()
        try:
            scores = session.query(Score).filter(
                Score.username == username
            ).order_by(Score.timestamp).all()
            
            if not scores:
                return {"error": "No scores found"}
            
            score_values = [s.total_score for s in scores]
            
            # Outlier detection
            outlier_result = self.detector.detect_outliers_ensemble(score_values)
            
            # Inconsistency analysis
            inconsistency = self.detector.detect_inconsistency_patterns(
                session, username
            )
            
            return {
                "username": username,
                "total_scores": len(score_values),
                "score_range": {
                    "min": min(score_values),
                    "max": max(score_values),
                    "mean": sum(score_values) / len(score_values)
                },
                "outlier_analysis": {
                    "outlier_count": len(outlier_result["outliers"]),
                    "outlier_percentage": (len(outlier_result["outliers"]) / len(score_values)) * 100,
                    "outliers": outlier_result["outliers"]
                },
                "consistency_analysis": {
                    "coefficient_of_variation": inconsistency.get("coefficient_of_variation", 0),
                    "is_highly_inconsistent": inconsistency.get("is_highly_inconsistent", False),
                    "inconsistent_transitions": inconsistency.get("inconsistent_transitions", 0)
                },
                "quality_assessment": self._assess_score_quality(
                    outlier_result, inconsistency, score_values
                )
            }
        
        finally:
            session.close()
    
    def get_cohort_analytics(self, age_group: str) -> Dict:
        """Get analytics for an age group cohort.

        Args:
            age_group (str): Age group to analyze.

        Returns:
            Dict: Cohort analytics including statistics and data quality.
        """
        session = get_session()
        try:
            scores = session.query(Score).filter(
                Score.detailed_age_group == age_group
            ).all()
            
            if not scores:
                return {"error": f"No scores found for age group {age_group}"}
            
            score_values = [s.total_score for s in scores]
            
            # Outlier analysis
            outlier_result = self.detector.detect_outliers_by_age_group(
                session, age_group, method="ensemble"
            )
            
            return {
                "age_group": age_group,
                "participant_count": len(scores),
                "score_statistics": {
                    "mean": sum(score_values) / len(score_values),
                    "median": sorted(score_values)[len(score_values) // 2],
                    "std_dev": self._calculate_std(score_values),
                    "range": [min(score_values), max(score_values)]
                },
                "data_quality": {
                    "outlier_count": outlier_result.get("outlier_count", 0),
                    "outlier_percentage": (outlier_result.get("outlier_count", 0) / len(score_values)) * 100,
                    "is_acceptable": (outlier_result.get("outlier_count", 0) / len(score_values)) < 0.15
                },
                "outlier_details": outlier_result.get("outlier_details", [])
            }
        
        finally:
            session.close()
    
    def generate_quality_report(self) -> Dict:
        """Generate overall data quality report.

        Returns:
            Dict: Comprehensive quality report for all data.
        """
        session = get_session()
        try:
            all_scores = session.query(Score).all()
            score_values = [s.total_score for s in all_scores]
            
            if not score_values:
                return {"error": "No scores in database"}
            
            outlier_result = self.detector.detect_outliers_global(
                session, method="ensemble"
            )
            
            age_groups = session.query(Score.detailed_age_group).distinct().all()
            
            return {
                "report_type": "data_quality",
                "total_scores": len(score_values),
                "global_outlier_percentage": (outlier_result.get("outlier_count", 0) / len(score_values)) * 100,
                "quality_assessment": self._assess_global_quality(
                    outlier_result, score_values
                ),
                "cohort_summary": [
                    self.get_cohort_analytics(ag[0]) 
                    for ag in age_groups if ag[0]
                ]
            }
        
        finally:
            session.close()
    
    # Helper methods
    
    def _calculate_average_change(self, values: List[int]) -> float:
        """Calculate average absolute change between consecutive values.

        Args:
            values (List[int]): List of values.

        Returns:
            float: Average absolute change.
        """
        if len(values) < 2:
            return 0
        
        changes = [abs(values[i+1] - values[i]) for i in range(len(values)-1)]
        return sum(changes) / len(changes)
    
    def _calculate_std(self, values: List[int]) -> float:
        """Calculate standard deviation.

        Args:
            values (List[int]): List of values.

        Returns:
            float: Standard deviation.
        """
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _assess_score_quality(self, outlier_result: Dict, 
                             inconsistency: Dict, scores: List[int]) -> Dict:
        """Assess overall quality of a user's scores.

        Args:
            outlier_result (Dict): Outlier detection results.
            inconsistency (Dict): Inconsistency analysis results.
            scores (List[int]): List of score values.

        Returns:
            Dict: Quality assessment with score, rating, and issues.
        """
        
        outlier_percentage = len(outlier_result["outliers"]) / len(scores) * 100
        cv = inconsistency.get("coefficient_of_variation", 0)
        
        quality_score = 100
        issues = []
        
        # Outlier assessment
        if outlier_percentage > 15:
            quality_score -= 30
            issues.append("High percentage of outliers")
        elif outlier_percentage > 10:
            quality_score -= 15
            issues.append("Moderate outlier count")
        
        # Consistency assessment
        if cv > 50:
            quality_score -= 20
            issues.append("Very high scoring variability")
        elif cv > 30:
            quality_score -= 10
            issues.append("High scoring variability")
        
        return {
            "quality_score": max(0, quality_score),
            "rating": self._rate_quality(quality_score),
            "issues": issues if issues else ["None - data looks good"]
        }
    
    def _assess_global_quality(self, outlier_result: Dict, 
                               scores: List[int]) -> str:
        """Assess global data quality.

        Args:
            outlier_result (Dict): Global outlier detection results.
            scores (List[int]): All score values.

        Returns:
            str: Quality rating string.
        """
        
        outlier_percentage = (outlier_result.get("outlier_count", 0) / len(scores)) * 100
        
        if outlier_percentage < 5:
            return "Excellent"
        elif outlier_percentage < 10:
            return "Good"
        elif outlier_percentage < 15:
            return "Acceptable"
        else:
            return "Poor - Review data collection"
    
    def _rate_quality(self, score: float) -> str:
        """Rate quality based on score.

        Args:
            score (float): Quality score.

        Returns:
            str: Quality rating.
        """
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Acceptable"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    analyzer = ScoreAnalyzer()
    
    # Example 1: Validate a new score
    print("\n=== Score Validation Example ===")
    validation = analyzer.validate_user_score(
        username="john_doe",
        score_value=150,
        age=25,
        age_group="18-25"
    )
    print(f"Valid: {validation['valid']}")
    print(f"Warnings: {validation['warnings']}")
    
    # Example 2: Get user analytics
    print("\n=== User Analytics Example ===")
    user_analytics = analyzer.get_score_analytics("john_doe")
    if "error" not in user_analytics:
        print(f"Total Scores: {user_analytics['total_scores']}")
        print(f"Outliers: {user_analytics['outlier_analysis']['outlier_count']}")
        print(f"Quality: {user_analytics['quality_assessment']['rating']}")
    
    # Example 3: Get cohort analytics
    print("\n=== Cohort Analytics Example ===")
    cohort_analytics = analyzer.get_cohort_analytics("18-25")
    if "error" not in cohort_analytics:
        print(f"Participants: {cohort_analytics['participant_count']}")
        print(f"Data Quality: {cohort_analytics['data_quality']['is_acceptable']}")
    
    # Example 4: Generate quality report
    print("\n=== Quality Report Example ===")
    report = analyzer.generate_quality_report()
    if "error" not in report:
        print(f"Total Scores: {report['total_scores']}")
        print(f"Global Quality: {report['quality_assessment']}")
