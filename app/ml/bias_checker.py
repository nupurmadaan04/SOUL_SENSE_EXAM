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
        from app.config import DB_PATH
        self.db_path = db_path if db_path is not None else DB_PATH
    
    def check_age_bias(self):
        """Simple check: Are scores different across age groups?"""
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
        """Check if questions have similar average responses across ages"""
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
        """Generate a simple bias report"""
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
    """Quick one-line bias check"""
    checker = SimpleBiasChecker()
    return checker.check_age_bias()
