"""
Simple Bias Checker for SOUL_SENSE_EXAM
Checks for age bias in test scores
"""

import sqlite3
import json
import os
from datetime import datetime

class SimpleBiasChecker:
    def __init__(self, db_path=None):
        """Initialize the SimpleBiasChecker.

        Args:
            db_path (str, optional): Path to the database file. If None, uses the default DB_PATH from config.
        """
        from app.config import DB_PATH
        self.db_path = db_path if db_path is not None else DB_PATH
    
    def check_age_bias(self):
        """Check for age bias in test scores by comparing averages across age groups.

        Analyzes the database to determine if there are significant differences in average
        scores between different age groups, which could indicate bias.

        Returns:
            dict: A dictionary containing the analysis results with the following keys:
                - status (str): 'ok', 'potential_bias', 'insufficient_data', or 'error'
                - message (str): Human-readable message about the results
                - issues (list, optional): List of bias issues found
                - overall_avg (float, optional): Overall average score
                - details (list, optional): Detailed statistics per age group

        Raises:
            No explicit exceptions raised; errors are caught and returned in the dict.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get average scores by age group
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN age < 18 THEN 'Under 18'
                        WHEN age BETWEEN 18 AND 25 THEN '18-25'
                        WHEN age BETWEEN 26 AND 35 THEN '26-35'
                        WHEN age BETWEEN 36 AND 50 THEN '36-50'
                        WHEN age BETWEEN 51 AND 65 THEN '51-65'
                        WHEN age > 65 THEN '65+'
                        ELSE 'Unknown'
                    END as age_group,
                    COUNT(*) as count,
                    AVG(total_score) as avg_score,
                    MIN(total_score) as min_score,
                    MAX(total_score) as max_score
                FROM scores 
                WHERE age IS NOT NULL
                GROUP BY age_group
                HAVING count >= 5  -- Only show groups with enough data
                ORDER BY avg_score DESC
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            if len(results) < 2:
                return {"status": "insufficient_data", "message": "Need more data from different age groups"}
            
            # Simple bias detection: Check if any group is 20% below others
            avg_scores = [r[2] for r in results if r[1] >= 5]  # r[2] is avg_score
            if len(avg_scores) < 2:
                return {"status": "ok", "message": "Not enough data yet"}
            
            overall_avg = sum(avg_scores) / len(avg_scores)
            bias_issues = []
            
            for row in results:
                age_group, count, avg_score = row[0], row[1], row[2]
                if count >= 5:
                    diff_percent = ((avg_score - overall_avg) / overall_avg) * 100
                    if diff_percent < -20:  # 20% below average
                        bias_issues.append(f"{age_group}: {avg_score:.1f} ({(diff_percent):+.1f}%)")
            
            if bias_issues:
                return {
                    "status": "potential_bias",
                    "message": "Possible age bias detected",
                    "issues": bias_issues,
                    "overall_avg": overall_avg,
                    "details": [{"group": r[0], "count": r[1], "avg": r[2]} for r in results]
                }
            
            return {
                "status": "ok", 
                "message": "No significant bias detected",
                "overall_avg": overall_avg,
                "details": [{"group": r[0], "count": r[1], "avg": r[2]} for r in results]
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_question_fairness(self):
        """Check if questions have similar average responses across age groups.

        Analyzes individual questions to see if younger and older respondents
        give significantly different average responses, which could indicate
        question bias or fairness issues.

        Returns:
            dict: A dictionary containing the analysis results with the following keys:
                - status (str): 'ok' or 'error'
                - biased_questions (list): List of questions with significant differences
                - total_questions_checked (int): Number of questions analyzed

        Raises:
            No explicit exceptions raised; errors are caught and returned in the dict.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    question_id,
                    CASE 
                        WHEN age < 35 THEN 'Younger'
                        WHEN age >= 35 THEN 'Older'
                        ELSE 'Unknown'
                    END as age_category,
                    AVG(response_value) as avg_response,
                    COUNT(*) as count
                FROM responses r
                JOIN scores s ON r.username = s.username 
                    AND DATE(r.timestamp) = DATE(s.timestamp)
                WHERE age IS NOT NULL 
                    AND age_category IN ('Younger', 'Older')
                GROUP BY question_id, age_category
                HAVING count >= 3
                ORDER BY question_id, age_category
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            # Group by question
            question_data = {}
            for row in results:
                qid, age_cat, avg_resp, count = row
                if qid not in question_data:
                    question_data[qid] = {}
                question_data[qid][age_cat] = {"avg": avg_resp, "count": count}
            
            # Find questions with big differences
            biased_questions = []
            for qid, data in question_data.items():
                if 'Younger' in data and 'Older' in data:
                    diff = abs(data['Younger']['avg'] - data['Older']['avg'])
                    if diff > 1.0:  # More than 1 point difference on 1-4 scale
                        biased_questions.append({
                            "question_id": qid,
                            "younger_avg": data['Younger']['avg'],
                            "older_avg": data['Older']['avg'],
                            "difference": diff
                        })
            
            return {
                "status": "ok",
                "biased_questions": biased_questions,
                "total_questions_checked": len(question_data)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def generate_bias_report(self):
        """Generate a comprehensive bias report and save it to a file.

        Combines age bias and question fairness analyses into a single report,
        saves it as a JSON file in the reports directory, and returns the data.

        Returns:
            dict: The complete bias report containing timestamp, age bias analysis,
                  and question fairness analysis.

        Raises:
            OSError: If unable to create the reports directory or write the file.
        """
        age_bias = self.check_age_bias()
        question_bias = self.check_question_fairness()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "age_bias_analysis": age_bias,
            "question_fairness_analysis": question_bias
        }
        
        # Save report
        os.makedirs("reports", exist_ok=True)
        report_file = f"reports/bias_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

# Simple standalone function
def quick_bias_check():
    """Perform a quick bias check on test scores.

    Creates a SimpleBiasChecker instance and runs the age bias check.

    Returns:
        dict: The result of the age bias check, containing status and analysis details.
    """
    checker = SimpleBiasChecker()
    return checker.check_age_bias()
